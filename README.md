# mini-articraft

## Setup

Install the package and development tools:

```bash
uv sync --group dev
```

Add your OpenAI API key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

Run the checks:

```bash
uv run pytest -q
uv run ruff check .
```

## Run

Generate a model:

```bash
uv run mini-articraft generate "make a folding chair"
```
