"""Runtime settings (.env / environment) and per-role model config (config/models.yaml)."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr | None = None
    tavily_api_key: SecretStr | None = None
    hf_token: SecretStr | None = None
    hf_username: str | None = None
    agent_code_url: str | None = None

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    scoring_api_url: str = "https://agents-course-unit4-scoring.hf.space"
    phoenix_endpoint: str | None = None

    data_dir: Path = Path("data")
    models_config: Path = Path("config/models.yaml")
    max_run_usd: float = 2.0

    @property
    def tasks_dir(self) -> Path:
        return self.data_dir / "tasks"

    @property
    def files_dir(self) -> Path:
        return self.tasks_dir / "files"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    def require(self, *names: str) -> None:
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            env = ", ".join(n.upper() for n in missing)
            raise SystemExit(f"Missing required setting(s): {env}. Add them to .env (see .env.example).")


class LLMRole(BaseModel):
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    # OpenRouter provider routing, e.g. ["google-ai-studio"] so YouTube URLs are accepted.
    provider_only: list[str] | None = None


class AgentRole(LLMRole):
    max_steps: int = 15
    planning_interval: int | None = None


class AudioRole(BaseModel):
    whisper_model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"


class ModelsConfig(BaseModel):
    agent: AgentRole
    vision: LLMRole
    video: LLMRole
    audio: AudioRole = AudioRole()


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_models_config() -> ModelsConfig:
    path = get_settings().models_config
    return ModelsConfig.model_validate(yaml.safe_load(path.read_text()))
