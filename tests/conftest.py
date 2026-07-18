from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from harness import CASSETTE_ROOT, ReplayHarness, ScenarioModel

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
    """A scratch cassette library under the test's tmp dir."""
    return ReplayHarness(tmp_path / "cassettes")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--record-cassettes",
        action="store_true",
        default=False,
        help=(
            "run cassette-backed tests live and re-record their cassettes "
            "(needs OPENAI_API_KEY); the default is offline replay"
        ),
    )


CassetteModelOpener = Callable[[str | None], AbstractContextManager[ScenarioModel]]


@pytest.fixture
def cassette_model(request: pytest.FixtureRequest) -> CassetteModelOpener:
    """Open a cassette-backed model for live/e2e tests.

    Default: offline replay of ``tests/cassettes/<name>.jsonl`` (the test's
    own name when none is given), skipping when no cassette exists. With
    ``--record-cassettes``: run live against the real model and re-record
    the cassette (needs ``OPENAI_API_KEY``).
    """
    record = request.config.getoption("--record-cassettes")
    library = ReplayHarness(CASSETTE_ROOT)

    @contextmanager
    def open_cassette(name: str | None = None) -> Iterator[ScenarioModel]:
        cassette_name = name or request.node.name
        if record:
            with library.capture(cassette_name, _live_model()) as recording:
                yield recording
            return
        if not library.has(cassette_name):
            pytest.skip(f"cassette {cassette_name!r} not recorded; run with --record-cassettes")
        yield library.replay(cassette_name)

    return open_cassette


def _live_model() -> Model:
    try:
        from mini_articraft.models.openai import OpenAIModel

        return OpenAIModel()
    except Exception as exc:
        pytest.skip(f"--record-cassettes needs OPENAI_API_KEY: {exc}")
