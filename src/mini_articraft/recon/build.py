"""Constructive primitives: rebuild an object AS CODE (route B).

The agent measures the target mesh (section/ray_probe/bounds), then constructs
clean solids here — real drawer boxes, solid walls — instead of segmenting
dirty scan geometry. Everything returns trimesh.Trimesh in world coords, ready
for Rig.add_part.
"""
from __future__ import annotations

import numpy as np
import trimesh

Vec3 = tuple[float, float, float]


def box(dims: Vec3, center: Vec3 = (0, 0, 0)) -> trimesh.Trimesh:
    """Solid box: dims=(dx,dy,dz), positioned at center."""
    m = trimesh.creation.box(extents=np.asarray(dims, float))
    m.apply_translation(np.asarray(center, float))
    return m


def cylinder(radius: float, height: float, center: Vec3 = (0, 0, 0),
             axis: Vec3 = (0, 0, 1)) -> trimesh.Trimesh:
    """Solid cylinder along `axis` (knobs, handles, axles)."""
    m = trimesh.creation.cylinder(radius=radius, height=height, sections=24)
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a) + 1e-12
    R = trimesh.geometry.align_vectors([0, 0, 1], a)
    if R is not None:
        m.apply_transform(R)
    m.apply_translation(np.asarray(center, float))
    return m


def open_box(dims: Vec3, wall: float, center: Vec3 = (0, 0, 0),
             open_face: str = "+z") -> trimesh.Trimesh:
    """Box with one open face and solid walls of thickness `wall` — a drawer
    box (+z open) or a cabinet shell (+y open = front). open_face is one of
    +x -x +y -y +z -z. Built from 5 slabs (no booleans, always watertight)."""
    d = np.asarray(dims, float)
    c = np.asarray(center, float)
    ax = "xyz".index(open_face[1])
    sign = 1.0 if open_face[0] == "+" else -1.0
    slabs = []
    # bottom slab opposite the open face
    b_dims = d.copy(); b_dims[ax] = wall
    b_cent = c.copy(); b_cent[ax] -= sign * (d[ax] - wall) / 2
    slabs.append(box(tuple(b_dims), tuple(b_cent)))
    # four side walls around the open axis
    for wax in range(3):
        if wax == ax:
            continue
        for s in (-1.0, 1.0):
            w_dims = d.copy()
            w_dims[wax] = wall
            w_dims[ax] -= wall  # sit on the bottom slab
            w_cent = c.copy()
            w_cent[wax] += s * (d[wax] - wall) / 2
            w_cent[ax] += sign * wall / 2
            slabs.append(box(tuple(w_dims), tuple(w_cent)))
    return trimesh.util.concatenate(slabs)


def merge(*meshes: trimesh.Trimesh) -> trimesh.Trimesh:
    """Concatenate solids into one part (rigid assembly, no boolean needed)."""
    return trimesh.util.concatenate(list(meshes))


def box_behind(front: trimesh.Trimesh, depth: float, wall: float | None = None,
               inward: Vec3 = (0, 1, 0), shrink: float = 0.06) -> trimesh.Trimesh:
    """Snap-fit an open drawer box BEHIND a carved front panel: dims come from
    the front's own bounds, extruded `depth` along `inward` (into the body),
    open on top. Use B.merge(front, box_behind(front, depth)) to give a scan
    facade a real interior. shrink insets the box so it clears the opening."""
    lo, hi = front.bounds
    d = np.asarray(inward, float)
    d /= np.linalg.norm(d) + 1e-12
    ax = int(np.argmax(np.abs(d)))
    sign = float(np.sign(d[ax]) or 1.0)
    dims = (hi - lo) * (1.0 - shrink)
    dims[ax] = depth
    center = (lo + hi) / 2
    center[ax] = (hi[ax] if sign > 0 else lo[ax]) + sign * depth / 2
    w = wall if wall is not None else max(0.015 * float(np.linalg.norm(dims)), 1e-3)
    return open_box(tuple(dims), w, tuple(center), open_face="+z")
