from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_OUTPUT_DIR = Path("runs")
DEFAULT_MAX_TURNS = 100
DEFAULT_COMPILE_TIMEOUT_SECONDS = 900.0
DEFAULT_OPENAI_MODEL = "gpt-5.5-2026-04-23"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MINI_ARTICRAFT_",
        extra="ignore",
        populate_by_name=True,
    )

    output_dir: Path = Field(
        default=DEFAULT_OUTPUT_DIR,
        validation_alias="MINI_ARTICRAFT_OUTPUT_DIR",
    )
    openai_model: str = Field(
        default=DEFAULT_OPENAI_MODEL,
        validation_alias="MINI_ARTICRAFT_MODEL",
    )
    openai_reasoning_effort: str = Field(
        default="high",
        validation_alias="MINI_ARTICRAFT_REASONING_EFFORT",
    )
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    max_turns: int = Field(default=DEFAULT_MAX_TURNS, validation_alias="MINI_ARTICRAFT_MAX_TURNS")
    compile_timeout_seconds: float = Field(
        default=DEFAULT_COMPILE_TIMEOUT_SECONDS,
        gt=0.0,
        validation_alias="MINI_ARTICRAFT_COMPILE_TIMEOUT_SECONDS",
    )


@cache
def get_settings() -> Settings:
    # openai_api_key has no default on purpose: it is populated from the
    # environment (OPENAI_API_KEY / .env) when the settings load.
    return Settings()  # pyright: ignore[reportCallIssue]
