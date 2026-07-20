"""Tests for the modular test environment itself (tests/harness.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from harness import (
    GOOD_MAIN_PY,
    CassetteError,
    CassetteMismatchError,
    ModelQuery,
    ReplayHarness,
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
# ReplayHarness
# ---------------------------------------------------------------------------


def test_capture_set_replay_erase_cycle(replay_harness: ReplayHarness) -> None:
    assert replay_harness.names() == []

    with replay_harness.capture("box", ScriptedModel([text("hi")])) as recording:
        run(recording.query([{"role": "user", "content": "go"}]))
    assert replay_harness.names() == ["box"]
    assert replay_harness.entries("box")[0]["response"]["text"] == "hi"

    replay = replay_harness.replay("box")
    assert run(replay.query([{"role": "user", "content": "go"}]))["text"] == "hi"
    replay.assert_exhausted()

    assert replay_harness.erase("box") is True
    assert replay_harness.erase("box") is False
    assert not replay_harness.has("box")


def test_capture_replaces_existing_and_rejects_empty_captures(
    replay_harness: ReplayHarness,
) -> None:
    replay_harness.set("run", [text("v1")])
    with (
        pytest.raises(CassetteError, match="recorded no exchanges"),
        replay_harness.capture("run", ScriptedModel([text("v2")])),
    ):
        pass  # never queried -> a broken capture
    assert not replay_harness.has("run")  # the old cassette was replaced up front


def test_set_installs_hand_authored_rows(replay_harness: ReplayHarness) -> None:
    path = replay_harness.set("authored", [calls(tool_call("compile")), text("done", cost=0.5)])

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["fingerprint"] for row in rows] == ["", ""]
    assert rows[0]["response"]["tool_calls"][0]["name"] == "compile"
    assert rows[1]["response"]["cost"] == 0.5

    replay = replay_harness.replay("authored")  # strict, but fingerprintless rows match anything
    assert run(replay.query([{"role": "user", "content": "anything"}]))["tool_calls"]
    with pytest.raises(AssertionError, match="never consumed"):
        replay.assert_exhausted()


def test_set_preserves_full_rows_and_refuses_empty(replay_harness: ReplayHarness) -> None:
    replay_harness.set("original", [text("hi")])
    rows = replay_harness.entries("original")
    replay_harness.set("copy", rows)
    assert replay_harness.entries("copy") == rows
    with pytest.raises(CassetteError, match="empty"):
        replay_harness.set("empty", [])


def test_library_rejects_unsafe_names(replay_harness: ReplayHarness) -> None:
    for bad in ("../up", "a/b", "", "with space"):
        with pytest.raises(ValueError, match="simple file name"):
            replay_harness.path(bad)


def test_clear_wipes_the_library(replay_harness: ReplayHarness) -> None:
    replay_harness.set("a", [text("a")])
    replay_harness.set("b", [text("b")])
    assert replay_harness.names() == ["a", "b"]
    assert replay_harness.clear() == 2
    assert replay_harness.names() == []


def test_strict_replay_detects_trajectory_drift(replay_harness: ReplayHarness) -> None:
    messages_1 = [{"role": "user", "content": "go"}]
    messages_2 = [*messages_1, {"role": "assistant", "content": "a"}]
    with replay_harness.capture("run", ScriptedModel([text("a"), text("b")])) as recording:
        run(recording.query(messages_1))
        run(recording.query(messages_2))

    replay = replay_harness.replay("run")
    assert run(replay.query(messages_1))["text"] == "a"
    with pytest.raises(CassetteMismatchError, match="turn 2 diverged"):
        run(replay.query([{"role": "user", "content": "different"}]))


def test_replay_beyond_the_cassette_is_a_clear_error(replay_harness: ReplayHarness) -> None:
    replay_harness.set("short", [text("only")])
    replay = replay_harness.replay("short")
    run(replay.query([]))
    with pytest.raises(ScriptExhaustedError, match="beyond the 1 cassette row"):
        run(replay.query([]))


def test_unknown_recording_is_a_clear_error(replay_harness: ReplayHarness) -> None:
    with pytest.raises(CassetteError, match="unknown recording"):
        replay_harness.entries("missing")
    with pytest.raises(CassetteError, match="unknown recording"):
        replay_harness.replay("missing")


def test_capture_stores_metadata_and_replay_skips_it(replay_harness: ReplayHarness) -> None:
    with replay_harness.capture(
        "run",
        ScriptedModel([text("a")]),
        meta={"prompt": "a box"},
    ) as recording:
        run(recording.query([]))

    assert replay_harness.meta("run") == {"prompt": "a box"}
    assert replay_harness.entries("run")[0]["meta"] == {"prompt": "a box"}
    replay = replay_harness.replay("run")
    assert run(replay.query([]))["text"] == "a"  # only exchange rows are replayed
    replay.assert_exhausted()


def test_set_preserves_metadata_rows_but_refuses_meta_only(
    replay_harness: ReplayHarness,
) -> None:
    replay_harness.set("with-meta", [{"meta": {"prompt": "x"}}, text("a")])
    rows = replay_harness.entries("with-meta")
    assert rows[0]["meta"] == {"prompt": "x"}
    assert rows[1]["response"]["text"] == "a"
    with pytest.raises(CassetteError, match="empty"):
        replay_harness.set("meta-only", [{"meta": {"prompt": "x"}}])


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
    with pytest.raises(ValueError, match="script= or model="):
        run_scenario("a box")
    with pytest.raises(ValueError, match="not both"):
        run_scenario("a box", [text("x")], model=ScriptedModel([text("y")]))
    with pytest.raises(ValueError, match="env= or tmp_path="):
        run_scenario("a box", [text("x")])


def test_captured_cassette_replays_a_full_scenario(
    tmp_path: Path, replay_harness: ReplayHarness
) -> None:
    script = [write_good_main(), calls(tool_call("compile")), text("done", cost=0.25)]
    with replay_harness.capture("box", ScriptedModel(script)) as recording:
        captured = run_scenario(
            "a box",
            model=recording,
            env=LocalEnvironment(output_dir=tmp_path / "a"),
        )
    assert captured.record.status == "success"

    replayed = run_scenario(
        "a box",
        model=replay_harness.replay("box"),
        env=LocalEnvironment(output_dir=tmp_path / "b"),
    )
    assert replayed.record.status == "success"
    assert replayed.result["message"] == "done"
    assert replayed.result["cost"] == 0.25
