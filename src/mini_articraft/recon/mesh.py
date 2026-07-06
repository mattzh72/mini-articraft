"""Mesh loading + cull primitives: the operations the agent composes to carve a
whole-object mesh into parts. Geometric + correctable (planes, boxes, regions).
"""
from __future__ import annotations

import numpy as np
import trimesh

Vec3 = tuple[float, float, float]


def load_mesh(path: str, *, normalize: bool = True, y_up_to_z_up: bool = True) -> trimesh.Trimesh:
    m = trimesh.load(path, force="mesh", process=True)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(list(m.geometry.values()))
    try:
        m.update_faces(m.nondegenerate_faces())
    except Exception:
        pass
    m.remove_unreferenced_vertices()
    if y_up_to_z_up:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    if normalize:
        m.apply_translation(-m.bounds.mean(0))
        m.apply_scale(1.0 / (np.linalg.norm(m.extents) + 1e-9))
    return m


def largest_component(m: trimesh.Trimesh) -> trimesh.Trimesh:
    comps = m.split(only_watertight=False)
    return max(comps, key=lambda c: len(c.faces)) if len(comps) else m


def upright(m: trimesh.Trimesh, timeout_s: float = 6.0) -> trimesh.Trimesh:
    """Rotate to the most probable STABLE resting pose. CAVEAT: "most stable" is
    NOT "semantically upright" — a tall fridge/oven is MORE stable lying flat, so
    this will lay it down. Only use when the object's natural pose IS its stable
    pose (a chest, a box). Prefer the reference photo to establish true up.
    Capped by a timeout; returns the mesh unchanged on failure."""
    import signal
    from .render import decimate
    proxy = trimesh.Trimesh(vertices=decimate(m, target=600).vertices,
                            faces=decimate(m, target=600).faces).convex_hull

    def _timeout(signum, frame):
        raise TimeoutError

    old = signal.getsignal(signal.SIGALRM) if hasattr(signal, "SIGALRM") else None
    try:
        if old is not None:
            signal.signal(signal.SIGALRM, _timeout)
            signal.setitimer(signal.ITIMER_REAL, timeout_s)
        T, _ = trimesh.poses.compute_stable_poses(proxy, n_samples=1, threshold=0.05)
    except Exception:
        return m
    finally:
        if old is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
    if not len(T):
        return m
    out = m.copy()
    out.apply_transform(T[0])
    out.apply_translation(-out.bounds.mean(0))
    return out


def section(m: trimesh.Trimesh, point: Vec3, normal: Vec3) -> dict:
    """Slice the mesh with a plane; return measurable 2D polylines (the profile
    view). Nested loops reveal cavities and wall thickness — exact answers that
    renders can only suggest. Returns {"loops": [Nx2 arrays in plane coords],
    "areas": [...], "to_3d": 4x4} (loops are closed polygons, plane frame)."""
    path = m.section(plane_origin=np.asarray(point, float),
                     plane_normal=np.asarray(normal, float))
    if path is None:
        return {"loops": [], "areas": [], "to_3d": np.eye(4)}
    planar, to_3d = path.to_2D()
    # walk entities directly: Path2D.discrete/polygons_closed only yield CLOSED
    # cycles, but real meshes are surface sheets whose profiles are open curves
    loops = [np.asarray(e.discrete(planar.vertices)) for e in planar.entities]
    areas = []
    for loop in loops:
        if len(loop) > 2 and np.allclose(loop[0], loop[-1], atol=1e-8):
            x, y = loop[:, 0], loop[:, 1]
            areas.append(float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2))
        else:
            areas.append(0.0)  # open polyline
    return {"loops": loops, "areas": areas, "to_3d": to_3d}


def ray_probe(m: trimesh.Trimesh, origin: Vec3, direction: Vec3,
              max_hits: int = 8) -> list[float]:
    """Distances of successive surface hits along a ray — 'what is behind this
    point?'. Two close hits = thin panel; a long gap = cavity; no second hit =
    open space. Exact hollowness/thickness measurement."""
    o = np.asarray(origin, float)
    d = np.asarray(direction, float)
    d = d / (np.linalg.norm(d) + 1e-12)
    # nudge origin forward so the surface we start on doesn't re-hit
    eps = 1e-4 * float(np.linalg.norm(m.extents))
    locs, _, _ = m.ray.intersects_location([o + d * eps], [d])
    if len(locs) == 0:
        return []
    ts = sorted(float(np.dot(loc - o, d)) for loc in locs)
    return ts[:max_hits]


def hinge_from_contact(moving: trimesh.Trimesh, body: trimesh.Trimesh, tol_frac: float = 0.05) -> dict:
    """Derive a revolute hinge on the seam where two parts touch: axis = PCA of the
    contact vertices, origin = their centroid. Keeps the part attached when it rotates."""
    from scipy.spatial import cKDTree
    diag = float(np.linalg.norm(moving.extents)) or 1.0
    tree = cKDTree(np.asarray(body.vertices))
    d, _ = tree.query(np.asarray(moving.vertices))
    seam = np.asarray(moving.vertices)[d < tol_frac * diag]
    if len(seam) < 8:
        seam = np.asarray(moving.vertices)[d < 3 * tol_frac * diag]
    if len(seam) < 8:
        # fallback: longest edge of the moving part's bbox, at the body-facing side
        ext = moving.extents; ax = int(np.argmax(ext))
        axis = tuple(float(i == ax) for i in range(3))
        return {"axis": axis, "origin": tuple(map(float, moving.centroid)),
                "provenance": "bbox fallback (no clear contact seam)"}
    centroid = seam.mean(0)
    _, _, vh = np.linalg.svd(seam - centroid, full_matrices=False)
    axis = vh[0] / (np.linalg.norm(vh[0]) + 1e-12)   # long direction of the seam
    w = vh[1] / (np.linalg.norm(vh[1]) + 1e-12)       # perpendicular, within the seam
    # the hinge is an EDGE of the seam (the fold), not its centre. pick the edge
    # nearest the body's bulk = where the moving part stays attached.
    proj = (seam - centroid) @ w
    lo_edge = seam[proj <= np.percentile(proj, 20)].mean(0)
    hi_edge = seam[proj >= np.percentile(proj, 80)].mean(0)
    bc = np.asarray(body.centroid)
    origin = lo_edge if np.linalg.norm(lo_edge - bc) <= np.linalg.norm(hi_edge - bc) else hi_edge
    return {"axis": tuple(map(float, axis)), "origin": tuple(map(float, origin)),
            "provenance": f"seam edge (of {len(seam)} contact verts) nearest body"}
