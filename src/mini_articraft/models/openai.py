from __future__ import annotations

import os
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from mini_articraft.env import load_env
from mini_articraft.errors import ModelError


class OpenAIModelConfig(BaseModel):
    model_name: str = Field(default_factory=lambda: os.getenv("MINI_ARTICRAFT_MODEL", "gpt-5.5"))
    reasoning_effort: str = Field(
        default_factory=lambda: os.getenv("MINI_ARTICRAFT_REASONING_EFFORT", "high")
    )
    api_key: str = Field(default_factory=lambda: os.environ["OPENAI_API_KEY"])

    def __init__(self, **data: Any):
        load_env()
        super().__init__(**data)


class OpenAIModel:
    def __init__(self, **kwargs: Any):
        self.config = OpenAIModelConfig(**kwargs)
        self.client = OpenAI(api_key=self.config.api_key)

    def query(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """Query the OpenAI Responses API and return the completed text response."""
        request: dict[str, Any] = {
            "model": self.config.model_name,
            "input": _input_messages(messages),
            "reasoning": {"effort": self.config.reasoning_effort},
        }
        instructions = _instructions(messages)
        if instructions:
            request["instructions"] = instructions
        request.update(kwargs)

        response = self.client.responses.create(**request)
        text = response.output_text
        if not text:
            raise ModelError("OpenAI response did not contain output_text")
        return {"text": text, "response": response.model_dump(mode="json")}


def _instructions(messages: list[dict[str, Any]]) -> str:
    return "\n\n".join(_message_text(message) for message in messages if message["role"] == "system")


def _input_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": message["role"],
            "content": _message_text(message),
        }
        for message in messages
        if message["role"] != "system"
    ]


def _message_text(message: dict[str, Any]) -> str:
    content = message["content"]
    if not isinstance(content, str):
        raise TypeError("OpenAIModel messages must use string content")
    return content
