from __future__ import annotations

import asyncio
from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, schema


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if args:
        raise ValueError("compile does not take arguments")
    if context.compiled_revision == context.revision and context.compile_result is not None:
        return context.compile_result
    result = await asyncio.to_thread(context.env.compile_path, context.run_dir)
    context.compile_result = result
    if result["status"] == "success":
        context.compiled_revision = context.revision
    return result


TOOL = Tool(
    "compile",
    schema(
        "compile",
        "Compile the current run using the existing environment compile flow. Run this after changing files and before the final response.",
        {},
        [],
    ),
    run,
)
