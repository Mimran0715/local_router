from pydantic import BaseModel
from task import CodingTask
from router import load_routes
from git_utils import create_worktree, remove_worktree, commit_result

class Job(BaseModel):
    task_id: str
    route: str
    status: str

def create_jobs(tasks:list) -> list:
    routes = load_routes()
    jobs = [Job(task_id=t.task_id, route=r, status="") for t in tasks for r in routes]
    jobs = jobs.sort(lambda j: j.route)
    return jobs  

def run_verifier(verifier, wt):
    pass

def log_result():
    pass

def run_jobs(job:Job, task: CodingTask, backend):
    wt = create_worktree(task.repo, task.id, task.base_commit, job.route)
    try: 
        agent_result = backend.run(job.route, task, wt)
        passed = run_verifier(task.verifier, wt)
        commit_result(wt, task.id)
        log_result({...})

    finally:
        remove_worktree(task.repo, wt)
