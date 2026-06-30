---
name: sdk-articulated-object
description: Read this when you need to create an ArticulatedObject, add CadQuery parts, connect them with joints, look up parts, or understand validation.
metadata:
  short-description: Object, part, joint helpers, and validation.
---

# ArticulatedObject

## Purpose

`ArticulatedObject` is the root authored assembly. Use it to create CadQuery
parts, connect them with joints, validate the part graph, and export the model.

## Import

```python
from mini_articraft.sdk import ArticulatedObject
```

## Recommended Surface

- `ArticulatedObject(...)`
- `model.part(...)`
- `model.joint(...)`
- `model.fixed(...)`
- `model.revolute(...)`
- `model.continuous(...)`
- `model.prismatic(...)`
- `model.get_part(...)`
- `model.validate()`
- `model.to_dict()`

## Construction

```python
ArticulatedObject(
    name: str,
    parts: list[Part] = [],
    joints: list[Joint] = [],
)
```

Important fields:

- `name`: model name.
- `parts`: authored CadQuery parts.
- `joints`: fixed or movable connections between parts.

For normal code, start with an empty model and add parts through helper calls.

```python
model = ArticulatedObject("drawer_box")
```

## Authoring Helpers

### `model.part(...)`

```python
model.part(
    name: str,
    shape: cadquery.Workplane | cadquery.Shape | cadquery.Assembly,
) -> Part
```

- Creates a `Part`, appends it to `model.parts`, and returns it.
- `shape` must be a CadQuery `Workplane`, `Shape`, or `Assembly`.
- Part names must be unique and non-empty.

```python
case = model.part("case", cq.Workplane("XY").box(0.4, 0.3, 0.12))
drawer = model.part("drawer", cq.Workplane("XY").box(0.34, 0.26, 0.08))
```

### `model.joint(...)`

```python
model.joint(
    name: str,
    joint_type: JointType | str,
    parent: str | Part,
    child: str | Part,
    *,
    origin: Origin | None = None,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: JointLimits | ContinuousLimits | tuple[float, float] | None = None,
) -> Joint
```

- `parent`, `child`: either part objects or part names.
- `origin`: transform from the parent part frame into the joint frame.
- `axis`: motion axis expressed in the joint frame.
- `limits`: joint limits where required.

Use this helper when the joint type is dynamic. Prefer the named helpers when
the type is known.

## Named Joint Helpers

### `model.fixed(...)`

```python
model.fixed(
    name: str,
    parent: str | Part,
    child: str | Part,
    *,
    origin: Origin | None = None,
) -> Joint
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
    parent: str | Part,
    child: str | Part,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: JointLimits | tuple[float, float],
    origin: Origin | None = None,
) -> Joint
```

Use a revolute joint for a bounded hinge or pivot.

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
    parent: str | Part,
    child: str | Part,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: ContinuousLimits,
    origin: Origin | None = None,
) -> Joint
```

Use a continuous joint for a free-spinning wheel, fan, knob, pulley, or shaft.

```python
model.continuous(
    "fork_to_wheel",
    fork,
    wheel,
    axis=(0.0, 1.0, 0.0),
    limits=ContinuousLimits(effort=2.0, velocity=20.0),
)
```

### `model.prismatic(...)`

```python
model.prismatic(
    name: str,
    parent: str | Part,
    child: str | Part,
    *,
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0),
    limits: JointLimits | tuple[float, float],
    origin: Origin | None = None,
) -> Joint
```

Use a prismatic joint for a drawer, slide, telescoping stage, plunger, or any
part that moves in a straight line.

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
4. Positive `REVOLUTE` and `CONTINUOUS` motion follows the right-hand rule
   around `axis`.
5. Positive `PRISMATIC` motion translates the child along `+axis`.

In practice, the usual mistake is choosing the correct hinge line but the wrong
axis sign. If increasing the joint value makes the child close into the parent,
negate `axis` instead of swapping `lower` and `upper`.

## Lookup Helpers

### `model.get_part(...)`

```python
model.get_part(part: str | Part) -> Part
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
- each moving joint uses the right limit type
- fixed joints do not use limits
- a model with more than one part has exactly one root part
- every part is reachable from the root part

This means the object graph is a tree. Use fixed joints for separate static
pieces that should remain part of the same assembly.

## Dictionary Form

### `model.to_dict()`

```python
model.to_dict() -> dict[str, object]
```

Returns a small JSON-ready description of the model:

- model name
- part names and CadQuery shape type names
- joint names, types, parent and child names, origins, axes, and limits

The export helper adds file paths to this payload when it writes `model.json`.

## See Also

- `20_core_types.md` for `Origin`, `JointLimits`, and `ContinuousLimits`.
- `35_joints.md` for joint examples and limit rules.
- `40_export.md` for the output manifest.
