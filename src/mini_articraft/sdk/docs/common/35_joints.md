---
name: sdk-joints
description: Read this before authoring fixed, revolute, continuous, or prismatic joints, especially when choosing origins, axes, limits, and positive motion.
metadata:
  short-description: Joint frames, axes, limits, and examples.
---

# Joints

## Purpose

Use joints to describe how parts are connected. A joint records the parent part,
the child part, the joint frame, the motion axis, and any required motion
limits.

## Import

```python
from mini_articraft.sdk import ContinuousLimits, JointLimits, JointType, Origin
```

## Recommended Surface

- `model.fixed(...)`
- `model.revolute(...)`
- `model.continuous(...)`
- `model.prismatic(...)`
- `JointLimits(...)`
- `ContinuousLimits(...)`
- `Origin(...)`

## Joint Frame

Each joint has an `origin` and an `axis`.

- `origin` places the joint frame in the parent part frame.
- `axis` is expressed in the joint frame.
- The default axis is `(0.0, 0.0, 1.0)` for revolute and continuous joints.
- The default axis is `(1.0, 0.0, 0.0)` for prismatic joints.

Author the child geometry so its local frame makes sense at `q=0`. For a hinge,
this usually means the child part frame sits on the hinge line. For a slide,
this usually means the child part frame sits at the seated position.

## Fixed Joints

Use a fixed joint when two parts do not move relative to each other but should
remain separate parts.

```python
model.fixed(
    "base_to_cover",
    base,
    cover,
    origin=Origin(xyz=(0.0, 0.0, 0.08)),
)
```

Rules:

- fixed joints do not use `axis`
- fixed joints must not use `limits`
- fixed joints still count as graph edges during validation

## Revolute Joints

Use a revolute joint for bounded rotation.

```python
model.revolute(
    "body_to_lid",
    body,
    lid,
    origin=Origin(xyz=(-0.11, 0.0, 0.05)),
    axis=(0.0, -1.0, 0.0),
    limits=JointLimits(lower=0.0, upper=1.2, effort=5.0, velocity=3.0),
)
```

Rules:

- revolute joints require `JointLimits`
- a `(lower, upper)` pair is accepted and converted to `JointLimits`
- the axis must be a non-zero 3-vector
- lower and upper are radians
- positive motion follows the right-hand rule around `axis`

### Example: Lid That Opens Upward

```python
# Closed lid geometry extends along local +X from the hinge line.
# Using -Y makes positive q lift the free edge toward +Z.
model.revolute(
    "body_to_lid",
    body,
    lid,
    origin=Origin(xyz=(-0.09, 0.0, 0.05)),
    axis=(0.0, -1.0, 0.0),
    limits=(0.0, 1.2),
)
```

### Example: Mirrored Lid With The Same Positive Direction

```python
# If the closed panel extends along local -X from the hinge line instead,
# flip the axis sign so positive q still opens upward.
model.revolute(
    "body_to_mirrored_lid",
    body,
    mirrored_lid,
    origin=Origin(xyz=(0.09, 0.0, 0.05)),
    axis=(0.0, 1.0, 0.0),
    limits=(0.0, 1.2),
)
```

## Continuous Joints

Use a continuous joint for unbounded rotation.

```python
model.continuous(
    "frame_to_rotor",
    frame,
    rotor,
    origin=Origin(xyz=(0.0, 0.0, 0.04)),
    axis=(0.0, 0.0, 1.0),
    limits=ContinuousLimits(effort=2.0, velocity=30.0),
)
```

Rules:

- continuous joints require `ContinuousLimits`
- continuous joints must not use lower or upper bounds
- the axis must be a non-zero 3-vector
- positive motion follows the right-hand rule around `axis`

Use this for wheels, fan rotors, free-spinning knobs, pulleys, and shafts.

## Prismatic Joints

Use a prismatic joint for bounded translation.

```python
model.prismatic(
    "cabinet_to_drawer",
    cabinet,
    drawer,
    origin=Origin(xyz=(0.0, 0.0, 0.10)),
    axis=(1.0, 0.0, 0.0),
    limits=JointLimits(lower=0.0, upper=0.28, effort=40.0, velocity=0.25),
)
```

Rules:

- prismatic joints require `JointLimits`
- a `(lower, upper)` pair is accepted and converted to `JointLimits`
- the axis must be a non-zero 3-vector
- lower and upper are distances in the same unit as the CadQuery geometry
- positive motion translates the child along `+axis`

### Example: Drawer That Extends Outward

```python
model.prismatic(
    "cabinet_to_drawer",
    cabinet,
    drawer,
    origin=Origin(xyz=(0.0, 0.0, 0.12)),
    axis=(1.0, 0.0, 0.0),
    limits=(0.0, 0.28),
)
```

### Retained Insertion For Slides

For sleeves, telescoping poles, nested rails, and similar slide assemblies,
size the moving member for the fully extended pose. If one part slides out of
another, model the sliding member with enough hidden length that it still
remains engaged at the upper limit.

Use this rule:

```text
sliding member length >= visible exposed length at max extension + minimum retained insertion
```

In practice:

- put the prismatic `origin` at the sleeve entry, socket lip, or seating plane
- choose `limits.upper` as the usable travel after preserving retained insertion
- let the child geometry extend past the joint frame in the hidden direction if
  that is what the real mechanism needs

```python
outer_sleeve = model.part("outer_sleeve", cq.Workplane("XY").box(0.06, 0.06, 0.24))
inner_mast = model.part("inner_mast", cq.Workplane("XY").box(0.04, 0.04, 0.62))

model.prismatic(
    "sleeve_to_mast",
    outer_sleeve,
    inner_mast,
    origin=Origin(xyz=(0.0, 0.0, 0.24)),
    axis=(0.0, 0.0, 1.0),
    limits=JointLimits(lower=0.0, upper=0.26, effort=80.0, velocity=0.20),
)
```

## Validation Rules

Use these rules when calling a joint helper:

- `REVOLUTE` and `PRISMATIC` require `JointLimits`.
- `CONTINUOUS` requires `ContinuousLimits`.
- `FIXED` must not use limits.
- `parent` and `child` must name different parts.
- each child part can have only one parent joint.
- joint names must be unique.
- moving joint axes must be non-zero.

If a joint moves in the wrong direction, negate the axis. Keep the lower and
upper bounds as the semantic range of the motion.

## See Also

- `30_articulated_object.md` for the object graph rules.
- `20_core_types.md` for the exact constructor signatures.
