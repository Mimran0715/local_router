import yaml  # pip install pyyaml
import subprocess
from typing import Optional
from task import CodingTask, load_tasks

def load_routes():
    with open("models.yaml") as f:
        cfg = yaml.safe_load(f)
        return cfg["backends"]

def choose_route(task: CodingTask) -> str:
    n_files = len(task.files_expected)
    if n_files <= 1 and len(task.prompt) < 400:
        return "local_small"
    if n_files <= 3:
        return "local_medium"
    return "codex"











