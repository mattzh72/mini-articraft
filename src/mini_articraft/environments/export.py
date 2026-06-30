from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq

from mini_articraft.sdk.joints import ContinuousLimits, Joint, JointLimits
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
    payload = _object_to_payload(obj)
    payload["files"] = {
        "parts": {name: path.relative_to(root).as_posix() for name, path in parts.items()}
    }
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    return ExportResult(root=root, manifest=manifest, parts=parts)


def _object_to_payload(obj: ArticulatedObject) -> dict[str, object]:
    return {
        "name": obj.name,
        "parts": [
            {"name": part.name, "shape_type": type(part.shape).__name__} for part in obj.parts
        ],
        "joints": [_joint_to_payload(joint) for joint in obj.joints],
    }


def _joint_to_payload(joint: Joint) -> dict[str, object]:
    return {
        "name": joint.name,
        "type": joint.type.value,
        "parent": joint.parent,
        "child": joint.child,
        "origin": {"xyz": joint.origin.xyz, "rpy": joint.origin.rpy},
        "axis": joint.axis,
        "limits": _limits_to_payload(joint.limits),
    }


def _limits_to_payload(limits: JointLimits | ContinuousLimits | None) -> dict[str, float] | None:
    if limits is None:
        return None
    if isinstance(limits, JointLimits):
        return {
            "lower": limits.lower,
            "upper": limits.upper,
            "effort": limits.effort,
            "velocity": limits.velocity,
        }
    return {"effort": limits.effort, "velocity": limits.velocity}


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
