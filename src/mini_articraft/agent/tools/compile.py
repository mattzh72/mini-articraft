from __future__ import annotations

import asyncio
from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, schema


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if args:
        raise ValueError("compile does not take arguments")
    if context.compile_is_fresh and context.compile_result is not None:
        return context.compile_result
    result = await asyncio.to_thread(context.env.compile_path, context.run_dir)
    context.compile_result = _agent_result(result)
    context.compile_is_fresh = result["status"] == "success"
    return context.compile_result


def _agent_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result[key]
        for key in (
            "status",
            "error",
            "stdout",
            "stderr",
            "traceback",
            "returncode",
            "test_report",
        )
        if key in result
    }


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
