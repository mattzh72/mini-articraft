# Core types

## Scope

This page documents the public names exported by `mini_articraft.sdk` and the
data values returned by public methods.

Generated scripts author SDK objects only. Compile owns export and record
creation.

## Public exports

`mini_articraft.sdk` exports these names:

```python
from mini_articraft.sdk import (
    AllowedOverlap,
    ArticulatedObject,
    CollisionFinding,
    DistanceFinding,
    Frame,
    SDKError,
    TestContext,
    TestFailure,
    TestReport,
    ValidationError,
)
```

Do not import `Origin`. Use `Frame`.

Do not import from modules below `mini_articraft.sdk`. Those modules are
implementation details.

## `ArticulatedObject`

```python
ArticulatedObject(name: str, *, units: str)
```

Creates an empty object model.

`units` is required. Supported values are `"meters"`, `"centimeters"`,
`"millimeters"`, `"inches"`, and `"feet"`.

The model owns:

- `name`, which is a non-empty string.
- `units`, which declares what build123d coordinates mean.
- `meters_per_unit`, which is the scale of one model unit in meters.
- `parts`, which is a list of registered part handles.
- `joints`, which is a list of registered joint handles.

Add parts with `model.part(...)`.

Add joints with `model.fixed(...)`, `model.revolute(...)`,
`model.continuous(...)`, and `model.prismatic(...)`.

## Part handles

`model.part(...)` returns a part handle.

A part handle has these public fields:

- `name`, which is the part name.
- `shape`, which is the build123d `Shape` used for the part.
- `color`, which is either `None` or an RGBA tuple with values from `0.0` to `1.0`.

The `color=` argument accepts RGB or RGBA. RGB is stored with alpha `1.0`.

Use color to make important parts readable in exported artifacts and previews.

You may pass a part handle anywhere a method accepts `str | part_handle`.

Use the part name string in tests when that is clearer.

## Joint handles

Each joint helper returns a joint handle.

A joint handle has these public fields:

- `name`
- `type`
- `parent`
- `child`
- `frame`
- `axis`
- `limits`

Generated scripts should pass joint handles to `ctx.pose(...)` only when useful.
String joint names are preferred in simple code.

Do not construct joint handles directly.

## `Frame`

```python
Frame(
    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
)
```

`Frame` defines the joint frame in the parent part frame.

`xyz` is translation.

`rpy` is rotation as roll, pitch, and yaw in radians.

Both fields must contain exactly three numeric values.

Use `Frame()` when the joint frame is at the parent part frame with no
translation and no rotation.

## Test dataclasses

### `TestFailure`

```python
TestFailure(name: str, details: str)
```

Records one failed check.

### `AllowedOverlap`

```python
AllowedOverlap(
    link_a: str,
    link_b: str,
    reason: str,
    elem_a: str | None = None,
    elem_b: str | None = None,
)
```

Records one intentional overlap allowance.

In the current mini SDK, `elem_a` and `elem_b` are stored in the report but are
not enforced. A matching allowance suppresses the whole part pair in the
baseline collision check.

### `CollisionFinding`

```python
CollisionFinding(
    link_a: str,
    link_b: str,
    contacts: int,
    max_depth: float | None = None,
    normal: tuple[float, float, float] | None = None,
    position: tuple[float, float, float] | None = None,
)
```

Represents collision details reported by FCL when they are available.

### `DistanceFinding`

```python
DistanceFinding(
    link_a: str,
    link_b: str,
    distance: float,
    nearest_a: tuple[float, float, float] | None = None,
    nearest_b: tuple[float, float, float] | None = None,
    collided: bool = False,
)
```

Represents a mesh distance result.

### `TestReport`

```python
TestReport(
    passed: bool,
    checks_run: int,
    checks: tuple[str, ...],
    failures: tuple[TestFailure, ...],
    warnings: tuple[str, ...] = (),
    allowances: tuple[str, ...] = (),
    allowed_isolated_parts: tuple[str, ...] = (),
    allowed_overlaps: tuple[AllowedOverlap, ...] = (),
)
```

`run_tests()` must return this type.

Use `ctx.report()` to create it.

Do not hand build a report unless a test specifically needs to return a known
fixed report.

## Errors

`ValidationError` is raised when a model definition, joint definition, pose, or
test argument is invalid.

`SDKError` is the base SDK error type.

Generated scripts do not need to catch these errors. Compile reports them.

## Units

Every object must declare units.

Use radians for rotations.

Use the same linear unit for build123d geometry, `Frame.xyz`, prismatic motion,
mesh distance checks, and contact tolerances.
