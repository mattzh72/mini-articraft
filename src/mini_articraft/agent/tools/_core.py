from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ToolContext:
    env: Any
    run_dir: Path
    workspace: Path
    revision: int = 0
    compiled_revision: int = -1
    compile_result: dict[str, Any] | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    schema: dict[str, Any]
    run: Callable[[ToolContext, dict[str, Any]], Awaitable[dict[str, Any]]]
    mutates: bool = False


def schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
        "strict": False,
    }


def scoped_path(base: Path, raw: str, label: str) -> Path:
    if not raw:
        raise ValueError("path is required")
    base = base.resolve()
    target = Path(raw)
    target = target if target.is_absolute() else base / target
    target = target.resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"path must stay inside the {label}") from exc
    return target


def workspace_path(workspace: Path, raw: str) -> Path:
    return scoped_path(workspace, raw, "run workspace")


def result_item(call_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "function_call_output", "call_id": call_id, "output": json.dumps(payload)}
