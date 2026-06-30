---
name: sdk-core-types
description: Read this when you need exact mini-articraft constructors and units for Origin, Part, Joint, JointLimits, ContinuousLimits, and ExportResult.
metadata:
  short-description: Core constructors, values, units, and errors.
---

# Core Types

## Purpose

This page documents the small set of value types used by the mini-articraft
SDK: transforms, parts, joints, joint limits, and export results.

## Import

```python
from mini_articraft.sdk import (
    ArticulatedObject,
    ContinuousLimits,
    ExportResult,
    Joint,
    JointLimits,
    JointType,
    Origin,
    Part,
    ValidationError,
    export_object,
)
```

## Units

CadQuery is unitless. For mini-articraft authoring, use meters when possible.

- `Origin.xyz` uses the same distance unit as the CadQuery geometry.
- `Origin.rpy` is `(roll, pitch, yaw)` in radians.
- Revolute joint limits are in radians.
- Continuous joints have no lower or upper position bounds.
- Prismatic joint limits use the same distance unit as the CadQuery geometry.

## Recommended Surface

- `Origin`
- `Part`
- `ArticulatedObject`
- `Joint`
- `JointType`
- `JointLimits`
- `ContinuousLimits`
- `ExportResult`
- `export_object(...)`

## Transforms

### `Origin`

```python
Origin(
    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0),
)
```

- `xyz`: translation from the parent part frame to the joint frame.
- `rpy`: rotation from the parent part frame to the joint frame.
- Both fields must contain exactly 3 numeric values.

Use `Origin()` when the joint frame is already at the parent part origin.

## Parts

### `Part`

```python
Part(
    name: str,
    shape: cadquery.Workplane | cadquery.Shape | cadquery.Assembly,
)
```

- `name`: required part name.
- `shape`: CadQuery geometry for that part.

Normally create parts through `model.part(...)` rather than by constructing
`Part` directly. The helper checks for duplicate names and appends the part to
the model.

```python
base = model.part("base", cq.Workplane("XY").box(0.3, 0.2, 0.05))
```

## Joint Types

### `JointType`

```python
JointType.FIXED
JointType.REVOLUTE
JointType.CONTINUOUS
JointType.PRISMATIC
```

String values are accepted by the helpers, but enum values make intent clearer.

```python
model.joint("base_to_lid", JointType.REVOLUTE, base, lid, limits=(0.0, 1.2))
```

## Joint Limits

### `JointLimits`

```python
JointLimits(
    lower: float,
    upper: float,
    effort: float = 1.0,
    velocity: float = 1.0,
)
```

- `lower`: lower joint-position bound.
- `upper`: upper joint-position bound.
- `effort`: positive effort value.
- `velocity`: positive velocity value.

Use `JointLimits` for `REVOLUTE` and `PRISMATIC` joints.

For convenience, a `(lower, upper)` pair is also accepted:

```python
model.revolute("base_to_lid", base, lid, limits=(0.0, 1.2))
```

Use explicit `JointLimits` when effort or velocity should be recorded:

```python
model.prismatic(
    "cabinet_to_drawer",
    cabinet,
    drawer,
    axis=(1.0, 0.0, 0.0),
    limits=JointLimits(lower=0.0, upper=0.28, effort=40.0, velocity=0.25),
)
```

### `ContinuousLimits`

```python
ContinuousLimits(
    effort: float = 1.0,
    velocity: float = 1.0,
)
```

- `effort`: positive effort value.
- `velocity`: positive velocity value.

Use `ContinuousLimits` for `CONTINUOUS` joints. A continuous joint is unbounded,
so it does not accept `lower` or `upper`.

```python
model.continuous(
    "hub_to_wheel",
    hub,
    wheel,
    axis=(0.0, 1.0, 0.0),
    limits=ContinuousLimits(effort=2.0, velocity=20.0),
)
```

## Joints

### `Joint`

```python
Joint(
    name: str,
    type: JointType | str,
    parent: str,
    child: str,
    origin: Origin = Origin(),
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: JointLimits | ContinuousLimits | None = None,
)
```

- `name`: required joint name.
- `type`: fixed, revolute, continuous, or prismatic.
- `parent`: parent part name.
- `child`: child part name.
- `origin`: joint frame expressed in the parent part frame.
- `axis`: motion axis expressed in the joint frame.
- `limits`: required for moving joints except fixed joints.

Normally create joints through `model.fixed(...)`, `model.revolute(...)`,
`model.continuous(...)`, `model.prismatic(...)`, or `model.joint(...)`.

## Export Results

### `ExportResult`

```python
ExportResult(
    root: pathlib.Path,
    manifest: pathlib.Path,
    parts: dict[str, pathlib.Path],
)
```

- `root`: output directory.
- `manifest`: path to `model.json`.
- `parts`: map from part name to exported part file.

## Errors

The SDK raises `ValidationError` for authoring mistakes such as missing parts,
duplicate names, bad vectors, invalid limits, and disconnected joint graphs.

```python
from mini_articraft.sdk import ValidationError

try:
    model.validate()
except ValidationError as exc:
    print(exc)
```

## See Also

- `30_articulated_object.md` for model construction and validation.
- `35_joints.md` for joint authoring patterns.
- `40_export.md` for export layout and manifest details.
