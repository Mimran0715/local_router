# backend.py
import os, shlex, subprocess

def _run(cmd, cwd, timeout, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                           text=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout,
                "stderr": p.stderr, "timeout": False}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": "", "timeout": True}

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

def run_verifier(verifier: str, wt, timeout=300) -> bool:
    try:
        p = subprocess.run(shlex.split(verifier), cwd=wt,
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0
    except subprocess.TimeoutExpired:
        return False