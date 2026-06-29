from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class LocalEnvironmentConfig(BaseModel):
    workdir: Path = Path("runs")
    timeout_seconds: int = 30


class LocalEnvironment:
    def __init__(self, **kwargs: Any):
        self.config = LocalEnvironmentConfig(**kwargs)

    def compile(self, code: str, *, name: str = "object") -> dict[str, Any]:
        """Compile generated code and return paths, warnings, and errors."""
        raise NotImplementedError
