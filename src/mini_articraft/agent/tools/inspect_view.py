from __future__ import annotations

import base64
import io
import math
import runpy
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.sdk import ArticulatedObject
from mini_articraft.sdk._collision import MeshCollisionKernel

_DEFAULT_COLOR = (0.70, 0.72, 0.74)
_FOV_DEGREES = 40.0
_LIGHT = np.array([0.35, -0.5, 0.8])
_LIGHT = _LIGHT / np.linalg.norm(_LIGHT)


@dataclass
class _Piece:
    name: str
    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray
    color: tuple[float, float, float]


def _load_model(workspace: Path) -> ArticulatedObject:
    globals_dict = runpy.run_path(str(workspace / "main.py"), run_name="__main__")
    model = globals_dict.get("object_model")
    if not isinstance(model, ArticulatedObject):
        raise ValueError("main.py must define object_model as an ArticulatedObject")
    return model


def _color_map(model: ArticulatedObject) -> dict[tuple[str, str], tuple[float, float, float]]:
    colors: dict[tuple[str, str], tuple[float, float, float]] = {}
    for part in model.parts:
        for shape in part._iter_shapes():
            if shape.color is None:
                rgb = _DEFAULT_COLOR
            else:
                rgb = (float(shape.color[0]), float(shape.color[1]), float(shape.color[2]))
            colors[(part.name, shape.name)] = rgb
    return colors


def _matches(part_name: str, shape_name: str, names: set[str]) -> bool:
    return (
        part_name in names or shape_name in names or f"{part_name}/{shape_name}" in names
    )


def _scene(
    model: ArticulatedObject,
    *,
    only: list[str] | None,
    pose: dict[str, float] | None,
) -> tuple[list[_Piece], dict[tuple[str, str], tuple[float, float, float]]]:
    kernel = MeshCollisionKernel(model, mesh_tolerance=0.0012)
    colors = _color_map(model)
    wanted = set(only) if only else None
    pieces: list[_Piece] = []
    identity: dict[tuple[str, str], tuple[float, float, float]] = {}
    for entry in kernel._all_entries(pose or {}):
        if wanted is not None and not _matches(entry.part_name, entry.shape_name, wanted):
            continue
        mesh = entry.world_mesh
        color = colors.get((entry.part_name, entry.shape_name), _DEFAULT_COLOR)
        pieces.append(
            _Piece(
                name=entry.shape_name,
                vertices=np.asarray(mesh.vertices, dtype=np.float64),
                faces=np.asarray(mesh.faces, dtype=np.int64),
                normals=np.asarray(mesh.vertex_normals, dtype=np.float64),
                color=color,
            )
        )
        identity[(entry.part_name, entry.shape_name)] = color
    if not pieces:
        raise ValueError("no geometry to render; check the 'only' names")
    return pieces, identity


def _framing(
    pieces: list[_Piece],
    *,
    target: Any,
    zoom: float,
    model: ArticulatedObject,
    only: list[str] | None,
    pose: dict[str, float] | None,
) -> tuple[np.ndarray, float]:
    scene = np.vstack([p.vertices for p in pieces])
    focus = scene
    if isinstance(target, str):
        kernel = MeshCollisionKernel(model, mesh_tolerance=0.0012)
        subset = [
            np.asarray(e.world_mesh.vertices)
            for e in kernel._all_entries(pose or {})
            if _matches(e.part_name, e.shape_name, {target})
        ]
        if subset:
            focus = np.vstack(subset)
    elif isinstance(target, (list, tuple)) and len(target) == 3:
        center = np.asarray([float(v) for v in target], dtype=np.float64)
        radius = float((scene.max(0) - scene.min(0)).max()) / 2.0 * max(0.2, float(zoom))
        return center, radius
    center = (focus.max(0) + focus.min(0)) / 2.0
    radius = float((focus.max(0) - focus.min(0)).max()) / 2.0 * 1.1 * max(0.2, float(zoom))
    return center, max(radius, 1e-4)


def _eye(center: np.ndarray, radius: float, azimuth: float, elevation: float) -> np.ndarray:
    az, el = math.radians(azimuth), math.radians(elevation)
    direction = np.array(
        [math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)]
    )
    distance = radius / math.tan(math.radians(_FOV_DEGREES) / 2.0) + radius
    return center + distance * direction


def _usdrecord_png(
    pieces: list[_Piece],
    center: np.ndarray,
    radius: float,
    azimuth: float,
    elevation: float,
    width: int,
) -> bytes:
    from pxr import Gf, Usd, UsdGeom

    tmp = Path(tempfile.mkdtemp(prefix="inspect_view_"))
    try:
        usd_path = tmp / "scene.usda"
        png_path = tmp / "out.png"
        stage = Usd.Stage.CreateNew(str(usd_path))
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.Xform.Define(stage, "/World")
        for index, piece in enumerate(pieces):
            mesh = UsdGeom.Mesh.Define(stage, f"/World/m{index}")
            mesh.CreatePointsAttr([Gf.Vec3f(*map(float, v)) for v in piece.vertices])
            mesh.CreateFaceVertexCountsAttr([3] * len(piece.faces))
            mesh.CreateFaceVertexIndicesAttr([int(x) for f in piece.faces for x in f])
            mesh.CreateDisplayColorAttr([Gf.Vec3f(*piece.color)])
            mesh.CreateNormalsAttr([Gf.Vec3f(*map(float, n)) for n in piece.normals])
            mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)

        eye = _eye(center, radius, azimuth, elevation)
        distance = float(np.linalg.norm(eye - center))
        camera = UsdGeom.Camera.Define(stage, "/World/cam")  # pyright: ignore[reportAttributeAccessIssue]
        transform = (
            Gf.Matrix4d(1)
            .SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*center), Gf.Vec3d(0, 0, 1))
            .GetInverse()
        )
        camera.AddTransformOp().Set(transform)
        near, far = max(distance * 0.001, 1e-4), distance * 10.0
        camera.CreateClippingRangeAttr(Gf.Vec2f(near, far))  # pyright: ignore[reportAttributeAccessIssue]
        aperture = 24.0 * 2.0 * math.tan(math.radians(_FOV_DEGREES) / 2.0)
        camera.CreateFocalLengthAttr(24.0)
        camera.CreateHorizontalApertureAttr(aperture)
        camera.CreateVerticalApertureAttr(aperture)
        stage.GetRootLayer().Save()

        subprocess.run(
            ["usdrecord", "--imageWidth", str(width), "--camera", "/World/cam",
             str(usd_path), str(png_path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return png_path.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _matplotlib_png(
    pieces: list[_Piece], center: np.ndarray, radius: float, azimuth: float, elevation: float
) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(6.5, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    for piece in pieces:
        base = np.asarray(piece.color)
        face_normals = piece.normals[piece.faces].mean(axis=1)
        brightness = 0.45 + 0.55 * np.clip(face_normals @ _LIGHT, 0.0, 1.0)
        face_colors = np.clip(base[None, :] * brightness[:, None], 0.0, 1.0)
        collection = Poly3DCollection(
            piece.vertices[piece.faces], facecolors=face_colors, edgecolor="none"
        )
        collection.set_zsort("average")
        ax.add_collection3d(collection)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=float(elevation), azim=float(azimuth))
    ax.axis("off")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


def _project(
    point: np.ndarray, eye: np.ndarray, center: np.ndarray, size: int
) -> tuple[float, float, float] | None:
    """Project a world point to pixel (x, y, depth) for the usdrecord square camera."""
    from pxr import Gf

    view = Gf.Matrix4d(1).SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*center), Gf.Vec3d(0, 0, 1))
    tanf = math.tan(math.radians(_FOV_DEGREES) / 2.0)
    pc = view.Transform(Gf.Vec3d(*(float(v) for v in point)))
    depth = -pc[2]
    if depth <= 0:
        return None
    px = (pc[0] / (depth * tanf) * 0.5 + 0.5) * size
    py = (1.0 - (pc[1] / (depth * tanf) * 0.5 + 0.5)) * size
    return px, py, depth


def _resolve_probe(
    pieces: list[_Piece], probe: Any
) -> tuple[np.ndarray, str] | None:
    if isinstance(probe, (list, tuple)) and len(probe) == 3:
        point = np.asarray([float(v) for v in probe], dtype=np.float64)
    elif isinstance(probe, str):
        match = next((p for p in pieces if p.name == probe), None)
        if match is None:
            return None
        point = match.vertices.mean(axis=0)
    else:
        return None
    label = f"probe ({point[0]:.3f}, {point[1]:.3f}, {point[2]:.3f})"
    return point, label


def _font() -> Any:
    from PIL import ImageFont

    try:
        from matplotlib import font_manager

        return ImageFont.truetype(font_manager.findfont("DejaVu Sans"), 13)
    except Exception:
        return ImageFont.load_default()


def _separate(boxes: list[dict[str, float]], size: int, *, pad: float = 4.0) -> None:
    """Nudge overlapping label boxes apart along their smaller overlap axis.

    ponytail: O(n^2) per iteration, but n is the shape count (~10-30), so this
    is negligible; swap for a spatial grid only if a model ever has hundreds.
    """
    for _ in range(80):
        moved = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) + pad
                oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) + pad
                if ox <= 0 or oy <= 0:
                    continue
                moved = True
                if oy <= ox:
                    shift = oy / 2.0
                    lo, hi = (a, b) if a["y"] <= b["y"] else (b, a)
                    lo["y"] -= shift
                    hi["y"] += shift
                else:
                    shift = ox / 2.0
                    lo, hi = (a, b) if a["x"] <= b["x"] else (b, a)
                    lo["x"] -= shift
                    hi["x"] += shift
        if not moved:
            break
    for box in boxes:
        box["x"] = max(2.0, min(size - box["w"] - 2.0, box["x"]))
        box["y"] = max(2.0, min(size - box["h"] - 2.0, box["y"]))


def _overlay(
    png: bytes,
    pieces: list[_Piece],
    eye: np.ndarray,
    center: np.ndarray,
    *,
    labels: bool,
    probe: Any,
) -> bytes:
    from PIL import Image, ImageDraw

    image = Image.open(io.BytesIO(png)).convert("RGB")
    size = image.width  # square render
    draw = ImageDraw.Draw(image)
    font = _font()

    def _text_box(text: str) -> tuple[float, float]:
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return right - left, bottom - top

    if labels:
        boxes: list[dict[str, float]] = []
        meta: list[tuple[str, float, float]] = []  # text, anchor x, anchor y
        for piece in pieces:
            projected = _project(piece.vertices.mean(axis=0), eye, center, size)
            if projected is None:
                continue
            ax, ay, depth = projected
            if not (0 <= ax < size and 0 <= ay < size):
                continue
            width, height = _text_box(piece.name)
            boxes.append(
                {"x": ax + 8, "y": ay - height - 8, "w": width, "h": height, "d": depth}
            )
            meta.append((piece.name, ax, ay))
        _separate(boxes, size)
        # Draw far labels first so nearer ones layer on top.
        for box, (text, ax, ay) in sorted(
            zip(boxes, meta, strict=True), key=lambda item: -item[0]["d"]
        ):
            cx, cy = box["x"] + box["w"] / 2.0, box["y"] + box["h"] / 2.0
            draw.line([ax, ay, cx, cy], fill=(150, 150, 110), width=1)
            draw.ellipse([ax - 2, ay - 2, ax + 2, ay + 2], fill=(230, 70, 60))
            draw.rectangle(
                [box["x"] - 3, box["y"] - 2, box["x"] + box["w"] + 3, box["y"] + box["h"] + 2],
                fill=(255, 255, 205),
                outline=(150, 150, 90),
            )
            draw.text((box["x"], box["y"]), text, fill=(20, 20, 20), font=font)

    if probe is not None:
        resolved = _resolve_probe(pieces, probe)
        if resolved is not None:
            projected = _project(resolved[0], eye, center, size)
            if projected is not None:
                px, py, _ = projected
                draw.line([px - 9, py, px + 9, py], fill=(220, 40, 40), width=2)
                draw.line([px, py - 9, px, py + 9], fill=(220, 40, 40), width=2)
                draw.ellipse([px - 5, py - 5, px + 5, py + 5], outline=(220, 40, 40), width=2)
                width, height = _text_box(resolved[1])
                draw.rectangle(
                    [px + 9, py + 6, px + 13 + width, py + 10 + height], fill=(255, 210, 120)
                )
                draw.text((px + 11, py + 8), resolved[1], fill=(20, 20, 20), font=font)

    buffer = io.BytesIO()
    image.save(buffer, format="png")
    return buffer.getvalue()


def render_png(
    model: ArticulatedObject,
    *,
    azimuth: float,
    elevation: float,
    zoom: float,
    target: Any,
    only: list[str] | None,
    pose: dict[str, float] | None,
    labels: bool = True,
    probe: Any = None,
    width: int = 720,
) -> bytes:
    pieces, _ = _scene(model, only=only, pose=pose)
    center, radius = _framing(
        pieces, target=target, zoom=zoom, model=model, only=only, pose=pose
    )
    try:
        png = _usdrecord_png(pieces, center, radius, azimuth, elevation, width)
    except (FileNotFoundError, subprocess.SubprocessError, ImportError, OSError):
        # usdrecord (a system binary needing a GL backend) may be absent, e.g. in CI;
        # fall back to a plain shaded matplotlib render so the tool still works. The
        # label/probe overlay needs the usdrecord camera, so it is skipped there.
        return _matplotlib_png(pieces, center, radius, azimuth, elevation)
    if not labels and probe is None:
        return png
    eye = _eye(center, radius, azimuth, elevation)
    return _overlay(png, pieces, eye, center, labels=labels, probe=probe)


async def run(context: ToolContext, args: dict[str, Any]) -> dict[str, Any]:
    model = _load_model(context.workspace)
    png = render_png(
        model,
        azimuth=float(args.get("azimuth", 45.0)),
        elevation=float(args.get("elevation", 20.0)),
        zoom=float(args.get("zoom", 1.0)),
        target=args.get("target"),
        only=args.get("only"),
        pose=args.get("pose"),
        labels=bool(args.get("labels", True)),
        probe=args.get("probe"),
    )
    return {"image_png_base64": base64.b64encode(png).decode("ascii")}


TOOL = Tool(
    "inspect_view",
    schema(
        "inspect_view",
        (
            "Render the current object to an image and see it, to check visual quality "
            "that compile checks cannot judge -- gaps, mounting blocks, seams, whether a "
            "handle looks molded or a hinge seats. Orbit with azimuth/elevation, frame a "
            "part or shape by name with `target` and tighten with `zoom` (<1 zooms in), "
            "isolate parts with `only`, and actuate joints with `pose` to inspect motion. "
            "Shape names are labelled at their positions so you can see where each is; "
            "set `probe` to a shape name or [x,y,z] to mark that spot and read its "
            "coordinate. Call it after a successful compile and fix what looks wrong."
        ),
        {
            "azimuth": {"type": "number", "description": "Orbit angle in degrees (default 45)."},
            "elevation": {
                "type": "number",
                "description": "Up/down angle in degrees (default 20).",
            },
            "zoom": {
                "type": "number",
                "description": "1.0 fits the target; <1 zooms in (crop), >1 zooms out.",
            },
            "target": {
                "type": ["string", "array"],
                "description": "A part or shape name to frame, or an [x,y,z] point. Default: whole object.",
            },
            "only": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Render only these part or shape names (isolate a region).",
            },
            "pose": {
                "type": "object",
                "description": "Joint name -> value, to actuate articulation before rendering.",
            },
            "labels": {
                "type": "boolean",
                "description": "Overlay shape-name labels at their positions (default true).",
            },
            "probe": {
                "type": ["string", "array"],
                "description": "A shape name or [x,y,z] point to mark with a reticle and its coordinate.",
            },
        },
        [],
    ),
    run,
)
