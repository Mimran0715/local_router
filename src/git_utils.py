import subprocess, os
from pathlib import Path

def git(*args, cwd, check=True):
    return subprocess.run(["git", *args], 
                          cwd=cwd,
                          check=check,
                          capture_output=True,
                          text=True)
    
def create_worktree(worktree: Path, task_id:str):
     git("add", "-A", cwd=worktree)
     git("commit", "-m", f"{task_id} attempt", cwd=worktree)

def remove_worktree(repo: Path, wt_path:Path):
    git("worktree", "remove", "--force", str(wt_path), cwd=repo)