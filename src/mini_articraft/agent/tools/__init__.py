from __future__ import annotations

from typing import Any

from mini_articraft.agent.tools._core import Tool, ToolContext, result_item
from mini_articraft.agent.tools.compile import TOOL as compile_tool
from mini_articraft.agent.tools.edit import TOOL as edit_tool
from mini_articraft.agent.tools.exec_command import TOOL as exec_command_tool
from mini_articraft.agent.tools.inspect_view import TOOL as inspect_view_tool
from mini_articraft.agent.tools.read import TOOL as read_tool
from mini_articraft.agent.tools.write import TOOL as write_tool
from mini_articraft.agent.tools.write_stdin import TOOL as write_stdin_tool

TOOLS = {
    tool.name: tool
    for tool in (
        read_tool,
        edit_tool,
        write_tool,
        exec_command_tool,
        write_stdin_tool,
        compile_tool,
        inspect_view_tool,
    )
}


def schemas(*, inspect_view: bool = True) -> list[dict[str, Any]]:
    return [
        tool.schema
        for name, tool in TOOLS.items()
        if inspect_view or name != "inspect_view"
    ]


def get(name: str, *, inspect_view: bool = True) -> Tool:
    if name == "inspect_view" and not inspect_view:
        raise ValueError(f"unknown tool: {name}")
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise ValueError(f"unknown tool: {name}") from exc


__all__ = ["Tool", "ToolContext", "get", "result_item", "schemas"]
