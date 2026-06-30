# Joints

## Scope

Joints define the part graph and the relative motion between parent and child
parts.

Use the joint helper methods on `ArticulatedObject`. Do not create joint objects
directly.

## Joint frame

Every joint has:

- A parent part.
- A child part.
- A `Frame` that places the joint frame in the parent part frame.
- An `axis` expressed in the joint frame.
- A motion value read from `ctx.pose(...)` during tests.

The child part frame is placed by this transform order:

```text
parent world transform
then joint frame
then joint motion
```

At pose value `0.0`, the joint motion is the identity transform.

Author the child geometry so the child local frame is correct at pose value
`0.0`.

## `Frame`

```python
Frame(
    xyz=(0.0, 0.0, 0.0),
    rpy=(0.0, 0.0, 0.0),
)
```

`xyz` translates from the parent part frame to the joint frame.

`rpy` rotates from the parent part frame to the joint frame. The order is roll,
pitch, then yaw. Values are radians.

## Fixed joint

```python
model.fixed(
    "parent_to_child",
    parent,
    child,
    frame=Frame(xyz=(0.0, 0.0, 0.04)),
)
```

Rules:

- No `axis` argument is accepted.
- No `limits` argument is accepted.
- The child stays fixed at `frame` relative to the parent.

## Revolute joint

```python
model.revolute(
    "body_to_lid",
    body,
    lid,
    frame=Frame(xyz=(-0.11, 0.0, 0.05)),
    axis=(0.0, -1.0, 0.0),
    limits=(0.0, 1.2),
)
```

Rules:

- `limits` is required.
- `limits` is `(lower, upper)` in radians.
- `axis` must contain three numeric values.
- `axis` must not be `(0.0, 0.0, 0.0)`.
- Positive motion follows the right hand rule around `axis`.

Use `ctx.pose(body_to_lid=value)` to test a rotated pose.

## Continuous joint

```python
model.continuous(
    "knob_axis",
    body,
    knob,
    frame=Frame(xyz=(0.0, 0.0, 0.03)),
    axis=(0.0, 0.0, 1.0),
)
```

Rules:

- No `limits` argument is accepted.
- `axis` must contain three numeric values.
- `axis` must not be `(0.0, 0.0, 0.0)`.
- Positive motion follows the right hand rule around `axis`.

Use a continuous joint only when any rotation angle is valid.

## Prismatic joint

```python
model.prismatic(
    "case_to_drawer",
    case,
    drawer,
    frame=Frame(xyz=(0.0, 0.0, 0.0)),
    axis=(1.0, 0.0, 0.0),
    limits=(0.0, 0.18),
)
```

Rules:

- `limits` is required.
- `limits` is `(lower, upper)` in the same unit as the geometry.
- `axis` must contain three numeric values.
- `axis` must not be `(0.0, 0.0, 0.0)`.
- Positive motion translates the child in the `axis` direction.

Use `ctx.pose(case_to_drawer=value)` to test an extended pose.

## Limits

For revolute and prismatic joints, `lower` must be less than or equal to
`upper`.

Use `0.0` for the closed, seated, or rest pose when possible. This makes tests
and export easier to read.

## Naming

Use names that state the relationship.

Prefer this form:

```python
model.revolute("base_to_lid", base, lid, ...)
```

Avoid names that only state the motion type, such as `"hinge1"`, unless the part
names already make the relationship clear.
