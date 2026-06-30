from __future__ import annotations

import asyncio
from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.compile_feedback import compile_failure_signature, render_compile_report


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    if args:
        raise ValueError("compile does not take arguments")
    if context.compile_is_fresh and context.compile_result is not None:
        return context.compile_result
    result = await asyncio.to_thread(context.env.compile_path, context.run_dir)
    context.compile_result = _agent_result(context, result)
    context.compile_is_fresh = result["status"] == "success"
    return context.compile_result


def _agent_result(context: ToolContext, result: dict[str, Any]) -> dict[str, Any]:
    compile_report = result.get("compile_report")
    if isinstance(compile_report, dict):
        signature = compile_failure_signature(compile_report)
        if signature is None:
            context.last_compile_failure_signature = None
            context.consecutive_compile_failures = 0
            result["compile_report"] = render_compile_report(compile_report)
        else:
            repeated = signature == context.last_compile_failure_signature
            context.last_compile_failure_signature = signature
            context.consecutive_compile_failures += 1
            result["compile_report"] = render_compile_report(
                compile_report,
                repeated=repeated,
                failure_streak=context.consecutive_compile_failures,
            )
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
            "compile_report",
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
