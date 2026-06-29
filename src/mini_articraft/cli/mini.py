from __future__ import annotations

import typer

app = typer.Typer(help="Generate articulated objects with mini-articraft.")


@app.command()
def generate(prompt: str) -> None:
    """Generate an object from a prompt."""
    raise NotImplementedError


def main() -> None:
    app()


if __name__ == "__main__":
    main()
