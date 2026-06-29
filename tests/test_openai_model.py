from __future__ import annotations

import pytest

from mini_articraft.errors import ModelError
from mini_articraft.models.openai import OpenAIModel


class FakeResponse:
    def __init__(self, text: str):
        self.output_text = text

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {"output_text": self.output_text}


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

    assert result == {"text": "result", "response": {"output_text": "result"}}
    assert responses.requests == [
        {
            "model": "gpt-5.5",
            "input": [{"role": "user", "content": "build a hinge"}],
            "reasoning": {"effort": "high"},
            "instructions": "write clean code",
            "max_output_tokens": 1000,
        }
    ]


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
    assert responses.requests[0]["reasoning"] == {"effort": "low"}


def test_openai_model_raises_without_text(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = FakeResponses(FakeResponse(""))

    class FakeOpenAI:
        def __init__(self, *, api_key: str):
            self.responses = responses

    monkeypatch.setattr("mini_articraft.models.openai.OpenAI", FakeOpenAI)

    with pytest.raises(ModelError):
        OpenAIModel(api_key="sk-test").query([{"role": "user", "content": "hello"}])
