from __future__ import annotations

import asyncio
import json
import shlex
import sys
from datetime import datetime
from typing import Any

import pytest

import mini_articraft.agent.tools as agent_tools
from mini_articraft.agent import Agent, events
from mini_articraft.agent.harness import (
    PROMPT_SLUG_MAX_LENGTH,
    _prompt_slug,
    _read_sdk_quickstart,
    _run_id_for_prompt,
)
from mini_articraft.agent.tools import Tool, ToolContext
from mini_articraft.agent.tools._core import workspace_digest
from mini_articraft.agent.tools._exec import MANAGER as EXEC_MANAGER
from mini_articraft.environments.local import DEFAULT_MAIN_PY, LocalEnvironment
from mini_articraft.record import Record, read_conversation


def run(awaitable):
    return asyncio.get_event_loop().run_until_complete(awaitable)


class FakeModel:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.calls: list[dict[str, Any]] = []
        self.config = type(
            "FakeConfig",
            (),
            {"openai_model": "gpt-test", "openai_reasoning_effort": "low"},
        )()

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
        usdz = context.run_dir / "result" / "usdz" / "0000.usdz"
        usdz.parent.mkdir(parents=True, exist_ok=True)
        usdz.write_bytes(b"test-usdz")
        result = {"status": "success", "usdz": str(usdz)}
        context.compile_result = result
        context.successful_compile_result = result
        context.successful_compile_digest = workspace_digest(context.workspace)
        return result

    return Tool("compile", fake_schema("compile"), run_compile)


MODEL_CODE = """
from build123d import *

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("box")
    base = model.part("base")
    base.add(Box(1, 1, 1), name="body")
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    return TestContext(object_model).report()
"""


def test_agent_writes_compiles_and_returns_final_response(tmp_path) -> None:
    model = FakeModel(
        [
            {
                "text": "",
                "cost": 0.25,
                "token_usage": {
                    "input_tokens": 100,
                    "cached_input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 120,
                },
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": MODEL_CODE})],
            },
            {
                "text": "",
                "cost": 0.25,
                "token_usage": {
                    "input_tokens": 200,
                    "cached_input_tokens": 20,
                    "output_tokens": 30,
                    "total_tokens": 230,
                },
                "tool_calls": [call("call_2", "compile", {})],
            },
            {
                "text": "done",
                "cost": 0.5,
                "token_usage": {
                    "input_tokens": 300,
                    "cached_input_tokens": 30,
                    "output_tokens": 40,
                    "total_tokens": 340,
                },
                "tool_calls": [],
            },
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=3)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["cost"] == 1.0
    assert result["token_usage"] == {
        "input_tokens": 600,
        "cached_input_tokens": 60,
        "output_tokens": 90,
        "total_tokens": 690,
    }
    assert result["message"] == "done"
    assert result["compile_report"]["status"] == "success"
    assert tmp_path.joinpath("box", "workspace", "main.py").is_file()
    record = Record.load(tmp_path / "box" / "record.json")
    assert record.status == "success"
    assert record.result == "result/usdz/0000.usdz"
    assert record.cost == 1.0
    assert record.token_usage["total_tokens"] == 690
    assert "<sdk_docs>" not in model.calls[0]["messages"][0]["content"]
    first_messages = model.calls[0]["messages"]
    assert [message["role"] for message in first_messages[:3]] == ["system", "user", "user"]
    assert first_messages[1]["content"].startswith("<sdk_quickstart>")
    assert "docs/sdk/common/30_articulated_object.md" in first_messages[1]["content"]
    assert first_messages[2]["content"].startswith("<task>")
    assert "a box" in first_messages[2]["content"]
    assert {tool["name"] for tool in model.calls[0]["tools"]} == {
        "read",
        "edit",
        "write",
        "exec_command",
        "write_stdin",
        "compile",
        "inspect_view",
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
        "<compile_required>" in str(message.get("content"))
        and "No successful compile has completed yet." in str(message.get("content"))
        for message in model.calls[2]["messages"]
    )
    conversation = read_conversation(tmp_path / "box" / "conversation.jsonl")
    assert any(
        "<compile_required>" in str(event.get("content"))
        and "No successful compile has completed yet." in str(event.get("content"))
        for event in conversation
    )


def test_agent_keeps_compile_fresh_after_read(
    monkeypatch,
    tmp_path,
) -> None:
    async def run_write(context, args):
        context.workspace.joinpath(args["path"]).write_text(args["content"], encoding="utf-8")
        return {"path": args["path"], "bytes": len(args["content"])}

    async def run_read(context, args):
        return {"path": args["path"], "text": "L1: ok"}

    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {
            "write": Tool("write", fake_schema("write"), run_write),
            "read": Tool("read", fake_schema("read"), run_read, supports_parallel=True),
            "compile": compile_success_tool(),
        },
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": "x"})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "", "tool_calls": [call("call_3", "read", {"path": "main.py"})]},
            {"text": "done after read", "tool_calls": []},
        ]
    )
    env = LocalEnvironment(output_dir=tmp_path)
    agent = Agent(model, env, max_turns=4)

    result = run(agent.run("a box", run_id="box"))

    assert result["status"] == "success"
    assert result["message"] == "done after read"
    assert len(model.calls) == 4


def test_agent_keeps_compile_fresh_after_inspection_and_noop_edits(
    monkeypatch,
    tmp_path,
) -> None:
    selected = {name: agent_tools.get(name) for name in ("write", "edit", "exec_command")}
    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        selected | {"compile": compile_success_tool()},
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": "x"})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {
                "text": "",
                "tool_calls": [
                    call(
                        "call_3",
                        "edit",
                        {"path": "main.py", "old_text": "x", "new_text": "x"},
                    )
                ],
            },
            {
                "text": "",
                "tool_calls": [
                    call(
                        "call_4",
                        "edit",
                        {"path": "main.py", "old_text": "missing", "new_text": "y"},
                    )
                ],
            },
            {
                "text": "",
                "tool_calls": [call("call_5", "exec_command", {"command": "printf inspected"})],
            },
            {"text": "done", "tool_calls": []},
        ]
    )

    result = run(Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=6).run("box"))

    assert result["status"] == "success"
    assert result["message"] == "done"


def test_agent_requires_new_compile_after_real_file_change(monkeypatch, tmp_path) -> None:
    write_tool = agent_tools.get("write")
    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {"write": write_tool, "compile": compile_success_tool()},
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": "x"})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {
                "text": "",
                "tool_calls": [call("call_3", "write", {"path": "main.py", "content": "y"})],
            },
            {"text": "too early", "tool_calls": []},
            {"text": "", "tool_calls": [call("call_4", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )

    result = run(Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=6).run("box"))

    assert result["status"] == "success"
    assert result["message"] == "done"
    assert any(
        "<compile_required>" in str(message.get("content"))
        and "changed since the last successful compile" in str(message.get("content"))
        for message in model.calls[4]["messages"]
    )


def test_running_exec_session_blocks_compile_and_finalization(monkeypatch, tmp_path) -> None:
    selected = {name: agent_tools.get(name) for name in ("exec_command", "write_stdin")}
    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        selected | {"compile": compile_success_tool()},
    )

    class SessionModel(FakeModel):
        async def query(self, messages, *, tools=None):
            self.calls.append({"messages": list(messages), "tools": list(tools or [])})
            turn = len(self.calls)
            if turn == 1:
                return {
                    "text": "",
                    "tool_calls": [
                        call(
                            "call_1",
                            "exec_command",
                            {
                                "command": "read value; printf changed > main.py",
                                "yield_time_ms": 10,
                            },
                        )
                    ],
                }
            if turn == 2:
                return {"text": "", "tool_calls": [call("call_2", "compile", {})]}
            if turn == 3:
                return {"text": "too early", "tool_calls": []}
            if turn == 4:
                session_id = next(
                    json.loads(message["output"])["result"]["session_id"]
                    for message in messages
                    if message.get("type") == "function_call_output"
                    and json.loads(message["output"]).get("result", {}).get("session_id")
                )
                return {
                    "text": "",
                    "tool_calls": [
                        call(
                            "call_3",
                            "write_stdin",
                            {"session_id": session_id, "chars": "go\n", "yield_time_ms": 1000},
                        )
                    ],
                }
            if turn == 5:
                return {"text": "", "tool_calls": [call("call_4", "compile", {})]}
            return {"text": "done", "tool_calls": []}

    result = run(
        Agent(
            SessionModel([]),
            LocalEnvironment(output_dir=tmp_path),
            max_turns=6,
        ).run("box", run_id="box")
    )

    assert result["status"] == "success"
    assert result["message"] == "done"
    conversation = read_conversation(tmp_path / "box" / "conversation.jsonl")
    assert any(
        "finish the running exec_command" in str(event.get("output")) for event in conversation
    )
    assert any("is still running" in str(event.get("content")) for event in conversation)


def test_agent_requires_visible_final_after_fresh_compile(monkeypatch, tmp_path) -> None:
    write_tool = agent_tools.get("write")
    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {"write": write_tool, "compile": compile_success_tool()},
    )
    model = FakeModel(
        [
            {
                "text": "",
                "tool_calls": [call("call_1", "write", {"path": "main.py", "content": "x"})],
            },
            {"text": "", "tool_calls": [call("call_2", "compile", {})]},
            {"text": "", "tool_calls": []},
            {"text": "done", "tool_calls": []},
        ]
    )

    result = run(Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=4).run("box"))

    assert result["message"] == "done"
    assert any(
        "<final_response_required>" in str(message.get("content"))
        for message in model.calls[3]["messages"]
    )


def test_agent_does_not_finalize_success_without_a_usdz_result(monkeypatch, tmp_path) -> None:
    async def run_compile(context, args):
        result = {"status": "success"}
        context.compile_result = result
        context.successful_compile_result = result
        context.successful_compile_digest = workspace_digest(context.workspace)
        return result

    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {"compile": Tool("compile", fake_schema("compile"), run_compile)},
    )
    model = FakeModel(
        [
            {"text": "", "tool_calls": [call("call_1", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )

    result = run(Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=2).run("box"))

    assert result["status"] == "error"
    assert result["result"] == ""
    assert result["error"] == "fresh compile did not produce a USDZ result"


def test_cached_success_survives_a_later_failed_compile(monkeypatch, tmp_path) -> None:
    attempts = 0

    async def run_compile(context, args):
        nonlocal attempts
        if context.refresh_compile_freshness():
            return context.successful_compile_result
        attempts += 1
        if attempts == 1:
            usdz = context.run_dir / "result" / "usdz" / "0000.usdz"
            usdz.parent.mkdir(parents=True, exist_ok=True)
            usdz.write_bytes(b"test-usdz")
            result = {"status": "success", "usdz": str(usdz)}
            context.compile_result = result
            context.successful_compile_result = result
            context.successful_compile_digest = workspace_digest(context.workspace)
            return result
        result = {"status": "error", "error": "bad geometry"}
        context.compile_result = result
        return result

    monkeypatch.setattr(
        agent_tools,
        "TOOLS",
        {
            "write": agent_tools.get("write"),
            "compile": Tool("compile", fake_schema("compile"), run_compile),
        },
    )
    model = FakeModel(
        [
            {"text": "", "tool_calls": [call("compile_1", "compile", {})]},
            {
                "text": "",
                "tool_calls": [call("change", "write", {"path": "main.py", "content": "bad"})],
            },
            {"text": "", "tool_calls": [call("compile_2", "compile", {})]},
            {
                "text": "",
                "tool_calls": [
                    call("restore", "write", {"path": "main.py", "content": DEFAULT_MAIN_PY})
                ],
            },
            {"text": "", "tool_calls": [call("compile_3", "compile", {})]},
            {"text": "done", "tool_calls": []},
        ]
    )

    result = run(
        Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=6).run("box", run_id="cached")
    )

    assert attempts == 2
    assert result["status"] == "success"
    assert result["result"] == "result/usdz/0000.usdz"


def test_agent_cancellation_terminates_a_live_exec_session(tmp_path) -> None:
    command = f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(60)'"

    class BlockingModel(FakeModel):
        def __init__(self) -> None:
            super().__init__([])
            self.waiting = asyncio.Event()

        async def query(
            self,
            messages: list[dict[str, Any]],
            *,
            tools: list[dict[str, Any]] | None = None,
        ) -> dict[str, Any]:
            self.calls.append({"messages": list(messages), "tools": list(tools or [])})
            if len(self.calls) == 1:
                return {
                    "text": "",
                    "tool_calls": [
                        call(
                            "exec",
                            "exec_command",
                            {"command": command, "yield_time_ms": 10},
                        )
                    ],
                }
            self.waiting.set()
            pending: asyncio.Future[None] = asyncio.Future()
            await pending
            raise AssertionError("blocking query unexpectedly completed")

    async def exercise() -> None:
        env = LocalEnvironment(output_dir=tmp_path)
        model = BlockingModel()
        task = asyncio.create_task(Agent(model, env, max_turns=3).run("box", run_id="cancel"))
        await asyncio.wait_for(model.waiting.wait(), timeout=5)
        context = ToolContext(env, tmp_path / "cancel", tmp_path / "cancel" / "workspace")
        assert EXEC_MANAGER.has_live_session(context)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not EXEC_MANAGER.has_live_session(context)

    run(exercise())


def test_agent_fails_third_consecutive_empty_response(tmp_path) -> None:
    model = FakeModel([{"text": "", "tool_calls": []} for _ in range(3)])

    result = run(Agent(model, LocalEnvironment(output_dir=tmp_path), max_turns=3).run("box"))

    assert result["status"] == "error"
    assert "three consecutive responses" in result["error"]
    assert any(
        "Do not continue with reasoning-only output." in str(message.get("content"))
        for message in model.calls[2]["messages"]
    )


def test_agent_records_model_query_failure(tmp_path) -> None:
    class FailingModel(FakeModel):
        async def query(self, messages, *, tools=None):
            self.calls.append({"messages": list(messages), "tools": list(tools or [])})
            raise RuntimeError("socket closed")

    result = run(
        Agent(FailingModel([]), LocalEnvironment(output_dir=tmp_path), max_turns=3).run("box")
    )

    assert result["status"] == "error"
    assert result["result"] == ""
    assert result["error"] == "model query failed: RuntimeError: socket closed"


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
    assert captured[0].model == "gpt-test"
    assert captured[0].reasoning_effort == "low"
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

    compile_finished = next(
        event
        for event in captured
        if isinstance(event, events.ToolFinished) and event.name == "compile"
    )
    assert "compile_report" in compile_finished.payload["result"]
    assert "compile_signals" not in compile_finished.payload["result"]

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
            "write": Tool("write", fake_schema("write"), run_write, supports_parallel=True),
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


def test_sdk_quickstart_user_message_is_preloaded() -> None:
    content = _read_sdk_quickstart()

    assert content.startswith("<sdk_quickstart>")
    assert "This SDK quickstart is preloaded for the run." in content
    assert "plausible build123d and mesh approaches" in content
    assert "parallel reads" in content
    assert "Do not stop at the first workable API" in content
    assert "# SDK quickstart" in content
    assert "`docs/sdk/common/40_testing.md`" in content
    assert content.endswith("</sdk_quickstart>")


def test_default_run_id_uses_datetime_and_clipped_prompt() -> None:
    prompt = "Make a tiny articulated desk lamp with a compliant hinge and a wide base"

    run_id = _run_id_for_prompt(prompt, now=datetime(2026, 6, 30, 14, 5, 9))

    assert run_id == "20260630-140509-make-a-tiny-articulated-desk-lamp-with-a-complia"


def test_prompt_slug_sanitizes_and_falls_back() -> None:
    assert _prompt_slug("  Drawer: 2-stage / slide!  ") == "drawer-2-stage-slide"
    assert _prompt_slug("...") == "prompt"
    assert len(_prompt_slug("x" * 200)) == PROMPT_SLUG_MAX_LENGTH
