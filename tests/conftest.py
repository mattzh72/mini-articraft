from __future__ import annotations

import asyncio

import pytest


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
