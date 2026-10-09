"""OpenRouter access: the agent's model, a plain chat helper for tools, and a run-wide cost cap."""

import threading
from functools import lru_cache
from typing import Any

from openai import OpenAI
from smolagents import ChatMessage, OpenAIModel

from gaia_agent.settings import AgentRole, LLMRole, get_settings


class BudgetExceededError(RuntimeError):
    pass


class CostTracker:
    """Sums OpenRouter's per-request `usage.cost` and refuses new calls past the limit."""

    def __init__(self, limit_usd: float | None = None):
        self.limit_usd = limit_usd
        self.total_usd = 0.0
        self.calls = 0
        self._lock = threading.Lock()

    def check(self) -> None:
        if self.limit_usd is not None and self.total_usd >= self.limit_usd:
            raise BudgetExceededError(f"Run budget of ${self.limit_usd:.2f} reached (spent ${self.total_usd:.4f}).")

    def add(self, usage: Any) -> float:
        cost = float(getattr(usage, "cost", None) or 0.0) if usage is not None else 0.0
        with self._lock:
            self.total_usd += cost
            self.calls += 1
        return cost

    @property
    def exceeded(self) -> bool:
        return self.limit_usd is not None and self.total_usd >= self.limit_usd


tracker = CostTracker()


def _extra_body(role: LLMRole) -> dict[str, Any]:
    extra: dict[str, Any] = {"usage": {"include": True}}
    if role.provider_only:
        extra["provider"] = {"only": role.provider_only}
    return extra


@lru_cache
def get_client() -> OpenAI:
    settings = get_settings()
    settings.require("openrouter_api_key")
    return OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key.get_secret_value(),
        max_retries=3,
        timeout=180,
    )


class TrackedOpenAIModel(OpenAIModel):
    """smolagents OpenAIModel that reports cost to the tracker and honours the budget."""

    def generate(self, *args, **kwargs) -> ChatMessage:
        tracker.check()
        message = super().generate(*args, **kwargs)
        tracker.add(getattr(message.raw, "usage", None))
        return message


def agent_model(role: AgentRole) -> TrackedOpenAIModel:
    settings = get_settings()
    settings.require("openrouter_api_key")
    return TrackedOpenAIModel(
        model_id=role.model,
        api_base=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key.get_secret_value(),
        temperature=role.temperature,
        max_tokens=role.max_tokens,
        extra_body=_extra_body(role),
    )


def chat(role: LLMRole, content: str | list[dict[str, Any]], system: str | None = None) -> str:
    """One-shot completion for tools (vision, video). `content` may be multimodal parts."""
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})
    tracker.check()
    response = get_client().chat.completions.create(
        model=role.model,
        messages=messages,
        temperature=role.temperature,
        max_tokens=role.max_tokens,
        extra_body=_extra_body(role),
    )
    tracker.add(response.usage)
    return response.choices[0].message.content or ""
