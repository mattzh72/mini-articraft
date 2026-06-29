from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from mini_articraft.sdk.object import ArticulatedObject, CadQueryShape


@dataclass(frozen=True)
class ExportResult:
    root: Path
    manifest: Path
    parts: dict[str, Path]


def export_object(
    obj: ArticulatedObject,
    output_dir: Path | str,
    *,
    part_format: str = "step",
) -> ExportResult:
    """Export CadQuery part files and a JSON manifest."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    obj.validate()

    suffix = _normalize_part_format(part_format)
    parts_dir = root / "parts"
    parts: dict[str, Path] = {}
    for part in obj.parts:
        path = parts_dir / f"{_safe_filename(part.name)}.{suffix}"
        _export_cadquery(part.shape, path)
        parts[part.name] = path

    manifest = root / "model.json"
    payload = obj.to_dict()
    payload["files"] = {
        "parts": {name: path.relative_to(root).as_posix() for name, path in parts.items()}
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    return ExportResult(root=root, manifest=manifest, parts=parts)


def _normalize_part_format(value: str) -> str:
    suffix = value.strip().lower().lstrip(".")
    if suffix not in {"step", "stp", "stl"}:
        raise ValueError("part_format must be one of: step, stp, stl")
    return suffix


def _safe_filename(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return name.strip("._") or "part"


def _export_cadquery(model: CadQueryShape, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(model, cq.Assembly):
        model.save(str(path))
        return
    cq.exporters.export(_coerce_shape(model), str(path))


def _coerce_shape(model: CadQueryShape) -> cq.Shape:
    if isinstance(model, cq.Shape):
        return model
    if isinstance(model, cq.Workplane):
        values = list(model.vals())
        if not values:
            raise TypeError("CadQuery Workplane produced no exportable shape")
        if not all(isinstance(value, cq.Shape) for value in values):
            raise TypeError("CadQuery Workplane produced non-shape objects")
        if len(values) == 1:
            return values[0]
        return cq.Compound.makeCompound(values)
    raise TypeError(
        "Unsupported CadQuery model type. Expected cadquery.Shape, Workplane, or Assembly."
    )
