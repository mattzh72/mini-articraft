from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Sequence

import numpy as np
import trimesh

from mini_articraft.errors import ValidationError
from mini_articraft.sdk.mesh import LoftGeometry, MeshGeometry, boolean_union

Vec3 = tuple[float, float, float]
RepairMode = Literal["off", "mesh"]


def _as_vec3(value: Sequence[float], *, name: str) -> Vec3:
    if len(value) != 3:
        raise ValidationError(f"{name} must have 3 values")
    try:
        point = (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must have 3 numeric values") from exc
    if not np.isfinite(point).all():
        raise ValidationError(f"{name} values must be finite")
    return point


def _normalize_loop(points: Sequence[Sequence[float]], *, name: str) -> tuple[Vec3, ...]:
    result: list[Vec3] = []
    for point in points:
        value = _as_vec3(point, name=f"{name}[]")
        if not result or value != result[-1]:
            result.append(value)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    if len(result) < 3:
        raise ValidationError(f"{name} must contain at least 3 distinct points")
    return tuple(result)


@dataclass(frozen=True)
class LoftSection:
    points: tuple[Vec3, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", _normalize_loop(self.points, name="section.points"))


@dataclass(frozen=True)
class SectionLoftSpec:
    sections: tuple[LoftSection, ...]
    path: tuple[Vec3, ...] | None = None
    cap: bool = True
    symmetry: Literal["mirror_yz"] | None = None
    repair: RepairMode = "mesh"

    def __post_init__(self) -> None:
        sections = tuple(
            section if isinstance(section, LoftSection) else LoftSection(tuple(section))
            for section in self.sections
        )
        if len(sections) < 2:
            raise ValidationError("SectionLoftSpec requires at least two sections")
        object.__setattr__(self, "sections", sections)
        if self.path is not None:
            path = tuple(_as_vec3(point, name="path[]") for point in self.path)
            if len(path) < 2:
                raise ValidationError("path must contain at least two points")
            object.__setattr__(self, "path", path)
        if self.symmetry not in {None, "mirror_yz"}:
            raise ValidationError("symmetry must be 'mirror_yz' or None")
        if self.repair not in {"off", "mesh"}:
            raise ValidationError("repair must be 'off' or 'mesh'")


def _coerce_spec(
    value: SectionLoftSpec | Sequence[LoftSection | Sequence[Sequence[float]]],
) -> SectionLoftSpec:
    if isinstance(value, SectionLoftSpec):
        return value
    return SectionLoftSpec(
        sections=tuple(
            section if isinstance(section, LoftSection) else LoftSection(tuple(section))
            for section in value
        )
    )


def _resample_loop(points: Sequence[Vec3], count: int) -> list[Vec3]:
    if len(points) == count:
        return list(points)
    closed = [*points, points[0]]
    lengths = [0.0]
    for start, end in zip(closed, closed[1:]):
        lengths.append(lengths[-1] + float(np.linalg.norm(np.subtract(end, start))))
    total = lengths[-1]
    if total <= 1e-12:
        raise ValidationError("loft section perimeter must be non-zero")
    result: list[Vec3] = []
    edge = 0
    for index in range(count):
        target = total * index / count
        while edge + 1 < len(lengths) and lengths[edge + 1] < target:
            edge += 1
        span = lengths[edge + 1] - lengths[edge]
        amount = 0.0 if span <= 1e-12 else (target - lengths[edge]) / span
        result.append(
            tuple(
                closed[edge][axis] + (closed[edge + 1][axis] - closed[edge][axis]) * amount
                for axis in range(3)
            )
        )
    return result


def _loop_normal(points: Sequence[Vec3]) -> np.ndarray:
    center = np.mean(np.asarray(points, dtype=np.float64), axis=0)
    normal = np.zeros(3, dtype=np.float64)
    for start, end in zip(points, [*points[1:], points[0]]):
        normal += np.cross(np.subtract(start, center), np.subtract(end, center))
    length = float(np.linalg.norm(normal))
    if length <= 1e-12:
        raise ValidationError("loft section must enclose a non-zero planar area")
    return normal / length


def _align_loop(reference: Sequence[Vec3], candidate: Sequence[Vec3]) -> list[Vec3]:
    values = list(candidate)
    if float(np.dot(_loop_normal(reference), _loop_normal(values))) < 0.0:
        values.reverse()
    reference_centered = np.asarray(reference, dtype=np.float64) - np.mean(reference, axis=0)
    candidate_centered = np.asarray(values, dtype=np.float64) - np.mean(values, axis=0)
    shift = min(
        range(len(values)),
        key=lambda index: float(
            np.sum((reference_centered - np.roll(candidate_centered, -index, axis=0)) ** 2)
        ),
    )
    return values[shift:] + values[:shift]


def _sample_polyline(points: Sequence[Vec3], amount: float) -> Vec3:
    lengths = [0.0]
    for start, end in zip(points, points[1:]):
        lengths.append(lengths[-1] + float(np.linalg.norm(np.subtract(end, start))))
    target = lengths[-1] * amount
    index = 0
    while index + 1 < len(lengths) and lengths[index + 1] < target:
        index += 1
    span = lengths[index + 1] - lengths[index]
    local = 0.0 if span <= 1e-12 else (target - lengths[index]) / span
    return tuple(
        points[index][axis] + (points[index + 1][axis] - points[index][axis]) * local
        for axis in range(3)
    )


def _path_adjusted_sections(spec: SectionLoftSpec, count: int) -> list[list[Vec3]]:
    sections = [_resample_loop(section.points, count) for section in spec.sections]
    aligned_sections = [sections[0]]
    for section in sections[1:]:
        aligned_sections.append(_align_loop(aligned_sections[-1], section))
    sections = aligned_sections
    path = spec.path
    if path is None:
        return sections
    start, end = path[0], path[-1]
    adjusted = []
    divisor = max(1, len(sections) - 1)
    for index, section in enumerate(sections):
        amount = index / divisor
        path_point = _sample_polyline(path, amount)
        baseline = tuple(start[axis] + (end[axis] - start[axis]) * amount for axis in range(3))
        residual = tuple(path_point[axis] - baseline[axis] for axis in range(3))
        adjusted.append(
            [tuple(point[axis] + residual[axis] for axis in range(3)) for point in section]
        )
    return adjusted


def _repair_mesh(geometry: MeshGeometry) -> MeshGeometry:
    if not geometry.vertices or not geometry.faces:
        return geometry.copy()
    mesh = trimesh.Trimesh(
        vertices=np.asarray(geometry.vertices, dtype=np.float64),
        faces=np.asarray(geometry.faces, dtype=np.int64),
        process=False,
    )
    mesh.update_faces(mesh.unique_faces() & mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    if not mesh.is_watertight:
        mesh.merge_vertices()
        mesh.update_faces(mesh.unique_faces() & mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=False)
    return MeshGeometry.from_trimesh(mesh)


def section_loft(
    spec: SectionLoftSpec | Sequence[LoftSection | Sequence[Sequence[float]]],
    /,
    **overrides: object,
) -> MeshGeometry:
    value = _coerce_spec(spec)
    if overrides:
        value = replace(value, **overrides)
    count = max(len(section.points) for section in value.sections)
    profiles = _path_adjusted_sections(value, count)
    geometry = LoftGeometry(profiles, cap=value.cap, closed=True)
    if value.symmetry == "mirror_yz":
        mirrored = geometry.copy().scale(-1.0, 1.0, 1.0)
        if geometry.is_watertight:
            geometry = boolean_union(geometry, mirrored)
        else:
            geometry.merge(mirrored)
    if value.repair == "mesh":
        geometry = _repair_mesh(geometry)
    return geometry


def repair_loft(
    geometry_or_spec: MeshGeometry
    | SectionLoftSpec
    | Sequence[LoftSection | Sequence[Sequence[float]]],
    /,
    *,
    repair: RepairMode = "mesh",
) -> MeshGeometry:
    if repair not in {"off", "mesh"}:
        raise ValidationError("repair must be 'off' or 'mesh'")
    if isinstance(geometry_or_spec, MeshGeometry):
        return geometry_or_spec.copy() if repair == "off" else _repair_mesh(geometry_or_spec)
    return section_loft(_coerce_spec(geometry_or_spec), repair=repair)


__all__ = [
    "LoftSection",
    "SectionLoftSpec",
    "repair_loft",
    "section_loft",
]
