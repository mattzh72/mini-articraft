from __future__ import annotations

from functools import cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MINI_ARTICRAFT_",
        extra="ignore",
        populate_by_name=True,
    )

    openai_model: str = Field("gpt-5.5", validation_alias="MINI_ARTICRAFT_MODEL")
    openai_reasoning_effort: str = Field(
        "high",
        validation_alias="MINI_ARTICRAFT_REASONING_EFFORT",
    )
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY")


@cache
def get_settings() -> Settings:
    return Settings()
