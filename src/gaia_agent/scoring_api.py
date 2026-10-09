"""Client for the course scoring API and the local task cache (questions + attached files)."""

import json
import shutil
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from gaia_agent.settings import Settings


class Task(BaseModel):
    task_id: str
    question: str
    level: str | None = Field(default=None, alias="Level")
    file_name: str = ""
    file_path: Path | None = None

    model_config = {"populate_by_name": True}


class Answer(BaseModel):
    task_id: str
    submitted_answer: str


class ScoringAPI:
    def __init__(self, base_url: str):
        self.http = httpx.Client(base_url=base_url, timeout=60, follow_redirects=True)

    def questions(self) -> list[Task]:
        response = self.http.get("/questions")
        response.raise_for_status()
        return [Task.model_validate(q) for q in response.json()]

    def download_file(self, task_id: str, dest: Path) -> Path:
        response = self.http.get(f"/files/{task_id}")
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        return dest

    def submit(self, username: str, agent_code: str, answers: list[Answer]) -> dict:
        payload = {
            "username": username.strip(),
            "agent_code": agent_code,
            "answers": [a.model_dump() for a in answers],
        }
        response = self.http.post("/submit", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()


def _download_from_gaia(settings: Settings, file_name: str, dest: Path) -> bool:
    if not settings.hf_token:
        return False
    from huggingface_hub import hf_hub_download

    try:
        path = hf_hub_download(
            "gaia-benchmark/GAIA",
            f"2023/validation/{file_name}",
            repo_type="dataset",
            token=settings.hf_token.get_secret_value(),
        )
    except Exception as e:
        print(f"  ! GAIA dataset download failed for {file_name}: {e}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, dest)
    return True


def fetch_tasks(settings: Settings) -> list[Task]:
    """Download questions and any attached files into data/tasks/.

    The course API's /files endpoint has been returning 404 for every task, so files fall back to
    the gated GAIA validation set on the Hub (needs HF_TOKEN and accepted dataset terms).
    """
    api = ScoringAPI(settings.scoring_api_url)
    tasks = api.questions()
    for task in tasks:
        if not task.file_name:
            continue
        dest = settings.files_dir / task.file_name
        if not dest.exists():
            try:
                api.download_file(task.task_id, dest)
            except httpx.HTTPStatusError:
                if not _download_from_gaia(settings, task.file_name, dest):
                    print(f"  ! could not get {task.file_name}; set HF_TOKEN and accept the GAIA dataset terms")
                    continue
        task.file_path = dest
    settings.tasks_dir.mkdir(parents=True, exist_ok=True)
    (settings.tasks_dir / "questions.json").write_text(
        json.dumps([t.model_dump(mode="json") for t in tasks], indent=2, ensure_ascii=False)
    )
    return tasks


def load_tasks(settings: Settings) -> list[Task]:
    path = settings.tasks_dir / "questions.json"
    if not path.exists():
        raise SystemExit("No cached tasks. Run `gaia fetch` first.")
    return [Task.model_validate(t) for t in json.loads(path.read_text())]
