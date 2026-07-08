# Wires, pipes, and sweeps

Use this page for swept profiles, circular wires, smooth tubes, authored paths,
arcs, and tube networks.

All coordinates, radii, and tolerances use meters. All angles use radians.
Path points are three dimensional values in the final mesh coordinate frame.

This page documents `SweepGeometry`, `PipeGeometry`, `ArcPipeGeometry`,
`WirePath`, `WirePolylineGeometry`, `wire_from_points`,
`tube_from_spline_points`, `sweep_profile_along_spline`, and
`tube_network_from_paths`.

```python
from mini_articraft.sdk import (
    ArcPipeGeometry,
    PipeGeometry,
    SweepGeometry,
    WirePath,
    WirePolylineGeometry,
    sweep_profile_along_spline,
    tube_from_spline_points,
    tube_network_from_paths,
    wire_from_points,
)
```

## Choose a helper

- Use `WirePolylineGeometry` or `wire_from_points(...)` for straight segments
  with optional bevels or rounded corners.
- Use `tube_from_spline_points(...)` for a smooth circular tube fitted through
  control points.
- Use `sweep_profile_along_spline(...)` for a smooth rail with a custom two
  dimensional profile.
- Use `PipeGeometry` when you already have the final sampled path.
- Use `ArcPipeGeometry` for one exact circular arc.
- Use `tube_network_from_paths(...)` when several circular paths must be joined
  into one mesh.

## SweepGeometry

```python
SweepGeometry(
    profile: Iterable[tuple[float, float]],
    path: Iterable[tuple[float, float, float]],
    *,
    cap: bool = False,
    closed: bool = True,
)
```

`SweepGeometry` is a short form of `PipeGeometry` for an open path with the
default up hint. The path needs at least two distinct finite points.

`closed` describes the profile, not the path. With `closed=True`, the profile
must contain at least three distinct points and have nonzero area. With
`closed=False`, it is an open polyline with at least two points. Caps are only
added when both `cap` and `closed` are true.

## PipeGeometry

```python
PipeGeometry(
    profile: Iterable[tuple[float, float]],
    path: Iterable[tuple[float, float, float]],
    *,
    cap: bool = False,
    closed: bool = True,
    path_closed: bool = False,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
)
```

The helper sweeps a two dimensional profile along a sampled path. It transports
a local frame along the path to reduce sudden profile roll.

At the first path point, profile X follows the local normal and profile Y
follows the local binormal. The helper derives those directions from the first
path tangent and `up_hint`. If the up hint is almost parallel to the tangent,
the helper selects a different fallback direction. A different up hint can
change the profile roll without changing the path.

The path needs at least two distinct finite points. Consecutive duplicate path
points are removed. The up hint must be nonzero.

With `path_closed=True`, the helper appends the first point when needed, joins
the last ring to the first ring, and disables caps. With an open path, `cap=True`
adds a cap at each end when the profile is closed.

Pipe caps use the average of the profile ring as a fan center. Use a profile
whose center lies inside the loop. A strongly concave profile can need a
different solid builder for reliable caps.

```python
rail_profile = [
    (-0.006, -0.003),
    (0.006, -0.003),
    (0.006, 0.003),
    (-0.006, 0.003),
]
rail = PipeGeometry(
    rail_profile,
    [(0.0, 0.0, 0.0), (0.05, 0.0, 0.03), (0.10, 0.0, 0.0)],
    cap=True,
)
```

## ArcPipeGeometry

```python
ArcPipeGeometry(
    profile: Iterable[tuple[float, float]],
    *,
    start_point: tuple[float, float, float],
    center: tuple[float, float, float],
    normal: tuple[float, float, float],
    angle: float,
    arc_segments: int = 20,
    cap: bool = False,
    closed: bool = True,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
)
```

This helper samples a circular arc with `sample_arc_3d(...)`, then passes that
path to `PipeGeometry`. `normal` defines the rotation axis through `center`.
The angle follows the right hand rule around that normal.

The start point must differ from the center. The radius direction must not be
collinear with the normal. Arc segments are clamped to at least 2. Profile,
cap, and up hint behavior match `PipeGeometry`.

```python
elbow = ArcPipeGeometry(
    rail_profile,
    start_point=(0.10, 0.0, 0.0),
    center=(0.0, 0.0, 0.0),
    normal=(0.0, 0.0, 1.0),
    angle=1.57079632679,
    arc_segments=24,
    cap=True,
)
```

## WirePath

`WirePath` stores an editable list of path points. Its methods mutate the path
and return the same path so calls can be chained. Duplicate consecutive points
are skipped.

```python
WirePath(start: tuple[float, float, float])

WirePath.from_points(
    points: Iterable[tuple[float, float, float]],
) -> WirePath

path.line_to(point: tuple[float, float, float]) -> WirePath
path.line_by(dx: float, dy: float, dz: float) -> WirePath
path.bezier_to(
    control1: tuple[float, float, float],
    control2: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    samples: int = 12,
) -> WirePath
path.arc(
    *,
    center: tuple[float, float, float],
    normal: tuple[float, float, float],
    angle: float,
    segments: int = 16,
) -> WirePath
path.extend(points: Iterable[tuple[float, float, float]]) -> WirePath
path.to_points() -> list[tuple[float, float, float]]
```

`from_points(...)` needs at least one point. `line_by(...)` adds an offset to
the current endpoint. `bezier_to(...)` makes one cubic Bezier segment from the
current endpoint. `arc(...)` starts at the current endpoint and uses the same
rules as `sample_arc_3d(...)`. `to_points()` returns a copy of the point list.

```python
path = (
    WirePath((-0.06, 0.0, 0.0))
    .line_by(0.02, 0.0, 0.0)
    .bezier_to(
        (-0.02, 0.0, 0.05),
        (0.02, 0.0, 0.05),
        (0.04, 0.0, 0.0),
        samples=16,
    )
    .line_to((0.06, 0.0, 0.0))
)
```

## Polyline wires

The class and function below have the same behavior. The function returns a
`MeshGeometry` and the class returns a `WirePolylineGeometry`.

```python
WirePolylineGeometry(
    points: Iterable[tuple[float, float, float]],
    *,
    radius: float,
    radial_segments: int = 16,
    closed_path: bool = False,
    cap_ends: bool = False,
    corner_mode: str = "fillet",
    corner_radius: float = 0.0,
    corner_segments: int = 8,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
)

wire_from_points(
    points: Iterable[tuple[float, float, float]],
    *,
    radius: float,
    radial_segments: int = 16,
    closed_path: bool = False,
    cap_ends: bool = False,
    corner_mode: str = "fillet",
    corner_radius: float = 0.0,
    corner_segments: int = 8,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry
```

The radius must be positive. `radial_segments` must be at least 6. The input
needs at least two distinct finite points. After that first check, segments
shorter than `min_segment_length` are removed. Use a positive minimum length
that is small relative to the visible wire.

Corner modes are `"miter"`, `"bevel"`, and `"fillet"`.

- Miter keeps the original corner point.
- Bevel replaces the corner with two trimmed points.
- Fillet adds a sampled quadratic bend between two trimmed points.

`corner_radius` is limited to 45 percent of each adjacent segment. A zero
corner radius leaves the centerline unchanged for every mode. `corner_segments`
is clamped to at least 2 when a fillet is built.

With `closed_path=True`, the helper closes the path and ignores `cap_ends`.
With an open path, `cap_ends=True` creates a watertight tube. The default
`cap_ends=False` leaves both ends open.

```python
guard = wire_from_points(
    [(-0.08, 0.0, 0.0), (0.0, 0.0, 0.06), (0.08, 0.0, 0.0)],
    radius=0.003,
    radial_segments=16,
    cap_ends=True,
    corner_mode="fillet",
    corner_radius=0.012,
    corner_segments=8,
)
```

## Smooth circular tubes

```python
tube_from_spline_points(
    points: Iterable[tuple[float, float, float]],
    *,
    radius: float,
    samples_per_segment: int = 12,
    closed_spline: bool = False,
    spline: str = "catmull_rom",
    alpha: float = 0.5,
    radial_segments: int = 16,
    cap_ends: bool = True,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry
```

The helper samples the requested spline, then passes the sampled path to
`wire_from_points(...)` with miter corners. Since the sampled points already
follow a smooth curve, the miter setting preserves that curve.

Supported spline names are `"catmull_rom"` and `"bezier"`. Catmull Rom fits
through the input points and uses `alpha`. Bezier input must contain `3 * n + 1`
control points. A closed Bezier chain must already end where it starts.

`closed_spline=True` closes the tube and disables end caps. With an open
spline, `cap_ends=True` creates closed ends. Radius, radial segment, up hint,
and minimum segment behavior match the polyline wire helper.

```python
handle = tube_from_spline_points(
    path.to_points(),
    radius=0.003,
    samples_per_segment=8,
    radial_segments=18,
    cap_ends=True,
)
```

Increase `samples_per_segment` when the centerline looks coarse. Increase
`radial_segments` when the circular section looks faceted.

## Smooth custom profile sweeps

```python
sweep_profile_along_spline(
    points: Iterable[tuple[float, float, float]],
    *,
    profile: Iterable[tuple[float, float]],
    samples_per_segment: int = 12,
    closed_spline: bool = False,
    spline: str = "catmull_rom",
    alpha: float = 0.5,
    cap_profile: bool = True,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry
```

Spline selection follows `tube_from_spline_points(...)`. The profile is a
closed two dimensional loop. `cap_profile=True` caps an open spline. A closed
spline never receives end caps.

Unlike `wire_from_points(...)`, this helper raises `ValueError` if the sampled
centerline contains a segment shorter than `min_segment_length`. Lower the
minimum only after checking that the control points do not contain accidental
duplicates.

The profile orientation follows the transported path frame. Use `up_hint` to
control its initial roll.

```python
from mini_articraft.sdk import rounded_rect_profile

trim = sweep_profile_along_spline(
    [(-0.05, 0.0, 0.0), (0.0, 0.02, 0.03), (0.05, 0.0, 0.0)],
    profile=rounded_rect_profile(0.006, 0.003, 0.0008),
    samples_per_segment=16,
    cap_profile=True,
)
```

## Tube networks

```python
tube_network_from_paths(
    paths: Iterable[Iterable[tuple[float, float, float]]],
    *,
    radius: float,
    radial_segments: int = 16,
    cap_ends: bool = True,
    corner_mode: str = "fillet",
    corner_radius: float = 0.0,
    corner_segments: int = 8,
    up_hint: tuple[float, float, float] = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
    shared_node_radius: float | None = None,
) -> MeshGeometry
```

At least one path is required, and each path needs at least two distinct finite
points. Tube radius must be positive. `shared_node_radius` defaults to the tube
radius and may be zero to disable shared node spheres.

The helper builds one `WirePolylineGeometry` for every path. It counts point
occurrences across the complete input, including repeated points in one path.
When a point occurs more than once, it can add a sphere at that point. Points
are considered the same after rounding by `min_segment_length`.

With `cap_ends=True`, every path is capped and Manifold unions the tubes and
shared node spheres. Intersecting paths can form one watertight body. Disjoint
paths can remain separate bodies inside one mesh. If Manifold cannot form a
valid closed result, the helper raises `ValueError`.

With `cap_ends=False`, the helper skips the boolean union and merges the
triangle lists. The result normally has open ends and can contain separate
components.

```python
frame = tube_network_from_paths(
    [
        [(-0.06, 0.0, 0.0), (0.0, 0.0, 0.0), (0.06, 0.0, 0.0)],
        [(0.0, -0.06, 0.0), (0.0, 0.0, 0.0), (0.0, 0.06, 0.0)],
    ],
    radius=0.004,
    radial_segments=12,
    cap_ends=True,
    shared_node_radius=0.005,
)
```

## Validation and common failures

- A path with fewer than two distinct points raises `ValueError`.
- A zero up hint or a zero arc normal raises `ValueError`.
- An invalid corner mode raises `ValueError`.
- A circular wire radius must be positive.
- A custom profile must contain enough distinct points for its `closed` mode.
- A network boolean requires closed input tubes, so keep `cap_ends=True` when
  you need a closed network solid.

## Related references

- Read [profiles and curve sampling](10_profiles.md) for spline and arc
  sampling details.
- Read [booleans and shells](40_booleans_and_shells.md) for the Manifold rules
  used by closed tube networks.
