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

- `docs/sdk/build123d/index.md` lists the copied build123d docs.
- `docs/sdk/build123d/markdown/build_part.md` documents `BuildPart`.
- `docs/sdk/build123d/markdown/build_sketch.md` documents `BuildSketch`.
- `docs/sdk/build123d/markdown/objects.md` documents objects such as `Box`, `Cylinder`, and `Sphere`.
- `docs/sdk/build123d/markdown/operations.md` documents operations such as `extrude`, `fillet`, `chamfer`, and `add`.
- `docs/sdk/build123d/markdown/assemblies.md` documents `Compound` based assemblies for fixed groups of shapes.
- `docs/sdk/build123d/markdown/import_export.md` documents build123d import and export helpers.
- `docs/sdk/build123d/markdown/direct_api_reference.md` documents the direct build123d API.
