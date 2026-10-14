from pathlib import Path
from task import load_tasks
from router import load_routes
from jobs import create_jobs, run_job, log_result, load_done

# map whatever your tasks' `repo` field holds to a local clone
BASE="~/Desktop"

REPOS = {"docs_rag": Path(BASE + "/docs_rag").expanduser(),
         "drafts-desktop": Path(BASE + "/drafts-desktop").expanduser(),
         "chat_cli": Path(BASE + "/chat_cli").expanduser(),
         "cli_summarizer": Path(BASE + "/cli_summarizer").expanduser()}

def main():
    tasks = {t.task_id: t for t in load_tasks("eval/tasks.json")}
    routes = load_routes()                      # dict: name -> backend config
    done = load_done()
    for job in create_jobs(list(tasks.values()), routes):
        if (job.task_id, job.route) in done:
            continue
        task = tasks[job.task_id]
        log_result(run_job(job, task, routes[job.route], REPOS[task.repo]))

if __name__ == "__main__":
    main()