from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from mini_articraft.agent import Agent
from mini_articraft.environments import LocalEnvironment
from mini_articraft.models import OpenAIModel
from mini_articraft.settings import Settings, get_settings

app = typer.Typer(help="Generate articulated objects with mini-articraft.", add_completion=False)


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
) -> None:
    """Generate an object from a prompt."""
    result = asyncio.run(_generate(prompt, model, output_dir, reasoning_effort))
    _print_result(result)


async def _generate(
    prompt: str,
    model: str | None,
    output_dir: Path | None,
    reasoning_effort: str | None,
) -> dict[str, object]:
    settings = _settings(model, output_dir, reasoning_effort)
    model_client = OpenAIModel(settings)
    try:
        env = LocalEnvironment(output_dir=settings.output_dir)
        return await Agent(model_client, env).run(prompt)
    finally:
        await model_client.close()


def _settings(
    model: str | None,
    output_dir: Path | None,
    reasoning_effort: str | None,
) -> Settings:
    updates: dict[str, object] = {}
    if model is not None:
        updates["openai_model"] = model
    if output_dir is not None:
        updates["output_dir"] = output_dir
    if reasoning_effort is not None:
        updates["openai_reasoning_effort"] = reasoning_effort
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
    app()


if __name__ == "__main__":
    main()
