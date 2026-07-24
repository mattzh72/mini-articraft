from __future__ import annotations

from mini_articraft import Model
from mini_articraft.models.gemini import GeminiModel
from mini_articraft.models.openai import OpenAIModel
from mini_articraft.settings import Settings


def create_model(settings: Settings) -> Model:
    if settings.provider == "openai":
        return OpenAIModel(settings)
    if settings.provider == "gemini":
        return GeminiModel(settings)
    raise ValueError(f"unsupported provider: {settings.provider}")


__all__ = ["create_model"]
