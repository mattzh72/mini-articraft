# SDK quickstart

Work in meters. Use radians for rotations and revolute limits.

Each `Part` is one rigid body. Add one or more named shapes to it. A shape can be a
`build123d.Shape` or `MeshGeometry`. Apply build123d `Pos`, `Rot`, or `Location` before you add
the shape. There is no second shape transform.

```python
from build123d import Box, Pos

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


model = ArticulatedObject("small_table")
body = model.part("body")
body.add(Box(0.8, 0.5, 0.04), name="top", color=(0.45, 0.24, 0.10))
body.add(Pos(X=0.36, Y=0.21, Z=-0.36) * Box(0.04, 0.04, 0.7), name="leg_1")

object_model = model


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    return ctx.report()
```

Every shape needs a unique name within its part. A color can contain RGB or RGBA values from
zero through one.

Use `model.articulation(...)` for fixed, revolute, continuous, and prismatic motion. Use named
shape arguments in exact checks when a part contains several shapes.

Read only the reference that applies to the next piece of geometry:

- Errors and validation: `docs/sdk/common/10_errors.md`.
- Shared units and types: `docs/sdk/common/20_core_types.md`.
- Named shapes and parts: `docs/sdk/common/30_articulated_object.md`.
- Articulations: `docs/sdk/common/35_joints.md`.
- Checks and geometry inspection: `docs/sdk/common/40_testing.md`.
- USDZ output: `docs/sdk/common/50_usdz_export.md`.
- Mesh editing, primitives, lathes, lofts, and extrusions:
  `docs/sdk/mesh/00_mesh_geometry.md`.
- Profiles and curve sampling: `docs/sdk/mesh/10_profiles.md`.
- Wires, pipes, and sweeps: `docs/sdk/mesh/20_wires_and_sweeps.md`.
- Section lofts and repair: `docs/sdk/mesh/30_section_lofts.md`.
- Mesh booleans, openings, and shell partitioning:
  `docs/sdk/mesh/40_booleans_and_shells.md`.

Detailed build123d pages are under `docs/sdk/build123d/`. Start with
`docs/sdk/build123d/key_concepts_algebra.md` for object algebra,
`docs/sdk/build123d/moving_objects.md` for placement,
`docs/sdk/build123d/operations.md` for solid operations, and
`docs/sdk/build123d/topology_selection.md` for selecting faces and edges.
The copied build123d examples may use arbitrary dimensions. Convert every dimension to meters in
mini-articraft.

Use the reference pages for API discovery. Use short `exec_command` inspections after authoring to
measure bounds, distances, collisions, and posed geometry.

Executable examples are under `docs/sdk/examples/`. Read only the example closest to the current
task. The set includes a hollow shell, a section loft with a swept wire, and a mixed build123d
and mesh articulated assembly.

Run `compile` after meaningful edits. Treat checks as design evidence. A failed check is not a
reason to remove or simplify geometry that the prompt requires.
