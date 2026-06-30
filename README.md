# mini-articraft

mini-articraft is a small reference version of Articraft.

The first goal is to keep the code easy to read. The core loop is:

```text
prompt -> model -> environment -> record
```

The core version includes a tiny CadQuery-based SDK, basic joints, a local compile environment, Markdown prompts, simple CLI commands, and USDZ output.

It will not include the full Articraft SDK, viewer, provenance system, or data library.

Generated scripts author `ArticulatedObject` instances. Compile translates the
SDK object into `result/model.usdz` and keeps `result/model.json` as a small
manifest.

## Development

Use uv:

```bash
uv sync --group dev
uv run pytest -q
uv run ruff check .
```

Put `OPENAI_API_KEY` in `.env` to use the default OpenAI Responses model adapter.
OpenAI is async Responses WebSocket-only, never stores responses, and requests GPT-5.5's full output budget.
