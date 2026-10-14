from pydantic import BaseModel
from typing import Literal
import json
from pathlib import Path

class CodingTask(BaseModel):
    task_id: str
    repo: str
    base_commit: str
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str
    verifier: str
    files_expected: list[str] = [] 

def load_tasks(task_file: str) -> list[CodingTask]:
    data = json.loads(Path(task_file).read_text())
    return [CodingTask(**t) for t in data["tasks"]]




