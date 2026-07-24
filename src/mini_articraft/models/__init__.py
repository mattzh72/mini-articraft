from __future__ import annotations

from mini_articraft.models.gemini import (
    GeminiModel,
)
from mini_articraft.models.gemini import (
    context_window_tokens_for as gemini_context_window_tokens_for,
)
from mini_articraft.models.openai import OpenAIModel
from mini_articraft.models.openai import (
    context_window_tokens_for as openai_context_window_tokens_for,
)
from mini_articraft.models.providers import create_model


def context_window_tokens_for(model: str) -> int | None:
    return openai_context_window_tokens_for(model) or gemini_context_window_tokens_for(model)


__all__ = ["GeminiModel", "OpenAIModel", "context_window_tokens_for", "create_model"]
