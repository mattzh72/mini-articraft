from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

import mini_articraft.agent.tools as agent_tools
from mini_articraft.agent import Agent, events
from mini_articraft.agent.harness import PROMPT_SLUG_MAX_LENGTH, _prompt_slug, _run_id_for_prompt
from mini_articraft.agent.tools import Tool
from mini_articraft.environments.local import LocalEnvironment
from mini_articraft.record import Record, append_conversation, read_conversation


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


def fake_schema(name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": name,
        "parameters": {"type": "object", "properties": {}, "required": []},
    }


def compile_success_tool() -> Tool:
    async def run_compile(context, args):
        context.compile_result = {"status": "success"}
        context.compiled_revision = context.revision
        record = Record.load(context.run_dir / "record.json")
        record.status = "success"
        record.attempts += 1
        record.result = "result/model.json"
        record.save(context.run_dir / "record.json")
        append_conversation(
            context.run_dir / "conversation.jsonl",
            {"role": "compiler", "status": "success", "error": ""},
        )
        return context.compile_result

    return Tool("compile", fake_schema("compile"), run_compile)


MODEL_CODE = """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("box")
object_model.part("base", cq.Workplane("XY").box(1, 1, 1))
"""


def test_agent_writes_compiles_and_returns_final_response(tmp_path) -> None:
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=3)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["message"] == "done"
    assert tmp_path.joinpath("box", "workspace", "main.py").is_file()
    assert "<sdk_docs>" in model.calls[0]["messages"][0]["content"]
    assert "`docs/sdk/common/35_joints.md`" in model.calls[0]["messages"][0]["content"]
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
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})],
            },
            {"text": "done too early", "tool_calls": []},
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=4)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["message"] == "done"
    assert any(
        message.get("content") == "Run compile before the final response."
        for message in model.calls[2]["messages"]
    )
    conversation = read_conversation(tmp_path / "box" / "conversation.jsonl")
    assert any(
        event.get("content") == "Run compile before the final response." for event in conversation
    )


def test_agent_emits_run_events(tmp_path) -> None:
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    captured: list[events.Event] = []
    agent = Agent(model, env, max_turns=3, on_event=captured.append)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert isinstance(captured[0], events.RunStarted)
    assert isinstance(captured[-1], events.RunFinished)
    kinds = {type(event) for event in captured}
    assert events.TurnStarted in kinds
    assert events.AssistantMessage in kinds
    assert events.ToolStarted in kinds
    assert events.ToolFinished in kinds

    write_finished = next(
        event
        for event in captured
        if isinstance(event, events.ToolFinished) and event.name == "write"
    )
    assert write_finished.payload["result"]["path"] == "main.py"
    assert write_finished.payload["result"]["bytes"] > 0

    run_finished = captured[-1]
    assert isinstance(run_finished, events.RunFinished)
    assert run_finished.status == "success"
    assert run_finished.turns == 3


def test_agent_runs_parallel_safe_tools_concurrently(monkeypatch, tmp_path) -> None:
    active = 0
    max_active = 0

    async def run_read(context, args):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return {"path": args["path"]}

    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {
            "read": Tool("read", fake_schema("read"), run_read, supports_parallel=True),
            "compile": compile_success_tool(),
        },
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [
                    call("call_1", "read", {"path": "a.py"}),
                    call("call_2", "read", {"path": "b.py"}),
                ],
            },
            {"text": "", "tool_calls": [call("call_3", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=3)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert max_active == 2
    outputs = [
        event
        for event in read_conversation(tmp_path / "box" / "conversation.jsonl")
        if event.get("type") == "function_call_output"
    ]
    assert [event["call_id"] for event in outputs[:2]] == ["call_1", "call_2"]


def test_agent_serializes_non_parallel_tools(monkeypatch, tmp_path) -> None:
    active = 0
    max_active = 0

    async def run_write(context, args):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return {"path": args["path"], "bytes": 1}

    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {
            "write": Tool("write", fake_schema("write"), run_write, mutates=True),
            "compile": compile_success_tool(),
        },
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [
                    call("call_1", "write", {"path": "a.py"}),
                    call("call_2", "write", {"path": "b.py"}),
                ],
            },
            {"text": "", "tool_calls": [call("call_3", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=3)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert max_active == 1


def test_default_run_id_uses_datetime_and_clipped_prompt() -> None:
    prompt = "Make a tiny articulated desk lamp with a compliant hinge and a wide base"

    run_id = _run_id_for_prompt(prompt, now=datetime(2026, 6, 30, 14, 5, 9))

    assert run_id == "20260630-140509-make-a-tiny-articulated-desk-lamp-with-a-complia"


def test_prompt_slug_sanitizes_and_falls_back() -> None:
    assert _prompt_slug("  Drawer: 2-stage / slide!  ") == "drawer-2-stage-slide"
    assert _prompt_slug("...") == "prompt"
    assert len(_prompt_slug("x" * 200)) == PROMPT_SLUG_MAX_LENGTH
