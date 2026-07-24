from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import uuid
from dataclasses import dataclass
from typing import Any

from mini_articraft.errors import ModelError
from mini_articraft.settings import DEFAULT_GEMINI_MODEL, Settings, get_settings

logger = logging.getLogger(__name__)

_RETRY_BASE_SECONDS = 0.5
_RETRY_MAX_SECONDS = 20.0
_SUPPORTED_MODELS = {
    "gemini-3.6-flash",
    "gemini-3.1-pro-preview",
}


@dataclass(frozen=True)
class _ModelSpec:
    context_window_tokens: int
    input_price: float
    cached_input_price: float
    output_price: float
    prompt_tier_threshold_tokens: int | None = None
    input_price_above_threshold: float | None = None
    cached_input_price_above_threshold: float | None = None
    output_price_above_threshold: float | None = None


# Prices are USD per million tokens for the Gemini Developer API Standard tier.
_MODELS = {
    "gemini-3.6-flash": _ModelSpec(
        context_window_tokens=1_000_000,
        input_price=1.50,
        cached_input_price=0.15,
        output_price=7.50,
    ),
    "gemini-3.1-pro-preview": _ModelSpec(
        context_window_tokens=1_000_000,
        input_price=2.00,
        cached_input_price=0.20,
        output_price=12.00,
        prompt_tier_threshold_tokens=200_000,
        input_price_above_threshold=4.00,
        cached_input_price_above_threshold=0.40,
        output_price_above_threshold=18.00,
    ),
}


class GeminiModel:
    def __init__(self, settings: Settings | None = None, *, client: Any | None = None):
        self.config = settings or get_settings()
        _raise_for_unsupported_model(self.config.gemini_model)
        self._client = client
        self._tool_call_names: dict[str, str] = {}

    @property
    def context_window_tokens(self) -> int:
        return context_window_tokens_for(self.config.gemini_model) or 0

    async def query(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Query Gemini and return the response shape used by the agent."""
        contents = _contents(messages, self._tool_call_names)
        config = _generate_config(_instructions(messages), tools)
        response = await self._send_with_retries(contents, config)
        text = _response_text(response)
        tool_calls = _response_tool_calls(response)
        for call in tool_calls:
            self._tool_call_names[str(call["id"])] = str(call["name"])
        if not text and not tool_calls:
            raise ModelError("Gemini response did not contain text or tool calls")

        token_usage = _response_token_usage(response)
        return {
            "text": text,
            "tool_calls": tool_calls,
            "token_usage": token_usage,
            "cost": _response_cost(self.config.gemini_model, token_usage),
            "response": response,
        }

    async def close(self) -> None:
        return None

    async def _send_with_retries(self, contents: list[Any], config: Any) -> Any:
        for attempt in range(1, self.config.gemini_max_attempts + 1):
            try:
                return await self._send(contents, config)
            except Exception as exc:
                if attempt >= self.config.gemini_max_attempts or not _should_retry(exc):
                    if isinstance(exc, ModelError):
                        raise
                    raise ModelError(f"Gemini request failed: {_format_exception(exc)}") from exc
                delay = random.random() * min(
                    _RETRY_MAX_SECONDS,
                    _RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
                )
                logger.warning(
                    "Gemini request failed (attempt %s/%s), retrying in %.2fs: %s",
                    attempt,
                    self.config.gemini_max_attempts,
                    delay,
                    _format_exception(exc),
                )
                await asyncio.sleep(delay)
        raise AssertionError("retry loop did not return or raise")

    async def _send(self, contents: list[Any], config: Any) -> Any:
        async def request() -> Any:
            return await self._client_or_create().aio.models.generate_content(
                model=self.config.gemini_model,
                contents=contents,
                config=config,
            )

        return await asyncio.wait_for(request(), timeout=self.config.gemini_request_timeout_seconds)

    def _client_or_create(self) -> Any:
        if self._client is None:
            api_key = gemini_api_key_value(self.config)
            if not api_key:
                raise ModelError("Gemini credentials are required. Set GEMINI_API_KEY.")
            try:
                from google import genai  # type: ignore
            except Exception as exc:
                raise ModelError(
                    "Gemini provider selected but the `google-genai` package is not installed."
                ) from exc
            self._client = genai.Client(api_key=api_key)
        return self._client


def gemini_api_key_value(settings: Settings) -> str:
    return (settings.gemini_api_key or "").strip()


def _instructions(messages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        _message_text(message)
        for message in messages
        if "type" not in message and message.get("role") == "system"
    )


def _contents(messages: list[dict[str, Any]], tool_call_names: dict[str, str]) -> list[Any]:
    return [
        content
        for message in messages
        if (content := _content(message, tool_call_names)) is not None
    ]


def _content(message: dict[str, Any], tool_call_names: dict[str, str]) -> Any | None:
    if message.get("role") == "system":
        return None
    if message.get("type") == "function_call_output":
        return _function_response_content(message, tool_call_names)
    if message.get("role") == "assistant":
        return _assistant_content(message, tool_call_names)
    if message.get("role") == "user":
        return _text_content("user", _message_text(message))
    return None


def _text_content(role: str, text: str) -> Any:
    from google.genai import types  # type: ignore

    return types.Content(role=role, parts=[types.Part(text=text)])


def _assistant_content(message: dict[str, Any], tool_call_names: dict[str, str]) -> Any | None:
    from google.genai import types  # type: ignore

    parts: list[Any] = []
    text = _message_text(message)
    if text:
        parts.append(types.Part(text=text))

    for call in message.get("tool_calls") or []:
        if not isinstance(call, dict):
            continue
        call_id = str(call.get("id") or "")
        name = str(call.get("name") or "")
        if call_id and name:
            tool_call_names[call_id] = name
        signature = _decode_signature(
            call.get("thought_signature")
            or call.get("extra_content", {}).get("google", {}).get("thought_signature")
        )
        parts.append(
            types.Part(
                function_call=types.FunctionCall(name=name, args=_arguments(call)),
                thought_signature=signature,
            )
        )

    if not parts:
        return None
    return types.Content(role="model", parts=parts)


def _function_response_content(
    message: dict[str, Any],
    tool_call_names: dict[str, str],
) -> Any:
    from google.genai import types  # type: ignore

    call_id = str(message.get("call_id") or "")
    name = tool_call_names.get(call_id) or call_id
    return types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name=name,
                    response=_tool_response_body(message.get("output")),
                )
            )
        ],
    )


def _tool_response_body(output: Any) -> Any:
    if isinstance(output, list):
        for item in output:
            if isinstance(item, dict) and item.get("type") == "input_text":
                return _json_body(item.get("text"))
        return {"output": output}
    return _json_body(output)


def _json_body(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"output": value}
    return value if isinstance(value, dict) else {"output": value}


def _arguments(call: dict[str, Any]) -> dict[str, Any]:
    raw = call.get("arguments") or "{}"
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}
        return parsed if isinstance(parsed, dict) else {"_raw": raw}
    return {"_raw": raw}


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if not isinstance(content, str):
        raise TypeError("GeminiModel messages must use string content")
    return content


def _generate_config(system_instruction: str, tools: list[dict[str, Any]] | None) -> Any:
    from google.genai import types  # type: ignore

    declarations = _function_declarations(tools or [])
    return types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        tools=[types.Tool(function_declarations=declarations)] if declarations else None,
    )


def _function_declarations(tools: list[dict[str, Any]]) -> list[Any]:
    from google.genai import types  # type: ignore

    declarations: list[Any] = []
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            continue
        declarations.append(
            types.FunctionDeclaration(
                name=str(tool.get("name") or ""),
                description=str(tool.get("description") or ""),
                parameters=_strip_unsupported_schema_keys(tool.get("parameters")),
            )
        )
    return declarations


def _strip_unsupported_schema_keys(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {
            key: _strip_unsupported_schema_keys(value)
            for key, value in schema.items()
            if key not in {"additionalProperties", "strict"}
        }
    if isinstance(schema, list):
        return [_strip_unsupported_schema_keys(item) for item in schema]
    return schema


def _response_text(response: Any) -> str:
    return "".join(
        str(part.text)
        for part in _response_parts(response)
        if getattr(part, "text", None) and not getattr(part, "thought", False)
    )


def _response_tool_calls(response: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for part in _response_parts(response):
        function_call = getattr(part, "function_call", None)
        if function_call is None:
            continue
        args = getattr(function_call, "args", None)
        if args is None:
            args = getattr(function_call, "arguments", None)
        call_id = str(getattr(function_call, "id", None) or f"call_{uuid.uuid4().hex}")
        call: dict[str, Any] = {
            "id": call_id,
            "name": str(getattr(function_call, "name", "") or ""),
            "arguments": json.dumps(args) if isinstance(args, (dict, list)) else str(args or "{}"),
        }
        signature = _encode_signature(
            getattr(part, "thought_signature", None)
            or getattr(function_call, "thought_signature", None)
        )
        if signature:
            call["thought_signature"] = signature
            call["extra_content"] = {"google": {"thought_signature": signature}}
        calls.append(call)
    return calls


def _response_parts(response: Any) -> list[Any]:
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    raw_parts = getattr(content, "parts", None) or []
    if isinstance(raw_parts, list):
        return raw_parts
    try:
        return list(raw_parts)
    except TypeError:
        return [raw_parts]


def _response_token_usage(response: Any) -> dict[str, int]:
    meta = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if meta is None:
        return {}

    prompt_tokens = _usage_int(meta, "prompt_token_count")
    candidates_tokens = _usage_int(meta, "candidates_token_count")
    total_tokens = _usage_int(meta, "total_token_count") or prompt_tokens + candidates_tokens
    cached_tokens = _usage_int(meta, "cached_content_token_count")
    return {
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "candidates_tokens": candidates_tokens,
        "input_tokens": prompt_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": candidates_tokens,
        "total_tokens": total_tokens,
    }


def _usage_int(meta: Any, name: str) -> int:
    value = meta.get(name) if isinstance(meta, dict) else getattr(meta, name, None)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _response_cost(model: str, usage: dict[str, int]) -> float:
    spec = _model_spec(model)
    if spec is None or not usage:
        return 0.0

    input_price = spec.input_price
    cached_input_price = spec.cached_input_price
    output_price = spec.output_price
    prompt_tokens = usage.get("prompt_tokens", 0)
    if (
        spec.prompt_tier_threshold_tokens is not None
        and prompt_tokens > spec.prompt_tier_threshold_tokens
    ):
        input_price = spec.input_price_above_threshold or input_price
        cached_input_price = spec.cached_input_price_above_threshold or cached_input_price
        output_price = spec.output_price_above_threshold or output_price

    cached_tokens = usage.get("cached_tokens", 0)
    uncached_tokens = max(0, prompt_tokens - cached_tokens)
    return round(
        (
            uncached_tokens * input_price
            + cached_tokens * cached_input_price
            + usage.get("candidates_tokens", 0) * output_price
        )
        / 1_000_000,
        8,
    )


def _model_spec(model: str) -> _ModelSpec | None:
    return _MODELS.get(model)


def context_window_tokens_for(model: str) -> int | None:
    spec = _model_spec(model)
    return spec.context_window_tokens if spec is not None else None


def _raise_for_unsupported_model(model: str) -> None:
    if model not in _SUPPORTED_MODELS:
        supported = ", ".join(sorted(_SUPPORTED_MODELS))
        raise ModelError(f"Unsupported Gemini model: {model}. Supported models: {supported}")


def _http_status(exc: BaseException) -> int | None:
    for attr in ("status_code", "http_status", "status", "code"):
        value = getattr(exc, attr, None)
        try:
            if callable(value):
                value = value()
        except Exception:
            value = None
        if isinstance(value, int) and 100 <= value <= 599:
            return value

    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None) or getattr(response, "status", None)
    return status if isinstance(status, int) and 100 <= status <= 599 else None


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return True

    status = _http_status(exc)
    if status is not None:
        if status in {408, 409, 425, 429} or status >= 500:
            return True
        if 400 <= status < 500:
            return False

    message = str(exc).lower()
    if any(
        token in message
        for token in (
            "overloaded",
            "temporarily unavailable",
            "service unavailable",
            "timeout",
            "timed out",
            "deadline exceeded",
            "rate limit",
            "too many requests",
            "resource exhausted",
            "connection reset",
            "connection aborted",
            "connection refused",
            "internal error",
            "backend error",
        )
    ):
        return True
    if any(
        token in message
        for token in (
            "api key",
            "unauthorized",
            "permission denied",
            "forbidden",
            "invalid argument",
            "not found",
        )
    ):
        return False
    return False


def _format_exception(exc: BaseException) -> str:
    status = _http_status(exc)
    message = str(exc).strip()
    summary = type(exc).__name__
    if status is not None:
        summary += f" (HTTP {status})"
    return f"{summary}: {message or repr(exc)}"


def _encode_signature(signature: bytes | str | None) -> str | None:
    if signature is None:
        return None
    if isinstance(signature, bytes):
        return base64.b64encode(signature).decode("utf-8")
    return signature


def _decode_signature(signature: bytes | str | None) -> bytes | None:
    if signature is None:
        return None
    if isinstance(signature, bytes):
        return signature
    try:
        return base64.b64decode(signature)
    except Exception:
        return signature.encode("utf-8")


__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "GeminiModel",
    "context_window_tokens_for",
    "gemini_api_key_value",
]
