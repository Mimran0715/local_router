from pydantic import BaseModel
from typing import Literal
import json
from pathlib import Path

class CodingTask(BaseModel):
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str
    files: list[str] = []
    repo: str
    base_commit: str
    verifier: str

def load_tasks(task_file: str) -> list:
    task_json = json.load(Path(task_file).read_text())
    tasks = [CodingTask(**task) for task in task_json]
    return tasks




