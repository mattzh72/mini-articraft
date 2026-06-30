---
name: sdk-core-types
description: Read this when you need the strict mini-articraft authoring imports, units, Origin constructor, part handles, joint handles, and limit tuple rules.
---

# Core Types

## Purpose

This page documents the public authoring surface for mini-articraft scripts.
The public SDK is intentionally small.

## Import

```python
from mini_articraft.sdk import ArticulatedObject, Origin, ValidationError
```

Use CadQuery directly for geometry.

```python
import cadquery as cq
```

## Public Surface

- `ArticulatedObject(...)`
- `Origin(...)`
- `model.part(...)`
- `model.fixed(...)`
- `model.revolute(...)`
- `model.prismatic(...)`
- `model.continuous(...)`
- `model.get_part(...)`
- `model.validate()`
- `ValidationError`

Do not import export helpers, low-level joint classes, or low-level part
classes from the SDK. The compile worker handles export after `object_model` is
defined.

## Units

CadQuery is unitless. In mini-articraft, use meters when possible.

- `Origin.xyz` uses the same distance unit as the CadQuery geometry.
- `Origin.rpy` is `(roll, pitch, yaw)` in radians.
- Revolute joint limits are radians.
- Prismatic joint limits use the same distance unit as the CadQuery geometry.
- Continuous joints have no lower or upper position bounds.

## Model

### `ArticulatedObject`

```python
ArticulatedObject(name: str)
```

Create one object model per script.

```python
model = ArticulatedObject("drawer_box")
```

The model owns parts and joints. Register geometry with `model.part(...)`, then
connect parts with named joint helpers.

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

## Part Handles

### `model.part(...)`

```python
model.part(
    name: str,
    shape: cadquery.Workplane | cadquery.Shape | cadquery.Assembly,
)
```

This registers a CadQuery shape as a named part and returns a part handle. Use
that handle when adding joints.

```python
base = model.part("base", cq.Workplane("XY").box(0.3, 0.2, 0.05))
lid = model.part("lid", cq.Workplane("XY").box(0.28, 0.18, 0.02))
```

Part names must be unique and non-empty.

## Joint Handles

Joint helpers return joint handles. Most scripts do not need to inspect them.

```python
hinge = model.revolute(
    "base_to_lid",
    base,
    lid,
    origin=Origin(xyz=(-0.14, 0.0, 0.04)),
    axis=(0.0, -1.0, 0.0),
    limits=(0.0, 1.2),
)
```

Use the named helpers for all joints.

## Limit Tuples

Use a `(lower, upper)` tuple for bounded motion.

```python
model.revolute("base_to_lid", base, lid, limits=(0.0, 1.2))
model.prismatic("case_to_drawer", case, drawer, limits=(0.0, 0.28))
```

The SDK records default effort and velocity values internally. The agent should
choose the motion range, not effort or velocity.

Continuous joints are unbounded, so they do not take limits.

```python
model.continuous("fork_to_wheel", fork, wheel, axis=(0.0, 1.0, 0.0))
```

## Errors

The SDK raises `ValidationError` for authoring mistakes such as missing parts,
duplicate names, bad vectors, invalid limits, and disconnected joint graphs.

```python
try:
    model.validate()
except ValidationError as exc:
    print(exc)
```

## See Also

- `30_articulated_object.md` for model construction and validation.
- `35_joints.md` for joint authoring patterns.
