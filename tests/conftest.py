from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

import pytest
from harness import CASSETTE_ROOT, ReplayHarness

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
    group = parser.getgroup("cassettes")
    group.addoption(
        "--record",
        action="store_true",
        default=False,
        help=(
            "run cassette-backed tests live and (re)record named cassettes (needs OPENAI_API_KEY)"
        ),
    )
    group.addoption(
        "--replay",
        action="store_true",
        default=False,
        help=(
            "replay named cassettes offline; exit if a cassette is missing "
            "(without this flag, cassette-backed tests always run live)"
        ),
    )


CassetteModelOpener = Callable[[str | None], AbstractContextManager[Model]]


@pytest.fixture
def cassette_model(request: pytest.FixtureRequest) -> CassetteModelOpener:
    """Open a named model for live/e2e tests.

    Names default to the test function (``cassette_model()``), or pass an
    explicit name such as ``cassette_model("latest")``.

    - default (no flags): always live (real model)
    - ``--record``: live + (re)write the cassette
    - ``--replay``: offline cassette only; exit if missing
    """
    record = bool(request.config.getoption("--record"))
    replay = bool(request.config.getoption("--replay"))
    if record and replay:
        pytest.exit("use only one of --record and --replay", returncode=2)

    library = ReplayHarness(CASSETTE_ROOT)

    @contextmanager
    def open_cassette(name: str | None = None) -> Iterator[Model]:
        cassette_name = name or request.node.name
        if replay:
            if not library.has(cassette_name):
                path = library.path(cassette_name)
                pytest.exit(
                    f"cassette {cassette_name!r} missing at {path}; record with --record",
                    returncode=1,
                )
            yield library.replay(cassette_name)
            return
        if record:
            with library.capture(cassette_name, _live_model()) as recording:
                yield recording
            return
        yield _live_model()

    return open_cassette


def _live_model() -> Model:
    try:
        from mini_articraft.models.openai import OpenAIModel

        return OpenAIModel()
    except Exception as exc:
        pytest.exit(f"live model needs OPENAI_API_KEY: {exc}", returncode=1)
