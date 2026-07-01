# Testing

## Scope

Every generated `main.py` must define `run_tests() -> TestReport`.

Use `run_tests()` for prompt specific checks. Compile adds baseline checks after
the authored report is returned.

## Required pattern

```python
from mini_articraft.sdk import TestContext, TestReport


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    return ctx.report()
```

## `TestContext`

```python
ctx = TestContext(
    model: ArticulatedObject,
    seed: int = 0,
    mesh_tolerance: float = 0.001,
)
```

`model` must be an `ArticulatedObject`.

`mesh_tolerance` controls build123d tessellation for mesh tests. It must be a
positive finite number. Smaller values create denser meshes and slower checks.

The default `mesh_tolerance` is `0.001`.

## Report helpers

### `ctx.report()`

```python
report = ctx.report()
```

Returns a `TestReport`.

Call this once at the end of `run_tests()`.

### `ctx.check(...)`

```python
ctx.check(name: str, ok: bool, details: str = "") -> bool
```

Records a custom check. Returns `ok`.

### `ctx.fail(...)`

```python
ctx.fail(name: str, details: str) -> bool
```

Records a failed check. Returns `False`.

### `ctx.warn(...)`

```python
ctx.warn(text: str) -> None
```

Records a warning. Warnings do not fail compile.

## Allowances

### `ctx.allow_overlap(...)`

```python
ctx.allow_overlap(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    reason: str,
    elem_a: str | None = None,
    elem_b: str | None = None,
) -> None
```

Allows an intentional baseline collision between two parts.

Rules:

- `reason` is required and must not be empty.
- The part pair is stored in sorted order.
- The allowance suppresses only the baseline collision failure for that pair.
- The allowance does not make `ctx.expect_no_collision(...)` pass.
- `elem_a` and `elem_b` are stored in the report but are not enforced in the current mini SDK.

### `ctx.allow_isolated_part(...)`

```python
ctx.allow_isolated_part(
    part: str | part_handle,
    *,
    reason: str,
) -> None
```

Allows one intentionally isolated part in the baseline isolated part check.

`reason` is required and must not be empty.

## Pose helpers

### `ctx.pose(...)`

```python
with ctx.pose({"joint_name": value}):
    ...

with ctx.pose(joint_name=value):
    ...
```

Temporarily applies joint positions inside the context manager.

Keys may be joint name strings or joint handles.

Values are floats.

Unknown joint names raise `ValidationError`.

The previous pose is restored when the context exits.

### `ctx.part_world_position(...)`

```python
ctx.part_world_position(part: str | part_handle) -> tuple[float, float, float] | None
```

Returns the world position of the part frame in the current pose.

Returns `None` when the part cannot be resolved in the current world transform
map.

### `ctx.link_world_position(...)`

```python
ctx.link_world_position(link: str | part_handle) -> tuple[float, float, float] | None
```

Alias for `ctx.part_world_position(...)`.

## Mesh collision checks

Collision and distance checks use `python-fcl` on tessellated build123d meshes.

The SDK uses `trimesh` to prepare triangle meshes and builds FCL BVH models.

Bounding boxes are not the source of truth for these checks.

FCL may use its own internal acceleration structures.

### `ctx.expect_no_collision(...)`

```python
ctx.expect_no_collision(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    name: str | None = None,
) -> bool
```

Passes when FCL reports no mesh collision between the two parts.

Fails when FCL reports a collision.

### `ctx.expect_collision(...)`

```python
ctx.expect_collision(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    name: str | None = None,
) -> bool
```

Passes when FCL reports a mesh collision between the two parts.

### `ctx.expect_contact(...)`

```python
ctx.expect_contact(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    contact_tol: float = 1e-6,
    name: str | None = None,
) -> bool
```

Passes when the parts collide or when their FCL distance is less than or equal
to `contact_tol`.

`contact_tol` must be finite and non-negative.

### `ctx.expect_distance(...)`

```python
ctx.expect_distance(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    min_distance: float = 0.0,
    max_distance: float | None = None,
    name: str | None = None,
) -> bool
```

Checks the FCL mesh distance between two parts.

Passes when the distance is greater than or equal to `min_distance`.

Also requires distance to be less than or equal to `max_distance` when
`max_distance` is provided.

`min_distance` and `max_distance` must be finite and non-negative.

`max_distance` must be greater than or equal to `min_distance`.

## Projection checks

Projection checks use tessellated mesh vertices in the current pose.

They are not collision checks.

Use them for directional clearance and containment checks.

### `ctx.expect_gap(...)`

```python
ctx.expect_gap(
    positive_link: str | part_handle,
    negative_link: str | part_handle,
    *,
    axis: str,
    min_gap: float | None = None,
    max_gap: float | None = None,
    max_penetration: float | None = None,
    name: str | None = None,
) -> bool
```

Computes:

```text
min coordinate of positive_link on axis
minus max coordinate of negative_link on axis
```

`axis` must be `"x"`, `"y"`, or `"z"`.

If `min_gap` is omitted, the lower bound is `-max_penetration`.

If both `min_gap` and `max_gap` are provided, `max_gap` must be greater than or
equal to `min_gap`.

### `ctx.expect_within(...)`

```python
ctx.expect_within(
    inner_link: str | part_handle,
    outer_link: str | part_handle,
    *,
    axes: str | Sequence[str] = "xy",
    margin: float = 0.0,
    name: str | None = None,
) -> bool
```

Passes when the projected mesh interval of `inner_link` is within the projected
mesh interval of `outer_link` on every requested axis, with the given margin.

`axes` may be a string such as `"xy"` or a sequence such as `("x", "y")`.

`margin` must be finite and non-negative.

### `ctx.expect_overlap(...)`

```python
ctx.expect_overlap(
    link_a: str | part_handle,
    link_b: str | part_handle,
    *,
    axes: str | Sequence[str] = "xy",
    min_overlap: float = 0.0,
    name: str | None = None,
) -> bool
```

Passes when the projected mesh intervals overlap by at least `min_overlap` on
every requested axis.

`min_overlap` must be finite and non-negative.

## Baseline checks

Compile runs these checks after authored tests:

```python
ctx.check_model_valid()
ctx.check_single_root_part()
ctx.fail_if_isolated_parts()
ctx.fail_if_parts_collide_in_current_pose()
```

Authored code may call these methods too, but this is not required.

### `ctx.check_model_valid()`

Runs `model.validate()` and records the result.

### `ctx.check_single_root_part()`

Passes when exactly one part has no parent joint.

### `ctx.fail_if_isolated_parts(...)`

```python
ctx.fail_if_isolated_parts(
    *,
    contact_tol: float = 1e-6,
    name: str | None = None,
) -> bool
```

Builds contact groups using FCL collision and FCL distance.

Fails when a part or group has no contact path to the root part.

`allow_isolated_part(...)` suppresses matching isolated part failures.

### `ctx.fail_if_parts_collide_in_current_pose(...)`

```python
ctx.fail_if_parts_collide_in_current_pose(
    *,
    ignore_adjacent: bool = True,
    name: str | None = None,
) -> bool
```

Uses FCL broadphase collision management for candidate pairs and FCL mesh
collision for the result.

When `ignore_adjacent` is `True`, parent and child pairs connected by a joint
are ignored.

`allow_overlap(...)` suppresses matching baseline failures.

## Example

```python
def run_tests() -> TestReport:
    ctx = TestContext(object_model)

    ctx.expect_contact("base", "lid")

    with ctx.pose(base_to_lid=0.9):
        ctx.expect_no_collision("base", "lid")
        ctx.expect_gap("lid", "base", axis="z", min_gap=0.01)

    return ctx.report()
```
