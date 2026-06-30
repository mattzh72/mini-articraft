# CadQuery in mini-articraft

## Purpose

mini-articraft uses CadQuery to author visible geometry. Each SDK `Part` owns a
CadQuery `Workplane`, `Shape`, or `Assembly` directly.

Use this page when:

- you need to create part geometry with CadQuery
- you need to decide whether to use a `Workplane`, `Shape`, or `Assembly`
- you are porting an idea from the larger Articraft SDK

## Import

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin
```

## Recommended Surface

- `cq.Workplane(...)`
- `cq.Shape`
- `cq.Assembly`
- `model.part(name, shape)`
- `model.fixed(...)`
- `model.revolute(...)`
- `model.continuous(...)`
- `model.prismatic(...)`

mini-articraft does not use `mesh_from_cadquery(...)`, `Visual`, `Mesh`,
`ArticulationType`, or `MotionLimits`. Those names belong to the larger
Articraft SDK.

## Units

CadQuery is unitless. In mini-articraft, use meters when possible.

- Revolute joint limits are radians.
- Prismatic joint limits use the same unit as the CadQuery geometry.
- `Origin.xyz` uses the same unit as the CadQuery geometry.
- `Origin.rpy` uses radians.

## Recommended Pattern

Create the CadQuery shape first, then register it as a part.

```python
door_shape = (
    cq.Workplane("XY")
    .box(0.58, 0.02, 0.78)
    .edges("|Z")
    .fillet(0.01)
)

door = model.part("door", door_shape)
```

Keep motion in the SDK joint graph, not in CadQuery assemblies. Use CadQuery for
shape and the mini-articraft SDK for the part tree.

## Workplane, Shape, and Assembly

### `cq.Workplane`

Use a `Workplane` for normal solid modeling.

```python
base = model.part(
    "base",
    cq.Workplane("XY")
    .box(0.30, 0.20, 0.05)
    .edges("|Z")
    .fillet(0.006),
)
```

### `cq.Shape`

Use a `Shape` when you call lower-level CadQuery APIs or when you finish a
workplane with `.val()`.

```python
plate_shape = cq.Workplane("XY").box(0.20, 0.12, 0.01).val()
plate = model.part("plate", plate_shape)
```

### `cq.Assembly`

Use a `cq.Assembly` when a single SDK part is easiest to author as several
fixed CadQuery components. Do not use a CadQuery assembly to describe an SDK
joint.

```python
knob = cq.Workplane("XY").circle(0.03).extrude(0.02)
pointer = cq.Workplane("XY").box(0.055, 0.006, 0.004).translate((0.02, 0.0, 0.012))

assembly = cq.Assembly()
assembly.add(knob, name="cap")
assembly.add(pointer, name="pointer")

dial = model.part("dial", assembly)
```

## Example

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("cabinet_door")

    body = model.part(
        "body",
        cq.Workplane("XY")
        .box(0.60, 0.30, 0.80)
        .faces(">Y")
        .workplane()
        .rect(0.50, 0.66)
        .cutBlind(-0.04),
    )

    door = model.part(
        "door",
        cq.Workplane("XY")
        .box(0.58, 0.02, 0.78)
        .edges("|Z")
        .fillet(0.01),
    )

    model.revolute(
        "body_to_door",
        body,
        door,
        origin=Origin(xyz=(-0.29, 0.15, 0.0)),
        axis=(0.0, 0.0, 1.0),
        limits=(0.0, 1.7),
    )

    return model


object_model = build_object_model()
```

## Advice

- Model part frames deliberately. A hinge child often works best when its local
  frame sits on the hinge line.
- Keep separate moving pieces as separate SDK parts.
- Use fixed joints for static pieces that should remain separate parts.
- Use semantic names such as `base`, `lid`, `drawer`, `wheel_0`, and
  `base_to_lid`.
- If a model needs special CadQuery behavior, read the focused CadQuery docs in
  `docs/sdk/cadquery/...`.

## See Also

- `docs/sdk/common/00_quickstart.md` for the overall script contract.
- `docs/sdk/common/30_articulated_object.md` for part and joint helpers.
- `docs/sdk/common/35_joints.md` for joint frames, axes, and limits.
