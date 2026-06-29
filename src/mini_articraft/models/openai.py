from __future__ import annotations

import inspect
import json
import time
from typing import Any

import websockets
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from mini_articraft.env import env_bool, env_float, env_int, getenv, require_env
from mini_articraft.errors import ModelError


class OpenAIModelConfig(BaseModel):
    model_name: str = Field(default_factory=lambda: getenv("MINI_ARTICRAFT_MODEL", "gpt-5.5"))
    reasoning_effort: str = Field(
        default_factory=lambda: getenv("MINI_ARTICRAFT_REASONING_EFFORT", "high")
    )
    reasoning_summary: str | None = Field(
        default_factory=lambda: getenv("MINI_ARTICRAFT_REASONING_SUMMARY")
    )
    max_output_tokens: int | None = Field(
        default_factory=lambda: env_int("MINI_ARTICRAFT_MAX_OUTPUT_TOKENS", 25_000)
    )
    transport: str = Field(
        default_factory=lambda: getenv("MINI_ARTICRAFT_OPENAI_TRANSPORT", "websocket")
    )
    store: bool = Field(default_factory=lambda: env_bool("MINI_ARTICRAFT_OPENAI_STORE", False))
    websocket_url: str = Field(
        default_factory=lambda: getenv(
            "MINI_ARTICRAFT_OPENAI_WEBSOCKET_URL",
            "wss://api.openai.com/v1/responses",
        )
    )
    websocket_max_age_seconds: float = Field(
        default_factory=lambda: env_float("MINI_ARTICRAFT_OPENAI_WEBSOCKET_MAX_AGE_SECONDS", 3300.0)
    )
    api_key: str = Field(default_factory=lambda: require_env("OPENAI_API_KEY"))


class OpenAIModel:
    def __init__(self, **kwargs: Any):
        self.config = OpenAIModelConfig(**kwargs)
        self.transport = _transport(self.config.transport)
        self.client = AsyncOpenAI(api_key=self.config.api_key)
        self._websocket: Any = None
        self._websocket_opened_at: float | None = None
        self._input_items: list[dict[str, Any]] = []
        self._last_message_count = 0
        self._previous_response_id: str | None = None

    async def query(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Query the OpenAI Responses API and return the completed text response."""
        new_items = self._new_input_items(messages)
        previous_response_id = None
        input_items = [*self._input_items, *new_items]
        if self.transport == "websocket" and self._previous_response_id is not None:
            previous_response_id = self._previous_response_id
            input_items = new_items

        request = self._request(messages, input_items, previous_response_id)
        request.update(kwargs)

        response = await self._send(request)
        text = _response_text(response)
        _raise_for_bad_status(response, text)
        if not text:
            raise ModelError("OpenAI response did not contain output_text")

        self._input_items.extend(new_items)
        self._input_items.extend(_response_output(response))
        self._previous_response_id = _response_id(response)
        self._last_message_count = len(messages)
        return {"text": text, "response": response}

    async def close(self) -> None:
        await self._close_websocket()
        result = self.client.close()
        if inspect.isawaitable(result):
            await result

    def _request(
        self,
        messages: list[dict[str, Any]],
        input_items: list[dict[str, Any]],
        previous_response_id: str | None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.config.model_name,
            "input": input_items,
            "reasoning": self._reasoning(),
            "include": ["reasoning.encrypted_content"],
            "store": self.config.store,
        }
        if self.config.max_output_tokens is not None:
            request["max_output_tokens"] = self.config.max_output_tokens
        if previous_response_id is not None:
            request["previous_response_id"] = previous_response_id
        instructions = _instructions(messages)
        if instructions:
            request["instructions"] = instructions
        return request

    def _reasoning(self) -> dict[str, str]:
        reasoning = {"effort": self.config.reasoning_effort}
        if self.config.reasoning_summary:
            reasoning["summary"] = self.config.reasoning_summary
        return reasoning

    async def _send(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.transport == "websocket":
            return await self._send_websocket(request)
        response = await self.client.responses.create(**request)
        return response.model_dump(mode="json")

    async def _send_websocket(self, request: dict[str, Any]) -> dict[str, Any]:
        websocket = await self._ensure_websocket()
        await websocket.send(json.dumps({"type": "response.create", **request}))
        return await _receive_websocket_response(websocket)

    async def _ensure_websocket(self) -> Any:
        if (
            self._websocket is not None
            and not getattr(self._websocket, "closed", False)
            and not self._websocket_is_stale()
        ):
            return self._websocket

        await self._close_websocket()
        self._websocket = await websockets.connect(
            self.config.websocket_url,
            additional_headers={"Authorization": f"Bearer {self.config.api_key}"},
            max_size=None,
        )
        self._websocket_opened_at = time.monotonic()
        return self._websocket

    def _websocket_is_stale(self) -> bool:
        if self._websocket_opened_at is None:
            return False
        if self.config.websocket_max_age_seconds <= 0:
            return False
        return (
            time.monotonic() - self._websocket_opened_at
        ) >= self.config.websocket_max_age_seconds

    async def _close_websocket(self) -> None:
        websocket = self._websocket
        self._websocket = None
        self._websocket_opened_at = None
        if websocket is not None:
            result = websocket.close()
            if inspect.isawaitable(result):
                await result

    def _new_input_items(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        new_items: list[dict[str, Any]] = []
        for message in messages[self._last_message_count :]:
            if "type" in message:
                new_items.append(message)
                continue
            if message["role"] == "system":
                continue
            if self._previous_response_id is not None and message["role"] == "assistant":
                continue
            new_items.append(_input_message(message))
        return new_items


async def _receive_websocket_response(websocket: Any) -> dict[str, Any]:
    while True:
        raw = await websocket.recv()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        event = json.loads(raw)
        event_type = event.get("type")

        if event_type == "error":
            raise ModelError(json.dumps(event, sort_keys=True))
        if event_type in {"response.completed", "response.incomplete"}:
            response = event.get("response")
            if not isinstance(response, dict):
                raise ModelError(f"{event_type} did not include a response object")
            return response
        if event_type == "response.failed":
            raise ModelError(json.dumps(event, sort_keys=True))


def _instructions(messages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        _message_text(message)
        for message in messages
        if "type" not in message and message["role"] == "system"
    )


def _input_message(message: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "role": message["role"],
        "content": _message_text(message),
    }
    phase = message.get("phase")
    if phase is not None:
        if message["role"] != "assistant":
            raise ValueError("phase is only valid on assistant messages")
        item["phase"] = phase
    return item


def _message_text(message: dict[str, Any]) -> str:
    content = message["content"]
    if not isinstance(content, str):
        raise TypeError("OpenAIModel messages must use string content")
    return content


def _response_id(response: dict[str, Any]) -> str | None:
    response_id = response.get("id")
    return response_id if isinstance(response_id, str) else None


def _response_output(response: dict[str, Any]) -> list[dict[str, Any]]:
    output = response.get("output")
    if not isinstance(output, list):
        return []
    return [item for item in output if isinstance(item, dict)]


def _response_text(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str):
        return output_text

    parts: list[str] = []
    for item in _response_output(response):
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def _raise_for_bad_status(response: dict[str, Any], text: str) -> None:
    status = response["status"]
    if status == "completed":
        return
    if status == "incomplete":
        details = response.get("incomplete_details") or {}
        reason = details.get("reason", "unknown")
        if text:
            raise ModelError(f"OpenAI response incomplete ({reason}); partial output returned")
        raise ModelError(f"OpenAI response incomplete ({reason}); no visible output")
    raise ModelError(f"OpenAI response ended with status {status}")


def _transport(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"websocket", "http"}:
        raise ValueError(f"unsupported OpenAI transport: {value}")
    return normalized
