"""Modular test environment for mini-articraft.

Verify the generation loop deeply without paying for model calls:

1. Unit lane -- call pure functions (SDK checks, compile feedback) directly;
   no harness needed.
2. Scripted agent lane -- :class:`ScriptedModel` plus :func:`run_scenario`
   drive the full agent loop (tools, reminders, compile freshness, record)
   with a deterministic model that can react to what the agent sends it.
"""

from __future__ import annotations

import asyncio
import inspect
import itertools
import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Generic, TypeVar

from mini_articraft.agent import Agent, events
from mini_articraft.agent.tools import Tool, ToolContext
from mini_articraft.agent.tools._core import schema as _tool_schema
from mini_articraft.agent.tools._core import workspace_digest
from mini_articraft.environments.local import LocalEnvironment
from mini_articraft.record import Record, read_conversation

T = TypeVar("T")
Item = TypeVar("Item")

Response = dict[str, Any]
ToolCall = dict[str, Any]
Messages = list[dict[str, Any]]


def run(awaitable: Awaitable[T]) -> T:
    """Drive an awaitable on the session event loop owned by conftest."""
    return asyncio.get_event_loop().run_until_complete(awaitable)


# ---------------------------------------------------------------------------
# Queries and responses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelQuery:
    """One recorded model query: the exact messages and tools the agent sent."""

    turn: int
    messages: Messages
    tools: list[dict[str, Any]]

    def contains(self, *needles: str) -> bool:
        """True when a single message content includes every ``needle``."""
        if not needles:
            raise ValueError("contains needs at least one needle")
        return any(
            all(needle in content for needle in needles)
            for content in (str(message.get("content")) for message in self.messages)
        )

    def tool_outputs(self) -> list[dict[str, Any]]:
        """Parsed ``function_call_output`` payloads the model has seen so far."""
        return _tool_outputs(self.messages)


def _tool_outputs(messages: Messages) -> list[dict[str, Any]]:
    return [
        json.loads(str(message.get("output") or "{}"))
        for message in messages
        if message.get("type") == "function_call_output"
    ]


def _record_query(
    queries: list[ModelQuery],
    messages: Messages,
    tools: list[dict[str, Any]] | None,
) -> ModelQuery:
    query = ModelQuery(
        turn=len(queries) + 1,
        messages=list(messages),
        tools=list(tools or []),
    )
    queries.append(query)
    return query


Step = Response | Callable[[ModelQuery], "Response | Awaitable[Response]"]

_call_ids = itertools.count(1)


def tool_call(
    name: str, args: dict[str, Any] | None = None, *, call_id: str | None = None
) -> ToolCall:
    """Build one tool call in the wire shape the agent harness consumes.

    Auto-generated ids are unique per process, not per test; pass ``call_id``
    when a test asserts on specific ids.
    """
    return {
        "id": call_id or f"call_{next(_call_ids)}",
        "name": name,
        "arguments": json.dumps(args or {}),
    }


def calls(*tool_calls: ToolCall, **fields: Any) -> Response:
    """A scripted response of tool calls with no visible text."""
    return {"text": "", "tool_calls": list(tool_calls), **fields}


def text(content: str, **fields: Any) -> Response:
    """A scripted response of visible text with no tool calls."""
    return {"text": content, "tool_calls": [], **fields}


def _normalize_response(response: Response) -> Response:
    """Fill the optional response fields without mutating the caller's dict."""
    if not isinstance(response, dict):
        raise TypeError(f"model responses must be dicts, got {type(response).__name__}")
    return {"text": "", "tool_calls": [], "cost": 0.0, "token_usage": {}, **response}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ScriptExhaustedError(RuntimeError):
    """The agent asked for more turns than the script provides."""


@dataclass(frozen=True)
class ModelIdentity:
    """The model attributes the agent harness reads through ``model.config``."""

    openai_model: str = "gpt-test"
    openai_reasoning_effort: str = "low"


class QueuedModel(Generic[Item]):
    """Base for finite models: a queue of canned responses plus a query log.

    Subclasses keep only their semantics -- what a queued item is and how one
    becomes a response. The queue itself (pop with a clear exhaustion error,
    ``remaining``, ``assert_exhausted``) lives here once.
    """

    noun: ClassVar[str] = "item"

    def __init__(
        self,
        items: Iterable[Item],
        *,
        model_name: str = "gpt-test",
        reasoning_effort: str = "low",
        context_window_tokens: int = 0,
    ):
        self._queue = list(items)
        self.queries: list[ModelQuery] = []
        self.config = ModelIdentity(model_name, reasoning_effort)
        self.context_window_tokens = context_window_tokens

    @property
    def remaining(self) -> int:
        return len(self._queue)

    def _next(self, query: ModelQuery) -> Item:
        if not self._queue:
            raise ScriptExhaustedError(
                f"agent queried turn {query.turn} beyond the {query.turn - 1} {self.noun}(s)"
            )
        return self._queue.pop(0)

    def assert_exhausted(self) -> None:
        """Fail when the agent finished without consuming the whole queue."""
        if self._queue:
            raise AssertionError(
                f"{len(self._queue)} {self.noun}(s) were never consumed; "
                "the agent finished earlier than expected"
            )

    async def close(self) -> None:
        pass


class ScriptedModel(QueuedModel[Step]):
    """A deterministic ``Model`` that plays a script of responses.

    Each step is either a response dict (see :func:`text` and :func:`calls`)
    or a callable receiving the :class:`ModelQuery` for this turn. Callables
    may assert on the messages the agent sent, react to earlier tool outputs,
    be ``async`` (e.g. block forever to test cancellation), or raise (to test
    model failure handling). Querying past the last step raises
    :class:`ScriptExhaustedError`, which the agent records as a model failure.
    """

    noun: ClassVar[str] = "scripted step"

    async def query(
        self,
        messages: Messages,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> Response:
        query = _record_query(self.queries, messages, tools)
        step = self._next(query)
        response = step(query) if callable(step) else step
        if inspect.isawaitable(response):
            response = await response
        return _normalize_response(response)


# ---------------------------------------------------------------------------
# Scenario runner
# ---------------------------------------------------------------------------


class EventRecorder:
    """Collect agent events and answer common questions about them."""

    def __init__(self) -> None:
        self.events: list[events.Event] = []

    def __call__(self, event: events.Event) -> None:
        self.events.append(event)

    def of(self, kind: type[T]) -> list[T]:
        """All events of one type, in order."""
        return [event for event in self.events if isinstance(event, kind)]

    def tool_finishes(self, name: str | None = None) -> list[events.ToolFinished]:
        """``ToolFinished`` events, optionally filtered to one tool."""
        finishes = self.of(events.ToolFinished)
        if name is None:
            return finishes
        return [event for event in finishes if event.name == name]

    @property
    def finished(self) -> events.RunFinished | None:
        """The terminal event, when the run emitted one last."""
        last = self.events[-1] if self.events else None
        return last if isinstance(last, events.RunFinished) else None


@dataclass
class RunArtifacts:
    """Everything a scenario produced, ready for deep assertions."""

    result: dict[str, Any]
    record: Record
    model: ScriptedModel
    recorder: EventRecorder
    run_dir: Path

    @property
    def workspace(self) -> Path:
        return self.run_dir / "workspace"

    @property
    def conversation(self) -> list[dict[str, Any]]:
        return read_conversation(self.run_dir / "conversation.jsonl")

    def tool_outputs(self) -> list[dict[str, Any]]:
        """Parsed tool result payloads from the persisted conversation."""
        return _tool_outputs(self.conversation)


def run_scenario(
    prompt: str,
    script: Iterable[Step],
    *,
    env: LocalEnvironment | None = None,
    tmp_path: Path | None = None,
    run_id: str = "scenario",
    max_turns: int = 10,
    assert_exhausted: bool = True,
) -> RunArtifacts:
    """Run the full agent loop for free and return deep-inspectable artifacts.

    Pass ``env`` to choose the environment or ``tmp_path`` for a plain
    ``LocalEnvironment``. By default the script must be consumed exactly;
    pass ``assert_exhausted=False`` for open-ended runs.
    """
    if env is None:
        if tmp_path is None:
            raise ValueError("run_scenario needs env= or tmp_path=")
        env = LocalEnvironment(output_dir=tmp_path)
    model = ScriptedModel(script)
    recorder = EventRecorder()
    agent = Agent(model, env, max_turns=max_turns, on_event=recorder)
    result = run(agent.run(prompt, run_id=run_id))
    if assert_exhausted:
        model.assert_exhausted()
    run_dir = Path(str(result["run"]))
    return RunArtifacts(
        result=result,
        record=Record.load(run_dir / "record.json"),
        model=model,
        recorder=recorder,
        run_dir=run_dir,
    )


# ---------------------------------------------------------------------------
# Tool fakes shared by agent-loop tests
# ---------------------------------------------------------------------------


def stub_schema(name: str) -> dict[str, Any]:
    """A minimal tool schema for monkeypatched tool tables."""
    return _tool_schema(name, name, {}, [])


def compile_success_tool() -> Tool:
    """A fake ``compile`` tool that always succeeds and mints a USDZ file."""

    async def run_compile(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
        usdz = context.run_dir / "result" / "usdz" / "0000.usdz"
        usdz.parent.mkdir(parents=True, exist_ok=True)
        usdz.write_bytes(b"test-usdz")
        result = {"status": "success", "usdz": str(usdz)}
        context.compile_result = result
        context.successful_compile_result = result
        context.successful_compile_digest = workspace_digest(context.workspace)
        return result

    return Tool("compile", stub_schema("compile"), run_compile)


# ---------------------------------------------------------------------------
# Canonical workspace sources
# ---------------------------------------------------------------------------

GOOD_MAIN_PY = """
from build123d import Box

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("box")
    base = model.part("base")
    base.add(Box(0.2, 0.2, 0.1), name="body")
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    return TestContext(object_model).report()
"""
