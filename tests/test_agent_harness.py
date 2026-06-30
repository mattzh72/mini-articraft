from __future__ import annotations

import asyncio
import json
from typing import Any

from mini_articraft.agent import Agent
from mini_articraft.environments.local import LocalEnvironment
from mini_articraft.record import read_conversation


def run(awaitable):
    return asyncio.run(awaitable)


class FakeModel:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def query(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"messages": list(messages), "tools": list(tools or [])})
        return self.responses.pop(0)

    async def close(self) -> None:
        pass


def call(call_id: str, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"id": call_id, "name": name, "arguments": json.dumps(args)}


MODEL_CODE = """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("box")
object_model.part("base", cq.Workplane("XY").box(1, 1, 1))
"""


def test_agent_writes_compiles_and_returns_final_response(tmp_path) -> None:
    model = FakeModel(
        [
            {"text": "", "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})]},
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, attempts=3)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["message"] == "done"
    assert tmp_path.joinpath("box", "workspace", "main.py").is_file()
    assert {tool["name"] for tool in model.calls[0]["tools"]} == {
        "read",
        "edit",
        "write",
        "exec_command",
        "write_stdin",
        "compile",
    }


def test_agent_requires_compile_before_final_response(tmp_path) -> None:
    model = FakeModel(
        [
            {"text": "", "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})]},
            {"text": "done too early", "tool_calls": []},
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, attempts=4)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["message"] == "done"
    assert any(
        message.get("content") == "Run compile before the final response."
        for message in model.calls[2]["messages"]
    )
    conversation = read_conversation(tmp_path / "box" / "conversation.jsonl")
    assert any(event.get("content") == "Run compile before the final response." for event in conversation)
