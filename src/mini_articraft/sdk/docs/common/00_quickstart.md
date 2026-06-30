# SDK quickstart

## Scope

This page defines the exact script contract for `main.py`. Use the other docs
only when you need the details for a specific API.

## Required file

Write one file named `main.py` in the run workspace.

The file must import public SDK names from `mini_articraft.sdk`.

The file may import CadQuery as `cadquery` or as `cq`.

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
import cadquery as cq

from mini_articraft.sdk import (
    ArticulatedObject,
    Origin,
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
- `Origin`
- `SDKError`
- `TestContext`
- `TestFailure`
- `TestReport`
- `ValidationError`

Do not import private modules such as `mini_articraft.sdk._collision`.

Do not import low level joint classes or part classes. The helper methods on
`ArticulatedObject` create the required objects.

## Minimal valid script

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("hinged_box")

    base = model.part(
        "base",
        cq.Workplane("XY").box(0.24, 0.18, 0.04),
    )
    lid = model.part(
        "lid",
        cq.Workplane("XY").box(0.22, 0.16, 0.018),
    )

    model.revolute(
        "base_to_lid",
        base,
        lid,
        origin=Origin(xyz=(-0.11, 0.0, 0.04)),
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

## Units

CadQuery geometry is unitless. In generated mini-articraft scripts, treat all
linear dimensions as meters.

Use radians for `Origin.rpy` and for revolute joint limits.

Use the same linear unit as the CadQuery geometry for `Origin.xyz`, prismatic
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

CadQuery docs:

- `docs/sdk/cadquery/35_cadquery.md` documents how mini-articraft accepts CadQuery geometry and what CadQuery objects may be registered as parts.
- `docs/sdk/cadquery/36_cadquery_primer.md` documents the CadQuery object types that are useful in mini-articraft scripts.
- `docs/sdk/cadquery/37_cadquery_workplane.md` documents the approved `cq.Workplane` patterns for generated scripts.
- `docs/sdk/cadquery/38_cadquery_sketch.md` documents the approved `cq.Sketch` patterns for generated scripts.
- `docs/sdk/cadquery/39_cadquery_assembly.md` documents how to use `cq.Assembly` as geometry inside one mini-articraft part.
- `docs/sdk/cadquery/39b_cadquery_free_function.md` documents when to avoid CadQuery free function APIs in generated scripts.
- `docs/sdk/cadquery/39c_cadquery_api_ref.md` lists the CadQuery calls that generated scripts should prefer.
