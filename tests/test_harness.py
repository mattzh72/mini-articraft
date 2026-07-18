"""Tests for the modular test environment itself (tests/harness.py)."""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import (
    GOOD_MAIN_PY,
    ModelQuery,
    Response,
    ScriptedModel,
    ScriptExhaustedError,
    calls,
    run,
    run_scenario,
    text,
    tool_call,
)

from mini_articraft.agent.events import TurnStarted
from mini_articraft.environments.local import LocalEnvironment


def write_good_main() -> Response:
    return calls(tool_call("write", {"path": "main.py", "content": GOOD_MAIN_PY}))


# ---------------------------------------------------------------------------
# ScriptedModel
# ---------------------------------------------------------------------------


def test_scripted_model_plays_steps_and_fills_defaults() -> None:
    model = ScriptedModel([text("hello"), calls(tool_call("read", {"path": "a.py"}))])

    first = run(model.query([{"role": "user", "content": "go"}]))
    assert first == {"text": "hello", "tool_calls": [], "cost": 0.0, "token_usage": {}}
    assert model.remaining == 1

    second = run(model.query([{"role": "user", "content": "go"}]))
    assert second["tool_calls"][0]["name"] == "read"
    assert model.remaining == 0
    assert [query.turn for query in model.queries] == [1, 2]
    assert model.queries[0].messages == [{"role": "user", "content": "go"}]
    model.assert_exhausted()


def test_scripted_model_exhaustion_raises_a_clear_error() -> None:
    model = ScriptedModel([text("only")])
    run(model.query([]))
    with pytest.raises(ScriptExhaustedError, match="turn 2 beyond the 1 scripted step"):
        run(model.query([]))


def test_assert_exhausted_catches_unplayed_steps() -> None:
    model = ScriptedModel([text("a"), text("b")])
    run(model.query([]))
    with pytest.raises(AssertionError, match="1 scripted step"):
        model.assert_exhausted()


def test_step_exceptions_propagate_as_model_failures() -> None:
    def fail(query: ModelQuery) -> Response:
        raise RuntimeError("socket closed")

    model = ScriptedModel([fail])
    with pytest.raises(RuntimeError, match="socket closed"):
        run(model.query([]))


def test_normalized_responses_do_not_mutate_step_dicts() -> None:
    step = {"text": "hi", "tool_calls": []}
    model = ScriptedModel([step])
    run(model.query([]))
    assert step == {"text": "hi", "tool_calls": []}


# ---------------------------------------------------------------------------
# run_scenario
# ---------------------------------------------------------------------------


def test_run_scenario_returns_deep_artifacts(tmp_path: Path) -> None:
    artifacts = run_scenario(
        "a box",
        [write_good_main(), calls(tool_call("compile")), text("done")],
        env=LocalEnvironment(output_dir=tmp_path),
    )

    assert artifacts.record.status == "success"
    assert artifacts.result["message"] == "done"
    assert (artifacts.workspace / "main.py").is_file()
    assert [event.turn for event in artifacts.recorder.of(TurnStarted)] == [1, 2, 3]
    assert len(artifacts.recorder.tool_finishes("compile")) == 1
    finished = artifacts.recorder.finished
    assert finished is not None
    assert finished.status == "success"
    assert artifacts.tool_outputs()[0]["result"]["path"] == "main.py"
    assert artifacts.model.queries[-1].turn == 3


def test_reactive_steps_can_assert_on_tool_outputs(tmp_path: Path) -> None:
    def check_write(query: ModelQuery) -> Response:
        outputs = query.tool_outputs()
        assert outputs[-1]["result"]["path"] == "main.py"
        return calls(tool_call("compile"))

    artifacts = run_scenario(
        "a box",
        [write_good_main(), check_write, text("done")],
        env=LocalEnvironment(output_dir=tmp_path),
    )
    assert artifacts.record.status == "success"


def test_run_scenario_fails_when_the_script_is_not_consumed(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="never consumed"):
        run_scenario(
            "a box",
            [text("done"), text("extra")],
            env=LocalEnvironment(output_dir=tmp_path),
            max_turns=1,
        )


def test_run_scenario_validates_its_arguments() -> None:
    with pytest.raises(ValueError, match="env= or tmp_path="):
        run_scenario("a box", [text("x")])
