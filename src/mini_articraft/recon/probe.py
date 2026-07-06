"""Probing/preview: render a Rig at a joint configuration and animate opening.
These become the agent's eyes on its own rig (does the part swing correctly?).
"""
from __future__ import annotations

import numpy as np
import trimesh

from .render import _bounds_of, orbit_camera, rasterize
from .rig import Rig


def probe_from_pixel(mesh: trimesh.Trimesh, cam, px: int, py: int):
    """Ray-cast a pixel in a rendered view to the 3D face it hits (the reticle move:
    the agent points at a pixel, we find where on the mesh that is)."""
    # ray in camera space, then to world
    d_cam = np.array([(px - cam.cx) / cam.fx, (py - cam.cy) / cam.fy, 1.0])
    d_world = cam.R.T @ d_cam
    origin = -cam.R.T @ cam.t
    locs, _, _ = mesh.ray.intersects_location([origin], [d_world])
    if len(locs) == 0:
        return None
    # nearest hit
    return locs[np.argmin(np.linalg.norm(locs - origin, axis=1))]




def part_world_transform(rig: Rig, part_name: str, config: dict[str, float]) -> np.ndarray:
    """World transform of a part for given joint values (single-level: child moves)."""
    T = np.eye(4)
    for j in rig.joints:
        if j.child != part_name:
            continue
        v = float(config.get(j.name, 0.0))
        if j.jtype in ("revolute", "continuous"):
            T = trimesh.transformations.rotation_matrix(v, j.axis, j.origin) @ T
        elif j.jtype == "prismatic":
            tr = np.eye(4); tr[:3, 3] = np.asarray(j.axis) * v
            T = tr @ T
    return T


def _posed_parts(rig: Rig, config: dict[str, float]):
    parts = []
    for p in rig.parts:
        m = p.mesh.copy()
        m.apply_transform(part_world_transform(rig, p.name, config))
        parts.append((m, p.color))
    return parts


def render_rig(rig: Rig, path: str, *, config: dict[str, float] | None = None,
               n: int = 4, elev: float = 16.0, width: int = 300, ss: int = 1) -> str:
    from PIL import Image
    parts = _posed_parts(rig, config or {})
    lo, hi = _bounds_of([m for m, _ in parts]); center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.4
    tiles = [rasterize(parts, orbit_camera(center, radius, 360 * k / n, elev, width, width), ss=ss)
             for k in range(n)]
    Image.fromarray(np.concatenate(tiles, axis=1)).save(path)
    return path


def animate_gif(rig: Rig, joint_name: str, path: str, *, n: int = 24, azim: float = 45.0,
                elev: float = 12.0, width: int = 340, orbit: float = 30.0, ss: int = 1) -> str:
    """Smooth open->close->open GIF; camera slowly orbits for a video feel."""
    from PIL import Image
    j = next(jj for jj in rig.joints if jj.name == joint_name)
    lo, hi = _bounds_of([p.mesh for p in rig.parts]); center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.5
    vals = list(np.linspace(j.lower, j.upper, n)) + list(np.linspace(j.upper, j.lower, n))
    frames = []
    for i, v in enumerate(vals):
        az = azim + orbit * np.sin(2 * np.pi * i / len(vals))
        cam = orbit_camera(center, radius, az, elev, width, width)
        frames.append(Image.fromarray(rasterize(_posed_parts(rig, {joint_name: float(v)}), cam, ss=ss)))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=55, loop=0)
    return path


def render_open(rig: Rig, joint_name: str, path: str, *, azim: float = 40.0, elev: float = 16.0,
                width: int = 300, states: int = 3, ss: int = 1) -> str:
    """Closed -> open montage of one joint (single fixed viewpoint)."""
    from PIL import Image, ImageDraw
    j = next(jj for jj in rig.joints if jj.name == joint_name)
    lo, hi = _bounds_of([p.mesh for p in rig.parts]); center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.4
    cam = orbit_camera(center, radius, azim, elev, width, width)
    tiles = []
    for s in range(states):
        v = j.lower + (j.upper - j.lower) * s / max(states - 1, 1)
        img = rasterize(_posed_parts(rig, {joint_name: v}), cam, ss=ss)
        pim = Image.fromarray(img)
        deg = int(np.degrees(v)) if j.jtype in ("revolute", "continuous") else round(v, 2)
        ImageDraw.Draw(pim).text((5, 5), f"{deg}", fill=(180, 0, 0))
        tiles.append(np.asarray(pim))
    Image.fromarray(np.concatenate(tiles, axis=1)).save(path)
    return path
