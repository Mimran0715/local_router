"""Slice test: run ONE (task, route) job step by step, with verbose output.

Use this to debug the harness before running the full loop in main.py.

    python slice_test.py                            # first easy task on local_small
    python slice_test.py --task t05 --route ollama_cloud
    python slice_test.py --keep                     # leave the worktree for inspection
    python slice_test.py --skip-baseline            # skip the "verifier fails before edit" check

Results go to slice_results.jsonl, NOT results.jsonl, so slice runs never
mark real jobs as done.
"""
import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

import backend
from git_utils import commit_result, create_worktree, git, remove_worktree
from main import REPOS  # task `repo` field -> local clone path
from router import load_routes
from task import load_tasks


def tail(text: str, n: int = 15) -> str:
    lines = (text or "").strip().splitlines()
    return "\n".join(lines[-n:]) if lines else "(empty)"


def status(wt: Path) -> set:
    """Set of `git status --porcelain` lines (tracked changes and untracked files)."""
    out = git("status", "--porcelain", "--untracked-files=all", cwd=wt).stdout
    return set(out.splitlines())


def ollama_models(api_base: str):
    """Return the set of model names the Ollama server lists, or None if unreachable."""
    try:
        with urllib.request.urlopen(f"{api_base.rstrip('/')}/api/tags", timeout=5) as r:
            return {m["name"] for m in json.load(r).get("models", [])}
    except (urllib.error.URLError, OSError, ValueError):
        return None


def preflight(task, cfg, repo: Path) -> bool:
    ok = True

    def check(label: str, cond: bool, detail: str = ""):
        nonlocal ok
        print(f"  [{'ok' if cond else 'FAIL'}] {label}" + (f" ({detail})" if detail else ""))
        ok = ok and cond

    check("repo path exists", repo.exists(), str(repo))
    if repo.exists():
        r = git("cat-file", "-e", f"{task.base_commit}^{{commit}}", cwd=repo, check=False)
        check("base_commit exists in repo", r.returncode == 0, task.base_commit[:7])

    kind = cfg["kind"]
    if kind == "ollama":
        check("aider on PATH", shutil.which("aider") is not None)
        models = ollama_models(cfg["api_base"])
        check("Ollama server reachable", models is not None, cfg["api_base"])
        if models is not None:
            name = cfg["model"].split("/", 1)[-1]
            if name in models:
                print(f"  [ok] model '{name}' is listed")
            else:
                print(f"  [warn] model '{name}' not listed by /api/tags "
                      "(local models need `ollama pull`; cloud tags may not appear)")
    elif kind == "codex_cli":
        check("codex on PATH", shutil.which("codex") is not None)
    else:
        check(f"known backend kind '{kind}'", False)
    return ok


def pick_task(tasks, task_id):
    if task_id:
        for t in tasks:
            if t.task_id == task_id:
                return t
        sys.exit(f"No task with task_id '{task_id}'")
    for t in tasks:
        if t.difficulty == "easy":
            return t
    sys.exit("No easy task found; pass --task")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", help="task_id to run (default: first easy task)")
    ap.add_argument("--route", default="local_small", help="backend name from models.yaml")
    ap.add_argument("--tasks", default="eval/tasks.json", help="path to the tasks file")
    ap.add_argument("--keep", action="store_true", help="keep the worktree instead of removing it")
    ap.add_argument("--skip-baseline", action="store_true",
                    help="skip running the verifier on the untouched checkout")
    args = ap.parse_args()

    tasks = load_tasks(args.tasks)
    print(f"Loaded {len(tasks)} tasks: {dict(Counter(t.difficulty for t in tasks))}")

    routes = load_routes()
    if args.route not in routes:
        sys.exit(f"Unknown route '{args.route}'. Available: {', '.join(routes)}")
    cfg = routes[args.route]

    task = pick_task(tasks, args.task)
    repo = REPOS.get(task.repo)
    if repo is None:
        sys.exit(f"No entry in REPOS for repo '{task.repo}'")

    print(f"\n== {task.task_id} [{task.difficulty}] on route '{args.route}' ({task.repo}) ==")
    print(f"prompt: {task.prompt[:200]}{'...' if len(task.prompt) > 200 else ''}")
    print(f"files_expected: {task.files_expected}")
    print(f"verifier: {task.verifier}")

    print("\n[1/5] Preflight")
    if not preflight(task, cfg, repo):
        sys.exit("\nPreflight failed; fix the items marked FAIL and rerun.")

    print("\n[2/5] Create worktree")
    wt = create_worktree(repo, task.task_id, args.route, task.base_commit)
    print(f"  {wt}")

    try:
        ok, note = backend.setup_worktree(repo, wt)
        print(f"  setup: {note}")
        if not ok:
            sys.exit("Setup failed; fix the issue above and rerun.")

        baseline = None
        if not args.skip_baseline:
            print("\n[3/5] Baseline: verifier on the untouched checkout (should FAIL)")
            baseline, out = backend.run_verifier(task.verifier, wt)
            print(f"  verifier {'PASSED' if baseline else 'failed'} before any edit")
            if baseline:
                print("  WARNING: it passes with no changes, so this task or its verifier is broken.")
            else:
                print("  last output:\n" + "\n".join("    " + l for l in tail(out, 8).splitlines()))
        else:
            print("\n[3/5] Baseline skipped")

        before = status(wt)  # ignore artifacts the baseline verifier left behind
        print(f"\n[4/5] Run agent ({cfg['kind']})")
        t0 = time.time()
        agent = backend.run(cfg, task, wt)
        agent_secs = round(time.time() - t0, 1)
        print(f"  returncode={agent['returncode']} timeout={agent['timeout']} ({agent_secs}s)")
        print("  stdout tail:\n" + "\n".join("    " + l for l in tail(agent["stdout"]).splitlines()))
        if agent["returncode"] != 0 or agent["timeout"]:
            print("  stderr tail:\n" + "\n".join("    " + l for l in tail(agent["stderr"]).splitlines()))

        changes = sorted(status(wt) - before)
        print("\n  files changed by the agent:")
        if changes:
            print("\n".join("    " + l for l in changes))
        else:
            print("    (none) WARNING: the agent made no file changes; check the stdout above")

        print("\n[5/5] Verify")
        t0 = time.time()
        passed, out = backend.run_verifier(task.verifier, wt)
        verify_secs = round(time.time() - t0, 1)
        print(f"  verifier {'PASSED' if passed else 'FAILED'} ({verify_secs}s)")
        if not passed:
            print("  last output:\n" + "\n".join("    " + l for l in tail(out, 20).splitlines()))

        commit_result(wt, task.task_id)
        result = {
            "mode": "slice",
            "task_id": task.task_id,
            "route": args.route,
            "passed": passed,
            "baseline_passed": baseline,
            "agent_seconds": agent_secs,
            "verify_seconds": verify_secs,
            "returncode": agent["returncode"],
            "timeout": agent["timeout"],
            "changed": bool(changes),
            "files_changed": [l[3:] for l in changes],
        }
        with open("slice_results.jsonl", "a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"\nLogged to slice_results.jsonl: {result}")
    finally:
        if args.keep:
            print(f"\nKept worktree for inspection: {wt}")
            print(f"  cd {wt} && git log --oneline -2 && git show --stat")
        else:
            remove_worktree(repo, wt)
            print("\nWorktree removed (branch eval/... stays in the repo; use --keep to inspect files)")


if __name__ == "__main__":
    main()