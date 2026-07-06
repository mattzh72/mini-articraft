"""Over-segmentation: carve a mesh into rigid PATCHES the agent then groups.

Connectivity-first: connected components ARE the modeler's part structure
(drawer boxes, fronts, knobs are separate islands). Only a giant fused island
(SAM3D-style scan) needs geometric subdivision — and for those, prefer letting
the agent cut in code over blind clustering.
"""
from __future__ import annotations

import colorsys

import numpy as np
import trimesh


def palette(n: int) -> np.ndarray:
    """Bright, maximally-distinct colors: golden-ratio hue walk, high sat/value."""
    cols, h = [], 0.0
    for i in range(n):
        s = [1.0, 0.55][i % 2]
        v = [1.0, 0.85][(i // 2) % 2]
        cols.append(colorsys.hsv_to_rgb(h % 1.0, s, v))
        h += 0.61803398875
    return np.asarray(cols)


def split_fused(mesh: trimesh.Trimesh, k: int = 12) -> np.ndarray:
    """Subdivide one fused surface into k cells by face position + normal
    (the normal term keeps cells from straddling folds). Returns face labels."""
    C = np.asarray(mesh.triangles_center)
    N = np.asarray(mesh.face_normals)
    diag = float(np.linalg.norm(mesh.extents)) or 1.0
    X = np.hstack([C / diag, 0.5 * N])
    rng = np.random.default_rng(0)
    cent = X[rng.choice(len(X), k, replace=False)]
    lab = np.zeros(len(X), int)
    for _ in range(40):
        new = ((X[:, None, :] - cent[None]) ** 2).sum(-1).argmin(1)
        if np.array_equal(new, lab):
            break
        lab = new
        cent = np.stack([X[lab == c].mean(0) if (lab == c).any() else cent[c]
                         for c in range(k)])
    return lab


def overseg_auto(mesh: trimesh.Trimesh, k_fused: int = 12,
                 min_frac: float = 0.002) -> tuple[np.ndarray, int]:
    """Face labels + patch count. Components = patches; a component holding
    >30% of faces is subdivided via split_fused; dust merges into nearest patch."""
    from scipy.spatial import cKDTree
    import trimesh.graph as G
    n_faces = len(mesh.faces)
    comp_faces = G.connected_components(mesh.face_adjacency, nodes=np.arange(n_faces))
    labels = np.full(n_faces, -1)
    next_lab = 0
    dust = []
    for fc in comp_faces:
        fc = np.asarray(fc)
        if len(fc) < max(8, min_frac * n_faces):
            dust.append(fc)
            continue
        if len(fc) > 0.3 * n_faces:
            sub = mesh.submesh([fc], append=True)
            sublab = split_fused(sub, k=k_fused)
            for c in range(k_fused):
                sel = fc[sublab == c]
                if len(sel):
                    labels[sel] = next_lab
                    next_lab += 1
        else:
            labels[fc] = next_lab
            next_lab += 1
    if dust and next_lab > 0:
        C = np.asarray(mesh.triangles_center)
        good = labels >= 0
        tree = cKDTree(C[good])
        glab = labels[good]
        for fc in dust:
            _, nn = tree.query(C[fc], workers=-1)
            labels[fc] = glab[nn]
    return labels, next_lab


def reduce_patches(mesh: trimesh.Trimesh, labels: np.ndarray, k: int,
                   max_patches: int = 18) -> tuple[np.ndarray, int]:
    """Collapse decorative clutter so the agent sees CANDIDATES, not noise
    (books on a shelf = dozens of patches that will never be moving parts).
    Keeps sibling-group members and the largest patches up to max_patches;
    every other patch is absorbed into its nearest kept patch. Returns
    (dense_labels, new_k). Run this right after overseg_auto when k is large."""
    from scipy.spatial import cKDTree
    if k <= max_patches:
        return labels, k
    area = np.asarray(mesh.area_faces)
    total = float(area.sum())
    patch_area = {c: float(area[labels == c].sum()) for c in range(k) if (labels == c).any()}
    # sibling groups qualify only if their members are SUBSTANTIAL — books on a
    # shelf are siblings of each other too, and must not survive the filter
    keep: list[int] = []
    groups = [g for g in sibling_hints(mesh, labels, k)
              if float(np.median([patch_area[c] for c in g])) >= 0.01 * total]
    for grp in sorted(groups, key=lambda g: -float(np.median([patch_area[c] for c in g]))):
        if len(keep) + len(grp) <= max_patches:
            keep.extend(grp)
    for c in sorted(patch_area, key=patch_area.get, reverse=True):
        if len(keep) >= max_patches:
            break
        if c not in keep:
            keep.append(c)
    keep_set = set(keep)
    C = np.asarray(mesh.triangles_center)
    kept_mask = np.isin(labels, list(keep_set))
    tree = cKDTree(C[kept_mask])
    klab = labels[kept_mask]
    out = labels.copy()
    drop = ~kept_mask
    if drop.any():
        _, nn = tree.query(C[drop], workers=-1)
        out[drop] = klab[nn]
    # dense renumbering so ids stay small and readable
    remap = {old: new for new, old in enumerate(sorted(set(out.tolist())))}
    out = np.vectorize(remap.get)(out)
    return out, len(remap)


def crease_lines(mesh: trimesh.Trimesh, angle_deg: float = 25.0,
                 max_lines: int = 10, min_frac: float = 0.08) -> list[dict]:
    """Named seam CANDIDATES: STRAIGHT chains of sharp-fold edges (dihedral >
    angle_deg), longest first. Joints live on creases — the machine enumerates
    them, YOU pick which one is the hinge. Each entry: {"id", "points" (Nx3),
    "segments", "length", "fold_deg", "dir" (unit line direction), "mid",
    "straightness"}. Render with R.render_creases to see ids on views.

    Edges are split into COLLINEAR runs (same direction + same line), NOT just
    connected components — otherwise on a detailed mesh all the sharp detail
    (wood grain, brackets, grooves) chains into one useless tangled blob."""
    ang = np.degrees(np.asarray(mesh.face_adjacency_angles))
    sharp = ang > angle_deg
    if not sharp.any():
        return []
    edges = np.asarray(mesh.face_adjacency_edges)[sharp]   # vertex-index pairs
    folds = ang[sharp]
    V = np.asarray(mesh.vertices)
    diag = float(np.linalg.norm(mesh.extents))
    p0, p1 = V[edges[:, 0]], V[edges[:, 1]]
    mids = (p0 + p1) / 2
    dirs = p1 - p0
    elen = np.linalg.norm(dirs, axis=1)
    ok = elen > 1e-9
    p0, p1, mids, dirs, elen, folds = p0[ok], p1[ok], mids[ok], dirs[ok], elen[ok], folds[ok]
    dirs = dirs / elen[:, None]
    dirs *= np.sign(dirs[:, np.argmax(np.abs(dirs).sum(0))] + 1e-12)[:, None]  # fold sign

    remaining = np.ones(len(mids), bool)
    tol_ang = np.radians(18.0)
    tol_perp = 0.02 * diag
    lines = []
    order = np.argsort(-elen)
    for seed in order:
        if not remaining[seed]:
            continue
        u = dirs[seed]
        # edges parallel to seed AND lying on the seed's line (small perp dist)
        par = remaining & (np.abs(dirs @ u) > np.cos(tol_ang))
        rel = mids - mids[seed]
        perp = np.linalg.norm(rel - (rel @ u)[:, None] * u, axis=1)
        member = par & (perp < tol_perp)
        if member.sum() < 2:
            remaining[seed] = False
            continue
        idx = np.nonzero(member)[0]
        # keep only the contiguous run along the line through the seed (split
        # gaps so two colinear-but-separated creases don't merge)
        t = (mids[idx] - mids[seed]) @ u
        so = np.argsort(t)
        idx, ts = idx[so], t[so]
        gaps = np.where(np.diff(ts) > 0.06 * diag)[0]
        segs = np.split(idx, gaps + 1)
        run = max(segs, key=lambda s: elen[s].sum())
        remaining[run] = False
        length = float(elen[run].sum())
        if length < min_frac * diag:
            continue
        pts = np.vstack([p0[run], p1[run]])
        cen = pts.mean(0)
        sv = np.linalg.svd(pts - cen, full_matrices=False)[1]
        lines.append({"points": pts,
                      "segments": np.stack([p0[run], p1[run]], axis=1),
                      "length": round(length, 4),
                      "fold_deg": round(float(np.mean(folds[run])), 1),
                      "dir": tuple(np.round(u, 4).tolist()),
                      "mid": tuple(np.round(cen, 4).tolist()),
                      "straightness": round(float(sv[0] / (sv[1] + 1e-9)), 1)})
    lines.sort(key=lambda d: -d["length"])
    lines = lines[:max_lines]
    for i, d in enumerate(lines):
        d["id"] = f"C{i}"
    return lines


def cut_at_marks(mesh: trimesh.Trimesh, cam, pixels, normal,
                 from_probe=None) -> tuple[np.ndarray, dict]:
    """POINT-AT-THE-SEAM grounding: you mark the seam line in a rendered view
    (list of (px,py) along the visible seam); we ray-cast each to the 3D
    surface, fit a cut plane through those points with the given `normal`
    (the direction the moving part travels — e.g. (0,0,1) for a lid that lifts),
    and label faces above/below. Use when the seam is VISIBLE but not a sharp
    crease (a chest lid lip, a flush panel line) — vision locates it, not folds.
    Returns (labels 0=below/1=above, info). `from_probe` = probe_from_pixel fn."""
    if from_probe is None:
        from .probe import probe_from_pixel as from_probe
    pts = []
    for (px, py) in pixels:
        hit = from_probe(mesh, cam, px, py)
        if hit is not None:
            pts.append(hit)
    if len(pts) < 1:
        return np.zeros(len(mesh.faces), int), {"error": "no seam pixels hit the mesh"}
    pts = np.asarray(pts)
    c = pts.mean(0)
    n = np.asarray(normal, float)
    n = n / (np.linalg.norm(n) + 1e-12)
    C = np.asarray(mesh.triangles_center)
    side = ((C - c) @ n) > 0
    labels = side.astype(int)
    return labels, {"seam_center": tuple(np.round(c, 4).tolist()),
                    "n_marks_hit": len(pts),
                    "above_faces": int(side.sum()), "below_faces": int((~side).sum())}


def spectral_order(mesh: trimesh.Trimesh, bridge: bool = True) -> np.ndarray:
    """Canonical 1D ordering of the surface: per-face Fiedler value (2nd
    eigenvector of the face-adjacency graph Laplacian). Adjacent faces get
    nearby values; the value changes fastest at BOTTLENECKS (hinge fillets,
    necks between parts) — so thresholding it is a principled cut:
        labels = (S.spectral_order(m) > t).astype(int)
    bridge=True adds nearest-neighbor links between disconnected pieces so one
    ordering spans the whole object. Returns (n_faces,) float in [0,1]."""
    import scipy.sparse as sp
    import scipy.sparse.linalg as spl
    from scipy.spatial import cKDTree
    n = len(mesh.faces)
    edges = [np.asarray(mesh.face_adjacency)]
    if bridge:
        import trimesh.graph as G
        comps = G.connected_components(mesh.face_adjacency, nodes=np.arange(n))
        if len(comps) > 1:
            comps = sorted([np.asarray(c) for c in comps], key=len, reverse=True)
            C = np.asarray(mesh.triangles_center)
            main = comps[0]
            tree = cKDTree(C[main])
            extra = []
            for c in comps[1:]:
                d, j = tree.query(C[c], k=1)
                i = int(np.argmin(d))
                extra.append([c[i], main[j[i]]])
            edges.append(np.asarray(extra))
    E = np.vstack(edges)
    w = np.ones(len(E))
    A = sp.coo_matrix((np.r_[w, w], (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])),
                      shape=(n, n)).tocsr()
    d = np.asarray(A.sum(1)).ravel()
    L = sp.diags(d) - A
    try:
        vals, vecs = spl.eigsh(L.asfptype(), k=2, sigma=-1e-8, which="LM")
        v = vecs[:, np.argsort(vals)[1]]
    except Exception:
        X = np.random.default_rng(0).standard_normal((n, 3))
        vals, vecs = spl.lobpcg(L.asfptype() + 1e-9 * sp.eye(n), X, largest=False,
                                maxiter=200, tol=1e-6)[0:2]
        v = vecs[:, np.argsort(vals)[1]]
    v = v - v.min()
    return v / (v.max() + 1e-12)


def neck_profile(mesh: trimesh.Trimesh, v: np.ndarray, bins: int = 60):
    """How 'narrow' the surface is at each level of the spectral order: for
    thresholds t, count adjacency edges crossing v<=t | v>t, normalized by the
    smaller side's area. Minima = necks = natural cut points. Returns
    (thresholds, narrowness) — plot/print and cut at the valleys."""
    fa = np.asarray(mesh.face_adjacency)
    va, vb = v[fa[:, 0]], v[fa[:, 1]]
    area = np.asarray(mesh.area_faces)
    total = float(area.sum())
    ts = np.linspace(0.05, 0.95, bins)
    out = []
    for t in ts:
        crossing = int(np.sum((va <= t) != (vb <= t)))
        a_lo = float(area[v <= t].sum())
        frac = min(a_lo, total - a_lo) / total
        out.append(crossing / max(frac, 1e-6))
    return ts, np.asarray(out)








def patch_mesh(mesh: trimesh.Trimesh, labels: np.ndarray, ids) -> trimesh.Trimesh:
    """Submesh of the given patch id(s)."""
    ids = [ids] if np.isscalar(ids) else list(ids)
    return mesh.submesh([np.nonzero(np.isin(labels, ids))[0]], append=True)


def strip_strays(part: trimesh.Trimesh):
    """Split a part into (clean, strays) by SHAPE CLASS of its pieces:
    - sheet (thin in one dim: drawer front, door panel)  -> keep
    - compact (similar in all dims: knob, handle, latch) -> keep
    - rod (thin in TWO dims: welded-in face-frame stiles, rails, trim
      streamers that would visibly ride along with the part) -> stray,
      IF it also runs past the part's sheet/compact core.
    Returns (clean_mesh, strays_mesh_or_None) — reattach strays to the base."""
    comps = part.split(only_watertight=False)
    if len(comps) <= 1:
        return part, None
    big = [c for c in comps if len(c.faces) >= 16]
    dust = [c for c in comps if len(c.faces) < 16]
    if not big:
        return part, None

    def shape_class(c):
        e = np.sort(np.asarray(c.extents, float))
        if e[1] < 0.18 * e[2]:      # thin in two dims, long in one
            return "rod"
        return "body"               # sheet or compact

    bodies = [c for c in big if shape_class(c) == "body"]
    rods = [c for c in big if shape_class(c) == "rod"]
    if not bodies or not rods:
        return part, None
    core = trimesh.util.concatenate(bodies)
    lo, hi = core.bounds
    pad = 0.15 * np.maximum(hi - lo, 1e-9)
    lo, hi = lo - pad, hi + pad
    keep, stray = list(bodies), []
    for r in rods:
        inside = bool(np.all(r.bounds[0] >= lo) and np.all(r.bounds[1] <= hi))
        (keep if inside else stray).append(r)   # rods past the core = strays
    # dust joins whichever side is nearest
    if dust:
        from scipy.spatial import cKDTree
        kc = np.vstack([k.centroid for k in keep])
        sc = np.vstack([s.centroid for s in stray]) if stray else None
        for d in dust:
            dk = float(cKDTree(kc).query(d.centroid)[0])
            ds = float(cKDTree(sc).query(d.centroid)[0]) if sc is not None else np.inf
            (keep if dk <= ds else stray).append(d)
    if not stray:
        return part, None
    return (trimesh.util.concatenate(keep), trimesh.util.concatenate(stray))


def sibling_hints(mesh: trimesh.Trimesh, labels: np.ndarray, k: int) -> list[list[int]]:
    """Groups of patches with near-identical bbox extents = likely repeated parts
    (drawers in a row, pairs of doors). Strong grouping prior."""
    exts = {}
    for c in range(k):
        m = labels == c
        if not m.any():
            continue
        exts[c] = np.ptp(mesh.triangles_center[m], axis=0)
    groups, used = [], set()
    ids = sorted(exts)
    for i, a in enumerate(ids):
        if a in used:
            continue
        sib = [a]
        for b in ids[i + 1:]:
            if b in used:
                continue
            if np.allclose(exts[a], exts[b], rtol=0.15,
                           atol=0.02 * float(np.linalg.norm(mesh.extents))):
                sib.append(b)
        if len(sib) > 1:
            groups.append(sib)
            used.update(sib)
    return groups


def patch_adjacency(mesh: trimesh.Trimesh, labels: np.ndarray,
                    tol_frac: float = 0.01) -> dict[int, set[int]]:
    """Which patches touch which (shared face-adjacency edges or near-contact).
    Useful for completeness checks: a patch touching ONLY door patches belongs
    to the door."""
    adj: dict[int, set[int]] = {}
    fa = mesh.face_adjacency
    la, lb = labels[fa[:, 0]], labels[fa[:, 1]]
    for a, b in zip(la, lb):
        if a != b:
            adj.setdefault(int(a), set()).add(int(b))
            adj.setdefault(int(b), set()).add(int(a))
    # near-contact between disconnected components
    from scipy.spatial import cKDTree
    ids = sorted(set(labels.tolist()))
    diag = float(np.linalg.norm(mesh.extents))
    cents = {c: mesh.triangles_center[labels == c] for c in ids}
    trees = {c: cKDTree(v) for c, v in cents.items()}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if b in adj.get(a, ()):
                continue
            d, _ = trees[a].query(cents[b][:: max(1, len(cents[b]) // 200)], k=1,
                                  workers=-1)
            if float(np.min(d)) < tol_frac * diag:
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    return adj
