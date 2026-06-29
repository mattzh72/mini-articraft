from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel


class OpenAIModelConfig(BaseModel):
    model_name: str = os.getenv("MINI_ARTICRAFT_MODEL", "gpt-4.1")


class OpenAIModel:
    def __init__(self, **kwargs: Any):
        self.config = OpenAIModelConfig(**kwargs)

    def query(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Query OpenAI and return generated object code."""
        raise NotImplementedError
