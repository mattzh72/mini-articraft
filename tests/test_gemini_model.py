from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from mini_articraft.errors import ModelError
from mini_articraft.models.gemini import (
    GeminiModel,
    context_window_tokens_for,
    gemini_api_key_value,
)
from mini_articraft.settings import DEFAULT_GEMINI_MODEL, Settings, get_settings


def run(awaitable):
    return asyncio.get_event_loop().run_until_complete(awaitable)


class FakeModels:
    def __init__(self, responses: list[Any]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[Any]):
        self.models = FakeModels(responses)
        self.aio = SimpleNamespace(models=self.models)


def text_response(
    text: str,
    *,
    prompt_tokens: int = 0,
    cached_tokens: int = 0,
    candidates_tokens: int = 0,
) -> Any:
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(text=text)])),
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=prompt_tokens,
            cached_content_token_count=cached_tokens,
            candidates_token_count=candidates_tokens,
            total_token_count=prompt_tokens + candidates_tokens,
        ),
    )


def function_call_response(name: str, args: dict[str, Any], *, call_id: str) -> Any:
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            function_call=SimpleNamespace(
                                id=call_id,
                                name=name,
                                args=args,
                            )
                        )
                    ]
                )
            )
        ],
    )


def gemini_model(
    responses: list[Any],
    **kwargs: Any,
) -> tuple[GeminiModel, FakeClient]:
    kwargs.setdefault("provider", "gemini")
    kwargs.setdefault("gemini_api_key", "gemini-test")
    kwargs.setdefault("gemini_model", DEFAULT_GEMINI_MODEL)
    client = FakeClient(responses)
    return GeminiModel(Settings(**kwargs), client=client), client


def dump(value: Any) -> Any:
    return value.model_dump(mode="json", exclude_none=True)


def test_gemini_model_sends_messages_tools_and_returns_text_and_cost() -> None:
    model, client = gemini_model(
        [
            text_response(
                "result",
                prompt_tokens=1_000,
                cached_tokens=100,
                candidates_tokens=20,
            )
        ]
    )
    tool = {
        "type": "function",
        "name": "write",
        "description": "write a file",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": False,
    }

    result = run(
        model.query(
            [
                {"role": "system", "content": "write clean code"},
                {"role": "user", "content": "build a hinge"},
            ],
            tools=[tool],
        )
    )

    assert result["text"] == "result"
    assert result["tool_calls"] == []
    assert result["cost"] == 0.001515
    assert result["token_usage"] == {
        "prompt_tokens": 1_000,
        "cached_tokens": 100,
        "candidates_tokens": 20,
        "input_tokens": 1_000,
        "cached_input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 1_020,
    }
    request = client.models.requests[0]
    assert request["model"] == "gemini-3.6-flash"
    assert [dump(content) for content in request["contents"]] == [
        {"role": "user", "parts": [{"text": "build a hinge"}]}
    ]
    config = dump(request["config"])
    assert config["system_instruction"] == "write clean code"
    declaration = config["tools"][0]["function_declarations"][0]
    assert declaration["name"] == "write"
    assert "additionalProperties" not in declaration["parameters"]


def test_gemini_model_converts_tool_calls_and_tool_results() -> None:
    model, client = gemini_model(
        [
            function_call_response("compile", {}, call_id="call_compile"),
            text_response("done"),
        ]
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": "build"}]

    first = run(model.query(messages, tools=[]))
    assert first["tool_calls"] == [
        {"id": "call_compile", "name": "compile", "arguments": "{}"}
    ]

    messages.extend(
        [
            {"role": "assistant", "content": "", "tool_calls": first["tool_calls"]},
            {
                "type": "function_call_output",
                "call_id": "call_compile",
                "output": json.dumps({"result": {"status": "success"}}),
            },
        ]
    )
    second = run(model.query(messages, tools=[]))

    assert second["text"] == "done"
    contents = [dump(content) for content in client.models.requests[1]["contents"]]
    assert contents == [
        {"role": "user", "parts": [{"text": "build"}]},
        {
            "role": "model",
            "parts": [{"function_call": {"name": "compile", "args": {}}}],
        },
        {
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "name": "compile",
                        "response": {"result": {"status": "success"}},
                    }
                }
            ],
        },
    ]


def test_gemini_model_returns_pro_long_context_cost() -> None:
    model, _client = gemini_model(
        [
            text_response(
                "result",
                prompt_tokens=200_001,
                cached_tokens=100_000,
                candidates_tokens=1_000,
            )
        ],
        gemini_model="gemini-3.1-pro-preview",
    )

    result = run(model.query([{"role": "user", "content": "build"}]))

    assert result["cost"] == 0.458004


def test_gemini_model_rejects_unsupported_models() -> None:
    with pytest.raises(ModelError, match="Unsupported Gemini model"):
        GeminiModel(
            Settings(
                provider="gemini",
                gemini_api_key="gemini-test",
                gemini_model="gemini-3.5-flash",
            )
        )

    assert context_window_tokens_for("gemini-3.6-flash") == 1_000_000
    assert context_window_tokens_for("gemini-3.1-pro-preview") == 1_000_000
    assert context_window_tokens_for("gemini-3.5-flash") is None


def test_gemini_model_wraps_provider_errors() -> None:
    class AuthError(Exception):
        status_code = 401

    model, client = gemini_model([AuthError("bad key")])

    with pytest.raises(ModelError, match=r"Gemini request failed: AuthError.*bad key"):
        run(model.query([{"role": "user", "content": "build"}]))

    assert len(client.models.requests) == 1


def test_gemini_model_loads_dotenv_key(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    tmp_path.joinpath(".env").write_text(
        "\n".join(
            [
                "MINI_ARTICRAFT_PROVIDER=gemini",
                "GEMINI_API_KEY=gemini-test",
                "MINI_ARTICRAFT_GEMINI_MODEL=gemini-3.1-pro-preview",
            ]
        )
    )

    settings = get_settings()

    assert settings.provider == "gemini"
    assert settings.gemini_model == "gemini-3.1-pro-preview"
    assert gemini_api_key_value(settings) == "gemini-test"
