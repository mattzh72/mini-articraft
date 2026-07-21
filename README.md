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

### Install a GitHub preview release

Preview releases attach the exact wheel tested by CI. This repository is private, so authenticate
the GitHub CLI before downloading an asset:

```bash
gh auth status
mkdir -p /tmp/mini-articraft-preview
gh release download sdk-preview-2026-07-21.1 \
  --repo mattzh72/mini-articraft \
  --pattern "mini_articraft-0.1.0-py3-none-any.whl" \
  --dir /tmp/mini-articraft-preview \
  --clobber

uv venv
uv pip install \
  --python .venv/bin/python \
  /tmp/mini-articraft-preview/mini_articraft-0.1.0-py3-none-any.whl
```

Code outside this checkout can then import the installed package normally:

```python
from mini_articraft.sdk import ArticulatedObject, TestContext
from mini_articraft.sdk.export import export_object
```

To record a preview as a project dependency instead of downloading its wheel, pin the release tag
over SSH:

```bash
uv add "mini-articraft @ git+ssh://git@github.com/mattzh72/mini-articraft.git@sdk-preview-2026-07-21.1"
```

### Create a GitHub preview release

Each release needs a unique PEP 440 prerelease version. Update `__version__` in
`src/mini_articraft/__init__.py` (for example, `0.1.1a1`), run `uv lock`, commit the change, and
push it. The tag must be exactly `v` plus that package version.

Run the manual release workflow against the commit to publish:

```bash
gh workflow run release-preview.yml \
  --ref your-branch-or-main \
  -f tag=v0.1.1a1
gh run watch
```

The workflow rejects mismatched or non-prerelease tags, builds with publishable dependency
metadata, checks and smoke-tests the wheel and sdist, creates `SHA256SUMS`, and publishes a GitHub
prerelease targeting the selected commit. Only the final release job receives `contents: write`.

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
