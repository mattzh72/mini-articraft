from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Protocol

import pytest
from harness import TAPE_ROOT, ReplayHarness

from mini_articraft import Model


@pytest.fixture(scope="session")
def _event_loop():
    """One event loop for the whole test session.

    The async tests drive coroutines through a small ``run`` helper. Creating
    and tearing down a fresh loop per call (``asyncio.run``) churns the Unix
    subprocess child watcher, which intermittently drops exec output or raises
    "Event loop is closed" on a later test. A single long-lived loop, closed
    once at the end, keeps that machinery stable.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        yield loop
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        asyncio.set_event_loop(None)
        loop.close()


@pytest.fixture(autouse=True)
def _use_session_loop(_event_loop):
    asyncio.set_event_loop(_event_loop)
    return _event_loop


@pytest.fixture
def replay_harness(tmp_path: Path) -> ReplayHarness:
    """A scratch tape library under the test's tmp dir."""
    return ReplayHarness(tmp_path / "tapes")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("tapes")
    group.addoption(
        "--record",
        action="store_true",
        default=False,
        help=(
            "run tape-backed tests live and (re)record named tapes "
            "(paid, deliberate opt-in; needs OPENAI_API_KEY)"
        ),
    )
    group.addoption(
        "--replay",
        action="store_true",
        default=False,
        help=(
            "replay named tapes offline and exit if one is missing; "
            "without this flag a missing tape only skips (the default)"
        ),
    )


class TapeModelOpener(Protocol):
    """Opens a tape-backed model by name (defaulting to the test's own name)."""

    def __call__(self, name: str | None = None) -> AbstractContextManager[Model]: ...


def _tape_model_opener(request: pytest.FixtureRequest) -> TapeModelOpener:
    """The tape mode matrix: default replays (skip when missing), ``--replay``
    makes a missing tape fatal, and only ``--record`` goes live.

    Kept as a plain function so tests can drive it without pytest internals.
    """
    record = bool(request.config.getoption("--record"))
    replay = bool(request.config.getoption("--replay"))
    if record and replay:
        pytest.exit("use only one of --record and --replay", returncode=2)

    library = ReplayHarness(TAPE_ROOT)

    @contextmanager
    def open_tape(name: str | None = None) -> Iterator[Model]:
        tape_name = name or request.node.name
        if record:
            with library.record(tape_name, _live_model()) as recording:
                yield recording
            return
        if not library.has(tape_name):
            path = library.path(tape_name)
            message = f"tape {tape_name!r} missing at {path}; record with --record"
            if replay:
                pytest.exit(message, returncode=1)
            pytest.skip(message)
        yield library.replay(tape_name)

    return open_tape


@pytest.fixture
def tape_model(request: pytest.FixtureRequest) -> TapeModelOpener:
    """Open a named model for live/e2e tests.

    Names default to the test function (``tape_model()``), or pass an
    explicit name such as ``tape_model("latest")``.

    - default (no flags): replay the tape offline; skip when missing
    - ``--record``: live + (re)write the tape (paid, deliberate opt-in)
    - ``--replay``: replay offline; exit if missing (the CI contract)
    """
    return _tape_model_opener(request)


def _live_model() -> Model:
    try:
        from mini_articraft.models.openai import OpenAIModel

        return OpenAIModel()
    except Exception as exc:
        pytest.fail(f"live model needs OPENAI_API_KEY: {exc}")
