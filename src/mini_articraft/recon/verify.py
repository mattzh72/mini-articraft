"""Physics verification: collision sweeps over a joint's range of motion.

The discriminating signals (validated on known good/bad drawer rigs):
- a correct joint's contact count DECAYS to ~zero as the part moves clear;
  a wrong group/axis keeps colliding (residual 10-100x higher at full open)
- the best slide axis is simply the one whose sweep decays fastest
"""
from __future__ import annotations

import numpy as np
import trimesh

from .probe import part_world_transform
from .rig import Rig

AXES6 = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]


def _manager(meshes: list[tuple[str, trimesh.Trimesh]]):
    from trimesh.collision import CollisionManager
    mgr = CollisionManager()
    for name, m in meshes:
        mgr.add_object(name, m)
    return mgr


def sweep_joint(rig: Rig, joint_name: str, steps: int = 5) -> list[int]:
    """Contact count between the joint's child and all other parts, swept
    closed -> open. Decay to ~0 = clean motion; persistence = bad group/axis."""
    j = next(jj for jj in rig.joints if jj.name == joint_name)
    mgr = _manager([(p.name, p.mesh) for p in rig.parts if p.name != j.child])
    child = next(p for p in rig.parts if p.name == j.child)
    counts = []
    for s in range(steps):
        v = j.lower + (j.upper - j.lower) * s / (steps - 1)
        m = child.mesh.copy()
        m.apply_transform(part_world_transform(rig, j.child, {joint_name: float(v)}))
        _, contacts = mgr.in_collision_single(m, return_data=True)
        counts.append(len(contacts))
    return counts


def best_slide_axis(moving: trimesh.Trimesh, others: list[trimesh.Trimesh],
                    steps: int = 4) -> tuple[tuple, list[int], dict]:
    """Rank the 6 axis directions by how fast the collision sweep decays; return
    (best_axis, its_counts, all_scores). Score = mean residual after the first step,
    normalized by the closed-state count (lower = cleaner exit)."""
    mgr = _manager([(f"o{i}", m) for i, m in enumerate(others)])
    scores, sweeps = {}, {}
    for ax in AXES6:
        a = np.asarray(ax, float)
        travel = float(moving.extents[int(np.argmax(np.abs(a)))]) * 0.8
        counts = []
        for s in range(steps):
            m = moving.copy()
            m.apply_translation(a * travel * s / (steps - 1))
            _, contacts = mgr.in_collision_single(m, return_data=True)
            counts.append(len(contacts))
        base = max(counts[0], 1)
        scores[ax] = float(np.mean(counts[1:]) / base)
        sweeps[ax] = counts
    best = min(scores, key=scores.get)
    return best, sweeps[best], {str(k): round(v, 3) for k, v in scores.items()}


def best_hinge(moving: trimesh.Trimesh, others: list[trimesh.Trimesh],
               steps: int = 4, max_angle: float = 1.4) -> dict:
    """Physics-ranked hinge search: candidate hinge lines are the 12 edges of the
    moving part's bbox (x both rotation signs); each is swept and scored by
    collision decay. Use for doors/lids where hinge_from_contact fails (a flush
    door touches its frame on all sides -> seam PCA gives a garbage axis).
    Returns {"axis", "origin", "counts", "score"}; score ~0 = swings clean."""
    mgr = _manager([(f"o{i}", m) for i, m in enumerate(others)])

    def bbox_edges(lo, hi):
        c = [lo, hi]
        corners = np.array([[c[i][0], c[j][1], c[k][2]]
                            for i in (0, 1) for j in (0, 1) for k in (0, 1)])
        return [(a, b) for ai, a in enumerate(corners) for b in corners[ai + 1:]
                if np.sum(~np.isclose(a, b)) == 1]

    # candidates: the moving part's bbox edges PLUS the contact-seam bbox edges.
    # seam edges are where real hinges live — and immune to bbox inflation from
    # protruding handles (a handle pushes the part bbox in front of the true
    # hinge line, making the door swing away from the body).
    edges = bbox_edges(*moving.bounds)
    from scipy.spatial import cKDTree
    diag = float(np.linalg.norm(moving.extents)) or 1.0
    body_pts = np.vstack([np.asarray(o.vertices) for o in others])
    d, _ = cKDTree(body_pts).query(np.asarray(moving.vertices), workers=-1)
    seam = np.asarray(moving.vertices)[d < 0.03 * diag]
    if len(seam) >= 8:
        edges += bbox_edges(seam.min(0), seam.max(0))
    best = None
    for a, b in edges:
        n = np.linalg.norm(b - a)
        if n < 1e-9:
            continue
        axis = (b - a) / n
        origin = (a + b) / 2
        for sign in (1.0, -1.0):
            counts = []
            m = None
            for s in range(steps):
                ang = sign * max_angle * s / (steps - 1)
                m = moving.copy()
                m.apply_transform(trimesh.transformations.rotation_matrix(
                    ang, axis, origin))
                _, contacts = mgr.in_collision_single(m, return_data=True)
                counts.append(len(contacts))
            residual = float(np.mean(counts[1:]) / max(counts[0], 1))
            # a real hinge KEEPS the part attached: penalize hinges that let the
            # fully-open part float away from the body (both grinding and
            # detaching disqualify — clean swing + sustained contact wins)
            detach = float(mgr.min_distance_single(m)) / diag
            score = residual + 25.0 * max(0.0, detach - 0.01)
            if best is None or score < best["score"]:
                best = {"axis": tuple(map(float, sign * axis)),
                        "origin": tuple(map(float, origin)),
                        "counts": counts, "detach": round(detach, 4),
                        "score": round(score, 4)}
    return best


def slide_limit(moving: trimesh.Trimesh, others: list[trimesh.Trimesh],
                axis, max_frac: float = 1.6, steps: int = 16) -> float:
    """COMPUTED prismatic travel: slide until the part pulls clear of contact
    (a drawer's useful travel), never past max_frac x its own length. Returns
    the upper limit in mesh units — use instead of guessing travel."""
    mgr = _manager([(f"o{i}", m) for i, m in enumerate(others)])
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a) + 1e-12
    span = float(moving.extents[int(np.argmax(np.abs(a)))]) * max_frac
    base = None
    for s in range(1, steps + 1):
        t = span * s / steps
        m = moving.copy()
        m.apply_translation(a * t)
        _, contacts = mgr.in_collision_single(m, return_data=True)
        n = len(contacts)
        if base is None:
            base = max(n, 1)
        if n <= max(2, 0.02 * base):
            return float(t)
    return float(span)


def swing_limit(moving: trimesh.Trimesh, others: list[trimesh.Trimesh],
                axis, origin, max_angle: float = 3.0, steps: int = 24) -> float:
    """COMPUTED revolute range: swing until the part hits the body again after
    leaving its seat (a door's stop). Returns the upper limit in radians."""
    mgr = _manager([(f"o{i}", m) for i, m in enumerate(others)])
    counts = []
    for s in range(steps + 1):
        ang = max_angle * s / steps
        m = moving.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(
            ang, np.asarray(axis, float), np.asarray(origin, float)))
        _, contacts = mgr.in_collision_single(m, return_data=True)
        counts.append(len(contacts))
    lowest = min(counts[1:]) if len(counts) > 1 else 0
    cleared = False
    for s in range(1, steps + 1):
        if counts[s] <= max(2, lowest):
            cleared = True
        elif cleared and counts[s] > max(4, 3 * max(lowest, 1)):
            return float(max_angle * (s - 1) / steps)  # last free angle
    return float(max_angle * 0.6) if not cleared else float(max_angle)


def seam_raggedness(moving: trimesh.Trimesh, body: trimesh.Trimesh) -> dict | None:
    """Quality of the split boundary between two parts. The moving part's open
    boundary edges that lie against the body form the seam; a correct clamshell/
    door split has a seam close to a straight line (ratio ~1-1.5). A ragged or
    meandering seam (ratio >> 2) means faces near the joint are misassigned —
    a sliver of the other part is riding along. Returns
    {"ratio", "seam_len", "line_len"} or None if no seam found."""
    from scipy.spatial import cKDTree
    # the split seam lives on the part's MAIN body; carried fragments (keys,
    # debris) have open edges everywhere and would drown the measurement
    comps = moving.split(only_watertight=False)
    if comps:
        main = max(comps, key=lambda c: len(c.faces))
        if len(main.faces) < 0.3 * len(moving.faces):
            return None  # pure soup: no meaningful seam
        moving = main
    es = np.asarray(moving.edges_sorted)
    uniq, counts = np.unique(es, axis=0, return_counts=True)
    open_edges = uniq[counts == 1]
    if len(open_edges) == 0:
        return None
    V = np.asarray(moving.vertices)
    mid = V[open_edges].mean(axis=1)
    diag = float(np.linalg.norm(moving.extents)) or 1.0
    d, _ = cKDTree(np.asarray(body.vertices)).query(mid, workers=-1)
    near = d < 0.03 * diag
    if near.sum() < 4:
        return None
    seg = V[open_edges[near]]
    seam_len = float(np.linalg.norm(seg[:, 0] - seg[:, 1], axis=1).sum())
    pts = seg.reshape(-1, 3)
    c = pts.mean(0)
    # straight-line reference: extent along the seam's principal direction
    u = np.linalg.svd(pts - c, full_matrices=False)[2][0]
    proj = (pts - c) @ u
    line_len = float(proj.max() - proj.min()) or 1e-9
    # PLACEMENT: a true hinge seam lies on a CREASE. Compare each seam edge's
    # moving-side normal to the nearest body-side normal: parallel normals
    # (fold ~0 deg) = the cut runs across flat surface, i.e. wrong place.
    mid_near = mid[near]
    bodyC = np.asarray(body.triangles_center)
    bt = cKDTree(bodyC)
    _, bj = bt.query(mid_near, workers=-1)
    bodyN = np.asarray(body.face_normals)[bj]
    # moving-side normals: nearest moving face to each seam midpoint
    mt = cKDTree(np.asarray(moving.triangles_center))
    _, mj = mt.query(mid_near, workers=-1)
    movN = np.asarray(moving.face_normals)[mj]
    cosang = np.clip(np.abs((movN * bodyN).sum(1)), 0, 1)
    fold = float(np.degrees(np.median(np.arccos(cosang))))
    return {"ratio": round(seam_len / line_len, 2), "fold_deg": round(fold, 1),
            "seam_len": round(seam_len, 4), "line_len": round(line_len, 4)}


def motion_report(rig: Rig, steps: int = 5) -> dict:
    """Per-joint sweep + verdict, formatted for agent feedback. Also flags
    moving parts carrying stray fragments (thin welded slivers never collide,
    so the sweep alone cannot punish them — but they ARE part of your part and
    will visibly ride along with the motion)."""
    from .segment import strip_strays
    out = {}
    for j in rig.joints:
        c = sweep_joint(rig, j.name, steps=steps)
        residual = np.mean(c[1:]) / max(c[0], 1)
        verdict = ("clean" if c[-1] <= max(2, c[0] * 0.05)
                   else "grinding" if residual < 0.5 else "BLOCKED")
        rep = {"contacts_closed_to_open": c, "verdict": verdict}
        child = next(p for p in rig.parts if p.name == j.child)
        parent = next((p for p in rig.parts if p.name == j.parent), None)
        _, strays = strip_strays(child.mesh)
        if strays is not None and len(strays.faces) > 0.01 * len(child.mesh.faces):
            rep["stray_faces"] = len(strays.faces)
            rep["warning"] = (f"{j.child} carries {len(strays.faces)} stray faces "
                              "outside its bulk — strip_strays it and put the "
                              "strays on the parent, or they fly with the part")
        if parent is not None:
            seam = seam_raggedness(child.mesh, parent.mesh)
            if seam is not None:
                rep["seam"] = seam
                fold = seam.get("fold_deg", 90)
                if j.jtype == "revolute" and fold < 12:
                    rep["seam_warning"] = (
                        f"seam lies on FLAT surface (fold {fold} deg; a hinge "
                        "seam sits on a crease) — your cut is in the wrong "
                        "place; move the label boundary to the fold line")
                elif seam["ratio"] > 2.5 and fold < 20:
                    # ragged AND off-crease = misassigned faces; ragged but
                    # ON-crease is usually just scan noise along the fillet
                    rep["seam_warning"] = (
                        f"split boundary is ragged (seam {seam['ratio']}x longer "
                        "than a straight line) and not on a crease — faces near "
                        "the joint are likely misassigned; refine your mask")
        out[j.name] = rep
    return out
