# Section lofts and repair

Use `section_loft(...)` when a form is described by ordered three dimensional
cross sections. This helper can reconcile different point counts, align
section loops, add path offsets, mirror a half form, and clean the result.

All coordinates and path values use meters.

This page documents `LoftSection`, `SectionLoftSpec`, `section_loft`, and
`repair_loft`.

```python
from mini_articraft.sdk import (
    LoftSection,
    SectionLoftSpec,
    repair_loft,
    section_loft,
)
```

Use `LoftGeometry` instead when all profiles already have the same point count
and need only a direct connection. Read [mesh geometry and solid
builders](00_mesh_geometry.md) for that lower level builder.

## LoftSection

```python
LoftSection(
    points: tuple[tuple[float, float, float], ...],
)
```

`points` is one ordered section loop. Every point must contain three finite
values. At least three points must remain after consecutive duplicates and a
repeated final endpoint are removed.

The constructor removes consecutive duplicate points. It also removes a final
point that exactly repeats the first point. You may provide either an explicitly
closed loop or a loop whose final edge is implied.

Keep the point order consistent around the shape. The loft aligns winding and
cyclic starting offsets, but clear correspondence still produces the most
predictable surface.

## SectionLoftSpec

```python
SectionLoftSpec(
    sections: tuple[LoftSection, ...],
    path: tuple[tuple[float, float, float], ...] | None = None,
    cap: bool = True,
    symmetry: Literal["mirror_yz"] | None = None,
    repair: Literal["off", "mesh"] = "mesh",
)
```

At least two sections are required. The constructor also accepts section values
that can be converted to `LoftSection`.

The fields have these meanings.

- `sections` defines the ordered cross sections from the first end to the last
  end.
- `path` optionally offsets the intermediate sections along a polyline. It must
  contain at least two finite points.
- `cap` requests end caps.
- `symmetry="mirror_yz"` mirrors the result across the YZ plane by reversing
  X.
- `repair="mesh"` runs the mesh cleanup pass. `repair="off"` returns the raw
  loft mesh.

### Path behavior

The path changes section positions. It does not rotate section planes to follow
the path tangent.

For each section, the helper samples a point at the matching fraction along the
path. It compares that point with the same fraction along the straight line
from the path start to the path end. The difference becomes a translation for
that section.

Use a path when the section centers should bow or deviate from a straight loft.
Keep the authored section planes in their intended orientation.

### Section alignment

The helper resamples every section to the largest section point count. It
samples points by distance around each closed perimeter.

It then reverses a loop when its normal opposes the previous loop and chooses
the cyclic point offset that best matches the previous loop.

## section_loft

```python
section_loft(
    spec: SectionLoftSpec
    | Sequence[LoftSection | Sequence[Sequence[float]]],
    /,
    **overrides,
) -> MeshGeometry
```

The first argument can be a `SectionLoftSpec` or a raw sequence of section
loops. Raw sections use all default spec values.

Keyword overrides replace fields on the resolved spec for this call. Use only
the field names listed on `SectionLoftSpec`. An unknown field raises
`TypeError`.

The helper creates a closed side loop between every pair of sections. It caps
the result when `cap=True`.

For `symmetry="mirror_yz"`, the helper mirrors the mesh across X. If the first
half is watertight, Manifold unions the two halves. If it is open, the helper
merges the triangle lists without a boolean union. Author a half form that
meets the YZ plane when you want one connected symmetric result.

### Raw section example

```python
housing = section_loft(
    [
        [
            (-0.05, -0.03, 0.00),
            (0.05, -0.03, 0.00),
            (0.05, 0.03, 0.00),
            (-0.05, 0.03, 0.00),
        ],
        [
            (-0.035, -0.025, 0.10),
            (0.035, -0.025, 0.10),
            (0.035, 0.025, 0.10),
            (-0.035, 0.025, 0.10),
        ],
    ]
)
```

### Path and symmetry example

```python
lower = LoftSection(
    (
        (0.00, -0.04, 0.00),
        (0.05, -0.04, 0.00),
        (0.05, 0.04, 0.00),
        (0.00, 0.04, 0.00),
    )
)
middle = LoftSection(
    (
        (0.00, -0.03, 0.10),
        (0.04, -0.03, 0.10),
        (0.04, 0.03, 0.10),
        (0.00, 0.03, 0.10),
    )
)
upper = LoftSection(
    (
        (0.00, -0.02, 0.20),
        (0.025, -0.02, 0.20),
        (0.025, 0.02, 0.20),
        (0.00, 0.02, 0.20),
    )
)

spec = SectionLoftSpec(
    sections=(lower, middle, upper),
    path=((0.0, 0.0, 0.0), (0.02, 0.0, 0.10), (0.0, 0.0, 0.20)),
    symmetry="mirror_yz",
)
housing = section_loft(spec)
```

## repair_loft

```python
repair_loft(
    geometry_or_spec: MeshGeometry
    | SectionLoftSpec
    | Sequence[LoftSection | Sequence[Sequence[float]]],
    /,
    *,
    repair: Literal["off", "mesh"] = "mesh",
) -> MeshGeometry
```

For a `MeshGeometry` input, `repair="off"` returns a copy. `repair="mesh"` runs
mesh cleanup on a copy.

For a spec or raw section input, the helper calls `section_loft(...)` with the
requested repair mode.

Mesh cleanup removes duplicate faces, degenerate faces, and unused vertices.
If the mesh is not watertight, it also merges coincident vertices and repeats
the face cleanup. It then fixes face normals.

Repair does not guarantee a watertight result. It does not fill a large missing
surface or infer a better section order. Fix invalid section geometry first.

```python
clean = repair_loft(housing, repair="mesh")
```

## Validation and common failures

- A section with fewer than three points after consecutive duplicate and final
  endpoint cleanup raises `ValidationError`. Repeated nonconsecutive points can
  pass construction and then fail the loft area check.
- A section with zero planar area fails while the loft is built.
- A spec with fewer than two sections raises `ValidationError`.
- A path with fewer than two points raises `ValidationError`.
- A path or section with nonfinite coordinates raises `ValidationError`.
- The only symmetry mode is `"mirror_yz"`.
- Repair modes are `"off"` and `"mesh"`.
- The first and last loft section centers must differ after path adjustment.

When a loft twists, check section order and point correspondence before adding
more sections. When caps fail, make the end sections planar and give them a
clear nonzero area.

## Related references

- Read [mesh geometry and solid builders](00_mesh_geometry.md) for
  `LoftGeometry`, which requires matching point counts and performs no path
  adjustment.
- Read [profiles and curve sampling](10_profiles.md) for superellipse side
  lofts with the fixed `(y, z_min, z_max, width)` section format.
- See `docs/sdk/examples/section_loft_with_wires.py` for an executable model.
