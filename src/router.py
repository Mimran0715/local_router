import yaml  # pip install pyyaml
import subprocess
from typing import Optional
from task import CodingTask, load_tasks

def load_routes():
    with open("models.yaml") as f:
        cfg = yaml.safe_load(f)
        return cfg["backends"]

def choose_route(task: CodingTask):
    pass











