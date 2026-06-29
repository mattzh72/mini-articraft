from __future__ import annotations

from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from mini_articraft.env import env_int, getenv, require_env
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
    api_key: str = Field(default_factory=lambda: require_env("OPENAI_API_KEY"))


class OpenAIModel:
    def __init__(self, **kwargs: Any):
        self.config = OpenAIModelConfig(**kwargs)
        self.client = OpenAI(api_key=self.config.api_key)

    def query(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Query the OpenAI Responses API and return the completed text response."""
        request: dict[str, Any] = {
            "model": self.config.model_name,
            "input": _input_messages(messages),
            "reasoning": self._reasoning(),
            "include": ["reasoning.encrypted_content"],
        }
        if self.config.max_output_tokens is not None:
            request["max_output_tokens"] = self.config.max_output_tokens
        instructions = _instructions(messages)
        if instructions:
            request["instructions"] = instructions
        request.update(kwargs)

        response = self.client.responses.create(**request)
        response_data = response.model_dump(mode="json")
        text = response.output_text
        _raise_for_bad_status(response_data, text)
        if not text:
            raise ModelError("OpenAI response did not contain output_text")
        return {"text": text, "response": response_data}

    def _reasoning(self) -> dict[str, str]:
        reasoning = {"effort": self.config.reasoning_effort}
        if self.config.reasoning_summary:
            reasoning["summary"] = self.config.reasoning_summary
        return reasoning


def _instructions(messages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        _message_text(message)
        for message in messages
        if "type" not in message and message["role"] == "system"
    )


def _input_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in messages:
        if "type" in message:
            items.append(message)
            continue
        if message["role"] == "system":
            continue
        items.append(_input_message(message))
    return items


def _input_message(message: dict[str, Any]) -> dict[str, Any]:
    item = {
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
