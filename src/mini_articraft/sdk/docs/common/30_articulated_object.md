---
name: sdk-articulated-object
description: Read this when you need to create an ArticulatedObject, add CadQuery parts, connect them with named joints, look up parts, or understand validation.
---

# ArticulatedObject

## Purpose

`ArticulatedObject` is the authored assembly. Use it to register CadQuery parts,
connect them with named joints, and validate the part graph.

## Import

```python
from mini_articraft.sdk import ArticulatedObject, Origin
```

## Recommended Surface

- `ArticulatedObject(...)`
- `model.part(...)`
- `model.fixed(...)`
- `model.revolute(...)`
- `model.continuous(...)`
- `model.prismatic(...)`
- `model.get_part(...)`
- `model.validate()`

The compile worker handles export after the script defines `object_model`.

## Construction

```python
ArticulatedObject(name: str)
```

For normal code, start with an empty model and add parts through helper calls.

```python
model = ArticulatedObject("drawer_box")
```

## Parts

### `model.part(...)`

```python
model.part(
    name: str,
    shape: cadquery.Workplane | cadquery.Shape | cadquery.Assembly,
)
```

- Creates a named part and returns a part handle.
- `shape` must be a CadQuery `Workplane`, `Shape`, or `Assembly`.
- Part names must be unique and non-empty.

```python
case = model.part("case", cq.Workplane("XY").box(0.4, 0.3, 0.12))
drawer = model.part("drawer", cq.Workplane("XY").box(0.34, 0.26, 0.08))
```

## Named Joint Helpers

Use the named joint helpers. They keep the authoring surface small and avoid
manual joint type selection.

### `model.fixed(...)`

```python
model.fixed(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    origin: Origin | None = None,
)
```

Use a fixed joint for mounted parts that should stay separate in the object
graph.

```python
model.fixed("base_to_panel", base, front_panel)
```

### `model.revolute(...)`

```python
model.revolute(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: tuple[float, float],
    origin: Origin | None = None,
)
```

Use a revolute joint for a bounded hinge or pivot. `limits` is `(lower, upper)`
in radians.

```python
model.revolute(
    "body_to_lid",
    body,
    lid,
    origin=Origin(xyz=(-0.11, 0.0, 0.05)),
    axis=(0.0, -1.0, 0.0),
    limits=(0.0, 1.2),
)
```

### `model.continuous(...)`

```python
model.continuous(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    origin: Origin | None = None,
)
```

Use a continuous joint for unbounded rotation. Continuous joints do not take
limits.

```python
model.continuous(
    "fork_to_wheel",
    fork,
    wheel,
    axis=(0.0, 1.0, 0.0),
)
```

### `model.prismatic(...)`

```python
model.prismatic(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0),
    limits: tuple[float, float],
    origin: Origin | None = None,
)
```

Use a prismatic joint for a drawer, slide, telescoping stage, plunger, or any
part that moves in a straight line. `limits` is `(lower, upper)` in the same
unit as the CadQuery geometry.

```python
model.prismatic(
    "cabinet_to_drawer",
    cabinet,
    drawer,
    origin=Origin(xyz=(0.0, 0.0, 0.06)),
    axis=(1.0, 0.0, 0.0),
    limits=(0.0, 0.28),
)
```

## Frame And Direction Conventions

Joints use a URDF-style joint frame:

1. `origin` places the joint frame relative to the parent part frame.
2. `axis` is written in the joint frame.
3. At `q=0`, the child part frame is coincident with the joint frame.
4. Positive revolute and continuous motion follows the right-hand rule around
   `axis`.
5. Positive prismatic motion translates the child along `+axis`.

If increasing the joint value moves the child in the wrong direction, negate
`axis`. Keep `limits` as the semantic motion range.

## Lookup Helpers

### `model.get_part(...)`

```python
model.get_part(part: str | part_handle)
```

Returns the named part. Raises `ValidationError` if it does not exist.

```python
lid = model.get_part("lid")
```

## Validation

### `model.validate()`

```python
model.validate() -> None
```

Validation includes:

- at least one part exists
- part names are unique
- joint names are unique
- each joint references existing parent and child parts
- each child part has at most one parent joint
- each moving joint has a non-zero axis
- each bounded moving joint has a `(lower, upper)` tuple
- fixed joints do not use limits
- a model with more than one part has exactly one root part
- every part is reachable from the root part

This means the object graph is a tree. Use fixed joints for separate static
pieces that should remain part of the same assembly.

## See Also

- `20_core_types.md` for the public authoring surface.
- `35_joints.md` for joint frames, axes, and limits.
