# SDK quickstart

## Scope

This page defines the script contract for `main.py`. Use the other docs only
when you need details for a specific API.

Generated scripts must author a Python SDK object. Compile owns export.

## Required file

Write one file named `main.py` in the run workspace.

The file must import public SDK names from `mini_articraft.sdk`.

The file should import build123d with this form:

```python
from build123d import *
```

The file must define these top level names:

```python
def build_object_model() -> ArticulatedObject: ...
object_model = build_object_model()
def run_tests() -> TestReport: ...
```

`object_model` must be an `ArticulatedObject`.

`run_tests()` must return a `TestReport`.

The compile worker runs `run_tests()` before export. Compile fails when
`run_tests()` is missing, when it returns another type, or when the returned
report has blocking failures.

## Public imports

Use this import form in generated scripts:

```python
from build123d import *

from mini_articraft.sdk import (
    ArticulatedObject,
    Frame,
    TestContext,
    TestReport,
    ValidationError,
)
```

Only these names are public from `mini_articraft.sdk`:

- `AllowedOverlap`
- `ArticulatedObject`
- `CollisionFinding`
- `DistanceFinding`
- `Frame`
- `SDKError`
- `TestContext`
- `TestFailure`
- `TestReport`
- `ValidationError`

Do not import `Origin`. The SDK uses `Frame`.

Do not import private modules such as `mini_articraft.sdk._collision`.

Do not import low level joint classes or part classes. The helper methods on
`ArticulatedObject` create the required objects.

## Minimal valid script

```python
from build123d import *

from mini_articraft.sdk import ArticulatedObject, Frame, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("hinged_box", units="meters")

    base = model.part(
        "base",
        Box(0.24, 0.18, 0.04, align=(Align.CENTER, Align.CENTER, Align.MIN)),
        color=(0.55, 0.57, 0.60),
    )
    lid = model.part(
        "lid",
        Pos(0.11, 0.0, 0.009) * Box(0.22, 0.16, 0.018),
        color=(0.20, 0.36, 0.70),
    )

    model.revolute(
        "base_to_lid",
        base,
        lid,
        frame=Frame(xyz=(-0.12, 0.0, 0.04)),
        axis=(0.0, -1.0, 0.0),
        limits=(0.0, 1.2),
    )

    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    ctx.expect_contact("base", "lid")
    with ctx.pose(base_to_lid=0.9):
        ctx.expect_no_collision("base", "lid")
    return ctx.report()
```

When you build geometry with a `BuildPart` context, pass `builder.part` to
`model.part(...)`, not the builder object itself.

## Units

Every `ArticulatedObject` must declare units.

Supported units are:

- `"meters"`
- `"centimeters"`
- `"millimeters"`
- `"inches"`
- `"feet"`

build123d geometry is unitless. The declared object units say what those numbers
mean. Use meters for room scale objects. Use millimeters for small mechanical or
fabrication style objects.

Use radians for `Frame.rpy` and for revolute joint limits.

Use the same linear unit as the build123d geometry for `Frame.xyz`, prismatic
limits, mesh distances, and test tolerances.

## Compile behavior

Compile performs these steps:

1. Run `main.py`.
2. Read `object_model`.
3. Run `run_tests()`.
4. Run baseline SDK checks.
5. Export the object only when all blocking tests pass.

The baseline checks validate the model, require one root part, check for
isolated parts, and check current pose part collisions.

Authored allowances from `run_tests()` carry into the baseline pass.

## Docs router

Common docs:

- `docs/sdk/common/00_quickstart.md` documents the script contract, public imports, units, compile behavior, and this router.
- `docs/sdk/common/20_core_types.md` documents exported SDK names, returned handles, dataclass fields, units, and errors.
- `docs/sdk/common/30_articulated_object.md` documents `ArticulatedObject`, parts, joint helpers, lookup, validation, and graph rules.
- `docs/sdk/common/35_joints.md` documents joint frames, fixed joints, revolute joints, continuous joints, prismatic joints, axes, and limits.
- `docs/sdk/common/40_testing.md` documents `TestReport`, `TestContext`, authored checks, baseline checks, mesh collision, distance checks, poses, and allowances.

build123d docs:

- `docs/sdk/build123d/algebra_definition.md` the formal object and placement algebra behind build123d algebra mode.
- `docs/sdk/build123d/algebra_performance.md` performance guidance for algebra mode, especially batching operations instead of repeatedly fusing in loops.
- `docs/sdk/build123d/assemblies.md` assembly organization with `Compound` trees, labels, joints, and packing helpers.
- `docs/sdk/build123d/build_line.md` the `BuildLine` context manager for constructing one-dimensional curves and wire geometry.
- `docs/sdk/build123d/build_part.md` the `BuildPart` context manager for creating three-dimensional parts from objects, sketches, and operations.
- `docs/sdk/build123d/build_sketch.md` the `BuildSketch` context manager for creating planar two-dimensional profiles.
- `docs/sdk/build123d/center.md` center calculations for CAD objects, including bounding-box, geometry, and mass centers.
- `docs/sdk/build123d/debugging_logging.md` debugging build123d scripts with Python debuggers, logging, and diagnostic output.
- `docs/sdk/build123d/examples_1.md` catalogs upstream build123d examples, with local verbatim copies under `docs/sdk/build123d/examples/`.
- `docs/sdk/build123d/introduction.md` explains build123d's design goals, BREP geometry, parametric Python, and differences from CadQuery.
- `docs/sdk/build123d/introductory_examples.md` is a broad tour of small build123d examples, with references to upstream example scripts when available.
- `docs/sdk/build123d/joints.md` build123d joints for arranging solids and compounds with rigid, revolute, linear, cylindrical, and ball motion relationships.
- `docs/sdk/build123d/key_concepts.md` explains topology, locations, moving shapes, selectors, and `ShapeList`.
- `docs/sdk/build123d/key_concepts_algebra.md` explains algebra mode with object arithmetic and placement arithmetic.
- `docs/sdk/build123d/key_concepts_builder.md` explains builder mode with `BuildLine`, `BuildSketch`, `BuildPart`, workplanes, locations, modes, and pending objects.
- `docs/sdk/build123d/location_arithmetic.md` algebra-mode placement semantics for planes, locations, positions, and rotations.
- `docs/sdk/build123d/moving_objects.md` explains builder-mode placement, algebra-mode placement, direct movement methods, translation, and rotation.
- `docs/sdk/build123d/objects.md` object constructors for 1D curves, 2D sketches, and 3D parts, including common primitives and object placement notes.
- `docs/sdk/build123d/OpenSCAD.md` explains how build123d differs from OpenSCAD and why profile-driven BREP modeling is usually preferable to solid-first CSG.
- `docs/sdk/build123d/operations.md` build123d operations such as add, extrude, fillet, chamfer, loft, mirror, offset, revolve, sweep, and split.
- `docs/sdk/build123d/tech_drawing_tutorial.md` explains how to create projected 2D technical drawing views from a build123d model and export SVG output.
- `docs/sdk/build123d/tips.md` build123d modeling tips, best practices, FAQ guidance, and common pitfalls.
- `docs/sdk/build123d/topology_selection.md` selectors, `ShapeList`, filtering, sorting, grouping, and topology exploration patterns.
- `docs/sdk/build123d/tttt.md` lists Too Tall Toby challenge references and build123d solution links from the upstream tutorial page.
- `docs/sdk/build123d/tutorial_constraints.md` explains how build123d uses precise construction and targeted constraint helpers instead of a broad sketch constraint solver.
- `docs/sdk/build123d/tutorial_design.md` is a step-by-step workflow for analyzing a part, choosing an origin, sketching profiles, extruding, filleting, and adding holes.
- `docs/sdk/build123d/tutorial_joints.md` is a build123d joint tutorial covering rigid, revolute, and cylindrical joints in a hinge assembly.
- `docs/sdk/build123d/tutorial_lego.md` is a step-by-step parametric Lego block tutorial using sketches, offsets, grids, extrusion, pips, and fillets.
- `docs/sdk/build123d/tutorial_selectors.md` is a step-by-step selector walkthrough that builds a part and fillets the intended edge using robust topological selection.
- `docs/sdk/build123d/tutorial_stl_reconstruction.md` explains a mesh-guided workflow for detecting primitive hints from STL files and rewriting them into clean build123d models.
- `docs/sdk/build123d/tutorial_surface_modeling.md` introduces direct surface modeling and build123d face construction tools.

build123d support files:

- `docs/sdk/build123d/assets/` contains upstream docs images and asset-local source files.
- `docs/sdk/build123d/examples/` contains upstream example scripts and data files.
- `docs/sdk/build123d/media/` contains standalone upstream docs media and reference files.
- `docs/sdk/build123d/snippets/` contains upstream docs-root source snippets used by literal includes.
