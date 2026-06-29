from __future__ import annotations

import pytest

from mini_articraft.errors import ModelError
from mini_articraft.models.openai import OpenAIModel


class FakeResponse:
    def __init__(
        self,
        text: str,
        *,
        status: str = "completed",
        incomplete_details: dict[str, object] | None = None,
    ):
        self.output_text = text
        self.status = status
        self.incomplete_details = incomplete_details

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "status": self.status,
            "incomplete_details": self.incomplete_details,
        }


class FakeResponses:
    def __init__(self, response: FakeResponse):
        self.requests: list[dict[str, object]] = []
        self.response = response

    def create(self, **kwargs: object) -> FakeResponse:
        self.requests.append(kwargs)
        return self.response


def test_openai_model_uses_responses_api(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses(FakeResponse("result"))

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            assert api_key == "sk-test"
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    result = OpenAIModel(api_key="sk-test").query(
        [
            {"role": "system", "content": "write clean code"},
            {"role": "user", "content": "build a hinge"},
        ],
        max_output_tokens=1000,
    )

    assert result == {"text": "result", "response": {"status": "completed", "incomplete_details": None}}
    assert responses.requests == [
        {
            "model": "gpt-5.5",
            "input": [{"role": "user", "content": "build a hinge"}],
            "reasoning": {"effort": "high"},
            "include": ["reasoning.encrypted_content"],
            "instructions": "write clean code",
            "max_output_tokens": 1000,
        }
    ]


def test_openai_model_round_trips_phase_and_response_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = FakeResponses(FakeResponse("result"))

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    OpenAIModel(api_key="sk-test").query(
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

    assert responses.requests[0]["input"] == [
        {
            "role": "assistant",
            "phase": "commentary",
            "content": "I will inspect the compile error.",
        },
        {"id": "rs_123", "type": "reasoning", "summary": []},
        {"role": "user", "content": "continue"},
    ]
    assert responses.requests[0]["max_output_tokens"] == 25_000
    assert responses.requests[0]["include"] == ["reasoning.encrypted_content"]


def test_openai_model_rejects_phase_on_user_message(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = FakeResponses(FakeResponse("result"))

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    with pytest.raises(ValueError, match="phase is only valid"):
        OpenAIModel(api_key="sk-test").query(
            [{"role": "user", "phase": "final_answer", "content": "hello"}]
        )


def test_openai_model_loads_dotenv(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MINI_ARTICRAFT_MODEL", raising=False)
    monkeypatch.delenv("MINI_ARTICRAFT_REASONING_EFFORT", raising=False)
    tmp_path.joinpath(".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-dotenv",
                "MINI_ARTICRAFT_MODEL=gpt-test",
                "MINI_ARTICRAFT_REASONING_EFFORT=low",
                "MINI_ARTICRAFT_REASONING_SUMMARY=auto",
                "MINI_ARTICRAFT_MAX_OUTPUT_TOKENS=12345",
            ]
        )
    )
    responses = FakeResponses(FakeResponse("result"))

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            assert api_key == "sk-dotenv"
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    OpenAIModel().query([{"role": "user", "content": "hello"}])

    assert responses.requests[0]["model"] == "gpt-test"
    assert responses.requests[0]["reasoning"] == {"effort": "low", "summary": "auto"}
    assert responses.requests[0]["max_output_tokens"] == 12345
    assert responses.requests[0]["include"] == ["reasoning.encrypted_content"]


def test_openai_model_raises_on_incomplete_response(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses(
        FakeResponse(
            "",
            status="incomplete",
            incomplete_details={"reason": "max_output_tokens"},
        )
    )

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    with pytest.raises(ModelError, match="max_output_tokens.*no visible output"):
        OpenAIModel(api_key="sk-test").query([{"role": "user", "content": "hello"}])


def test_openai_model_raises_on_partial_incomplete_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = FakeResponses(
        FakeResponse(
            "partial",
            status="incomplete",
            incomplete_details={"reason": "max_output_tokens"},
        )
    )

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    with pytest.raises(ModelError, match="partial output returned"):
        OpenAIModel(api_key="sk-test").query([{"role": "user", "content": "hello"}])


def test_openai_model_raises_without_text(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses(FakeResponse(""))

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    with pytest.raises(ModelError):
        OpenAIModel(api_key="sk-test").query([{"role": "user", "content": "hello"}])
