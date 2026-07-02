from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

import mini_articraft.agent.tools as tools
from mini_articraft import Environment, Model, package_dir
from mini_articraft.agent import events
from mini_articraft.agent.tools import ToolContext
from mini_articraft.record import Record, append_conversation
from mini_articraft.settings import DEFAULT_MAX_TURNS

PROMPT_SLUG_MAX_LENGTH = 48


class AgentConfig(BaseModel):
    max_turns: int = DEFAULT_MAX_TURNS
    output_path: Path | None = None


class Agent:
    def __init__(
        self,
        model: Model,
        env: Environment,
        *,
        on_event: Callable[[events.Event], None] | None = None,
        **kwargs: Any,
    ):
        self.config = AgentConfig(**kwargs)
        self.model = model
        self.env = env
        self.messages: list[dict[str, Any]] = []
        self._on_event = on_event

    def _emit(self, event: events.Event) -> None:
        if self._on_event is not None:
            self._on_event(event)

    async def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        run_id = str(kwargs.get("run_id") or _run_id_for_prompt(prompt))
        run_dir = self.env.create_run(run_id)
        context = ToolContext(self.env, run_dir, run_dir / "workspace")
        conversation_path = run_dir / "conversation.jsonl"

        self.messages = [
            {
                "role": "system",
                "content": _read_prompt("system.md"),
            },
            {
                "role": "user",
                "content": _read_sdk_quickstart(),
            },
            {"role": "user", "content": _read_prompt("task.md").replace("{{ prompt }}", prompt)},
        ]
        for message in self.messages:
            append_conversation(conversation_path, message)

        model_config = getattr(self.model, "config", None)
        model_name = getattr(model_config, "openai_model", "")
        reasoning_effort = getattr(model_config, "openai_reasoning_effort", "")
        context_window_tokens = int(getattr(self.model, "context_window_tokens", 0) or 0)
        self._emit(
            events.RunStarted(
                run_id,
                model_name,
                prompt,
                reasoning_effort,
                context_window_tokens,
            )
        )

        started = time.perf_counter()
        final_text = ""
        cost = 0.0
        token_usage: dict[str, int] = {}
        turn = 0
        hit_max_turns = False
        for turn in range(1, self.config.max_turns + 1):
            self._emit(events.TurnStarted(turn))
            response = await self.model.query(self.messages, tools=tools.schemas())
            cost += _cost(response)
            response_usage = _token_usage(response)
            token_usage = _add_token_usage(token_usage, response_usage)
            _save_cost(run_dir, cost, token_usage)
            text = str(response.get("text") or "")
            tool_calls = list(response.get("tool_calls") or [])
            assistant = {
                "role": "assistant",
                "content": text,
                "tool_calls": tool_calls,
                "token_usage": response_usage,
            }
            self.messages.append(assistant)
            append_conversation(conversation_path, assistant)
            self._emit(events.AssistantMessage(turn, text, tool_calls, response_usage))

            if not tool_calls:
                if context.compile_is_fresh and context.compile_result:
                    final_text = text
                    break
                reminder = {"role": "user", "content": "Run compile before the final response."}
                self.messages.append(reminder)
                append_conversation(conversation_path, reminder)
                continue

            await self._run_tool_calls(context, tool_calls, conversation_path)
        else:
            hit_max_turns = True

        record = Record.load(run_dir / "record.json")
        if hit_max_turns:
            record.status = "error"
            record.error = "agent hit max turns limit"
            record.save(run_dir / "record.json")

        data = record.to_dict()
        data["message"] = final_text
        data["run"] = str(run_dir)
        if context.compile_result and isinstance(
            context.compile_result.get("compile_report"),
            dict,
        ):
            data["compile_report"] = context.compile_result["compile_report"]
        if self.config.output_path:
            record.save(self.config.output_path)
        self._emit(
            events.RunFinished(
                status=str(data.get("status") or ""),
                run=str(run_dir),
                result=str(data.get("result") or ""),
                error=str(data.get("error") or ""),
                turns=turn,
                duration=round(time.perf_counter() - started, 4),
                cost=float(data.get("cost") or 0.0),
                token_usage=dict(data.get("token_usage") or {}),
            )
        )
        return data

    async def _run_tool_calls(
        self,
        context: ToolContext,
        tool_calls: list[dict[str, Any]],
        conversation_path: Path,
    ) -> None:
        batch: list[dict[str, Any]] = []
        for call in tool_calls:
            if _supports_parallel(call):
                batch.append(call)
                continue

            await self._run_tool_batch(context, batch, conversation_path)
            batch = []
            await self._run_tool_batch(context, [call], conversation_path)

        await self._run_tool_batch(context, batch, conversation_path)

    async def _run_tool_batch(
        self,
        context: ToolContext,
        tool_calls: list[dict[str, Any]],
        conversation_path: Path,
    ) -> None:
        if not tool_calls:
            return

        started = []
        for call in tool_calls:
            self._emit(
                events.ToolStarted(
                    str(call["id"]), str(call["name"]), str(call.get("arguments") or "{}")
                )
            )
            started.append(time.perf_counter())

        items = await asyncio.gather(*(self._run_tool(context, call) for call in tool_calls))
        for call, item, tool_started in zip(tool_calls, items, started, strict=True):
            self.messages.append(item)
            append_conversation(conversation_path, item)
            self._emit(
                events.ToolFinished(
                    str(call["id"]),
                    str(call["name"]),
                    json.loads(item["output"]),
                    round(time.perf_counter() - tool_started, 4),
                )
            )

    async def _run_tool(self, context: ToolContext, call: dict[str, Any]) -> dict[str, Any]:
        name = str(call["name"])
        call_id = str(call["id"])
        try:
            if name != "compile":
                context.compile_is_fresh = False
            tool = tools.get(name)
            payload = {"result": await tool.run(context, _arguments(call))}
        except Exception as exc:
            payload = {"error": str(exc)}
        return tools.result_item(call_id, payload)


def _arguments(call: dict[str, Any]) -> dict[str, Any]:
    raw = call.get("arguments") or "{}"
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("tool arguments must be a JSON object")
    return payload


def _supports_parallel(call: dict[str, Any]) -> bool:
    try:
        return tools.get(str(call["name"])).supports_parallel
    except (KeyError, ValueError):
        return False


def _save_cost(run_dir: Path, cost: float, token_usage: dict[str, int]) -> None:
    record = Record.load(run_dir / "record.json")
    record.cost = round(cost, 8)
    record.token_usage = dict(token_usage)
    record.save(run_dir / "record.json")


def _cost(response: dict[str, Any]) -> float:
    try:
        return float(response.get("cost") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _token_usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("token_usage")
    if not isinstance(usage, dict):
        return {}
    return {str(key): int(value) for key, value in usage.items()}


def _add_token_usage(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    keys = left.keys() | right.keys()
    return {key: left.get(key, 0) + right.get(key, 0) for key in keys}


def _read_prompt(name: str) -> str:
    return (package_dir / "prompts" / name).read_text(encoding="utf-8")


def _read_sdk_quickstart() -> str:
    quickstart = (package_dir / "sdk" / "docs" / "common" / "00_quickstart.md").read_text(
        encoding="utf-8"
    )
    return (
        "<sdk_quickstart>\n"
        "This SDK quickstart is preloaded for the run. Use it as the first "
        "reference. Before writing code, read thoroughly through the routed docs "
        "and local build123d examples that relate to the current object.\n\n"
        f"{quickstart.rstrip()}\n"
        "</sdk_quickstart>"
    )


def _run_id_for_prompt(prompt: str, *, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{_prompt_slug(prompt)}"


def _prompt_slug(prompt: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")
    slug = slug[:PROMPT_SLUG_MAX_LENGTH].strip("-")
    return slug or "prompt"
