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

Run the SDK speed and mesh quality benchmark:

```bash
uv run python benchmarks/sdk_benchmark.py --suite extended
```

See [benchmarks/README.md](benchmarks/README.md) for saved comparisons and smaller suites.

## Use the Python SDK

Add mini-articraft directly from GitHub while the package is pre-release:

```bash
uv add "mini-articraft @ git+https://github.com/mattzh72/mini-articraft"
```

The root SDK owns object modeling, geometry, articulations, and physical checks. Mesh operations
live in `mini_articraft.sdk.mesh`; USDZ publication is explicit so a normal SDK import does not
eagerly load OpenUSD.

```python
from build123d import Box

from mini_articraft.sdk import ArticulatedObject, TestContext
from mini_articraft.sdk.export import export_object

model = ArticulatedObject("box")
model.part("body").add(Box(0.1, 0.1, 0.1), name="shell")
model.validate()

report = TestContext(model).report()
assert report.passed

result = export_object(model, "output")
print(result.usdz)
```

See the [hinged box](examples/hinged_box/main.py) and
[procedural mesh knob](examples/mesh_knob/main.py) for complete examples.

## Run

Generate a model:

```bash
uv run mini-articraft generate "make a folding chair"
```

Inspect every numbered USDZ version from a run:

```bash
uv run mini-articraft view 20260713-175925-make-a-realistic-articulated-desk-lamp
```

Pass a run ID from the default output directory or a path to a run. The viewer opens in your
browser with version switching, part selection, and joint controls. It needs an internet
connection to load Three.js.
