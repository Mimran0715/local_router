# jobs.py
import json, time
from pathlib import Path
from pydantic import BaseModel
from git_utils import create_worktree, remove_worktree, commit_result
from backend import run, run_verifier

class Job(BaseModel):
    task_id: str
    route: str

def create_jobs(tasks, routes):
    jobs = [Job(task_id=t.task_id, route=r) for t in tasks for r in routes]
    return sorted(jobs, key=lambda j: j.route)   # batch by backend

def run_job(job, task, cfg, repo_path):
    wt = create_worktree(repo_path, task.task_id, job.route, task.base_commit)
    start = time.time()
    try:
        agent = run(cfg, task, wt)
        passed = run_verifier(task.verifier, wt)
        commit_result(wt, task.task_id)
        return {"task_id": task.task_id, "route": job.route, "passed": passed,
                "seconds": round(time.time() - start, 1),
                "returncode": agent["returncode"], "timeout": agent["timeout"]}
    finally:
        remove_worktree(repo_path, wt)

def log_result(result, path="results.jsonl"):
    with open(path, "a") as f:
        f.write(json.dumps(result) + "\n")

def load_done(path="results.jsonl"):
    p = Path(path)
    if not p.exists():
        return set()
    return {(r["task_id"], r["route"]) for r in map(json.loads, p.read_text().splitlines())}