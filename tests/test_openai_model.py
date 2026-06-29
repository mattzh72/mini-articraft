from __future__ import annotations

import asyncio
import json

import pytest

from mini_articraft.errors import ModelError
from mini_articraft.models.openai import OpenAIModel
from mini_articraft.settings import Settings, get_settings


def run(awaitable):
    return asyncio.run(awaitable)


def response_event(
    text: str,
    *,
    response_id: str = "resp_1",
    status: str = "completed",
    incomplete_details: dict[str, object] | None = None,
    output: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "type": f"response.{status}",
        "response": {
            "id": response_id,
            "status": status,
            "incomplete_details": incomplete_details,
            "output": output
            if output is not None
            else [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
        },
    }


class FakeWebSocket:
    def __init__(self, events: list[dict[str, object]]):
        self.closed = False
        self.sent: list[dict[str, object]] = []
        self.events = [json.dumps(event) for event in events]

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def recv(self) -> str:
        return self.events.pop(0)

    async def close(self) -> None:
        self.closed = True


def patch_websocket(monkeypatch: pytest.MonkeyPatch, socket: FakeWebSocket) -> None:
    async def connect(url: str, *, additional_headers: dict[str, str], max_size: object):
        assert url == "wss://api.openai.com/v1/responses"
        assert additional_headers == {"Authorization": "Bearer sk-test"}
        assert max_size is None
        return socket

    monkeypatch.setattr("mini_articraft.models.openai.websockets.connect", connect)


def openai_model(**kwargs: object) -> OpenAIModel:
    return OpenAIModel(Settings(openai_api_key="sk-test", **kwargs))


def test_openai_model_uses_websocket(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = FakeWebSocket([response_event("result")])
    patch_websocket(monkeypatch, socket)

    result = run(
        openai_model().query(
            [
                {"role": "system", "content": "write clean code"},
                {"role": "user", "content": "build a hinge"},
            ]
        )
    )

    assert result["text"] == "result"
    assert socket.sent == [
        {
            "type": "response.create",
            "model": "gpt-5.5",
            "input": [{"role": "user", "content": "build a hinge"}],
            "reasoning": {"effort": "high"},
            "include": ["reasoning.encrypted_content"],
            "store": False,
            "max_output_tokens": 128_000,
            "instructions": "write clean code",
        }
    ]


def test_openai_model_uses_incremental_websocket_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    socket = FakeWebSocket(
        [
            response_event(
                "first",
                response_id="resp_1",
                output=[
                    {"type": "reasoning", "encrypted_content": "encrypted"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "first"}],
                    },
                ],
            ),
            response_event("second", response_id="resp_2"),
        ]
    )
    patch_websocket(monkeypatch, socket)
    model = openai_model()

    run(model.query([{"role": "system", "content": "system"}, {"role": "user", "content": "one"}]))
    run(
        model.query(
            [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "one"},
                {"role": "assistant", "content": "first"},
                {"role": "user", "content": "two"},
            ]
        )
    )

    assert socket.sent[1]["previous_response_id"] == "resp_1"
    assert socket.sent[1]["input"] == [{"role": "user", "content": "two"}]
    assert model._input_items[1] == {"type": "reasoning", "encrypted_content": "encrypted"}


def test_openai_model_round_trips_phase_and_response_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    socket = FakeWebSocket([response_event("result")])
    patch_websocket(monkeypatch, socket)

    run(
        openai_model().query(
            [
                {"role": "system", "content": "system contract"},
                {
                    "role": "assistant",
                    "phase": "commentary",
                    "content": "I will inspect the compile error.",
                },
                {"id": "rs_123", "type": "reasoning", "summary": []},
                {"role": "user", "content": "continue"},
            ],
        )
    )

    assert socket.sent[0]["input"] == [
        {
            "role": "assistant",
            "content": "I will inspect the compile error.",
            "phase": "commentary",
        },
        {"id": "rs_123", "type": "reasoning", "summary": []},
        {"role": "user", "content": "continue"},
    ]


def test_openai_model_rejects_phase_on_user_message() -> None:
    with pytest.raises(ValueError, match="phase is only valid"):
        run(openai_model().query([{"role": "user", "phase": "final_answer", "content": "hello"}]))


def test_openai_model_loads_dotenv(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINI_ARTICRAFT_MODEL", raising=False)
    monkeypatch.delenv("MINI_ARTICRAFT_REASONING_EFFORT", raising=False)
    tmp_path.joinpath(".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-test",
                "MINI_ARTICRAFT_MODEL=gpt-test",
                "MINI_ARTICRAFT_REASONING_EFFORT=low",
            ]
        )
    )
    socket = FakeWebSocket([response_event("result")])
    patch_websocket(monkeypatch, socket)

    run(OpenAIModel().query([{"role": "user", "content": "hello"}]))

    assert socket.sent[0]["model"] == "gpt-test"
    assert socket.sent[0]["reasoning"] == {"effort": "low"}
    assert socket.sent[0]["max_output_tokens"] == 128_000
    assert socket.sent[0]["include"] == ["reasoning.encrypted_content"]
    assert socket.sent[0]["store"] is False


def test_openai_model_raises_on_incomplete_response(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = FakeWebSocket(
        [
            response_event(
                "",
                status="incomplete",
                incomplete_details={"reason": "max_output_tokens"},
                output=[],
            )
        ]
    )
    patch_websocket(monkeypatch, socket)

    with pytest.raises(ModelError, match="max_output_tokens.*no visible output"):
        run(openai_model().query([{"role": "user", "content": "hello"}]))


def test_openai_model_raises_on_partial_incomplete_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    socket = FakeWebSocket(
        [
            response_event(
                "partial",
                status="incomplete",
                incomplete_details={"reason": "max_output_tokens"},
            )
        ]
    )
    patch_websocket(monkeypatch, socket)

    with pytest.raises(ModelError, match="partial output returned"):
        run(openai_model().query([{"role": "user", "content": "hello"}]))


def test_openai_model_raises_on_websocket_error(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = FakeWebSocket(
        [
            {
                "type": "error",
                "status": 400,
                "error": {
                    "code": "previous_response_not_found",
                    "message": "missing response",
                },
            }
        ]
    )
    patch_websocket(monkeypatch, socket)

    with pytest.raises(ModelError, match="previous_response_not_found"):
        run(openai_model().query([{"role": "user", "content": "hello"}]))


def test_openai_model_raises_without_text(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = FakeWebSocket([response_event("", output=[])])
    patch_websocket(monkeypatch, socket)

    with pytest.raises(ModelError, match="output_text"):
        run(openai_model().query([{"role": "user", "content": "hello"}]))
