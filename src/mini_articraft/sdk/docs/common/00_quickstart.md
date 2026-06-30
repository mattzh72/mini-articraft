---
name: sdk-quickstart
description: Start here for every mini-articraft SDK script. Covers the script contract, imports, default workflow, and the generated reference inventory.
---

# SDK Quickstart

## Purpose

Use this page to start a new mini-articraft SDK script. It defines the script
contract, the import pattern, and one minimal example.

The agent is responsible for authoring the object model. The compile worker is
responsible for validation, part export, and the output manifest.

## Script Contract

Every generated script should define:

- `object_model` as a `mini_articraft.sdk.ArticulatedObject`

For normal authoring, use a small builder function and assign its result:

```python
def build_object_model() -> ArticulatedObject:
    ...


object_model = build_object_model()
```

The local compile worker loads `workspace/main.py`, checks that `object_model`
is an `ArticulatedObject`, validates it, and writes the result files.

## Import Contract

Authoring helpers are exposed as top-level public imports from
`mini_articraft.sdk`.

```python
# Correct
from mini_articraft.sdk import ArticulatedObject, Origin

# Wrong
from mini_articraft.sdk.object import ArticulatedObject
from sdk import ArticulatedObject
```

Use `cadquery` directly for geometry.

```python
import cadquery as cq
```

## Reference Inventory

The agent inserts the current reference inventory here at run time. It lists
every SDK doc path and its description from frontmatter.

Use `read(path="docs/sdk/...")` to open detailed docs only when they are needed.
Read a selected page fully before relying on it.

## Recommended Imports

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin
```

## Minimal Example

```python
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Origin


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("example_box_lid")

    base = model.part(
        "base",
        cq.Workplane("XY")
        .box(0.24, 0.18, 0.04)
        .edges("|Z")
        .fillet(0.008),
    )

    lid = model.part(
        "lid",
        cq.Workplane("XY")
        .box(0.22, 0.16, 0.018)
        .edges("|Z")
        .fillet(0.006),
    )

    model.revolute(
        "base_to_lid",
        base,
        lid,
        origin=Origin(xyz=(-0.11, 0.0, 0.04)),
        axis=(0.0, -1.0, 0.0),
        limits=(0.0, 1.2),
    )

    return model


object_model = build_object_model()
```

This example uses a hinge-line frame for the lid. The lid geometry is authored
as its own CadQuery shape, and the joint records how that part should move
relative to the base.

## Recommended Workflow

1. Choose the object identity, real-world scale, root part, moving parts, and
   visible geometry.
2. Build each part as a CadQuery `Workplane`, `Shape`, or `Assembly`.
3. Register each part with `model.part(...)`.
4. Add fixed joints for mounted static parts.
5. Add revolute, prismatic, or continuous joints for moving parts.
6. Call `model.validate()` while debugging, or let the compile worker validate
   the object.

## Authoring Notes

- Keep the part graph as one tree with exactly one root part.
- Give each separate part a clear support relationship through a joint.
- Use semantic names such as `base`, `lid`, `drawer`, `wheel_0`, and
  `base_to_lid`.
- Use CadQuery operations for visible shape detail. Do not add extra SDK
  layers for geometry that CadQuery can express directly.
- Use meters for distances when possible, and keep prismatic limits in the same
  unit as the CadQuery geometry.
- Use `(lower, upper)` tuples for revolute and prismatic limits.
- Use `model.continuous(...)` without limits for unbounded rotation.
- Read `docs/sdk/common/35_joints.md` before adding non-fixed joints.
- Read the relevant `docs/sdk/cadquery/...` page before using detailed CadQuery
  patterns.
