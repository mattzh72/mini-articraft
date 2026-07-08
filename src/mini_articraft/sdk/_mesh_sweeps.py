from __future__ import annotations

import math
from typing import Iterable, Sequence

from mini_articraft.sdk._mesh_core import (
    _EPS,
    MeshGeometry,
    SphereGeometry,
    Vec2,
    Vec3,
    _ensure_ccw,
    _profile_2d,
    _triangulate_simple,
    _v_add,
    _v_cross,
    _v_dot,
    _v_lerp,
    _v_norm,
    _v_normalize,
    _v_scale,
    _v_sub,
)
from mini_articraft.sdk._mesh_profiles import (
    sample_arc_3d,
    sample_catmull_rom_spline_3d,
    sample_cubic_bezier_spline_3d,
)


def _path_points(path: Iterable[Sequence[float]], *, minimum: int = 2) -> list[Vec3]:
    result: list[Vec3] = []
    for raw in path:
        if len(raw) != 3:
            raise ValueError("path points must have 3 values")
        point = (float(raw[0]), float(raw[1]), float(raw[2]))
        if not all(math.isfinite(value) for value in point):
            raise ValueError("path points must be finite")
        if not result or _v_norm(_v_sub(point, result[-1])) > _EPS:
            result.append(point)
    if len(result) < minimum:
        raise ValueError(f"path requires at least {minimum} distinct points")
    return result


def _validated_up_hint(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("up_hint must have 3 values")
    hint = (float(value[0]), float(value[1]), float(value[2]))
    if not all(math.isfinite(component) for component in hint) or _v_norm(hint) <= _EPS:
        raise ValueError("up_hint must be finite and non-zero")
    return hint


class SweepGeometry(MeshGeometry):
    def __init__(
        self,
        profile: Iterable[Sequence[float]],
        path: Iterable[Sequence[float]],
        *,
        cap: bool = False,
        closed: bool = True,
    ):
        sweep = PipeGeometry(profile, path, cap=cap, closed=closed)
        super().__init__(sweep.vertices, sweep.faces)


def _tangents(path: Sequence[Vec3]) -> list[Vec3]:
    result = []
    for index in range(len(path)):
        if index == 0:
            direction = _v_sub(path[1], path[0])
        elif index == len(path) - 1:
            direction = _v_sub(path[-1], path[-2])
        else:
            direction = _v_sub(path[index + 1], path[index - 1])
        result.append(_v_normalize(direction))
    return result


def _initial_frame(tangent: Vec3, up_hint: Vec3) -> tuple[Vec3, Vec3]:
    up = _v_normalize(up_hint)
    if abs(_v_dot(up, tangent)) > 0.95:
        up = (0.0, 1.0, 0.0) if abs(tangent[1]) < 0.95 else (1.0, 0.0, 0.0)
    normal = _v_normalize(_v_cross(up, tangent))
    return normal, _v_normalize(_v_cross(tangent, normal))


class PipeGeometry(MeshGeometry):
    """Sweep a profile along a path using a parallel-transport style frame."""

    def __init__(
        self,
        profile: Iterable[Sequence[float]],
        path: Iterable[Sequence[float]],
        *,
        cap: bool = False,
        closed: bool = True,
        path_closed: bool = False,
        up_hint: Vec3 = (0.0, 0.0, 1.0),
    ):
        profile_points = (
            _ensure_ccw(_profile_2d(profile)) if closed else _profile_2d(profile, minimum=2)
        )
        path_values = _path_points(path)
        up_hint = _validated_up_hint(up_hint)
        if path_closed:
            if _v_norm(_v_sub(path_values[0], path_values[-1])) > _EPS:
                path_values.append(path_values[0])
            cap = False
        tangent_values = _tangents(path_values)
        normal, binormal = _initial_frame(tangent_values[0], up_hint)
        normals = [normal]
        binormals = [binormal]
        for tangent in tangent_values[1:]:
            projected = _v_sub(normals[-1], _v_scale(tangent, _v_dot(normals[-1], tangent)))
            if _v_norm(projected) <= _EPS:
                projected = _v_cross(binormals[-1], tangent)
            normal = _v_normalize(projected)
            normals.append(normal)
            binormals.append(_v_normalize(_v_cross(tangent, normal)))
        if path_closed:
            normals[-1], binormals[-1] = normals[0], binormals[0]

        rings: list[list[Vec3]] = []
        for index, point in enumerate(path_values):
            rings.append(
                [
                    _v_add(
                        point,
                        _v_add(_v_scale(normals[index], x), _v_scale(binormals[index], y)),
                    )
                    for x, y in profile_points
                ]
            )
        count = len(profile_points)
        vertices = [point for ring in rings for point in ring]
        faces: list[tuple[int, int, int]] = []
        segment_count = count if closed else count - 1
        for ring_index in range(len(rings) - 1):
            start = ring_index * count
            following_start = start + count
            for index in range(segment_count):
                following = (index + 1) % count
                faces.extend(
                    (
                        (start + index, start + following, following_start + following),
                        (start + index, following_start + following, following_start + index),
                    )
                )
        if cap and closed:
            triangles = _triangulate_simple(profile_points)
            end_offset = (len(rings) - 1) * count
            faces.extend((c, b, a) for a, b, c in triangles)
            faces.extend((end_offset + a, end_offset + b, end_offset + c) for a, b, c in triangles)
        super().__init__(vertices, faces)


class ArcPipeGeometry(MeshGeometry):
    def __init__(
        self,
        profile: Iterable[Sequence[float]],
        *,
        start_point: Vec3,
        center: Vec3,
        normal: Vec3,
        angle: float,
        arc_segments: int = 20,
        cap: bool = False,
        closed: bool = True,
        up_hint: Vec3 = (0.0, 0.0, 1.0),
    ):
        pipe = PipeGeometry(
            profile,
            sample_arc_3d(
                start_point=start_point,
                center=center,
                normal=normal,
                angle=angle,
                segments=arc_segments,
            ),
            cap=cap,
            closed=closed,
            up_hint=up_hint,
        )
        super().__init__(pipe.vertices, pipe.faces)


def _rounded_centerline(
    points: list[Vec3], *, mode: str, radius: float, segments: int, closed: bool
) -> list[Vec3]:
    if mode not in {"miter", "bevel", "fillet"}:
        raise ValueError("corner_mode must be 'miter', 'bevel', or 'fillet'")
    if radius <= _EPS or mode == "miter" or len(points) < 3:
        return points
    ring = points[:-1] if closed and _v_norm(_v_sub(points[0], points[-1])) <= _EPS else points
    output: list[Vec3] = []
    count = len(ring)
    indices = range(count) if closed else range(1, count - 1)
    if not closed:
        output.append(ring[0])
    for index in indices:
        previous = ring[(index - 1) % count]
        corner = ring[index]
        following = ring[(index + 1) % count]
        incoming_length = _v_norm(_v_sub(corner, previous))
        outgoing_length = _v_norm(_v_sub(following, corner))
        trim = min(float(radius), incoming_length * 0.45, outgoing_length * 0.45)
        if trim <= _EPS:
            output.append(corner)
            continue
        before = _v_lerp(corner, previous, trim / incoming_length)
        after = _v_lerp(corner, following, trim / outgoing_length)
        output.append(before)
        if mode == "bevel":
            output.append(after)
        else:
            for sample in range(1, max(2, int(segments)) + 1):
                amount = sample / max(2, int(segments))
                inverse = 1.0 - amount
                output.append(
                    tuple(
                        inverse**2 * before[axis]
                        + 2.0 * inverse * amount * corner[axis]
                        + amount**2 * after[axis]
                        for axis in range(3)
                    )
                )
    if not closed:
        output.append(ring[-1])
    else:
        output.append(output[0])
    return output


class WirePolylineGeometry(MeshGeometry):
    def __init__(
        self,
        points: Iterable[Sequence[float]],
        *,
        radius: float,
        radial_segments: int = 16,
        closed_path: bool = False,
        cap_ends: bool = False,
        corner_mode: str = "fillet",
        corner_radius: float = 0.0,
        corner_segments: int = 8,
        up_hint: Vec3 = (0.0, 0.0, 1.0),
        min_segment_length: float = 1e-6,
    ):
        radius = float(radius)
        if radius <= 0.0 or not math.isfinite(radius):
            raise ValueError("radius must be positive")
        if radial_segments < 6:
            raise ValueError("radial_segments must be at least 6")
        corner_radius = float(corner_radius)
        min_segment_length = float(min_segment_length)
        if corner_radius < 0.0 or not math.isfinite(corner_radius):
            raise ValueError("corner_radius must be finite and non-negative")
        if corner_segments < 2:
            raise ValueError("corner_segments must be at least 2")
        if min_segment_length <= 0.0 or not math.isfinite(min_segment_length):
            raise ValueError("min_segment_length must be finite and positive")
        raw = _path_points(points)
        filtered = [raw[0]]
        for point in raw[1:]:
            if _v_norm(_v_sub(point, filtered[-1])) >= min_segment_length:
                filtered.append(point)
        if closed_path and _v_norm(_v_sub(filtered[0], filtered[-1])) > _EPS:
            filtered.append(filtered[0])
        centerline = _rounded_centerline(
            filtered,
            mode=corner_mode,
            radius=corner_radius,
            segments=corner_segments,
            closed=closed_path,
        )
        profile = [
            (
                radius * math.cos(2.0 * math.pi * index / radial_segments),
                radius * math.sin(2.0 * math.pi * index / radial_segments),
            )
            for index in range(radial_segments)
        ]
        pipe = PipeGeometry(
            profile,
            centerline,
            cap=cap_ends and not closed_path,
            path_closed=closed_path,
            up_hint=up_hint,
        )
        super().__init__(pipe.vertices, pipe.faces)


def wire_from_points(
    points: Iterable[Sequence[float]],
    *,
    radius: float,
    radial_segments: int = 16,
    closed_path: bool = False,
    cap_ends: bool = False,
    corner_mode: str = "fillet",
    corner_radius: float = 0.0,
    corner_segments: int = 8,
    up_hint: Vec3 = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry:
    return WirePolylineGeometry(
        points,
        radius=radius,
        radial_segments=radial_segments,
        closed_path=closed_path,
        cap_ends=cap_ends,
        corner_mode=corner_mode,
        corner_radius=corner_radius,
        corner_segments=corner_segments,
        up_hint=up_hint,
        min_segment_length=min_segment_length,
    )


def _sample_spline(
    points: Iterable[Vec3],
    *,
    spline: str,
    samples_per_segment: int,
    closed: bool,
    alpha: float,
) -> list[Vec3]:
    values = list(points)
    key = spline.strip().lower().replace("-", "_")
    if key in {"catmullrom", "catmull_rom"}:
        return sample_catmull_rom_spline_3d(
            values,
            samples_per_segment=samples_per_segment,
            closed=closed,
            alpha=alpha,
        )
    if key in {"bezier", "cubic_bezier", "cubicbezier"}:
        sampled = sample_cubic_bezier_spline_3d(values, samples_per_segment=samples_per_segment)
        if closed and _v_norm(_v_sub(sampled[0], sampled[-1])) > _EPS:
            raise ValueError("a closed Bezier spline must end where it starts")
        return sampled
    raise ValueError("spline must be 'catmull_rom' or 'bezier'")


def tube_from_spline_points(
    points: Iterable[Vec3],
    *,
    radius: float,
    samples_per_segment: int = 12,
    closed_spline: bool = False,
    spline: str = "catmull_rom",
    alpha: float = 0.5,
    radial_segments: int = 16,
    cap_ends: bool = True,
    up_hint: Vec3 = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry:
    return wire_from_points(
        _sample_spline(
            points,
            spline=spline,
            samples_per_segment=samples_per_segment,
            closed=closed_spline,
            alpha=alpha,
        ),
        radius=radius,
        radial_segments=radial_segments,
        closed_path=closed_spline,
        cap_ends=cap_ends,
        corner_mode="miter",
        up_hint=up_hint,
        min_segment_length=min_segment_length,
    )


def sweep_profile_along_spline(
    points: Iterable[Vec3],
    *,
    profile: Iterable[Vec2],
    samples_per_segment: int = 12,
    closed_spline: bool = False,
    spline: str = "catmull_rom",
    alpha: float = 0.5,
    cap_profile: bool = True,
    up_hint: Vec3 = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
) -> MeshGeometry:
    min_segment_length = float(min_segment_length)
    if min_segment_length <= 0.0 or not math.isfinite(min_segment_length):
        raise ValueError("min_segment_length must be finite and positive")
    centerline = _sample_spline(
        points,
        spline=spline,
        samples_per_segment=samples_per_segment,
        closed=closed_spline,
        alpha=alpha,
    )
    centerline = _path_points(centerline)
    if any(
        _v_norm(_v_sub(centerline[index], centerline[index - 1])) < min_segment_length
        for index in range(1, len(centerline))
    ):
        raise ValueError("spline contains segments shorter than min_segment_length")
    return PipeGeometry(
        profile,
        centerline,
        cap=cap_profile and not closed_spline,
        path_closed=closed_spline,
        up_hint=up_hint,
    )


def tube_network_from_paths(
    paths: Iterable[Iterable[Vec3]],
    *,
    radius: float,
    radial_segments: int = 16,
    cap_ends: bool = True,
    corner_mode: str = "fillet",
    corner_radius: float = 0.0,
    corner_segments: int = 8,
    up_hint: Vec3 = (0.0, 0.0, 1.0),
    min_segment_length: float = 1e-6,
    shared_node_radius: float | None = None,
) -> MeshGeometry:
    path_values = [_path_points(path) for path in paths]
    if not path_values:
        raise ValueError("tube network requires at least one path")
    radius = float(radius)
    node_radius = radius if shared_node_radius is None else float(shared_node_radius)
    if (
        radius <= 0.0
        or node_radius < 0.0
        or not math.isfinite(radius)
        or not math.isfinite(node_radius)
    ):
        raise ValueError(
            "tube and node radii must be finite and non-negative, with a positive tube radius"
        )
    solids = [
        WirePolylineGeometry(
            path,
            radius=radius,
            radial_segments=radial_segments,
            cap_ends=cap_ends,
            corner_mode=corner_mode,
            corner_radius=corner_radius,
            corner_segments=corner_segments,
            up_hint=up_hint,
            min_segment_length=min_segment_length,
        )
        for path in path_values
    ]
    nodes: dict[tuple[int, int, int], tuple[Vec3, int]] = {}
    step = max(float(min_segment_length), _EPS)
    for path in path_values:
        for point in path:
            key = tuple(round(value / step) for value in point)
            previous = nodes.get(key)
            nodes[key] = (point, 1 if previous is None else previous[1] + 1)
    for point, occurrences in nodes.values():
        if occurrences < 2 or node_radius <= 0.0:
            continue
        solids.append(
            SphereGeometry(
                node_radius,
                width_segments=max(12, radial_segments),
                height_segments=max(8, radial_segments // 2),
            ).translate(*point)
        )
    if not solids:
        raise ValueError("tube network produced no geometry")
    if not cap_ends:
        result = MeshGeometry()
        for solid in solids:
            result.merge(solid)
        return result

    from mini_articraft.sdk._mesh_boolean import _boolean_union_many

    try:
        return _boolean_union_many(solids)
    except ValueError as exc:
        raise ValueError("tube network could not form one closed manifold solid") from exc


__all__ = [
    "ArcPipeGeometry",
    "PipeGeometry",
    "SweepGeometry",
    "WirePolylineGeometry",
    "sweep_profile_along_spline",
    "tube_from_spline_points",
    "tube_network_from_paths",
    "wire_from_points",
]
