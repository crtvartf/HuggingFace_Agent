"""Runs the agent over tasks, recording one JSON line per task in data/runs/<name>/answers.jsonl."""

import json
import time
from pathlib import Path

from pydantic import BaseModel

from gaia_agent.agent import build_agent, task_prompt
from gaia_agent.answer import normalize_answer
from gaia_agent.llm import BudgetExceededError, tracker
from gaia_agent.scoring_api import Task
from gaia_agent.settings import ModelsConfig


class TaskResult(BaseModel):
    task_id: str
    question: str
    answer: str
    raw_answer: str
    state: str  # success | max_steps_error | error | budget_exceeded
    error: str | None = None
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_s: float = 0.0
    model: str


def load_results(run_dir: Path) -> dict[str, TaskResult]:
    path = run_dir / "answers.jsonl"
    if not path.exists():
        return {}
    results = [TaskResult.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]
    return {r.task_id: r for r in results}


def run_task(task: Task, models: ModelsConfig) -> TaskResult:
    spent_before, started = tracker.total_usd, time.time()
    base = {"task_id": task.task_id, "question": task.question, "model": models.agent.model}
    try:
        result = build_agent(models).run(task_prompt(task), return_full_result=True)
    except Exception as e:
        state = "budget_exceeded" if tracker.exceeded or isinstance(e, BudgetExceededError) else "error"
        return TaskResult(
            **base,
            answer="",
            raw_answer="",
            state=state,
            error=f"{type(e).__name__}: {e}",
            cost_usd=tracker.total_usd - spent_before,
            duration_s=time.time() - started,
        )
    usage = result.token_usage
    return TaskResult(
        **base,
        answer=normalize_answer(result.output),
        raw_answer=str(result.output),
        state=result.state,
        steps=sum(1 for s in result.steps if s.get("step_number") is not None),
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        cost_usd=tracker.total_usd - spent_before,
        duration_s=time.time() - started,
    )


def run_tasks(tasks: list[Task], models: ModelsConfig, run_dir: Path, rerun: bool = False) -> list[TaskResult]:
    """Answer each task; skips tasks already answered in run_dir unless rerun is set."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "models.json").write_text(models.model_dump_json(indent=2))
    done = {} if rerun else {k: v for k, v in load_results(run_dir).items() if v.state != "error"}
    results = []
    with (run_dir / "answers.jsonl").open("a") as out:
        for i, task in enumerate(tasks, 1):
            if task.task_id in done:
                results.append(done[task.task_id])
                continue
            print(f"\n=== [{i}/{len(tasks)}] {task.task_id} :: {task.question[:100]}")
            result = run_task(task, models)
            out.write(result.model_dump_json() + "\n")
            out.flush()
            results.append(result)
            print(
                f"--> {result.state}: {result.answer!r}  "
                f"(${result.cost_usd:.4f}, {result.duration_s:.0f}s, total ${tracker.total_usd:.4f})"
            )
            if result.state == "budget_exceeded":
                print("Budget cap reached; stopping. Raise MAX_RUN_USD or pass --max-usd to continue.")
                break
    return results


def latest_answers(run_dir: Path) -> list[dict]:
    """Last answer per task (later lines win), as submission dicts."""
    return [{"task_id": r.task_id, "submitted_answer": r.answer} for r in load_results(run_dir).values()]


def write_summary(run_dir: Path, rows: list[dict]) -> None:
    (run_dir / "eval.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
