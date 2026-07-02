from __future__ import annotations

from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.agent.tools._exec import (
    MANAGER,
    MAX_OUTPUT_TOKENS_PROPERTY,
    YIELD_TIME_MS_PROPERTY,
    collect,
)


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    session = await MANAGER.start(context, args)
    return await collect(session, args)


TOOL = Tool(
    "exec_command",
    schema(
        "exec_command",
        "Runs a command in the run directory, returning output or a session ID for ongoing interaction. Use bounded yields for long work, then call write_stdin to poll or send input.",
        {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command. Defaults to the run workspace. Relative paths are resolved against the workspace; absolute paths must stay inside it.",
            },
            "shell": {
                "type": "string",
                "description": "Shell binary to launch. Defaults to the user's default shell.",
            },
            "login": {
                "type": "boolean",
                "description": "True runs the shell with -lc; false uses -c. Defaults to true.",
            },
            "timeout": {
                "type": "number",
                "description": "Hard timeout in seconds. If it elapses while the process is still running, the process group is killed and timed_out is returned.",
            },
            "yield_time_ms": YIELD_TIME_MS_PROPERTY,
            "max_output_tokens": MAX_OUTPUT_TOKENS_PROPERTY,
        },
        ["command"],
    ),
    run,
    supports_parallel=True,
)
