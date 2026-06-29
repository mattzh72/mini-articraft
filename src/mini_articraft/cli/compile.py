from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="Compile a mini-articraft script.")


@app.command()
def compile(path: Path) -> None:
    """Compile one generated script."""
    raise NotImplementedError


def main() -> None:
    app()


if __name__ == "__main__":
    main()
