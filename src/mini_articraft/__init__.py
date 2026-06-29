from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

__version__ = "0.1.0"

package_dir = Path(__file__).resolve().parent


class Model(Protocol):
    def query(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...


class Environment(Protocol):
    def compile(self, code: str, *, name: str = "object") -> dict[str, Any]: ...


class Agent(Protocol):
    def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]: ...


__all__ = ["Agent", "Environment", "Model", "__version__", "package_dir"]
