# git_utils.py
import subprocess
from pathlib import Path

RUNS_DIR = Path("/tmp/runs")

def git(*args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check,
                          capture_output=True, text=True)

def create_worktree(repo: Path, task_id: str, route: str, base_commit: str) -> Path:
    path = RUNS_DIR / f"{task_id}-{route}"
    git("worktree", "add", "-B", f"eval/{task_id}-{route}", str(path), base_commit, cwd=repo)
    return path

def commit_result(wt: Path, task_id: str):
    git("add", "-A", cwd=wt)
    git("commit", "-m", f"{task_id} attempt", "--allow-empty", cwd=wt)

def remove_worktree(repo: Path, wt: Path):
    git("worktree", "remove", "--force", str(wt), cwd=repo)