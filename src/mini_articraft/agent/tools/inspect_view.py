from __future__ import annotations

import base64
import io
import runpy
from pathlib import Path
from typing import Any

import numpy as np

from mini_articraft.agent.tools._core import Tool, ToolContext, schema
from mini_articraft.sdk import ArticulatedObject
from mini_articraft.sdk._collision import MeshCollisionKernel

_DEFAULT_COLOR = (0.70, 0.72, 0.74)


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


def _matches(entry: Any, names: set[str]) -> bool:
    return (
        entry.part_name in names
        or entry.shape_name in names
        or f"{entry.part_name}/{entry.shape_name}" in names
    )


def render_png(
    model: ArticulatedObject,
    *,
    azimuth: float,
    elevation: float,
    zoom: float,
    target: Any,
    only: list[str] | None,
    pose: dict[str, float] | None,
) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    kernel = MeshCollisionKernel(model, mesh_tolerance=0.0012)
    entries = kernel._all_entries(pose or {})
    colors = _color_map(model)

    if only:
        wanted = set(only)
        entries = [entry for entry in entries if _matches(entry, wanted)]
    if not entries:
        raise ValueError("no geometry to render; check the 'only' names")

    fig = plt.figure(figsize=(6.5, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    all_vertices: list[np.ndarray] = []
    for entry in entries:
        rgb = colors.get((entry.part_name, entry.shape_name), _DEFAULT_COLOR)
        mesh = entry.world_mesh
        collection = Poly3DCollection(
            mesh.vertices[mesh.faces], facecolor=rgb, edgecolor="k", linewidths=0.03
        )
        collection.set_zsort("average")
        ax.add_collection3d(collection)
        all_vertices.append(np.asarray(mesh.vertices))

    scene = np.vstack(all_vertices)
    focus = scene
    if isinstance(target, str):
        subset = [
            np.asarray(entry.world_mesh.vertices) for entry in entries if _matches(entry, {target})
        ]
        if subset:
            focus = np.vstack(subset)
    elif isinstance(target, (list, tuple)) and len(target) == 3:
        center = np.asarray([float(v) for v in target], dtype=np.float64)
        radius = float((scene.max(0) - scene.min(0)).max()) / 2.0
        _apply_camera(ax, center, radius, zoom, azimuth, elevation)
        return _to_png(fig, plt)

    center = (focus.max(0) + focus.min(0)) / 2.0
    radius = float((focus.max(0) - focus.min(0)).max()) / 2.0 * 1.1
    _apply_camera(ax, center, radius, zoom, azimuth, elevation)
    return _to_png(fig, plt)


def _apply_camera(ax, center, radius, zoom, azimuth, elevation) -> None:
    radius = max(radius * max(0.05, float(zoom)), 1e-4)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=float(elevation), azim=float(azimuth))
    ax.axis("off")


def _to_png(fig, plt) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()


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
    )
    described = {
        "azimuth": args.get("azimuth", 45.0),
        "elevation": args.get("elevation", 20.0),
        "zoom": args.get("zoom", 1.0),
        "target": args.get("target"),
        "only": args.get("only"),
        "pose": args.get("pose"),
    }
    return {
        "image_png_base64": base64.b64encode(png).decode("ascii"),
        "view": {k: v for k, v in described.items() if v is not None},
    }


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
            "Call it after a successful compile and fix what looks wrong."
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
        },
        [],
    ),
    run,
)
