"""Builds the smolagents CodeAgent and the per-task prompt."""

from pathlib import Path

from smolagents import CodeAgent

from gaia_agent.answer import check_final_answer
from gaia_agent.llm import agent_model
from gaia_agent.scoring_api import Task
from gaia_agent.settings import ModelsConfig
from gaia_agent.tools import ALL_TOOLS

INSTRUCTIONS = (Path(__file__).parent / "prompts" / "instructions.md").read_text()

AUTHORIZED_IMPORTS = [
    "pandas",
    "numpy",
    "math",
    "statistics",
    "re",
    "datetime",
    "json",
    "collections",
    "itertools",
    "fractions",
    "decimal",
    "unicodedata",
    "chess",
    "openpyxl",
    "csv",
]


def build_agent(models: ModelsConfig) -> CodeAgent:
    role = models.agent
    return CodeAgent(
        tools=ALL_TOOLS,
        model=agent_model(role),
        instructions=INSTRUCTIONS,
        max_steps=role.max_steps,
        planning_interval=role.planning_interval,
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        final_answer_checks=[check_final_answer],
        verbosity_level=1,
    )


def task_prompt(task: Task) -> str:
    prompt = task.question
    if task.file_path:
        prompt += (
            f"\n\nAttached file: {Path(task.file_path).resolve()} "
            f"(type: {Path(task.file_path).suffix.lstrip('.') or 'unknown'})"
        )
    return prompt
