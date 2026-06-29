# mini-articraft

mini-articraft is a small reference version of Articraft.

The first goal is to keep the code easy to read. The core loop is:

```text
prompt -> model -> environment -> record
```

The first version will include a tiny CadQuery-based SDK, basic joints, a local compile environment, Markdown prompts, and simple CLI commands.

It will not include the full Articraft SDK, viewer, provenance system, or data library.

## Development

Use uv:

```bash
uv sync --group dev
uv run pytest -q
uv run ruff check .
```

Put `OPENAI_API_KEY` in `.env` to use the default OpenAI Responses model adapter.
Reasoning output is capped with `MINI_ARTICRAFT_MAX_OUTPUT_TOKENS`, which includes hidden reasoning tokens.
