from __future__ import annotations

import json
from typing import Any

import websockets

from mini_articraft.errors import ModelError
from mini_articraft.settings import Settings, get_settings

_WEBSOCKET_URL = "wss://api.openai.com/v1/responses"
_MAX_OUTPUT_TOKENS = 128_000
_CONTEXT_WINDOWS = {
    "gpt-5.5-pro": 1_050_000,
    "gpt-5.5": 1_050_000,
    "gpt-5.4-pro": 1_050_000,
    "gpt-5.4-mini": 400_000,
    "gpt-5.4-nano": 400_000,
    "gpt-5.4": 1_050_000,
}
_TOKEN_PRICES_PER_MILLION = {
    "gpt-5.5-pro": (30.0, 30.0, 180.0),
    "gpt-5.5": (5.0, 0.5, 30.0),
    "gpt-5.4-pro": (30.0, 30.0, 180.0),
    "gpt-5.4-mini": (0.75, 0.075, 4.5),
    "gpt-5.4-nano": (0.2, 0.02, 1.25),
    "gpt-5.4": (2.5, 0.25, 15.0),
}


class OpenAIModel:
    def __init__(self, settings: Settings | None = None):
        self.config = settings or get_settings()
        self._websocket: Any = None
        self._input_items: list[dict[str, Any]] = []
        self._last_message_count = 0
        self._previous_response_id: str | None = None

    @property
    def context_window_tokens(self) -> int:
        return context_window_tokens_for(self.config.openai_model) or 0

    async def query(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Query the OpenAI Responses API and return the completed text response."""
        new_items = self._new_input_items(messages)
        previous_response_id = None
        input_items = [*self._input_items, *new_items]
        if self._previous_response_id is not None:
            previous_response_id = self._previous_response_id
            input_items = new_items

        request = self._request(messages, input_items, previous_response_id, tools)

        response = await self._send_websocket(request)
        text = _response_text(response)
        tool_calls = _response_tool_calls(response)
        _raise_for_bad_status(response, text)
        if not text and not tool_calls:
            raise ModelError("OpenAI response did not contain output_text")

        self._input_items.extend(new_items)
        self._input_items.extend(_response_output(response))
        self._previous_response_id = _response_id(response)
        self._last_message_count = len(messages)
        return {
            "text": text,
            "tool_calls": tool_calls,
            "token_usage": _response_token_usage(response),
            "cost": _response_cost(response),
            "response": response,
        }

    async def close(self) -> None:
        await self._close_websocket()

    def _request(
        self,
        messages: list[dict[str, Any]],
        input_items: list[dict[str, Any]],
        previous_response_id: str | None,
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.config.openai_model,
            "input": input_items,
            "reasoning": self._reasoning(),
            "include": ["reasoning.encrypted_content"],
            "max_output_tokens": _MAX_OUTPUT_TOKENS,
            "store": False,
        }
        if previous_response_id is not None:
            request["previous_response_id"] = previous_response_id
        if tools:
            request["tools"] = tools
            request["parallel_tool_calls"] = True
        instructions = _instructions(messages)
        if instructions:
            request["instructions"] = instructions
        return request

    def _reasoning(self) -> dict[str, str]:
        return {"effort": self.config.openai_reasoning_effort}

    async def _send_websocket(self, request: dict[str, Any]) -> dict[str, Any]:
        websocket = await self._ensure_websocket()
        await websocket.send(json.dumps({"type": "response.create", **request}))
        return await _receive_websocket_response(websocket)

    async def _ensure_websocket(self) -> Any:
        if self._websocket is not None and not getattr(self._websocket, "closed", False):
            return self._websocket

        await self._close_websocket()
        self._websocket = await websockets.connect(
            _WEBSOCKET_URL,
            additional_headers={"Authorization": f"Bearer {self.config.openai_api_key}"},
            max_size=None,
        )
        return self._websocket

    async def _close_websocket(self) -> None:
        websocket = self._websocket
        self._websocket = None
        if websocket is not None:
            await websocket.close()

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


def _response_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for item in _response_output(response):
        if item.get("type") != "function_call":
            continue
        calls.append(
            {
                "id": item["call_id"],
                "name": item["name"],
                "arguments": item.get("arguments") or "{}",
            }
        )
    return calls


def _response_cost(response: dict[str, Any]) -> float:
    prices = _prices_for(str(response.get("model") or ""))
    usage = _response_token_usage(response)
    if not usage or prices is None:
        return 0.0

    input_price, cached_price, output_price = prices
    uncached_tokens = max(0, usage["input_tokens"] - usage["cached_input_tokens"])
    return round(
        (
            uncached_tokens * input_price
            + usage["cached_input_tokens"] * cached_price
            + usage["output_tokens"] * output_price
        )
        / 1_000_000,
        8,
    )


def _response_token_usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return {}

    details = usage.get("input_tokens_details")
    cached_tokens = _int(details.get("cached_tokens")) if isinstance(details, dict) else 0
    input_tokens = _int(usage.get("input_tokens"))
    output_tokens = _int(usage.get("output_tokens"))
    total_tokens = _int(usage.get("total_tokens")) or input_tokens + output_tokens
    return {
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _prices_for(model: str) -> tuple[float, float, float] | None:
    for name, prices in sorted(_TOKEN_PRICES_PER_MILLION.items(), key=lambda item: -len(item[0])):
        if model == name or model.startswith(f"{name}-"):
            return prices
    return None


def context_window_tokens_for(model: str) -> int | None:
    for name, tokens in sorted(_CONTEXT_WINDOWS.items(), key=lambda item: -len(item[0])):
        if model == name or model.startswith(f"{name}-"):
            return tokens
    return None


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
