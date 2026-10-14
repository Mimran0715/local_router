import os, shlex, signal, subprocess
from pathlib import Path

def _run(cmd, cwd, timeout, env=None, log_path=None):
    """Run cmd in its own process group; output goes to a log file you can `tail -f`."""
    cwd = Path(cwd)
    log_path = Path(log_path) if log_path else cwd.parent / f"{cwd.name}-{Path(cmd[0]).name}.log"
    timed_out = False
    with open(log_path, "w") as log:
        proc = subprocess.Popen(
            cmd, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL,            # nothing can block waiting for keyboard input
            stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,              # own process group, so the whole tree can be killed
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:                                 # also runs on Ctrl-C
            try:
                os.killpg(proc.pid, signal.SIGKILL)   # kills grandchildren and leftover servers too
            except ProcessLookupError:
                pass
            proc.wait()
    output = log_path.read_text(errors="replace")
    return {"returncode": None if timed_out else proc.returncode,
            "stdout": output, "stderr": "", "timeout": timed_out}

def setup_worktree(repo, wt, timeout=900):
    """Make a fresh worktree runnable. Returns (ok, note).

    Worktrees only contain tracked files, so node_modules and .venv don't exist yet.
    """
    repo, wt = Path(repo), Path(wt)
    notes = []
    if (wt / "package.json").exists() and not (wt / "node_modules").exists():
        nm = repo / "node_modules"
        if nm.exists():
            (wt / "node_modules").symlink_to(nm, target_is_directory=True)
            notes.append("linked node_modules from the main checkout")
        else:
            notes.append(f"WARNING: package.json found but {nm} is missing; run `npm ci` there")
    if (wt / "pyproject.toml").exists() and (wt / "uv.lock").exists():
        r = _run(["uv", "sync", "--frozen"], wt, timeout)
        if r["timeout"] or r["returncode"] != 0:
            return False, "uv sync failed:\n" + r["stdout"][-1500:]
        notes.append("uv sync ok")
    return True, "; ".join(notes) or "nothing to set up"

def build_prompt(task) -> str:
    if not task.files_expected:
        return task.prompt
    files = "\n".join(f"- {f}" for f in task.files_expected)
    return f"{task.prompt}\n\nThe relevant files are:\n{files}"

def run_aider(cfg, task, wt, timeout=600):
    env = {**os.environ, "OLLAMA_API_BASE": cfg["api_base"]}
    cmd = ["aider", "--model", cfg["model"], "--message", build_prompt(task),
           "--yes-always", "--no-auto-commits", "--no-stream", "--no-pretty",
           "--no-check-update", "--no-analytics", *task.files_expected]
    return _run(cmd, wt, timeout, env)

def run_codex(cfg, task, wt, timeout=900):
    # confirm flags (sandbox/approval mode) with `codex exec --help`
    return _run(["codex", "exec", build_prompt(task)], wt, timeout)

def run(cfg, task, wt):
    if cfg["kind"] == "ollama":
        return run_aider(cfg, task, wt)
    if cfg["kind"] == "codex_cli":
        return run_codex(cfg, task, wt)
    raise ValueError(f"unknown backend kind: {cfg['kind']}")

def run_verifier(verifier: str, wt, timeout=180):
    # CI: vitest/jest and others skip watch mode. No .pyc files: they pollute the worktree
    # and can go stale if an edit lands in the same second.
    env = {**os.environ, "CI": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = _run(shlex.split(verifier), wt, timeout, env)
    except FileNotFoundError as e:
        return False, f"verifier command not found: {e}"
    if r["timeout"]:
        return False, f"TIMED OUT after {timeout}s\n" + r["stdout"][-2000:]
    return r["returncode"] == 0, r["stdout"]