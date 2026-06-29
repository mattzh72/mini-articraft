from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mini_articraft import Environment, Model
from mini_articraft.record import Record


class AgentConfig(BaseModel):
    attempts: int = 3
    output_path: Path | None = None


class DefaultAgent:
    def __init__(self, model: Model, env: Environment, **kwargs: Any):
        self.config = AgentConfig(**kwargs)
        self.model = model
        self.env = env
        self.messages: list[dict[str, Any]] = []

    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Run the generate and compile loop."""
        raise NotImplementedError

    def save(self, record: Record) -> dict[str, Any]:
        data = record.to_dict()
        if self.config.output_path:
            record.save(self.config.output_path)
        return data
