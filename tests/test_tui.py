from __future__ import annotations

import io
import json

from rich.console import Console

from mini_articraft.agent import events
from mini_articraft.cli.tui import PRIMARY_STYLE, RunRenderer


def _renderer() -> tuple[RunRenderer, Console]:
    console = Console(file=io.StringIO(), width=120)
    return RunRenderer(console), console


def _text(console: Console) -> str:
    return console.file.getvalue()


def test_renderer_primary_status_style_is_white() -> None:
    renderer, _console = _renderer()

    assert str(renderer.status_text().style) == PRIMARY_STYLE


def test_renderer_streams_transcript() -> None:
    renderer, console = _renderer()
    sequence = [
        events.RunStarted("run-x", "gpt-5.5", "a box"),
        events.TurnStarted(1),
        events.AssistantMessage(1, "I'll write the file.", [{"id": "c1", "name": "write"}]),
        events.ToolStarted("c1", "write", '{"path": "main.py"}'),
        events.ToolFinished("c1", "write", {"result": {"path": "main.py", "bytes": 412}}, 0.01),
    ]
    for event in sequence:
        renderer.handle(event)

    out = _text(console)
    assert "run-x" in out
    assert "gpt-5.5" in out
    assert "I'll write the file." in out
    assert "write(main.py)" in out
    assert "main.py (412 bytes)" in out


def test_renderer_shows_compile_and_errors() -> None:
    renderer, console = _renderer()
    renderer.handle(
        events.ToolFinished(
            "c1",
            "compile",
            {"result": {"status": "error", "error": "NameError: foo", "stderr": "Traceback\nboom"}},
            0.1,
        )
    )
    renderer.handle(events.ToolFinished("c2", "read", {"error": "file not found"}, 0.0))

    out = _text(console)
    assert "compile error: NameError: foo" in out
    assert "read error: file not found" in out


def test_renderer_truncates_long_output() -> None:
    renderer, console = _renderer()
    stdout = "\n".join(f"line {i}" for i in range(20))
    renderer.handle(
        events.ToolFinished(
            "c1",
            "exec_command",
            {
                "result": {
                    "returncode": 0,
                    "running": False,
                    "wall_time_seconds": 0.2,
                    "stdout": stdout,
                }
            },
            0.2,
        )
    )

    out = _text(console)
    assert "exec rc=0" in out
    assert "line 0" in out
    assert "… (truncated)" in out
    assert "line 19" not in out


def test_final_summary_success() -> None:
    renderer, console = _renderer()
    summary = renderer.final_summary(
        events.RunFinished(
            status="success", run="runs/run-x", result="result/model.usdz", turns=3, duration=18.4
        )
    )
    console.print(summary)

    out = _text(console)
    assert "success" in out
    assert "runs/run-x" in out
    assert "3 turns" in out


def test_final_summary_error_includes_message() -> None:
    renderer, console = _renderer()
    summary = renderer.final_summary(
        events.RunFinished(status="error", run="runs/run-x", error="compile failed", turns=5)
    )
    console.print(summary)

    out = _text(console)
    assert "error" in out
    assert "compile failed" in out


def test_replay_rows_resolve_tool_names() -> None:
    renderer, console = _renderer()
    rows = [
        {"role": "system", "content": "you are an agent"},
        {"role": "user", "content": "make a box"},
        {
            "role": "assistant",
            "content": "writing",
            "tool_calls": [
                {"id": "c1", "name": "write", "arguments": json.dumps({"path": "main.py"})}
            ],
        },
        {
            "type": "function_call_output",
            "call_id": "c1",
            "output": json.dumps({"result": {"path": "main.py", "bytes": 120}}),
        },
        {"role": "compiler", "status": "success", "error": ""},
    ]
    for row in rows:
        renderer.render_row(row)

    out = _text(console)
    assert "make a box" in out
    assert "write(main.py)" in out
    assert "main.py (120 bytes)" in out
    assert "compile ok" in out
    assert renderer.turn == 1
