from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

import mini_articraft.agent.tools as tools
from mini_articraft import Environment, Model, package_dir
from mini_articraft.agent.tools import ToolContext
from mini_articraft.record import Record, append_conversation


class AgentConfig(BaseModel):
    attempts: int = 3
    output_path: Path | None = None


class Agent:
    def __init__(self, model: Model, env: Environment, **kwargs: Any):
        self.config = AgentConfig(**kwargs)
        self.model = model
        self.env = env
        self.messages: list[dict[str, Any]] = []

    async def run(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        run_id = str(kwargs.get("run_id") or f"run-{uuid.uuid4().hex[:8]}")
        run_dir = self.env.create_run(run_id)
        context = ToolContext(self.env, run_dir, run_dir / "workspace")
        conversation_path = run_dir / "conversation.jsonl"

        self.messages = [
            {"role": "system", "content": _read_prompt("system.md")},
            {"role": "user", "content": _read_prompt("task.md").replace("{{ prompt }}", prompt)},
        ]
        for message in self.messages:
            append_conversation(conversation_path, message)

        final_text = ""
        for _ in range(self.config.attempts):
            response = await self.model.query(self.messages, tools=tools.schemas())
            text = str(response.get("text") or "")
            tool_calls = list(response.get("tool_calls") or [])
            assistant = {"role": "assistant", "content": text, "tool_calls": tool_calls}
            self.messages.append(assistant)
            append_conversation(conversation_path, assistant)

            if not tool_calls:
                if context.compiled_revision == context.revision and context.compile_result:
                    final_text = text
                    break
                reminder = {"role": "user", "content": "Run compile before the final response."}
                self.messages.append(reminder)
                append_conversation(conversation_path, reminder)
                continue

            for call in tool_calls:
                item = await self._run_tool(context, call)
                self.messages.append(item)
                append_conversation(conversation_path, item)
        else:
            record = Record.load(run_dir / "record.json")
            record.status = "error"
            record.error = "agent hit attempts limit"
            record.save(run_dir / "record.json")

        data = Record.load(run_dir / "record.json").to_dict()
        data["message"] = final_text
        data["run"] = str(run_dir)
        if self.config.output_path:
            Record.load(run_dir / "record.json").save(self.config.output_path)
        return data

    async def _run_tool(self, context: ToolContext, call: dict[str, Any]) -> dict[str, Any]:
        name = str(call["name"])
        call_id = str(call["id"])
        try:
            tool = tools.get(name)
            payload = {"result": await tool.run(context, _arguments(call))}
            if tool.mutates:
                context.revision += 1
        except Exception as exc:
            payload = {"error": str(exc)}
        return tools.result_item(call_id, payload)


def _arguments(call: dict[str, Any]) -> dict[str, Any]:
    raw = call.get("arguments") or "{}"
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("tool arguments must be a JSON object")
    return payload


def _read_prompt(name: str) -> str:
    return (package_dir / "prompts" / name).read_text(encoding="utf-8")
