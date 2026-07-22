# mini-articraft

A simpler, sharper take on [articraft](https://github.com/mattzh72/articraft) — the same
core idea, distilled to a single agent loop and a mesh SDK. Give it a prompt, get back an
articulated 3D object: an agent writes and iterates on a build script against the mesh
SDK, the compiler checks the geometry (including the articulation in motion), and the
result exports as a posable USDZ you can open in the built-in viewer.

<p align="center">
  <img src="assets/readme/stand_mixer.gif" width="44%" alt="Stand mixer: head tilting back while the view orbits">
  <img src="assets/readme/desk_fan.gif" width="44%" alt="Desk fan: rotor spinning inside its cage while the view orbits">
</p>

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

Run the SDK speed and mesh quality benchmark:

```bash
uv run python benchmarks/sdk_benchmark.py --suite extended
```

See [benchmarks/README.md](benchmarks/README.md) for saved comparisons and smaller suites.

## Run

Generate a model:

```bash
uv run mini-articraft generate "make a folding chair"
```

Inspect every numbered USDZ version from a run:

```bash
uv run mini-articraft view 20260713-175925-make-a-realistic-articulated-desk-lamp
```

Pass a run ID from the default output directory or a path to a run. The viewer opens in
your browser with version switching, part selection, and joint controls. It needs an
internet connection to load Three.js.

## Docs

The agent builds objects against the SDK reference in
[`src/mini_articraft/sdk/docs`](src/mini_articraft/sdk/docs) — the same docs are the best
way to understand the SDK yourself:

- [`common/`](src/mini_articraft/sdk/docs/common) — the quickstart, core types, parts and
  joints, authoring tests, and USDZ export.
- [`mesh/`](src/mini_articraft/sdk/docs/mesh) — geometry, profiles, sweeps, lofts, and the
  boolean/weld operations that fuse parts into one molded piece.
- [`examples/`](src/mini_articraft/sdk/docs/examples) — executable worked examples (a
  molded mug handle, a hollow shell, a mixed assembly) that the agent clones for its task.

See [AGENTS.md](AGENTS.md) for how the repo is organized and what to keep small.
