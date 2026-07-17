from __future__ import annotations

import numpy as np
from trimesh.proximity import closest_point

from mini_articraft.sdk._mesh_boolean import boolean_difference, boolean_union
from mini_articraft.sdk._mesh_core import MeshGeometry

_AXES = {"x": 0, "y": 1, "z": 2}


class SnapRefused(ValueError):
    """Raised when snapping a piece to touch would move it further than allowed."""


def _require_mesh(geometry: object, label: str) -> MeshGeometry:
    if not isinstance(geometry, MeshGeometry):
        raise TypeError(f"{label} must be MeshGeometry")
    return geometry


def _nearest_gap(anchor: MeshGeometry, piece: MeshGeometry) -> tuple[float, np.ndarray]:
    """Smallest surface gap between two solids and the unit direction piece -> anchor."""
    a_mesh = anchor.to_trimesh()
    b_mesh = piece.to_trimesh()
    points_on_a, dist_b, _ = closest_point(a_mesh, b_mesh.vertices)
    i = int(np.argmin(dist_b))
    point_a, point_b, dist = points_on_a[i], b_mesh.vertices[i], float(dist_b[i])
    points_on_b, dist_a, _ = closest_point(b_mesh, a_mesh.vertices)
    j = int(np.argmin(dist_a))
    if dist_a[j] < dist:
        point_a, point_b, dist = a_mesh.vertices[j], points_on_b[j], float(dist_a[j])
    direction = np.asarray(point_a, dtype=np.float64) - np.asarray(point_b, dtype=np.float64)
    norm = float(np.linalg.norm(direction))
    unit = direction / norm if norm > 1e-12 else np.zeros(3)
    return dist, unit


def snap_to(
    anchor: MeshGeometry,
    piece: MeshGeometry,
    *,
    overlap: float = 0.004,
    max_move: float = 0.02,
    axis: str | None = None,
) -> MeshGeometry:
    """Translate ``piece`` toward ``anchor`` until they overlap by about ``overlap``.

    Use this before ``weld`` (or before adding an overlapping shape) when a protrusion
    was placed with a small gap to the form it should meet, so you do not have to hit
    the exact coordinate by hand. Like the other mesh transforms it moves ``piece`` in
    place and returns it; snap the piece BEFORE you add it, and use the returned value,
    so every later check and articulation sees the real snapped position.

    ``snap_to`` only translates the whole piece, so it fits a single freely-placeable
    attachment (a boss, a foot, a spout root). It cannot help a piece whose position is
    fixed by a mechanism (a hinge barrel on its axis) or one that must meet the body at
    more than one place (a handle with two ends) -- move those by fixing their own shape
    or path instead.

    It raises ``SnapRefused`` when closing the gap would move the piece further than
    ``max_move``; a large required move means the piece is constrained or misplaced, and
    silently teleporting it would break the design. Pass ``axis`` (``"x"``, ``"y"``, or
    ``"z"``) to constrain the motion to one direction, e.g. to close a vertical gap
    without shifting a piece off a shared axis.
    """
    anchor = _require_mesh(anchor, "anchor")
    piece = _require_mesh(piece, "piece")
    overlap = float(overlap)
    if overlap < 0.0:
        raise ValueError("overlap must be non-negative")
    max_move = float(max_move)
    if max_move <= 0.0:
        raise ValueError("max_move must be positive")

    dist, unit = _nearest_gap(anchor, piece)
    if axis is not None:
        if axis not in _AXES:
            raise ValueError(f"axis must be one of x, y, z; got {axis!r}")
        k = _AXES[axis]
        sign = np.sign(unit[k]) or 1.0
        unit = np.zeros(3)
        unit[k] = sign

    move = (dist + overlap) * unit
    magnitude = float(np.linalg.norm(move))
    if magnitude > max_move:
        raise SnapRefused(
            f"closing the gap needs {magnitude * 1000:.1f} mm, over max_move "
            f"{max_move * 1000:.0f} mm; the piece is likely constrained or misplaced -- "
            f"fix its placement or shape instead of snapping"
        )
    return piece.translate(float(move[0]), float(move[1]), float(move[2]))


def weld(
    *geometries: MeshGeometry,
    trim: MeshGeometry | None = None,
) -> MeshGeometry:
    """Fuse overlapping solids into one molded piece with an exact boolean union.

    Place the pieces so they overlap (overlap within a part is free; use ``snap_to`` to
    close a small gap first), then ``weld`` them into a single shape and add THAT to the
    part. The result keeps the exact input surfaces, so fine detail is preserved. Because
    the pieces become one shape they take one color, so weld pieces that share a material;
    keep a differently colored piece (a black handle on a steel body) as its own
    overlapping shape instead.

    When the body is a hollow shell and a protrusion pokes through the wall into the
    cavity, pass ``trim`` (the solid that fills the cavity) to difference that stub away
    after the union, so nothing dangles inside the interior.
    """
    geoms = [_require_mesh(g, f"geometries[{i}]") for i, g in enumerate(geometries)]
    if len(geoms) < 2:
        raise ValueError("weld needs at least two geometries")

    result = geoms[0]
    for geometry in geoms[1:]:
        result = boolean_union(result, geometry)
    if trim is not None:
        result = boolean_difference(result, _require_mesh(trim, "trim"))
    return result


__all__ = ["SnapRefused", "snap_to", "weld"]
