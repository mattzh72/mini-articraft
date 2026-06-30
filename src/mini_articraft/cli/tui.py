"""Rich rendering for agent runs.

The renderer turns run events into a streaming transcript. The same code draws
a live run (events arrive from the harness callback while a pinned spinner
animates above) and a replayed run (conversation rows read back from disk). All
rich usage lives here so the agent core stays UI-free.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text

from mini_articraft.agent import events
from mini_articraft.record import Record, read_conversation

EventHandler = Callable[[events.Event], None]
LiveRun = Callable[[EventHandler], Awaitable[dict[str, Any]]]
PRIMARY_STYLE = "white"


def run_live(generate: LiveRun) -> dict[str, Any]:
    console = Console()
    renderer = RunRenderer(console)
    try:
        with Live(
            Text("starting…", style=PRIMARY_STYLE),
            console=console,
            auto_refresh=True,
            refresh_per_second=12,
            transient=True,
            vertical_overflow="visible",
        ) as live:
            renderer.attach(live)
            result = asyncio.run(generate(renderer.handle))
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print(Text("✗ interrupted", style="dim"))
        raise

    if renderer.finished is not None:
        console.print(renderer.final_summary(renderer.finished))
    return result


def replay_run(run_dir: Path, *, delay: float = 0.0, console: Console | None = None) -> None:
    console = console or Console()
    renderer = RunRenderer(console)
    console.print(Rule(run_dir.name, style=PRIMARY_STYLE))
    for row in read_conversation(run_dir / "conversation.jsonl"):
        renderer.render_row(row)
        if delay > 0 and console.is_terminal:
            time.sleep(delay)

    record = Record.load(run_dir / "record.json")
    console.print(
        renderer.final_summary(
            events.RunFinished(
                status=record.status,
                run=str(run_dir),
                result=record.result,
                error=record.error,
                turns=renderer.turn,
            )
        )
    )


class _StatusLine:
    """A live status line. Re-rendered by ``Live`` each tick so the spinner
    animates and the elapsed clock keeps ticking during a blocking model call."""

    def __init__(self, renderer: RunRenderer) -> None:
        self._renderer = renderer
        self._spinner = Spinner("dots", style=PRIMARY_STYLE)

    def __rich__(self) -> Spinner:
        self._spinner.update(text=self._renderer.status_text())
        return self._spinner


class RunRenderer:
    def __init__(self, console: Console, *, max_output_lines: int = 6) -> None:
        self.console = console
        self.max_output_lines = max_output_lines
        self._live: Live | None = None
        self._status = _StatusLine(self)
        self._names: dict[str, str] = {}
        self._turn = 0
        self._activity = "starting"
        self._started: float | None = None
        self._finished: events.RunFinished | None = None

    # ------------------------------------------------------------------ live --
    def attach(self, live: Live) -> None:
        self._live = live
        live.update(self._status)

    @property
    def finished(self) -> events.RunFinished | None:
        return self._finished

    @property
    def turn(self) -> int:
        return self._turn

    def status_text(self) -> Text:
        return Text(
            f"turn {self._turn} · {self._activity} · {self._elapsed():.0f}s",
            style=PRIMARY_STYLE,
        )

    def handle(self, event: events.Event) -> None:
        match event:
            case events.RunStarted(run_id=run_id, model=model):
                self._started = time.monotonic()
                self._activity = "thinking"
                title = f"{run_id} · {model}" if model else run_id
                self._print(Rule(title, style=PRIMARY_STYLE))
            case events.TurnStarted(turn=turn):
                self._turn = turn
                self._activity = "thinking"
            case events.AssistantMessage(text=text, tool_calls=tool_calls):
                self._print_assistant(text, tool_calls, print_calls=False)
            case events.ToolStarted(call_id=call_id, name=name, arguments=arguments):
                self._names[call_id] = name
                self._activity = name
                self._print_tool_call(name, arguments)
            case events.ToolFinished(call_id=call_id, name=name, payload=payload):
                self._names.setdefault(call_id, name)
                self._print_tool_result(name, payload)
            case events.RunFinished():
                self._finished = event

    def final_summary(self, event: events.RunFinished) -> Text:
        ok = event.status == "success"
        parts = [f"{'✓' if ok else '✗'} {event.status or 'unknown'}"]
        if event.run:
            parts.append(event.run)
        if event.turns:
            parts.append(f"{event.turns} turns")
        if event.duration is not None:
            parts.append(f"{event.duration:.1f}s")
        line = Text(" · ".join(parts), style="bold green" if ok else "bold red")
        if not ok and event.error:
            line.append("\n  " + _clip(event.error, 200), style="red")
        return line

    # ---------------------------------------------------------------- replay --
    def render_row(self, row: dict[str, Any]) -> None:
        match row.get("role"), row.get("type"):
            case "system", _:
                self._print(Text("· system prompt loaded", style="dim"))
            case "user", _:
                self._print_user(str(row.get("content") or ""))
            case "assistant", _:
                self._turn += 1
                tool_calls = list(row.get("tool_calls") or [])
                self._print_assistant(str(row.get("content") or ""), tool_calls, print_calls=True)
            case "compiler", _:
                self._print_compile(str(row.get("status") or ""), str(row.get("error") or ""))
            case _, "function_call_output":
                call_id = str(row.get("call_id") or "")
                name = self._names.get(call_id, "tool")
                self._print_tool_result(name, _load_output(row.get("output")))

    # --------------------------------------------------------------- helpers --
    def _print(self, renderable: Any) -> None:
        console = self._live.console if self._live is not None else self.console
        console.print(renderable)

    def _print_user(self, content: str) -> None:
        text = Text("▸ ", style="bold magenta")
        text.append(_clip(content, 200), style="magenta")
        self._print(text)

    def _print_assistant(
        self, text: str, tool_calls: list[dict[str, Any]], *, print_calls: bool
    ) -> None:
        body = text.strip()
        if not body and not tool_calls:
            return
        self._print(Text(f"turn {self._turn}", style="dim"))
        if body:
            line = Text()
            line.append("● ", style="bold green")
            line.append(body, style="white")
            self._print(line)
        if print_calls:
            for call in tool_calls:
                self._names[str(call.get("id") or "")] = str(call.get("name") or "")
                self._print_tool_call(str(call.get("name") or ""), str(call.get("arguments") or ""))

    def _print_tool_call(self, name: str, arguments: str) -> None:
        line = Text("  → ", style=PRIMARY_STYLE)
        summary = _args_summary(name, arguments)
        line.append(f"{name}({summary})" if summary else f"{name}()", style=PRIMARY_STYLE)
        self._print(line)

    def _print_tool_result(self, name: str, payload: dict[str, Any]) -> None:
        if "error" in payload:
            self._print(_indented(f"✗ {name} error: {_clip(str(payload['error']), 200)}", "red"))
            return
        result = payload.get("result")
        result = result if isinstance(result, dict) else {}
        match name:
            case "write" | "edit":
                detail = f"{result.get('bytes')} bytes" if "bytes" in result else "replaced"
                self._print(_indented(f"✓ {result.get('path', '')} ({detail})", "green"))
            case "read":
                self._print(_indented(f"✓ {result.get('path', '')}", "green"))
            case "compile":
                self._print_compile(str(result.get("status") or ""), str(result.get("error") or ""))
                self._print_output(result.get("stderr"))
            case "exec_command" | "write_stdin":
                self._print(_indented(self._exec_summary(result), self._exec_style(result)))
                self._print_output(result.get("stdout"))
                self._print_output(result.get("stderr"))
            case _:
                self._print(_indented(f"✓ {name}", "green"))

    def _print_compile(self, status: str, error: str) -> None:
        if status == "success":
            self._print(_indented("✓ compile ok", "green"))
        else:
            detail = f": {_clip(error, 200)}" if error else ""
            self._print(_indented(f"✗ compile error{detail}", "red"))

    def _print_output(self, output: Any) -> None:
        text = str(output or "")
        if not text.strip():
            return
        lines = text.splitlines()
        clipped = lines[: self.max_output_lines]
        for line in clipped:
            self._print(_indented(_clip(line, 120), "dim", depth=6))
        if len(lines) > len(clipped):
            self._print(_indented("… (truncated)", "dim", depth=6))

    @staticmethod
    def _exec_summary(result: dict[str, Any]) -> str:
        if result.get("timed_out"):
            return "✗ exec timed out"
        if result.get("running") or result.get("returncode") is None:
            return f"▷ exec running (session {result.get('session_id')})"
        wall = result.get("wall_time_seconds")
        suffix = f" ({wall}s)" if wall is not None else ""
        return f"✓ exec rc={result.get('returncode')}{suffix}"

    @staticmethod
    def _exec_style(result: dict[str, Any]) -> str:
        if result.get("timed_out") or result.get("returncode") not in (0, None):
            return "red"
        return "green" if result.get("returncode") == 0 else "yellow"

    def _elapsed(self) -> float:
        return 0.0 if self._started is None else time.monotonic() - self._started


def _indented(text: str, style: str, *, depth: int = 4) -> Text:
    return Text(" " * depth + text, style=style)


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _args_summary(name: str, arguments: str) -> str:
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(args, dict):
        return ""
    if name in ("write", "edit", "read"):
        return str(args.get("path", ""))
    if name == "exec_command":
        return _clip(str(args.get("command", "")), 60)
    if name == "write_stdin":
        return f"session {args.get('session_id', '')}"
    if name == "compile":
        return ""
    return _clip(", ".join(f"{key}={value}" for key, value in args.items()), 60)


def _load_output(output: Any) -> dict[str, Any]:
    try:
        payload = json.loads(output or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
