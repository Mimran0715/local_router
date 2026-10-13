import yaml  # pip install pyyaml
import subprocess
from typing import Optional
from task import CodingTask
from backend import run_aider, run_codex

def load_routes():
    with open("models.yaml") as f:
        cfg = yaml.safe_load(f)
        return cfg["backends"]

def choose_route(task: CodingTask):
    routes = [route for route in load_routes()]
    if task.difficulty == "easy":
        run_aider() # Ollama local
    elif task.difficulty == "medium":
        run_aider() # Ollama cloud
    elif task.difficulty == "hard":
        run_codex()











