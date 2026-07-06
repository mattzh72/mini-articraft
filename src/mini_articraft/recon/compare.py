"""Compare a code-built reconstruction against the target mesh: the error
signal for the fit loop. Numbers first (bbox diff, per-view silhouette IoU),
plus overlay images (silhouettes, section profiles) so mismatches are visible.
"""
from __future__ import annotations

import math

import numpy as np
import trimesh

from .mesh import section
from .render import Camera, look_at, rasterize


def _silhouette(mesh: trimesh.Trimesh, cam: Camera) -> np.ndarray:
    img = rasterize([(mesh, (0.0, 0.0, 0.0))], cam)
    return img[:, :, 0] < 250  # non-white = object


def _cams(target: trimesh.Trimesh, width: int = 240) -> dict[str, Camera]:
    lo, hi = target.bounds
    center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.5
    f = 0.5 * width / math.tan(math.radians(45) / 2)
    dirs = {"front": (0, -1, 0.001), "right": (1, 0, 0.001),
            "top": (0.001, 0.001, 1), "iso": (1, -1, 0.7)}
    cams = {}
    for name, d in dirs.items():
        eye = center + np.asarray(d, float) / np.linalg.norm(d) * radius
        R, t = look_at(eye, center)
        cams[name] = Camera(width, width, f, f, width / 2, width / 2, R, t)
    return cams


def silhouette_check(augmented: trimesh.Trimesh, original: trimesh.Trimesh,
                     min_iou: float = 0.97) -> dict:
    """Guardrail for mesh+generated fusion: added geometry may fill interiors
    but must NOT change the object seen from outside. Returns {"ok", "iou"}."""
    cams = _cams(original)
    ious = {}
    for name, cam in cams.items():
        sa, so = _silhouette(augmented, cam), _silhouette(original, cam)
        union = float(np.logical_or(sa, so).sum()) or 1.0
        ious[name] = round(float(np.logical_and(sa, so).sum()) / union, 3)
    return {"ok": all(v >= min_iou for v in ious.values()), "iou": ious}


def compare(built: trimesh.Trimesh, target: trimesh.Trimesh,
            out_prefix: str | None = None, sections: int = 3) -> dict:
    """Fit-loop error signal. Returns:
    - bbox_err: per-axis size difference (built minus target, target units)
    - iou: silhouette intersection-over-union per view (1.0 = perfect)
    - images: overlay paths (if out_prefix given): silhouettes (red=built only,
      blue=target only, dark=both) and section profile overlays."""
    res: dict = {}
    bt, tg = built.bounds, target.bounds
    res["bbox_built"] = np.round(bt[1] - bt[0], 4).tolist()
    res["bbox_target"] = np.round(tg[1] - tg[0], 4).tolist()
    res["bbox_err"] = np.round((bt[1] - bt[0]) - (tg[1] - tg[0]), 4).tolist()
    res["center_err"] = np.round(built.bounds.mean(0) - target.bounds.mean(0), 4).tolist()

    cams = _cams(target)
    ious, images = {}, []
    for name, cam in cams.items():
        sb = _silhouette(built, cam)
        st = _silhouette(target, cam)
        inter = float(np.logical_and(sb, st).sum())
        union = float(np.logical_or(sb, st).sum()) or 1.0
        ious[name] = round(inter / union, 3)
        if out_prefix:
            from PIL import Image
            W = cam.width
            rgb = np.full((W, W, 3), 255, np.uint8)
            rgb[st] = (120, 150, 235)      # target only: blue
            rgb[sb] = (235, 120, 120)      # built only: red
            rgb[np.logical_and(sb, st)] = (70, 70, 80)  # both: dark
            p = f"{out_prefix}_sil_{name}.png"
            Image.fromarray(rgb).save(p)
            images.append(p)
    res["iou"] = ious

    if out_prefix and sections > 0:
        from PIL import Image, ImageDraw
        lo, hi = target.bounds
        for i in range(sections):
            z = lo[2] + (hi[2] - lo[2]) * (i + 1) / (sections + 1)
            st = section(target, (0, 0, float(z)), (0, 0, 1))
            sb = section(built, (0, 0, float(z)), (0, 0, 1))
            W = 420
            img = Image.new("RGB", (W, W), (255, 255, 255))
            dr = ImageDraw.Draw(img)
            allp = [lp for s in (st, sb) for lp in s["loops"] if len(lp)]
            if allp:
                pts = np.vstack(allp)
                p0, span = pts.min(0), float(max(np.ptp(pts, axis=0).max(), 1e-9))
                pad = 30

                def px(p):
                    q = (p - p0) / span * (W - 2 * pad) + pad
                    return q[0], W - q[1]
                for lp in st["loops"]:
                    dr.line([px(p) for p in lp], fill=(120, 150, 235), width=3)
                for lp in sb["loops"]:
                    dr.line([px(p) for p in lp], fill=(220, 60, 60), width=1)
            dr.text((6, 4), f"z={z:.3f} blue=target red=built", fill=(0, 0, 0))
            p = f"{out_prefix}_sec_{i}.png"
            img.save(p)
            images.append(p)
    if out_prefix:
        res["images"] = images
    return res
