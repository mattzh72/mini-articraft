from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from mini_articraft.agent import Agent, events
from mini_articraft.cli.tui import replay_run, run_live
from mini_articraft.environments import LocalEnvironment
from mini_articraft.models import OpenAIModel
from mini_articraft.settings import DEFAULT_OUTPUT_DIR, Settings, get_settings
from mini_articraft.viewer import serve_viewer

app = typer.Typer(help="Generate articulated objects with mini-articraft.", add_completion=False)
COMMANDS = {"generate", "replay", "view"}


@app.command()
def generate(
    prompt: str,
    model: str | None = typer.Option(None, "-m", "--model", help="Model to use."),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Run output directory."),
    reasoning_effort: str | None = typer.Option(
        None,
        "--reasoning-effort",
        help="OpenAI reasoning effort.",
    ),
    tui: bool | None = typer.Option(
        None,
        "--tui/--no-tui",
        help="Show the live run UI (default: on when attached to a terminal).",
    ),
) -> None:
    """Generate an object from a prompt."""
    settings = _settings(model, output_dir, reasoning_effort)
    use_tui = tui if tui is not None else sys.stdout.isatty()
    if use_tui:
        _generate_with_tui(settings, prompt)
    else:
        _print_result(asyncio.run(_generate(settings, prompt)))


@app.command()
def replay(
    run: str = typer.Argument(
        ..., help="Run id under the output directory, or a path to a run directory."
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Run output directory."),
    delay: float = typer.Option(0.0, "--delay", help="Pause between events in seconds (TTY only)."),
) -> None:
    """Re-render a recorded run from its conversation log."""
    run_dir = _resolve_run_dir(run, output_dir)
    conversation = run_dir / "conversation.jsonl"
    if not conversation.is_file():
        typer.echo(f"no conversation log at {conversation}", err=True)
        raise typer.Exit(1)

    replay_run(run_dir, delay=delay)


@app.command()
def view(
    run: str = typer.Argument(
        ..., help="Run id under the output directory, or a path to a run directory."
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Run output directory."),
) -> None:
    """Open the articulated USDZ outputs for a run."""
    try:
        serve_viewer(_resolve_run_dir(run, output_dir))
    except (OSError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from None


async def _generate(
    settings: Settings,
    prompt: str,
    *,
    on_event: Callable[[events.Event], None] | None = None,
) -> dict[str, Any]:
    model_client = OpenAIModel(settings)
    try:
        env = LocalEnvironment(output_dir=settings.output_dir)
        agent_kwargs: dict[str, Any] = {"max_turns": settings.max_turns}
        if on_event is not None:
            agent_kwargs["on_event"] = on_event
        return await Agent(model_client, env, **agent_kwargs).run(prompt)
    finally:
        await model_client.close()


def _generate_with_tui(settings: Settings, prompt: str) -> None:
    try:
        result = run_live(lambda on_event: _generate(settings, prompt, on_event=on_event))
    except (KeyboardInterrupt, asyncio.CancelledError):
        raise typer.Exit(130) from None

    if str(result.get("status")) != "success":
        raise typer.Exit(1)


def _resolve_run_dir(run: str, output_dir: Path | None) -> Path:
    candidate = Path(run)
    return candidate if candidate.is_dir() else (output_dir or _default_output_dir()) / run


def _default_output_dir() -> Path:
    try:
        return get_settings().output_dir
    except ValidationError:
        return DEFAULT_OUTPUT_DIR


def _settings(
    model: str | None,
    output_dir: Path | None,
    reasoning_effort: str | None,
) -> Settings:
    updates = {
        key: value
        for key, value in (
            ("openai_model", model),
            ("output_dir", output_dir),
            ("openai_reasoning_effort", reasoning_effort),
        )
        if value is not None
    }
    return get_settings().model_copy(update=updates)


def _print_result(result: dict[str, object]) -> None:
    typer.echo(f"status: {result.get('status', '')}")
    typer.echo(f"run: {result.get('run', '')}")
    if result.get("result"):
        typer.echo(f"result: {result['result']}")
    if result.get("message"):
        typer.echo(str(result["message"]))
    if result.get("error"):
        typer.echo(f"error: {result['error']}", err=True)
    if result.get("status") != "success":
        raise typer.Exit(1)


def main() -> None:
    app(args=_app_args(sys.argv[1:]), prog_name="mini-articraft")


def _app_args(argv: list[str]) -> list[str]:
    if not argv or argv[0] in COMMANDS or argv[0] in {"--help", "-h"}:
        return argv
    return ["generate", *argv]


if __name__ == "__main__":
    main()
