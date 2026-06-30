# ArticulatedObject

## Scope

`ArticulatedObject` is the object model that `main.py` must export as
`object_model`.

Use it to register CadQuery parts and connect those parts with joints.

## Constructor

```python
model = ArticulatedObject(name: str)
```

`name` must be a non-empty string.

Create one `ArticulatedObject` per generated script.

## `model.part(...)`

```python
part = model.part(
    name: str,
    shape: cq.Workplane | cq.Shape | cq.Assembly,
)
```

Creates a named part and returns a part handle.

Rules:

- `name` must be a non-empty string.
- `name` must be unique within the model.
- `shape` must be a CadQuery `Workplane`, `Shape`, or `Assembly`.
- A part is the unit used by joints, export, and collision tests.

Example:

```python
base = model.part("base", cq.Workplane("XY").box(0.3, 0.2, 0.04))
lid = model.part("lid", cq.Workplane("XY").box(0.28, 0.18, 0.018))
```

## Part references

Methods that accept a part reference accept either:

- The part name as `str`.
- The part handle returned by `model.part(...)`.

Both forms are valid:

```python
model.fixed("base_to_foot", "base", "foot")
model.fixed("base_to_lid_stop", base, lid_stop)
```

## Fixed joints

```python
joint = model.fixed(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    origin: Origin | None = None,
)
```

Use `fixed` when the child part does not move relative to the parent part.

Fixed joints still connect the part graph.

## Revolute joints

```python
joint = model.revolute(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    limits: tuple[float, float],
    origin: Origin | None = None,
)
```

Use `revolute` for bounded rotation.

`limits` is required and is `(lower, upper)` in radians.

## Continuous joints

```python
joint = model.continuous(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    origin: Origin | None = None,
)
```

Use `continuous` for unbounded rotation.

Continuous joints do not take position limits.

## Prismatic joints

```python
joint = model.prismatic(
    name: str,
    parent: str | part_handle,
    child: str | part_handle,
    *,
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0),
    limits: tuple[float, float],
    origin: Origin | None = None,
)
```

Use `prismatic` for bounded translation.

`limits` is required and is `(lower, upper)` in the same unit as the geometry.

## `model.get_part(...)`

```python
part = model.get_part(part: str | part_handle)
```

Returns the matching part handle.

Raises `ValidationError` when the part does not exist.

## `model.validate()`

```python
model.validate()
```

Validates the part and joint graph.

Validation requires:

- At least one part.
- Unique part names.
- Unique joint names.
- Every joint parent and child must exist.
- A joint cannot connect a part to itself.
- A child part cannot have more than one parent joint.
- A model with more than one part must have exactly one root part.
- Every part must be reachable from the root.
- Revolute, continuous, and prismatic axes must be non-zero.
- Revolute and prismatic joints must have valid lower and upper limits.

Compile runs validation through the baseline tests.

Generated scripts may call `model.validate()` in helper code when early failure
is useful.

## Graph rules

The part graph is a tree rooted at one part.

Every non-root part should be the child of exactly one joint.

Use fixed joints for parts that are permanently attached but should remain
separate for export or testing.

Do not leave decorative or support parts unconnected unless `run_tests()` calls
`ctx.allow_isolated_part(...)` with a reason.
