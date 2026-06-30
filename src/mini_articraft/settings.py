from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MINI_ARTICRAFT_",
        extra="ignore",
        populate_by_name=True,
    )

    output_dir: Path = Field(Path("runs"), validation_alias="MINI_ARTICRAFT_OUTPUT_DIR")
    openai_model: str = Field("gpt-5.5", validation_alias="MINI_ARTICRAFT_MODEL")
    openai_reasoning_effort: str = Field(
        "high",
        validation_alias="MINI_ARTICRAFT_REASONING_EFFORT",
    )
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")
    max_turns: int = Field(200, validation_alias="MINI_ARTICRAFT_MAX_TURNS")


@cache
def get_settings() -> Settings:
    return Settings()
