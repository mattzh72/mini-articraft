from __future__ import annotations

from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from mini_articraft.cli import mini
from mini_articraft.settings import Settings


class FakeOpenAIModel:
    instances: list["FakeOpenAIModel"] = []

    def __init__(self, settings: Settings):
        self.settings = settings
        self.closed = False
        self.instances.append(self)

    async def close(self) -> None:
        self.closed = True


class FakeEnvironment:
    instances: list["FakeEnvironment"] = []

    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs
        self.instances.append(self)


class FakeAgent:
    instances: list["FakeAgent"] = []
    result: dict[str, object] = {
        "status": "success",
        "run": "/tmp/run",
        "result": "result/model.json",
        "message": "done",
    }

    def __init__(self, model: FakeOpenAIModel, env: FakeEnvironment, **kwargs: Any):
        self.model = model
        self.env = env
        self.kwargs = kwargs
        self.prompt = ""
        self.instances.append(self)

    async def run(self, prompt: str) -> dict[str, object]:
        self.prompt = prompt
        return self.result


def reset_fakes() -> None:
    FakeOpenAIModel.instances = []
    FakeEnvironment.instances = []
    FakeAgent.instances = []
    FakeAgent.result = {
        "status": "success",
        "run": "/tmp/run",
        "result": "result/model.json",
        "message": "done",
    }


def test_cli_runs_agent_with_only_core_overrides(monkeypatch, tmp_path: Path) -> None:
    reset_fakes()
    monkeypatch.setattr(mini, "OpenAIModel", FakeOpenAIModel)
    monkeypatch.setattr(mini, "LocalEnvironment", FakeEnvironment)
    monkeypatch.setattr(mini, "Agent", FakeAgent)
    monkeypatch.setattr(mini, "get_settings", lambda: Settings(openai_api_key="sk-test", max_turns=123))

    output_dir = tmp_path / "runs"
    result = CliRunner().invoke(
        mini.app,
        [
            "make a hinge",
            "--model",
            "gpt-test",
            "--output-dir",
            str(output_dir),
            "--reasoning-effort",
            "low",
        ],
    )

    assert result.exit_code == 0
    assert FakeOpenAIModel.instances[0].settings.openai_model == "gpt-test"
    assert FakeOpenAIModel.instances[0].settings.output_dir == output_dir
    assert FakeOpenAIModel.instances[0].settings.openai_reasoning_effort == "low"
    assert FakeOpenAIModel.instances[0].closed is True
    assert FakeEnvironment.instances[0].kwargs == {"output_dir": output_dir}
    assert FakeAgent.instances[0].kwargs == {"max_turns": 123}
    assert FakeAgent.instances[0].prompt == "make a hinge"
    assert "status: success" in result.output
    assert "run: /tmp/run" in result.output


def test_cli_exits_nonzero_when_agent_fails(monkeypatch) -> None:
    reset_fakes()
    FakeAgent.result = {"status": "error", "run": "/tmp/run", "error": "compile failed"}
    monkeypatch.setattr(mini, "OpenAIModel", FakeOpenAIModel)
    monkeypatch.setattr(mini, "LocalEnvironment", FakeEnvironment)
    monkeypatch.setattr(mini, "Agent", FakeAgent)
    monkeypatch.setattr(mini, "get_settings", lambda: Settings(openai_api_key="sk-test"))

    result = CliRunner().invoke(mini.app, ["make a hinge"])

    assert result.exit_code == 1
    assert "error: compile failed" in result.output
