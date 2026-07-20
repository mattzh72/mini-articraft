"""Tests for the tape_model fixture's record/replay mode matrix.

The contract: a bare ``pytest`` run never calls a paid model. The default
replays offline (skipping when no tape exists), ``--replay`` makes a missing
tape a hard failure (the CI contract), and ``--record`` is the only way a
test goes live -- deliberate, flagged, and paid.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from harness import (
    RecordingModel,
    ReplayHarness,
    ReplayModel,
    ScriptedModel,
    run,
    text,
)


class _FakeConfig:
    def __init__(self, *, record: bool = False, replay: bool = False):
        self._options = {"--record": record, "--replay": replay}

    def getoption(self, name: str) -> bool:
        return self._options.get(name, False)


@dataclass
class _FakeNode:
    name: str


@dataclass
class _FakeRequest:
    config: _FakeConfig
    node: _FakeNode


def _opener(request: _FakeRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """The fixture's open_tape, bound to a fake request and a tmp library."""
    import conftest

    monkeypatch.setattr(conftest, "TAPE_ROOT", tmp_path / "tapes")
    return conftest._tape_model_opener(cast(pytest.FixtureRequest, request))


def test_default_replay_skips_a_missing_tape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opener = _opener(_FakeRequest(_FakeConfig(), _FakeNode("missing_test")), monkeypatch, tmp_path)
    with pytest.raises(pytest.skip.Exception, match="record with --record"), opener():
        pass


def test_replay_flag_exits_on_a_missing_tape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opener = _opener(
        _FakeRequest(_FakeConfig(replay=True), _FakeNode("missing_test")), monkeypatch, tmp_path
    )
    with pytest.raises(pytest.exit.Exception) as exc_info, opener():
        pass
    assert exc_info.value.returncode == 1


def test_default_replays_an_existing_tape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ReplayHarness(tmp_path / "tapes").set("happy_test", [text("hi")])
    opener = _opener(_FakeRequest(_FakeConfig(), _FakeNode("happy_test")), monkeypatch, tmp_path)
    with opener() as model:
        assert isinstance(model, ReplayModel)
        assert run(model.query([]))["text"] == "hi"


def test_record_runs_live_and_writes_the_tape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import conftest

    monkeypatch.setattr(conftest, "_live_model", lambda: ScriptedModel([text("live")]))
    opener = _opener(
        _FakeRequest(_FakeConfig(record=True), _FakeNode("rec_test")), monkeypatch, tmp_path
    )
    with opener() as model:
        assert isinstance(model, RecordingModel)
        run(model.query([]))

    library = ReplayHarness(tmp_path / "tapes")
    assert library.has("rec_test")
    assert library.entries("rec_test")[0]["response"]["text"] == "live"


def test_record_and_replay_together_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(pytest.exit.Exception) as exc_info:
        _opener(
            _FakeRequest(_FakeConfig(record=True, replay=True), _FakeNode("x")),
            monkeypatch,
            tmp_path,
        )
    assert exc_info.value.returncode == 2
