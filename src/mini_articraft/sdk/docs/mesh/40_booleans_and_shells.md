# Booleans, openings, and shell partitions

Use this page for Manifold mesh booleans, hollow mesh shells, face opening
throats, and axis aligned shell partitions.

All coordinates, dimensions, gaps, and depths use meters.

This page documents `boolean_union`, `boolean_difference`,
`boolean_intersection`, `cut_opening_on_face`, `ShellPartitionRegion`,
`ShellPartitionSpec`, and `partition_shell`.

```python
from mini_articraft.sdk import (
    BoxGeometry,
    ShellPartitionRegion,
    ShellPartitionSpec,
    boolean_difference,
    boolean_intersection,
    boolean_union,
    cut_opening_on_face,
    partition_shell,
    rounded_rect_profile,
)
```

## Mesh boolean rules

The boolean helpers use Manifold. Each input must be a nonempty valid closed
`MeshGeometry` solid. A mesh that only contains a surface, an uncapped pipe, or
separate open triangles is not a valid boolean input.

The helpers validate both inputs and return a new `MeshGeometry`. They do not
mutate either input.

A valid boolean can return an empty mesh. For example, the intersection of two
separated boxes is empty.

The output can contain more than one closed body. A union of separated solids
does not invent a bridge between them.

## boolean_union

```python
boolean_union(
    a: MeshGeometry,
    b: MeshGeometry,
) -> MeshGeometry
```

The result contains the volume occupied by either input.

```python
left = BoxGeometry((0.10, 0.08, 0.06)).translate(-0.03, 0.0, 0.0)
right = BoxGeometry((0.10, 0.08, 0.06)).translate(0.03, 0.0, 0.0)
joined = boolean_union(left, right)
```

Use `merge(...)` instead when you only need to combine triangle lists and do
not need one solved solid boundary.

## boolean_difference

```python
boolean_difference(
    a: MeshGeometry,
    b: MeshGeometry,
) -> MeshGeometry
```

The result contains the volume of `a` after removing the volume of `b`.

### Hollow shell example

```python
outer = BoxGeometry((0.30, 0.24, 0.20))

# The inner box extends through the top of the outer box. The remaining mesh
# has side walls and a floor, with a visible opening at the top.
inner = BoxGeometry((0.26, 0.20, 0.19)).translate(0.0, 0.0, 0.025)

shell = boolean_difference(outer, inner)
```

The example leaves a side wall thickness of `0.02` and a floor thickness of
`0.03`. The inner cutter extends above the outer top, so Manifold creates a real
opening instead of a sealed internal void.

Keep a positive wall thickness. A cutter that is exactly tangent to the outer
surface can create a fragile result. Extend a through cutter slightly beyond
the surface that it must open.

## boolean_intersection

```python
boolean_intersection(
    a: MeshGeometry,
    b: MeshGeometry,
) -> MeshGeometry
```

The result contains only the volume shared by both inputs. Shell partitioning
uses this operation to capture the part of a shell inside an axis aligned
region box.

## Boolean errors

The helpers raise `TypeError` when an input is not `MeshGeometry`.
`MeshGeometry.validate()` can raise `ValidationError` for invalid vertices or
faces. The helpers raise `ValueError` when an input is empty, open, nonmanifold,
or rejected by Manifold. The error names input `a` or `b` so you
can inspect the failing mesh.

Check these properties before retrying a failed boolean.

```python
geometry.validate()
print(geometry.is_watertight)
print(geometry.bounds)
```

Do not retry the same operation with arbitrary offsets until it happens to
pass. Find the open edge, zero thickness wall, duplicate face, or invalid input
builder first.

## Add a throat to an existing face opening

```python
cut_opening_on_face(
    shell_geometry: MeshGeometry,
    *,
    face: str,
    opening_profile: Iterable[tuple[float, float]],
    depth: float,
    offset: tuple[float, float] = (0.0, 0.0),
    taper: float = 0.0,
) -> MeshGeometry
```

This helper adds the interior side walls of an opening throat. It mutates
`shell_geometry`, returns that same mesh, and does not subtract a closed face.
The opening boundary must already exist in the shell surface.

Supported face values are `"+x"`, `"-x"`, `"+y"`, `"-y"`, `"+z"`, and
`"-z"`. The helper places the outer profile on the selected extreme plane of
the mesh bounds and moves the inner profile inward by `depth`.

The two profile coordinates map to the face like this.

- On an X face, the profile coordinates map to Y and Z.
- On a Y face, the profile coordinates map to X and Z.
- On a Z face, the profile coordinates map to X and Y.

`offset` moves the profile in those two face coordinates. Depth must be
positive. The opening profile must contain at least three distinct points and
have nonzero area.

The inner profile scale is `1 - taper`, measured around the profile center. A
positive taper narrows the throat inward. A negative taper widens it. The
absolute taper value must be less than 0.95.

```python
opening = rounded_rect_profile(0.08, 0.04, 0.006)
cut_opening_on_face(
    shell_with_existing_top_hole,
    face="+z",
    opening_profile=opening,
    depth=0.015,
    offset=(0.0, 0.01),
    taper=0.10,
)
```

If the face is still closed, use `boolean_difference(...)` with a closed cutter
to make the opening. Do not use `cut_opening_on_face(...)` as a substitute for
that subtraction.

## ShellPartitionRegion

```python
ShellPartitionRegion(
    name: str,
    side: Literal["full", "left", "right", "center"] = "full",
    x_min: float | None = None,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    z_min: float | None = None,
    z_max: float | None = None,
)
```

A region defines an axis aligned cutter in the shell coordinate frame. Its name
must be nonempty. Every supplied bound must be finite. A minimum must be less
than its matching maximum.

Omitted bounds extend past the shell bounds by the spec `padding` value.

The `side` field adds an X constraint around the model origin.

- `"full"` adds no side constraint.
- `"left"` limits the high X value to `-center_gap / 2`.
- `"right"` limits the low X value to `center_gap / 2`.
- `"center"` limits X to the center gap and requires a positive center gap.

Explicit X bounds still apply. The side constraint can make a region empty,
which raises `ValidationError` during partitioning.

## ShellPartitionSpec

```python
ShellPartitionSpec(
    shell: MeshGeometry,
    regions: tuple[ShellPartitionRegion, ...],
    splitters: tuple[MeshGeometry, ...] = (),
    remainder_name: str | None = None,
    center_gap: float = 0.0,
    padding: float = 0.01,
)
```

`shell` must be a nonempty closed `MeshGeometry` solid because partitioning
uses Manifold.

At least one region is required. Region names must be unique. Every splitter
must also be a nonempty closed `MeshGeometry` solid.

`remainder_name` optionally stores all geometry left after the named regions.
It must be nonempty and different from every region name.

`center_gap` must be finite and nonnegative. `padding` must be finite and
positive.

## partition_shell

```python
partition_shell(
    spec: ShellPartitionSpec | MeshGeometry,
    /,
    **overrides,
) -> dict[str, MeshGeometry]
```

You may pass a complete spec, or pass a shell and provide `regions=...` plus
other spec fields as keyword arguments. Keyword overrides replace fields on an
existing spec for this call.

The operation follows this order.

1. It copies the shell.
2. It subtracts every splitter from the working shell in authored order.
3. It processes regions in authored order.
4. For each region, it intersects the remaining shell with the region box.
5. It stores that piece under the region name and subtracts it from the
   remaining shell.
6. If `remainder_name` is set, it stores the final remainder under that name.

Region order matters because each region can only capture geometry that remains
after earlier regions. A broad `"full"` region with no explicit bounds can
capture the whole shell and leave later regions empty.

The helper raises `ValidationError` when a region captures no geometry. It can
also raise a boolean `ValueError` for an open or invalid solid.

```python
spec = ShellPartitionSpec(
    shell=BoxGeometry((0.20, 0.30, 0.10)),
    regions=(
        ShellPartitionRegion("left_front", side="left", y_max=0.0),
        ShellPartitionRegion("right_front", side="right", y_max=0.0),
    ),
    remainder_name="body",
    center_gap=0.01,
)

pieces = partition_shell(spec)
left_front = pieces["left_front"]
right_front = pieces["right_front"]
body = pieces["body"]
```

The result meshes are independent. Add them as named shapes when they belong to
one rigid part, or add them to separate parts when the prompt requires separate
motion.

## weld: attach a protrusion with a smooth blend

Use `weld(*geometries, radius=0.006)` to merge overlapping or nearly-touching
solids into ONE blended solid. Where the pieces meet it grows a rounded fillet of
size `radius` -- like smoothing clay over the joint -- instead of leaving a sharp
seam or a stuck-on block.

This is the correct way to ATTACH a protrusion to a form: a handle to a body, a
spout to a shell, a boss to a panel. Do not author a thin strap and then bridge the
gap to the body with an oversized mounting block. Instead, build the protrusion so
it (and any small mount blobs) OVERLAP the target a few millimeters -- overlap
within a rigid part is free -- then weld them into one molded shape:

```python
from mini_articraft.sdk import weld, rounded_rect_profile, sweep_profile_along_spline, BoxGeometry

strap = sweep_profile_along_spline(handle_path, profile=rounded_rect_profile(0.024, 0.017, 0.005))
top_mount = BoxGeometry((0.03, 0.03, 0.03)).translate(*top_anchor)     # overlaps the body
bottom_mount = BoxGeometry((0.03, 0.03, 0.03)).translate(*bottom_anchor)
handle = weld(strap, top_mount, bottom_mount, radius=0.007)            # one smooth molded handle
part.add(handle, name="handle", color=DARK_PLASTIC)
```

Weld pieces that share a color, since the result is a single shape (add it with one
color). The blend only bridges gaps up to about `radius`, so overlap the pieces
first. Inputs must be closed manifold solids.

## Decision guide

- Use `weld(...)` to attach a handle/spout/boss to a form as one molded piece,
  instead of a strap plus a bridging block.
- Use `boolean_difference(...)` to create a cavity or a real hole in a closed
  solid.
- To trim a protrusion so it conforms to a HOLLOW body, subtract a SOLID form of
  the body's outer surface, not the thin shell. Subtracting a thin wall removes
  only a wall-thick slice and leaves sliver fragments at the junction; a solid
  cutting tool trims the protrusion's end cleanly to one piece. (Build the solid
  from the same outer profile, e.g. a solid `LatheGeometry` of the outer contour.)
- Use `cut_opening_on_face(...)` only when the outer opening boundary already
  exists and you need its throat walls.
- Use `partition_shell(...)` to divide one closed solid into named axis aligned
  pieces.
- Use direct `MeshGeometry.merge(...)` when separate triangle components are
  acceptable and you do not need one solved solid boundary.

## Related references

- Read [mesh geometry and solid builders](00_mesh_geometry.md) for closed
  primitive inputs and build123d mesh conversion.
- Read [wires and sweeps](20_wires_and_sweeps.md) for closed tube networks that
  use Manifold union.
- See `docs/sdk/examples/hollow_shell.py` for an executable hollow shell built
  with `BoxGeometry` and `boolean_difference(...)`.
