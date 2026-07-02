from __future__ import annotations

from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.agent.tools._exec import MANAGER, collect, session_id, write


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    session = MANAGER.get(context, session_id(args.get("session_id")))
    await write(session, str(args.get("chars") or ""))
    return await collect(session, args)


TOOL = Tool(
    "write_stdin",
    schema(
        "write_stdin",
        "Writes characters to an existing exec_command session and returns recent output. Use empty chars to poll without writing.",
        {
            "session_id": {
                "type": "integer",
                "description": "Identifier of the running exec_command session.",
            },
            "chars": {
                "type": "string",
                "description": "Bytes to write to stdin. Defaults to empty, which polls without writing.",
            },
            "yield_time_ms": {
                "type": "integer",
                "description": "Wait before yielding output. Defaults to 10000 ms; values above 30000 ms are capped.",
            },
            "max_output_tokens": {
                "type": "integer",
                "description": "Output token budget. Defaults to 10000 tokens; larger requests may be capped by policy.",
            },
        },
        ["session_id"],
    ),
    run,
)
