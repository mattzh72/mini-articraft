from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from numbers import Integral
from typing import TYPE_CHECKING, TypeAlias, cast

import numpy as np
import trimesh

from mini_articraft.errors import ValidationError

if TYPE_CHECKING:
    from build123d.topology import Shape
    from manifold3d import DoubleNx2

Vec2: TypeAlias = tuple[float, float]
Vec3: TypeAlias = tuple[float, float, float]
Face: TypeAlias = tuple[int, int, int]

_EPS = 1e-10


def _vec2(value: Sequence[float], *, name: str = "point") -> Vec2:
    if len(value) != 2:
        raise ValueError(f"{name} must have 2 elements")
    point = (float(value[0]), float(value[1]))
    if not all(math.isfinite(component) for component in point):
        raise ValueError(f"{name} values must be finite")
    return point


def _vec3(value: Sequence[float], *, name: str = "point") -> Vec3:
    if len(value) != 3:
        raise ValueError(f"{name} must have 3 elements")
    point = (float(value[0]), float(value[1]), float(value[2]))
    if not all(math.isfinite(component) for component in point):
        raise ValueError(f"{name} values must be finite")
    return point


def _v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_scale(value: Vec3, scale: float) -> Vec3:
    return (value[0] * scale, value[1] * scale, value[2] * scale)


def _v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _v_norm(value: Vec3) -> float:
    return math.sqrt(_v_dot(value, value))


def _v_normalize(value: Vec3) -> Vec3:
    length = _v_norm(value)
    if length <= _EPS:
        raise ValueError("cannot normalize a zero-length vector")
    return _v_scale(value, 1.0 / length)


def _v_lerp(a: Vec3, b: Vec3, amount: float) -> Vec3:
    return _v_add(a, _v_scale(_v_sub(b, a), amount))


def _same2(a: Vec2, b: Vec2, tolerance: float = 1e-9) -> bool:
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def _same3(a: Vec3, b: Vec3, tolerance: float = 1e-9) -> bool:
    return all(abs(a[index] - b[index]) <= tolerance for index in range(3))


def _profile_2d(profile: Iterable[Sequence[float]], *, minimum: int = 3) -> list[Vec2]:
    points: list[Vec2] = []
    for index, raw in enumerate(profile):
        point = _vec2(raw, name=f"profile[{index}]")
        if not points or not _same2(points[-1], point):
            points.append(point)
    if len(points) > 1 and _same2(points[0], points[-1]):
        points.pop()
    if len(points) < minimum:
        raise ValueError(f"profile must contain at least {minimum} distinct points")
    return points


def _profile_3d(profile: Iterable[Sequence[float]], *, minimum: int = 2) -> list[Vec3]:
    points: list[Vec3] = []
    for index, raw in enumerate(profile):
        point = _vec3(raw, name=f"profile[{index}]")
        if not points or not _same3(points[-1], point):
            points.append(point)
    if len(points) > 1 and _same3(points[0], points[-1]):
        points.pop()
    if len(points) < minimum:
        raise ValueError(f"profile must contain at least {minimum} distinct points")
    return points


def _polygon_area(points: Sequence[Vec2]) -> float:
    return 0.5 * sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )


def _ensure_ccw(points: list[Vec2]) -> list[Vec2]:
    area = _polygon_area(points)
    if abs(area) <= _EPS:
        raise ValueError("profile area must be non-zero")
    return points if area > 0.0 else list(reversed(points))


def _point_on_segment(point: Vec2, start: Vec2, end: Vec2, tolerance: float = 1e-9) -> bool:
    cross = (end[0] - start[0]) * (point[1] - start[1]) - (end[1] - start[1]) * (
        point[0] - start[0]
    )
    if abs(cross) > tolerance:
        return False
    dot = (point[0] - start[0]) * (end[0] - start[0]) + (point[1] - start[1]) * (end[1] - start[1])
    squared_length = (end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2
    return -tolerance <= dot <= squared_length + tolerance


def _point_in_polygon(point: Vec2, polygon: Sequence[Vec2]) -> bool:
    inside = False
    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]
        if _point_on_segment(point, start, end):
            return True
        if (start[1] > point[1]) == (end[1] > point[1]):
            continue
        crossing_x = start[0] + (point[1] - start[1]) * (end[0] - start[0]) / (end[1] - start[1])
        if crossing_x >= point[0]:
            inside = not inside
    return inside


def _cross_z(a: Vec2, b: Vec2, c: Vec2) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_triangle(point: Vec2, a: Vec2, b: Vec2, c: Vec2) -> bool:
    values = (_cross_z(a, b, point), _cross_z(b, c, point), _cross_z(c, a, point))
    return all(value >= -1e-10 for value in values) or all(value <= 1e-10 for value in values)


def _triangulate_simple(points: list[Vec2]) -> list[Face]:
    points = _ensure_ccw(points)
    indices = list(range(len(points)))
    triangles: list[Face] = []
    guard = len(indices) ** 2
    while len(indices) > 3 and guard > 0:
        guard -= 1
        for cursor, current in enumerate(indices):
            previous = indices[cursor - 1]
            following = indices[(cursor + 1) % len(indices)]
            if _cross_z(points[previous], points[current], points[following]) <= _EPS:
                continue
            if any(
                _point_in_triangle(
                    points[index], points[previous], points[current], points[following]
                )
                for index in indices
                if index not in {previous, current, following}
            ):
                continue
            triangles.append((previous, current, following))
            del indices[cursor]
            break
        else:
            raise ValueError("failed to triangulate profile; ensure it is a simple polygon")
    if len(indices) == 3:
        triangles.append((indices[0], indices[1], indices[2]))
    return triangles


def _triangulate_with_holes(
    outer: list[Vec2], holes: list[list[Vec2]]
) -> tuple[list[Vec2], list[Face]]:
    outer = _ensure_ccw(outer)
    holes = [_ensure_ccw(hole) for hole in holes]
    if not holes:
        return outer, _triangulate_simple(outer)
    for hole in holes:
        center = (
            sum(point[0] for point in hole) / len(hole),
            sum(point[1] for point in hole) / len(hole),
        )
        if not _point_in_polygon(center, outer):
            raise ValueError("hole profile must lie inside the outer profile")

    rings = [outer, *(list(reversed(hole)) for hole in holes)]
    flat = [point for ring in rings for point in ring]
    try:
        import manifold3d

        polygons = cast(
            "list[DoubleNx2[int]]",
            [np.asarray(ring, dtype=np.float64) for ring in rings],
        )
        raw = manifold3d.triangulate(polygons, epsilon=1e-9)
        triangles: list[Face] = [
            (int(face[0]), int(face[1]), int(face[2])) for face in np.asarray(raw)
        ]
        return flat, triangles
    except ImportError:
        pass
    except Exception as exc:
        raise ValueError("failed to triangulate profiles with holes") from exc

    raise RuntimeError(
        "profiles with holes require the `manifold3d` package; install project dependencies"
    )


@dataclass
class MeshGeometry:
    """A small, mutable triangle mesh in meters."""

    vertices: list[Vec3] = field(default_factory=list)
    faces: list[Face] = field(default_factory=list)

    def __post_init__(self) -> None:
        try:
            self.vertices = [
                _vec3(vertex, name=f"vertices[{index}]")
                for index, vertex in enumerate(self.vertices)
            ]
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        normalized_faces: list[Face] = []
        for index, face in enumerate(self.faces):
            if len(face) != 3:
                raise ValidationError(f"faces[{index}] must contain exactly 3 indices")
            if any(not isinstance(value, Integral) or isinstance(value, bool) for value in face):
                raise ValidationError(f"faces[{index}] indices must be integers")
            normalized_faces.append((int(face[0]), int(face[1]), int(face[2])))
        self.faces = normalized_faces
        self.validate()

    def validate(self) -> None:
        for index, vertex in enumerate(self.vertices):
            try:
                valid = len(vertex) == 3 and all(math.isfinite(float(value)) for value in vertex)
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise ValidationError(f"vertices[{index}] must contain 3 finite values")
        for index, face in enumerate(self.faces):
            if len(face) != 3:
                raise ValidationError(f"faces[{index}] must contain exactly 3 indices")
            if any(not isinstance(value, Integral) or isinstance(value, bool) for value in face):
                raise ValidationError(f"faces[{index}] indices must be integers")
            if len(set(face)) != 3:
                raise ValidationError(f"faces[{index}] must reference 3 distinct vertices")
            if min(face) < 0 or max(face) >= len(self.vertices):
                raise ValidationError(f"faces[{index}] references a vertex outside the mesh")

    @classmethod
    def from_trimesh(cls, mesh: trimesh.Trimesh, *, process: bool = False) -> MeshGeometry:
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError("mesh must be trimesh.Trimesh")
        if process:
            mesh = mesh.copy()
            mesh.process(validate=True)
        return cls(
            vertices=[
                (float(vertex[0]), float(vertex[1]), float(vertex[2])) for vertex in mesh.vertices
            ],
            faces=[(int(face[0]), int(face[1]), int(face[2])) for face in mesh.faces],
        )

    def to_trimesh(self, *, process: bool = False) -> trimesh.Trimesh:
        self.validate()
        return trimesh.Trimesh(
            vertices=np.asarray(self.vertices, dtype=np.float64),
            faces=np.asarray(self.faces, dtype=np.int64),
            process=process,
            validate=process,
        )

    @property
    def bounds(self) -> tuple[Vec3, Vec3]:
        if not self.vertices:
            raise ValidationError("mesh has no vertices")
        self.validate()
        values = np.asarray(self.vertices, dtype=np.float64)
        return (
            (
                float(values[:, 0].min()),
                float(values[:, 1].min()),
                float(values[:, 2].min()),
            ),
            (
                float(values[:, 0].max()),
                float(values[:, 1].max()),
                float(values[:, 2].max()),
            ),
        )

    @property
    def is_watertight(self) -> bool:
        return bool(self.faces) and bool(self.to_trimesh().is_watertight)

    def copy(self) -> MeshGeometry:
        return MeshGeometry(vertices=list(self.vertices), faces=list(self.faces))

    def add_vertex(self, x: float, y: float, z: float) -> int:
        vertex = _vec3((x, y, z), name="vertex")
        self.vertices.append(vertex)
        return len(self.vertices) - 1

    def add_face(self, a: int, b: int, c: int) -> None:
        face = (a, b, c)
        if any(not isinstance(value, Integral) or isinstance(value, bool) for value in face):
            raise ValidationError("face indices must be integers")
        normalized = (int(a), int(b), int(c))
        if len(set(normalized)) != 3:
            raise ValidationError("face must reference 3 distinct vertices")
        if min(normalized) < 0 or max(normalized) >= len(self.vertices):
            raise ValidationError("face references a vertex outside the mesh")
        self.faces.append(normalized)

    def merge(self, other: MeshGeometry) -> MeshGeometry:
        if not isinstance(other, MeshGeometry):
            raise TypeError("other must be MeshGeometry")
        other.validate()
        offset = len(self.vertices)
        self.vertices.extend(other.vertices)
        self.faces.extend((a + offset, b + offset, c + offset) for a, b, c in other.faces)
        return self

    def translate(self, dx: float, dy: float, dz: float) -> MeshGeometry:
        delta = _vec3((dx, dy, dz), name="translation")
        self.vertices = [_v_add(vertex, delta) for vertex in self.vertices]
        return self

    def scale(self, sx: float, sy: float | None = None, sz: float | None = None) -> MeshGeometry:
        values = (float(sx), float(sx if sy is None else sy), float(sx if sz is None else sz))
        if not all(math.isfinite(value) for value in values):
            raise ValueError("scale values must be finite")
        if any(abs(value) <= _EPS for value in values):
            raise ValueError("scale values must be non-zero")
        self.vertices = [
            (vertex[0] * values[0], vertex[1] * values[1], vertex[2] * values[2])
            for vertex in self.vertices
        ]
        if values[0] * values[1] * values[2] < 0.0:
            self.faces = [(a, c, b) for a, b, c in self.faces]
        return self

    def rotate(
        self,
        axis: Sequence[float],
        angle: float,
        *,
        origin: Sequence[float] = (0.0, 0.0, 0.0),
    ) -> MeshGeometry:
        direction = _v_normalize(_vec3(axis, name="axis"))
        pivot = _vec3(origin, name="origin")
        angle = float(angle)
        if not math.isfinite(angle):
            raise ValueError("angle must be finite")
        cosine = math.cos(angle)
        sine = math.sin(angle)

        def rotate_vertex(vertex: Vec3) -> Vec3:
            relative = _v_sub(vertex, pivot)
            rotated = _v_add(
                _v_add(_v_scale(relative, cosine), _v_scale(_v_cross(direction, relative), sine)),
                _v_scale(direction, _v_dot(direction, relative) * (1.0 - cosine)),
            )
            return _v_add(pivot, rotated)

        self.vertices = [rotate_vertex(vertex) for vertex in self.vertices]
        return self

    def rotate_x(self, angle: float) -> MeshGeometry:
        return self.rotate((1.0, 0.0, 0.0), angle)

    def rotate_y(self, angle: float) -> MeshGeometry:
        return self.rotate((0.0, 1.0, 0.0), angle)

    def rotate_z(self, angle: float) -> MeshGeometry:
        return self.rotate((0.0, 0.0, 1.0), angle)

    def to_obj(self) -> str:
        self.validate()
        lines = ["o mesh"]
        lines.extend(f"v {x:.9f} {y:.9f} {z:.9f}" for x, y, z in self.vertices)
        lines.extend(f"f {a + 1} {b + 1} {c + 1}" for a, b, c in self.faces)
        return "\n".join([*lines, ""])


def _from_created(mesh: trimesh.Trimesh) -> MeshGeometry:
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=True)
    return MeshGeometry.from_trimesh(mesh)


class BoxGeometry(MeshGeometry):
    def __init__(self, size: Sequence[float]):
        dimensions = _vec3(size, name="size")
        if any(value <= 0.0 for value in dimensions):
            raise ValueError("box size values must be positive")
        created = _from_created(trimesh.creation.box(extents=dimensions))
        super().__init__(created.vertices, created.faces)


class CylinderGeometry(MeshGeometry):
    def __init__(
        self, radius: float, height: float, *, radial_segments: int = 48, closed: bool = True
    ):
        radius, height = float(radius), float(height)
        if radius <= 0.0 or height <= 0.0:
            raise ValueError("cylinder radius and height must be positive")
        sections = max(3, int(radial_segments))
        if closed:
            created = _from_created(
                trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
            )
            super().__init__(created.vertices, created.faces)
            return
        vertices: list[Vec3] = []
        faces: list[Face] = []
        half = height * 0.5
        for z in (-half, half):
            vertices.extend(
                (
                    radius * math.cos(2.0 * math.pi * index / sections),
                    radius * math.sin(2.0 * math.pi * index / sections),
                    z,
                )
                for index in range(sections)
            )
        for index in range(sections):
            following = (index + 1) % sections
            faces.extend(
                (
                    (index, following, sections + following),
                    (index, sections + following, sections + index),
                )
            )
        super().__init__(vertices, faces)


class ConeGeometry(MeshGeometry):
    def __init__(
        self, radius: float, height: float, *, radial_segments: int = 48, closed: bool = True
    ):
        radius, height = float(radius), float(height)
        if radius <= 0.0 or height <= 0.0:
            raise ValueError("cone radius and height must be positive")
        sections = max(3, int(radial_segments))
        created = trimesh.creation.cone(radius=radius, height=height, sections=sections)
        created.apply_translation((0.0, 0.0, -height * 0.5))
        if not closed:
            normals = created.face_normals
            keep = np.abs(normals[:, 2]) < 0.999
            created.update_faces(keep)
            created.remove_unreferenced_vertices()
        converted = _from_created(created)
        super().__init__(converted.vertices, converted.faces)


class SphereGeometry(MeshGeometry):
    def __init__(self, radius: float, *, width_segments: int = 48, height_segments: int = 24):
        radius = float(radius)
        if radius <= 0.0:
            raise ValueError("sphere radius must be positive")
        count = (max(8, int(width_segments)), max(4, int(height_segments)))
        created = _from_created(trimesh.creation.uv_sphere(radius=radius, count=count))
        super().__init__(created.vertices, created.faces)


class DomeGeometry(MeshGeometry):
    def __init__(
        self,
        radius: float | Sequence[float],
        *,
        radial_segments: int = 48,
        height_segments: int = 20,
        closed: bool = True,
    ):
        if isinstance(radius, (int, float)):
            radii = (float(radius),) * 3
        else:
            radii = _vec3(radius, name="radius")
        if any(value <= 0.0 for value in radii):
            raise ValueError("dome radii must be positive")
        radial_segments = max(3, int(radial_segments))
        height_segments = max(1, int(height_segments))
        vertices: list[Vec3] = [(0.0, 0.0, radii[2])]
        for row in range(1, height_segments + 1):
            phi = 0.5 * math.pi * row / height_segments
            for column in range(radial_segments):
                theta = 2.0 * math.pi * column / radial_segments
                vertices.append(
                    (
                        radii[0] * math.sin(phi) * math.cos(theta),
                        radii[1] * math.sin(phi) * math.sin(theta),
                        radii[2] * math.cos(phi),
                    )
                )
        faces: list[Face] = [
            (0, 1 + column, 1 + (column + 1) % radial_segments) for column in range(radial_segments)
        ]
        for row in range(height_segments - 1):
            start = 1 + row * radial_segments
            following_start = start + radial_segments
            for column in range(radial_segments):
                following = (column + 1) % radial_segments
                faces.extend(
                    (
                        (start + column, following_start + column, following_start + following),
                        (start + column, following_start + following, start + following),
                    )
                )
        if closed:
            center = len(vertices)
            vertices.append((0.0, 0.0, 0.0))
            start = 1 + (height_segments - 1) * radial_segments
            faces.extend(
                (center, start + (column + 1) % radial_segments, start + column)
                for column in range(radial_segments)
            )
        super().__init__(vertices, faces)


class CapsuleGeometry(MeshGeometry):
    def __init__(
        self,
        radius: float,
        length: float,
        *,
        radial_segments: int = 48,
        height_segments: int = 14,
    ):
        radius, length = float(radius), float(length)
        if radius <= 0.0 or length < 0.0:
            raise ValueError("capsule radius must be positive and length non-negative")
        if length <= _EPS:
            sphere = SphereGeometry(
                radius,
                width_segments=radial_segments,
                height_segments=max(4, height_segments * 2),
            )
            super().__init__(sphere.vertices, sphere.faces)
            return
        created = trimesh.creation.capsule(
            height=length,
            radius=radius,
            count=(max(8, int(radial_segments)), max(4, int(height_segments))),
        )
        converted = _from_created(created)
        super().__init__(converted.vertices, converted.faces)


class TorusGeometry(MeshGeometry):
    def __init__(
        self,
        radius: float,
        tube: float,
        *,
        radial_segments: int = 24,
        tubular_segments: int = 64,
    ):
        radius, tube = float(radius), float(tube)
        if radius <= 0.0 or tube <= 0.0:
            raise ValueError("torus radius and tube must be positive")
        created = _from_created(
            trimesh.creation.torus(
                major_radius=radius,
                minor_radius=tube,
                major_sections=max(3, int(tubular_segments)),
                minor_sections=max(3, int(radial_segments)),
            )
        )
        super().__init__(created.vertices, created.faces)


def _cap_connector(
    start: Vec2, end: Vec2, mode: str, samples: int, *, outward_z: float
) -> list[Vec2]:
    if mode not in {"flat", "round"}:
        raise ValueError("lathe cap mode must be 'flat' or 'round'")
    if mode == "flat":
        return [start, end]
    samples = max(2, int(samples))
    distance = math.hypot(start[0] - end[0], start[1] - end[1])
    radial_direction = 1.0 if start[0] >= end[0] else -1.0
    control = (
        (start[0] + end[0]) * 0.5 + radial_direction * distance * 0.35,
        (start[1] + end[1]) * 0.5 + math.copysign(distance * 0.5, outward_z),
    )
    return [
        (
            (1.0 - amount) ** 2 * start[0]
            + 2.0 * (1.0 - amount) * amount * control[0]
            + amount**2 * end[0],
            (1.0 - amount) ** 2 * start[1]
            + 2.0 * (1.0 - amount) * amount * control[1]
            + amount**2 * end[1],
        )
        for amount in (index / samples for index in range(samples + 1))
    ]


class LatheGeometry(MeshGeometry):
    @classmethod
    def from_shell_profiles(
        cls,
        outer_profile: Iterable[Sequence[float]],
        inner_profile: Iterable[Sequence[float]],
        *,
        segments: int = 48,
        start_cap: str = "flat",
        end_cap: str = "flat",
        lip_samples: int = 6,
    ) -> LatheGeometry:
        outer = _profile_2d(outer_profile, minimum=2)
        inner = _profile_2d(inner_profile, minimum=2)
        axis_direction = 1.0 if outer[-1][1] + inner[-1][1] >= outer[0][1] + inner[0][1] else -1.0
        end = _cap_connector(outer[-1], inner[-1], end_cap, lip_samples, outward_z=axis_direction)
        start = _cap_connector(
            inner[0], outer[0], start_cap, lip_samples, outward_z=-axis_direction
        )
        profile = [*outer, *end[1:], *reversed(inner[:-1]), *start[1:]]
        return cls(profile, segments=segments, closed=True)

    def __init__(
        self, profile: Iterable[Sequence[float]], *, segments: int = 48, closed: bool = True
    ):
        points = _profile_2d(profile, minimum=3) if closed else _profile_2d(profile, minimum=2)
        if closed:
            points = _ensure_ccw(points)
        if any(radius < -_EPS for radius, _z in points):
            raise ValueError("lathe profile radii must be non-negative")
        revolve_points = [*points, points[0]] if closed else points
        created = trimesh.creation.revolve(
            np.asarray(revolve_points, dtype=np.float64),
            sections=max(3, int(segments)),
            cap=False,
        )
        converted = _from_created(created) if closed else MeshGeometry.from_trimesh(created)
        super().__init__(converted.vertices, converted.faces)


class LoftGeometry(MeshGeometry):
    def __init__(
        self,
        profiles: Iterable[Iterable[Sequence[float]]],
        *,
        cap: bool = True,
        closed: bool = True,
    ):
        rings = [_profile_3d(profile, minimum=3 if closed else 2) for profile in profiles]
        if len(rings) < 2:
            raise ValueError("loft requires at least two profiles")
        count = len(rings[0])
        if any(len(ring) != count for ring in rings):
            raise ValueError("loft profiles must have the same point count")

        def ring_center(ring: Sequence[Vec3]) -> Vec3:
            return (
                sum(point[0] for point in ring) / len(ring),
                sum(point[1] for point in ring) / len(ring),
                sum(point[2] for point in ring) / len(ring),
            )

        def ring_normal(ring: Sequence[Vec3]) -> Vec3:
            center = ring_center(ring)
            normal = (0.0, 0.0, 0.0)
            for index, point in enumerate(ring):
                following = ring[(index + 1) % len(ring)]
                normal = _v_add(
                    normal,
                    _v_cross(_v_sub(point, center), _v_sub(following, center)),
                )
            if _v_norm(normal) <= _EPS:
                raise ValueError("loft profiles must enclose a non-zero planar area")
            return _v_normalize(normal)

        if closed:
            path_direction = _v_sub(ring_center(rings[-1]), ring_center(rings[0]))
            if _v_norm(path_direction) <= _EPS:
                raise ValueError("first and last loft profiles must have distinct centers")
            reference_normal = ring_normal(rings[0])
            if _v_dot(reference_normal, path_direction) < 0.0:
                rings = [list(reversed(ring)) for ring in rings]
                reference_normal = _v_scale(reference_normal, -1.0)
            for index in range(1, len(rings)):
                if _v_dot(ring_normal(rings[index]), reference_normal) < 0.0:
                    rings[index] = list(reversed(rings[index]))

        vertices = [point for ring in rings for point in ring]
        faces: list[Face] = []
        segment_count = count if closed else count - 1
        for ring_index in range(len(rings) - 1):
            start = ring_index * count
            following_start = start + count
            for point_index in range(segment_count):
                following = (point_index + 1) % count
                faces.extend(
                    (
                        (start + point_index, start + following, following_start + following),
                        (
                            start + point_index,
                            following_start + following,
                            following_start + point_index,
                        ),
                    )
                )
        if cap and closed:
            for ring_index, neighbor_index, offset in (
                (0, 1, 0),
                (len(rings) - 1, len(rings) - 2, (len(rings) - 1) * count),
            ):
                ring = rings[ring_index]
                normal = _v_cross(_v_sub(ring[1], ring[0]), _v_sub(ring[2], ring[0]))
                axis = max(range(3), key=lambda index: abs(normal[index]))
                projected: list[Vec2]
                if axis == 0:
                    projected = [(point[1], point[2]) for point in ring]
                elif axis == 1:
                    projected = [(point[0], point[2]) for point in ring]
                else:
                    projected = [(point[0], point[1]) for point in ring]
                order = list(range(count))
                if _polygon_area(projected) < 0.0:
                    order.reverse()
                triangles = [
                    (order[a], order[b], order[c])
                    for a, b, c in _triangulate_simple([projected[index] for index in order])
                ]
                center = ring_center(ring)
                neighbor = ring_center(rings[neighbor_index])
                outward = _v_sub(center, neighbor)
                for a, b, c in triangles:
                    face = (offset + a, offset + b, offset + c)
                    face_normal = _v_cross(
                        _v_sub(vertices[face[1]], vertices[face[0]]),
                        _v_sub(vertices[face[2]], vertices[face[0]]),
                    )
                    faces.append(
                        (face[2], face[1], face[0]) if _v_dot(face_normal, outward) < 0.0 else face
                    )
        super().__init__(vertices, faces)


class ExtrudeGeometry(MeshGeometry):
    @classmethod
    def centered(
        cls,
        profile: Iterable[Sequence[float]],
        height: float,
        *,
        cap: bool = True,
        closed: bool = True,
    ) -> ExtrudeGeometry:
        return cls(profile, height, cap=cap, center=True, closed=closed)

    @classmethod
    def from_z0(
        cls,
        profile: Iterable[Sequence[float]],
        height: float,
        *,
        cap: bool = True,
        closed: bool = True,
    ) -> ExtrudeGeometry:
        return cls(profile, height, cap=cap, center=False, closed=closed)

    def __init__(
        self,
        profile: Iterable[Sequence[float]],
        height: float,
        *,
        cap: bool = True,
        center: bool = True,
        closed: bool = True,
    ):
        height = float(height)
        if height <= 0.0:
            raise ValueError("extrude height must be positive")
        points = _ensure_ccw(_profile_2d(profile))
        z0 = -height * 0.5 if center else 0.0
        loft = LoftGeometry(
            [[(x, y, z0) for x, y in points], [(x, y, z0 + height) for x, y in points]],
            cap=cap and closed,
            closed=closed,
        )
        super().__init__(loft.vertices, loft.faces)


class ExtrudeWithHolesGeometry(MeshGeometry):
    def __init__(
        self,
        outer_profile: Iterable[Sequence[float]],
        hole_profiles: Iterable[Iterable[Sequence[float]]],
        height: float,
        *,
        cap: bool = True,
        center: bool = True,
        closed: bool = True,
    ):
        height = float(height)
        if height <= 0.0:
            raise ValueError("extrude height must be positive")
        outer = _ensure_ccw(_profile_2d(outer_profile))
        holes = [_ensure_ccw(_profile_2d(profile)) for profile in hole_profiles]
        if not holes:
            plain = ExtrudeGeometry(outer, height, cap=cap, center=center, closed=closed)
            super().__init__(plain.vertices, plain.faces)
            return
        z0 = -height * 0.5 if center else 0.0
        z1 = z0 + height
        vertices: list[Vec3] = []
        faces: list[Face] = []
        bottom_indices: list[int] = []
        top_indices: list[int] = []
        for ring, inward in ((outer, False), *((hole, True) for hole in holes)):
            oriented_ring = list(reversed(ring)) if inward else ring
            start = len(vertices)
            vertices.extend((x, y, z0) for x, y in oriented_ring)
            vertices.extend((x, y, z1) for x, y in oriented_ring)
            count = len(oriented_ring)
            bottom_indices.extend(range(start, start + count))
            top_indices.extend(range(start + count, start + 2 * count))
            for index in range(count):
                following = (index + 1) % count
                faces.extend(
                    (
                        (start + index, start + following, start + count + following),
                        (start + index, start + count + following, start + count + index),
                    )
                )
        if cap and closed:
            flat, triangles = _triangulate_with_holes(outer, holes)
            if len(flat) != len(bottom_indices):
                raise RuntimeError("hole triangulation returned an unexpected vertex layout")
            faces.extend(
                (bottom_indices[c], bottom_indices[b], bottom_indices[a]) for a, b, c in triangles
            )
            faces.extend((top_indices[a], top_indices[b], top_indices[c]) for a, b, c in triangles)
        super().__init__(vertices, faces)


def build123d_to_mesh(
    shape: Shape, *, tolerance: float = 0.0001, angular_tolerance: float = 0.1
) -> MeshGeometry:
    """Tessellate a build123d shape, including its current Location, into a mesh."""

    from build123d.topology import Shape

    if not isinstance(shape, Shape):
        raise TypeError("shape must be a build123d Shape")
    if (
        tolerance <= 0.0
        or angular_tolerance <= 0.0
        or not math.isfinite(tolerance)
        or not math.isfinite(angular_tolerance)
    ):
        raise ValueError("tessellation tolerances must be positive")
    try:
        validity = shape.is_valid
        if not (validity() if callable(validity) else validity):
            raise ValidationError("build123d shape is not valid")
    except AttributeError:
        pass
    vertices, faces = shape.tessellate(float(tolerance), float(angular_tolerance))
    if not vertices or not faces:
        raise ValidationError("build123d shape tessellated to an empty mesh")
    geometry = MeshGeometry(
        vertices=[(float(vertex.X), float(vertex.Y), float(vertex.Z)) for vertex in vertices],
        faces=[(int(face[0]), int(face[1]), int(face[2])) for face in faces],
    )
    mesh = geometry.to_trimesh(process=True)
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=True)
    return MeshGeometry.from_trimesh(mesh)


__all__ = [
    "BoxGeometry",
    "CapsuleGeometry",
    "ConeGeometry",
    "CylinderGeometry",
    "DomeGeometry",
    "ExtrudeGeometry",
    "ExtrudeWithHolesGeometry",
    "LatheGeometry",
    "LoftGeometry",
    "MeshGeometry",
    "SphereGeometry",
    "TorusGeometry",
    "build123d_to_mesh",
]
