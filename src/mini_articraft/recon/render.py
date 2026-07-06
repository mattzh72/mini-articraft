"""Self-contained numpy rasterizer for probing renders (no GPU, no GL).

Renders a list of (mesh, rgba) parts with a z-buffer + simple shading, white
background. Used to give the agent eyes on the mesh and to preview rigs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh


@dataclass
class Camera:
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    R: np.ndarray  # 3x3 world->camera
    t: np.ndarray  # 3


def look_at(eye, target, up=(0.0, 0.0, 1.0)) -> tuple[np.ndarray, np.ndarray]:
    eye = np.asarray(eye, float); target = np.asarray(target, float)
    z = target - eye; z /= np.linalg.norm(z) + 1e-12
    up = np.asarray(up, float)
    x = np.cross(z, up)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross(z, np.array([0.0, 1.0, 0.0]))
    x /= np.linalg.norm(x) + 1e-12
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=0)
    t = -R @ eye
    return R, t


def orbit_camera(center, radius, azim_deg, elev_deg=18.0, width=320, height=320, fov_deg=45.0):
    az, el = math.radians(azim_deg), math.radians(elev_deg)
    eye = np.asarray(center, float) + radius * np.array(
        [math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    R, t = look_at(eye, center)
    f = 0.5 * height / math.tan(math.radians(fov_deg) / 2)
    return Camera(width, height, f, f, width / 2, height / 2, R, t)


def decimate(mesh: trimesh.Trimesh, target: int = 20000) -> trimesh.Trimesh:
    """Decimate for fast rasterization (pure-numpy raster is per-face)."""
    if len(mesh.faces) <= target:
        return mesh
    try:
        import fast_simplification
        v, f = fast_simplification.simplify(
            np.asarray(mesh.vertices, np.float32), np.asarray(mesh.faces, np.int64),
            target_count=target)
        return trimesh.Trimesh(vertices=v, faces=f, process=False)
    except Exception:
        return mesh


def rasterize(parts: list[tuple[trimesh.Trimesh, tuple]], cam: Camera,
              ss: int = 1, shade: bool = True, return_zbuf: bool = False):
    """parts: list of (mesh, (r,g,b) in 0..1). Returns HxWx3 uint8, white bg.
    ss>1 = supersample: render at ss x resolution, downsample with LANCZOS
    (anti-aliased edges; cost scales with ss^2). shade=False renders flat
    colors (exact values — used for ID buffers)."""
    if ss > 1 and not return_zbuf:
        from PIL import Image
        big = Camera(cam.width * ss, cam.height * ss, cam.fx * ss, cam.fy * ss,
                     cam.cx * ss, cam.cy * ss, cam.R, cam.t)
        img = rasterize(parts, big, ss=1, shade=shade)
        pim = Image.fromarray(img).resize((cam.width, cam.height), Image.LANCZOS)
        return np.asarray(pim)
    parts = [(decimate(m), c) for m, c in parts]
    W, H = cam.width, cam.height
    color = np.ones((H, W, 3))
    zbuf = np.full((H, W), np.inf)
    light = np.array([0.3, 0.45, 1.0]); light /= np.linalg.norm(light)
    for mesh, rgb in parts:
        V = np.asarray(mesh.vertices, float)
        F = np.asarray(mesh.faces, int)
        if len(F) == 0:
            continue
        cam_pts = V @ cam.R.T + cam.t
        z = cam_pts[:, 2]
        uv = np.empty((len(V), 2))
        uv[:, 0] = cam.fx * cam_pts[:, 0] / z + cam.cx
        uv[:, 1] = cam.fy * cam_pts[:, 1] / z + cam.cy
        fn = mesh.face_normals
        shades = (0.4 + 0.6 * np.clip(fn @ light, 0, 1)) if shade \
            else np.ones(len(F))
        # rgb may be a flat (3,) color OR a per-face (nfaces,3) array (texture)
        rgb_arr = np.asarray(rgb, float)
        per_face = rgb_arr.ndim == 2
        for fi in range(len(F)):
            a, b, c = F[fi]
            if z[a] <= 0 or z[b] <= 0 or z[c] <= 0:
                continue
            p = uv[[a, b, c]]
            minx = max(int(np.floor(p[:, 0].min())), 0)
            miny = max(int(np.floor(p[:, 1].min())), 0)
            maxx = min(int(np.ceil(p[:, 0].max())), W - 1)
            maxy = min(int(np.ceil(p[:, 1].max())), H - 1)
            if maxx < minx or maxy < miny:
                continue
            xs, ys = np.meshgrid(np.arange(minx, maxx + 1), np.arange(miny, maxy + 1))
            px, py = xs + 0.5, ys + 0.5
            d = (p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1])
            if abs(d) < 1e-9:
                continue
            w0 = ((p[1, 1] - p[2, 1]) * (px - p[2, 0]) + (p[2, 0] - p[1, 0]) * (py - p[2, 1])) / d
            w1 = ((p[2, 1] - p[0, 1]) * (px - p[2, 0]) + (p[0, 0] - p[2, 0]) * (py - p[2, 1])) / d
            w2 = 1 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            zt = w0 * z[a] + w1 * z[b] + w2 * z[c]
            sub = zbuf[miny:maxy + 1, minx:maxx + 1]
            wr = inside & (zt < sub)
            sub[wr] = zt[wr]
            base = rgb_arr[fi] if per_face else rgb_arr
            col = np.clip(base * shades[fi], 0, 1)
            color[miny:maxy + 1, minx:maxx + 1][wr] = col
    if return_zbuf:
        return (color * 255).astype(np.uint8), zbuf
    return (color * 255).astype(np.uint8)


def _bounds_of(meshes: list[trimesh.Trimesh]) -> tuple[np.ndarray, np.ndarray]:
    lo = np.min([m.bounds[0] for m in meshes], axis=0)
    hi = np.max([m.bounds[1] for m in meshes], axis=0)
    return lo, hi


def draw_triad(pim, cam: Camera) -> None:
    """Axis compass in the lower-left corner: +X red, +Y green, +Z blue,
    projected with the view's own rotation. Ground truth about the picture."""
    from PIL import ImageDraw
    dr = ImageDraw.Draw(pim)
    ox, oy = 30, cam.height - 30
    for axis, col, lab in [((1, 0, 0), (200, 40, 40), "x"),
                           ((0, 1, 0), (30, 150, 40), "y"),
                           ((0, 0, 1), (40, 70, 220), "z")]:
        d = cam.R @ np.asarray(axis, float)
        dx, dy = 24 * d[0], 24 * d[1]
        dr.line([(ox, oy), (ox + dx, oy + dy)], fill=col, width=2)
        dr.text((ox + dx * 1.35 - 3, oy + dy * 1.35 - 5), lab, fill=col)





def _patch_cam(mesh: trimesh.Trimesh, direction, width: int) -> Camera:
    lo, hi = mesh.bounds
    center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.45
    d = np.asarray(direction, float)
    eye = center + d / np.linalg.norm(d) * radius
    R, t = look_at(eye, center)
    f = 0.5 * width / math.tan(math.radians(45) / 2)
    return Camera(width, width, f, f, width / 2, width / 2, R, t)


def _id_buffer(mesh: trimesh.Trimesh, labels, k: int, cam: Camera) -> np.ndarray:
    """Per-pixel patch id with occlusion (-1 = background)."""
    parts = [(mesh.submesh([np.nonzero(labels == c)[0]], append=True),
              ((c + 1) / 255.0, 0.0, 0.0)) for c in range(k) if (labels == c).any()]
    img = rasterize(parts, cam, shade=False)
    ids = img[:, :, 0].astype(int) - 1
    ids[img[:, :, 1] > 128] = -1
    return ids


def render_numbered(mesh: trimesh.Trimesh, labels, k: int, path: str, views=None) -> str:
    """Patch overview: colors + ids, labels placed only where the patch is visible."""
    from PIL import Image, ImageDraw
    from .segment import palette
    cols = palette(k)
    parts = [(mesh.submesh([np.nonzero(labels == c)[0]], append=True), tuple(cols[c]))
             for c in range(k) if (labels == c).any()]
    W = 380
    tiles = []
    for d in (views or [(0, -1, 0.15), (1, -0.6, 0.35), (0.15, 0.25, 1.0)]):
        cam = _patch_cam(mesh, d, W)
        img = rasterize(parts, cam)
        ids = _id_buffer(mesh, labels, k, cam)
        pim = Image.fromarray(img)
        dr = ImageDraw.Draw(pim)
        for c in range(k):
            ys, xs = np.nonzero(ids == c)
            if len(xs) < 60:
                continue
            x, y = float(np.median(xs)), float(np.median(ys))
            if ids[int(y), int(x)] != c:
                j = int(np.argmin((xs - x) ** 2 + (ys - y) ** 2))
                x, y = float(xs[j]), float(ys[j])
            dr.text((x - 4, y - 5), str(c), fill=(0, 0, 0))
            dr.text((x - 5, y - 6), str(c), fill=(255, 255, 255))
        tiles.append(np.asarray(pim))
    Image.fromarray(np.concatenate(tiles, axis=1)).save(path)
    return path


def render_legend(mesh: trimesh.Trimesh, labels, k: int, path: str, tile: int = 190,
                  direction=(1, -1, 0.55)) -> str:
    """Contact sheet, one consistent view: each patch solid red where visible,
    translucent where hidden (x-ray), captioned id + surface share."""
    from PIL import Image, ImageDraw
    ids = [c for c in range(k) if (labels == c).any()]
    cam = _patch_cam(mesh, direction, tile)
    base = rasterize([(mesh, (0.72, 0.72, 0.75))], cam).astype(float)
    idbuf = _id_buffer(mesh, labels, k, cam)
    tiles = []
    for c in ids:
        sel = mesh.submesh([np.nonzero(labels == c)[0]], append=True)
        solo = rasterize([(sel, (1.0, 0.0, 0.0))], cam, shade=False)
        sil = solo[:, :, 1] < 128
        img = base.copy()
        hid = sil & (idbuf != c)
        vis = idbuf == c
        img[hid] = img[hid] * 0.55 + np.array([255, 120, 120]) * 0.45
        img[vis] = img[vis] * 0.25 + np.array([225, 20, 20]) * 0.75
        pim = Image.fromarray(img.astype(np.uint8))
        share = 100 * (labels == c).sum() / len(labels)
        ImageDraw.Draw(pim).text((5, 3), f"patch {c}  ({share:.0f}%)", fill=(0, 0, 0))
        tiles.append(np.asarray(pim))
    ncol = 6
    rows = []
    for r in range(0, len(tiles), ncol):
        row = tiles[r:r + ncol]
        row += [np.full_like(tiles[0], 255)] * (ncol - len(row))
        rows.append(np.concatenate(row, axis=1))
    Image.fromarray(np.concatenate(rows, axis=0)).save(path)
    return path


def look(parts, path: str, *, direction=(1, -1, 0.6), center=None, zoom: float = 1.0,
         width: int = 420, ss: int = 1) -> str:
    """Render from any viewpoint. parts: mesh or [(mesh,(r,g,b)),...]. Aim at a
    point (center) and zoom in for close-ups."""
    from PIL import Image
    if hasattr(parts, "faces"):
        parts = [(parts, (0.62, 0.62, 0.67))]
    lo, hi = _bounds_of([m for m, _ in parts])
    c = np.asarray(center, float) if center is not None else (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.45 / max(zoom, 1e-3)
    d = np.asarray(direction, float)
    eye = c + d / (np.linalg.norm(d) + 1e-12) * radius
    R, t = look_at(eye, c)
    f = 0.5 * width / math.tan(math.radians(45) / 2)
    cam = Camera(width, width, f, f, width / 2, width / 2, R, t)
    pim = Image.fromarray(rasterize(parts, cam, ss=ss))
    draw_triad(pim, cam)
    pim.save(path)
    return path


def collage(images: list, path: str, *, cols: int = 3, labels: list | None = None,
            tile: int = 360) -> str:
    """Tile images into one labeled sheet."""
    from PIL import Image, ImageDraw, ImageOps
    ims = []
    for i, p in enumerate(images):
        im = ImageOps.contain(Image.open(p).convert("RGB"), (tile, tile))
        canvas = Image.new("RGB", (tile, tile + 16), (255, 255, 255))
        canvas.paste(im, ((tile - im.width) // 2, 16 + (tile - im.height) // 2))
        lab = labels[i] if labels and i < len(labels) else Path(p).stem
        ImageDraw.Draw(canvas).text((4, 2), str(lab), fill=(0, 0, 0))
        ims.append(canvas)
    blank = Image.new("RGB", ims[0].size, (255, 255, 255))
    rows = []
    for r in range(0, len(ims), cols):
        row = ims[r:r + cols] + [blank] * (cols - len(ims[r:r + cols]))
        rows.append(np.concatenate([np.asarray(t) for t in row], axis=1))
    Image.fromarray(np.concatenate(rows, axis=0)).save(path)
    return path


def render_creases(mesh: trimesh.Trimesh, creases: list, path: str, *,
                   direction=(1, -1, 0.6), width: int = 520, ss: int = 2) -> str:
    """Mesh ghosted grey with each crease candidate drawn + labeled (occlusion-honest)."""
    from PIL import Image, ImageDraw
    lo, hi = mesh.bounds
    center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.5
    d = np.asarray(direction, float)
    eye = center + d / np.linalg.norm(d) * radius
    R, t = look_at(eye, center)
    f = 0.5 * width / math.tan(math.radians(45) / 2)
    cam = Camera(width, width, f, f, width / 2, width / 2, R, t)
    img, zbuf = rasterize([(mesh, (0.85, 0.85, 0.88))], cam, return_zbuf=True)
    pim = Image.fromarray(img)
    dr = ImageDraw.Draw(pim)
    cols = [(210, 40, 40), (40, 90, 210), (30, 160, 60), (220, 140, 20),
            (150, 40, 190), (20, 160, 160), (200, 60, 130), (110, 110, 30)]
    W = cam.width
    diag = float(np.linalg.norm(mesh.extents))

    def proj(p3):
        pc = cam.R @ np.asarray(p3, float) + cam.t
        if pc[2] <= 0:
            return None
        return (cam.fx * pc[0] / pc[2] + cam.cx, cam.fy * pc[1] / pc[2] + cam.cy, pc[2])
    for i, c in enumerate(creases):
        col = cols[i % len(cols)]
        label_at = None
        for a, b in c["segments"]:
            pa, pb = proj(a), proj(b)
            if pa is None or pb is None:
                continue
            mx, my, mz = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (pa[2] + pb[2]) / 2
            xi, yi = int(np.clip(mx, 0, W - 1)), int(np.clip(my, 0, W - 1))
            if mz <= zbuf[yi, xi] + 0.02 * diag:
                dr.line([pa[:2], pb[:2]], fill=col, width=3)
                if label_at is None:
                    label_at = (mx, my)
        if label_at is not None:
            x, y = label_at
            dr.rectangle([x + 4, y - 9, x + 4 + 8 * len(c["id"]), y + 4], fill=(255, 255, 255))
            dr.text((x + 6, y - 8), c["id"], fill=col)
    draw_triad(pim, cam)
    pim.save(path)
    return path


def render_grid(mesh: trimesh.Trimesh, path: str, *, views=None, width: int = 460,
                step: float = 0.1, ss: int = 2) -> str:
    """Grey mesh with SURFACE graph-paper: coordinate contour lines painted on
    the visible surface (blue=z, red=x, green=y levels every `step`), plus axis
    rulers. Read any point's true coordinate and specify cuts in real values."""
    from PIL import Image, ImageDraw
    lo, hi = mesh.bounds
    center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.6
    f = 0.5 * width / math.tan(math.radians(45) / 2)
    axcol = [(200, 60, 60), (40, 160, 60), (60, 90, 210)]

    def ticks(a):
        s = math.ceil(lo[a] / step) * step
        out = []
        while s <= hi[a] + 1e-9:
            out.append(round(s, 3)); s += step
        return out
    tiles = []
    for d in (views or [(0.35, -1, 0.16), (1, -0.35, 0.16)]):
        dd = np.asarray(d, float)
        eye = center + dd / np.linalg.norm(dd) * radius
        R, t = look_at(eye, center)
        cam = Camera(width, width, f, f, width / 2, width / 2, R, t)
        img, zbuf = rasterize([(mesh, (0.74, 0.75, 0.80))], cam, return_zbuf=True)
        col = img.astype(float)
        ys, xs = np.nonzero(np.isfinite(zbuf))
        if len(xs):
            zc = zbuf[ys, xs]
            camp = np.stack([(xs - cam.cx) / cam.fx * zc,
                             (ys - cam.cy) / cam.fy * zc, zc], axis=1)
            world = (camp - cam.t) @ cam.R
            band = 0.008 * float(np.linalg.norm(hi - lo))
            for ax in range(3):
                w = world[:, ax]
                on = np.abs(w - np.round(w / step) * step) < band
                col[ys[on], xs[on]] = 0.35 * col[ys[on], xs[on]] + 0.65 * np.array(axcol[ax])
        pim = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(pim)

        def screen(p):
            pc = cam.R @ np.asarray(p, float) + cam.t
            if pc[2] <= 0.01:
                return None
            return (cam.fx * pc[0] / pc[2] + cam.cx, cam.fy * pc[1] / pc[2] + cam.cy)
        for ax in range(3):
            for tv in ticks(ax):
                p = lo.copy(); p[ax] = tv
                sp = screen(p)
                if sp and 0 <= sp[0] < width and 0 <= sp[1] < width:
                    dr.line([(sp[0] - 3, sp[1]), (sp[0] + 3, sp[1])], fill=axcol[ax], width=2)
                    dr.text((sp[0] + 4, sp[1] - 5), f"{'xyz'[ax]}{tv:+.1f}", fill=axcol[ax])
        draw_triad(pim, cam)
        tiles.append(np.asarray(pim))
    Image.fromarray(np.concatenate(tiles, axis=1)).save(path)
    return path


def render_section(sec: dict, path: str, *, width: int = 500) -> str:
    """Draw the polylines from mesh.section() (profile drawing)."""
    from PIL import Image, ImageDraw
    loops = sec.get("loops", [])
    img = Image.new("RGB", (width, width), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    if loops:
        allp = np.vstack([lp for lp in loops if len(lp)])
        lo, hi = allp.min(0), allp.max(0)
        span = float(max((hi - lo).max(), 1e-9))
        pad = 0.08 * width

        def to_px(p):
            q = (p - lo) / span * (width - 2 * pad) + pad
            return q[0], width - q[1]
        cols = [(200, 30, 30), (30, 80, 200), (30, 160, 60), (220, 140, 20),
                (140, 40, 180), (20, 150, 150)]
        for i, (loop, area) in enumerate(zip(loops, sec.get("areas", [0] * len(loops)))):
            if len(loop) < 2:
                continue
            c = cols[i % len(cols)]
            pts = [to_px(p) for p in loop]
            dr.line(pts, fill=c, width=2)
    dr.text((6, 4), f"{len(loops)} polylines", fill=(0, 0, 0))
    img.save(path)
    return path


def render_views(parts: list, path: str, *, n: int = 4, elev: float = 18.0,
                 width: int = 300, labels: bool = True) -> str:
    """Horizontal montage of n orbit views."""
    from PIL import Image, ImageDraw
    lo, hi = _bounds_of([m for m, _ in parts]); center = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo)) * 1.4
    tiles = []
    for k in range(n):
        cam = orbit_camera(center, radius, 360 * k / n, elev, width, width)
        pim = Image.fromarray(rasterize(parts, cam))
        if labels:
            ImageDraw.Draw(pim).text((5, 5), f"{int(360 * k / n)}deg", fill=(180, 0, 0))
        draw_triad(pim, cam)
        tiles.append(np.asarray(pim))
    Image.fromarray(np.concatenate(tiles, axis=1)).save(path)
    return path
