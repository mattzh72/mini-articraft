# SDK benchmarks

The SDK benchmark measures construction, conversion, boolean operations, welds,
refinement, collision checks, and core mesh work. It records timing and mesh
quality in one JSON file.

Run the standard suite with:

```bash
uv run python benchmarks/sdk_benchmark.py --output /tmp/sdk-benchmark.json
```

Use the quick suite while editing:

```bash
uv run python benchmarks/sdk_benchmark.py --suite quick
```

The extended suite adds larger welds, tube networks, shell partitioning, and
full compiler checks:

```bash
uv run python benchmarks/sdk_benchmark.py \
  --suite extended \
  --output /tmp/sdk-benchmark-before.json
```

Compare a later run with the saved result:

```bash
uv run python benchmarks/sdk_benchmark.py \
  --suite extended \
  --compare /tmp/sdk-benchmark-before.json \
  --output /tmp/sdk-benchmark-after.json
```

The comparison fails if a mesh loses watertightness, changes its connected body
count, gains invalid edges or degenerate triangles, or changes volume or surface
area beyond the allowed tolerance. It also checks the low end of triangle
quality. Timing changes are reported but do not fail the command because normal
machine load can affect short measurements.
