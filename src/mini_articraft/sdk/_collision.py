from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TypeAlias

import fcl
import numpy as np
import trimesh
from build123d.topology import Shape

from mini_articraft.errors import ValidationError
from mini_articraft.sdk.joints import Frame, Joint, JointType
from mini_articraft.sdk.object import ArticulatedObject, Build123dShape

Vec3: TypeAlias = tuple[float, float, float]
Mat4: TypeAlias = np.ndarray


@dataclass(frozen=True)
class ContactInfo:
    position: Vec3 | None
    normal: Vec3 | None
    depth: float | None


@dataclass(frozen=True)
class CollisionQuery:
    part_a: str
    part_b: str
    collided: bool
    contacts: tuple[ContactInfo, ...] = ()

    @property
    def max_depth(self) -> float | None:
        depths = [contact.depth for contact in self.contacts if contact.depth is not None]
        if not depths:
            return None
        return max(depths)


@dataclass(frozen=True)
class DistanceQuery:
    part_a: str
    part_b: str
    distance: float
    collided: bool
    nearest_a: Vec3 | None = None
    nearest_b: Vec3 | None = None
    contacts: tuple[ContactInfo, ...] = ()


@dataclass(frozen=True)
class GeometryConnectivityFinding:
    part: str
    connected: int
    total: int
    disconnected: tuple[str, ...]
    contact_tol: float


@dataclass(frozen=True)
class _PartMesh:
    mesh: trimesh.Trimesh
    fcl_model: object


@dataclass(frozen=True)
class _GeometryComponent:
    name: str
    shape: Shape


@dataclass(frozen=True)
class _CollisionEntry:
    part_name: str
    obj: object


class MeshCollisionKernel:
    def __init__(self, model: ArticulatedObject, *, mesh_tolerance: float) -> None:
        if mesh_tolerance <= 0.0 or not math.isfinite(mesh_tolerance):
            raise ValidationError("mesh_tolerance must be a positive finite number")
        self.model = model
        self.mesh_tolerance = float(mesh_tolerance)
        self._part_mesh_cache: dict[tuple[str, int, float], _PartMesh] = {}
        self._component_cache: dict[tuple[str, int, float], tuple[_GeometryComponent, ...]] = {}

    def part_world_position(
        self,
        part_name: str,
        pose: dict[str, float],
    ) -> Vec3 | None:
        transform = self.world_transforms(pose).get(part_name)
        if transform is None:
            return None
        return _array_to_vec3(transform[:3, 3])

    def part_world_vertices(self, part_name: str, pose: dict[str, float]) -> np.ndarray:
        mesh = self._part_mesh(part_name).mesh
        transform = self.world_transforms(pose).get(part_name)
        if transform is None:
            raise ValidationError(f"unknown part: {part_name!r}")
        return _transform_points(np.asarray(mesh.vertices, dtype=np.float64), transform)

    def world_transforms(self, pose: dict[str, float]) -> dict[str, Mat4]:
        parts = {part.name: part for part in self.model.parts}
        child_joints: dict[str, list[Joint]] = {name: [] for name in parts}
        child_names: set[str] = set()
        for joint in self.model.joints:
            if joint.parent in parts and joint.child in parts:
                child_joints[joint.parent].append(joint)
                child_names.add(joint.child)

        roots = [name for name in parts if name not in child_names]
        transforms: dict[str, Mat4] = {}
        stack = [(root, _identity()) for root in roots]
        while stack:
            part_name, transform = stack.pop()
            transforms[part_name] = transform
            for joint in child_joints.get(part_name, []):
                child_transform = (
                    transform
                    @ _frame_matrix(joint.frame)
                    @ _motion_matrix(
                        joint,
                        float(pose.get(joint.name, 0.0)),
                    )
                )
                stack.append((joint.child, child_transform))
        return transforms

    def collision_between(
        self,
        part_a: str,
        part_b: str,
        pose: dict[str, float],
        *,
        max_contacts: int = 16,
    ) -> CollisionQuery:
        transforms = self.world_transforms(pose)
        entry_a = self._collision_entry(part_a, transforms)
        entry_b = self._collision_entry(part_b, transforms)
        return _collide_entries(entry_a, entry_b, max_contacts=max_contacts)

    def distance_between(
        self,
        part_a: str,
        part_b: str,
        pose: dict[str, float],
        *,
        max_contacts: int = 16,
    ) -> DistanceQuery:
        transforms = self.world_transforms(pose)
        entry_a = self._collision_entry(part_a, transforms)
        entry_b = self._collision_entry(part_b, transforms)
        return _distance_entries(entry_a, entry_b, max_contacts=max_contacts)

    def pair_distances(
        self,
        pose: dict[str, float],
        *,
        max_contacts: int = 16,
    ) -> list[DistanceQuery]:
        transforms = self.world_transforms(pose)
        entries = [self._collision_entry(part.name, transforms) for part in self.model.parts]
        return [
            _distance_entries(entry_a, entry_b, max_contacts=max_contacts)
            for index, entry_a in enumerate(entries)
            for entry_b in entries[index + 1 :]
        ]

    def colliding_pairs(
        self,
        pose: dict[str, float],
        *,
        allowed_pairs: set[tuple[str, str]] | None = None,
        max_contacts: int = 16,
    ) -> list[CollisionQuery]:
        transforms = self.world_transforms(pose)
        entries = [self._collision_entry(part.name, transforms) for part in self.model.parts]
        manager = fcl.DynamicAABBTreeCollisionManager()
        manager.registerObjects([entry.obj for entry in entries])
        manager.setup()

        by_id = {id(entry.obj): entry for entry in entries}
        seen: set[tuple[str, str]] = set()
        found: list[CollisionQuery] = []
        allowed = allowed_pairs or set()
        unmapped_callback_pair = False

        def callback(obj_a: object, obj_b: object, _data: object) -> bool:
            nonlocal unmapped_callback_pair
            entry_a = _entry_for_object(obj_a, entries=entries, by_id=by_id)
            entry_b = _entry_for_object(obj_b, entries=entries, by_id=by_id)
            if entry_a is None or entry_b is None:
                unmapped_callback_pair = True
                return False
            if entry_a.part_name == entry_b.part_name:
                return False
            key = _pair_key(entry_a.part_name, entry_b.part_name)
            if key in seen or key in allowed:
                return False
            seen.add(key)
            query = _collide_entries(entry_a, entry_b, max_contacts=max_contacts)
            if query.collided:
                found.append(query)
            return False

        manager.collide(None, callback)
        if unmapped_callback_pair:
            # python-fcl may hand callbacks wrapper objects that cannot be mapped
            # back to the registered Python objects. Keep the manager call for
            # parity with the FCL path, then recover exact details directly.
            for index, entry_a in enumerate(entries):
                for entry_b in entries[index + 1 :]:
                    key = _pair_key(entry_a.part_name, entry_b.part_name)
                    if key in seen or key in allowed:
                        continue
                    seen.add(key)
                    query = _collide_entries(entry_a, entry_b, max_contacts=max_contacts)
                    if query.collided:
                        found.append(query)
        return found

    def disconnected_geometry_islands(
        self,
        *,
        contact_tol: float,
    ) -> list[GeometryConnectivityFinding]:
        findings: list[GeometryConnectivityFinding] = []
        for part in self.model.parts:
            components = self._geometry_components(part.name)
            if len(components) <= 1:
                continue

            groups, nearest = _component_connectivity(components, contact_tol=contact_tol)
            largest = max(groups, key=lambda group: (len(group), -min(group)))
            if len(largest) == len(components):
                continue

            disconnected: list[str] = []
            for index, component in enumerate(components):
                if index in largest:
                    continue
                nearest_index, distance = nearest.get(index, (None, None))
                if nearest_index is None or distance is None:
                    disconnected.append(component.name)
                    continue
                disconnected.append(
                    f"{component.name} nearest={components[nearest_index].name} "
                    f"distance={distance:.6g}"
                )

            findings.append(
                GeometryConnectivityFinding(
                    part=part.name,
                    connected=len(largest),
                    total=len(components),
                    disconnected=tuple(disconnected),
                    contact_tol=contact_tol,
                )
            )
        return findings

    def _collision_entry(self, part_name: str, transforms: dict[str, Mat4]) -> _CollisionEntry:
        part_mesh = self._part_mesh(part_name)
        transform = transforms.get(part_name)
        if transform is None:
            raise ValidationError(f"unknown part: {part_name!r}")
        obj = fcl.CollisionObject(part_mesh.fcl_model, _fcl_transform(transform))
        return _CollisionEntry(part_name=part_name, obj=obj)

    def _part_mesh(self, part_name: str) -> _PartMesh:
        part = self.model.get_part(part_name)
        cache_key = (part.name, id(part.shape), self.mesh_tolerance)
        cached = self._part_mesh_cache.get(cache_key)
        if cached is not None:
            return cached

        shape = _build123d_shape(part.shape)
        mesh = _shape_to_mesh(shape, self.mesh_tolerance)
        bvh = _mesh_to_bvh(mesh)
        cached = _PartMesh(mesh=mesh, fcl_model=bvh)
        self._part_mesh_cache[cache_key] = cached
        return cached

    def _geometry_components(self, part_name: str) -> tuple[_GeometryComponent, ...]:
        part = self.model.get_part(part_name)
        cache_key = (part.name, id(part.shape), self.mesh_tolerance)
        cached = self._component_cache.get(cache_key)
        if cached is not None:
            return cached

        components: list[_GeometryComponent] = []
        for index, shape in enumerate(_build123d_components(part.shape), start=1):
            components.append(
                _GeometryComponent(
                    name=f"solid_{index:03d}",
                    shape=shape,
                )
            )
        cached = tuple(components)
        self._component_cache[cache_key] = cached
        return cached


def _component_connectivity(
    components: tuple[_GeometryComponent, ...],
    *,
    contact_tol: float,
) -> tuple[list[set[int]], dict[int, tuple[int, float]]]:
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(components))}
    nearest: dict[int, tuple[int, float]] = {}
    for index, component in enumerate(components):
        for other_index in range(index + 1, len(components)):
            other = components[other_index]
            distance = float(component.shape.distance(other.shape))
            if distance <= contact_tol:
                adjacency[index].add(other_index)
                adjacency[other_index].add(index)
            _remember_nearest(nearest, index, other_index, distance)
            _remember_nearest(nearest, other_index, index, distance)

    remaining = set(range(len(components)))
    groups: list[set[int]] = []
    while remaining:
        start = min(remaining)
        group: set[int] = set()
        stack = [start]
        remaining.remove(start)
        while stack:
            current = stack.pop()
            group.add(current)
            for neighbor in sorted(adjacency[current]):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                stack.append(neighbor)
        groups.append(group)
    return groups, nearest


def _remember_nearest(
    nearest: dict[int, tuple[int, float]],
    index: int,
    other_index: int,
    distance: float,
) -> None:
    current = nearest.get(index)
    if current is None or distance < current[1]:
        nearest[index] = (other_index, distance)


def _collide_entries(
    entry_a: _CollisionEntry,
    entry_b: _CollisionEntry,
    *,
    max_contacts: int,
) -> CollisionQuery:
    request = fcl.CollisionRequest(
        num_max_contacts=max(1, int(max_contacts)),
        enable_contact=True,
    )
    result = fcl.CollisionResult()
    collided = int(fcl.collide(entry_a.obj, entry_b.obj, request, result)) > 0
    contacts = tuple(_contact_info(contact) for contact in getattr(result, "contacts", []) or [])
    return CollisionQuery(
        part_a=entry_a.part_name,
        part_b=entry_b.part_name,
        collided=collided,
        contacts=contacts,
    )


def _distance_entries(
    entry_a: _CollisionEntry,
    entry_b: _CollisionEntry,
    *,
    max_contacts: int,
) -> DistanceQuery:
    collision = _collide_entries(entry_a, entry_b, max_contacts=max_contacts)
    if collision.collided:
        return DistanceQuery(
            part_a=entry_a.part_name,
            part_b=entry_b.part_name,
            distance=0.0,
            collided=True,
            contacts=collision.contacts,
        )

    request = fcl.DistanceRequest(enable_nearest_points=True)
    result = fcl.DistanceResult()
    distance = float(fcl.distance(entry_a.obj, entry_b.obj, request, result))
    nearest_points = getattr(result, "nearest_points", None)
    nearest_a = None
    nearest_b = None
    if isinstance(nearest_points, (list, tuple)) and len(nearest_points) == 2:
        nearest_a = _array_to_vec3(nearest_points[0])
        nearest_b = _array_to_vec3(nearest_points[1])
    return DistanceQuery(
        part_a=entry_a.part_name,
        part_b=entry_b.part_name,
        distance=distance,
        collided=False,
        nearest_a=nearest_a,
        nearest_b=nearest_b,
    )


def _entry_for_object(
    obj: object,
    *,
    entries: list[_CollisionEntry],
    by_id: dict[int, _CollisionEntry],
) -> _CollisionEntry | None:
    entry = by_id.get(id(obj))
    if entry is not None:
        return entry
    for candidate in entries:
        if candidate.obj is obj or candidate.obj == obj:
            return candidate
    return None


def _build123d_shape(model: Build123dShape) -> Shape:
    if isinstance(model, Shape):
        return model
    raise ValidationError("Unsupported build123d model type. Expected build123d Shape.")


def _build123d_components(model: Build123dShape) -> list[Shape]:
    shape = _build123d_shape(model)
    try:
        solids: list[Shape] = [solid for solid in shape.solids() if solid is not None]
    except Exception:
        solids = []
    if solids:
        return solids
    return [shape]


def _shape_to_mesh(shape: Shape, tolerance: float) -> trimesh.Trimesh:
    vertices, faces = shape.tessellate(tolerance)
    if not vertices or not faces:
        raise ValidationError("build123d shape produced an empty collision mesh")
    mesh = trimesh.Trimesh(
        vertices=np.asarray([[v.X, v.Y, v.Z] for v in vertices], dtype=np.float64),
        faces=np.asarray(faces, dtype=np.int32),
        process=False,
    )
    if mesh.vertices.size == 0 or mesh.faces.size == 0:
        raise ValidationError("build123d shape produced an empty collision mesh")
    return mesh


def _mesh_to_bvh(mesh: trimesh.Trimesh) -> object:
    vertices = np.ascontiguousarray(mesh.vertices, dtype=np.float64)
    faces = np.ascontiguousarray(mesh.faces, dtype=np.int32)
    model = fcl.BVHModel()
    model.beginModel(len(vertices), len(faces))
    model.addSubModel(vertices, faces)
    model.endModel()
    return model


def _identity() -> Mat4:
    return np.identity(4, dtype=np.float64)


def _frame_matrix(frame: Frame) -> Mat4:
    matrix = _rpy_matrix(frame.rpy)
    matrix[:3, 3] = np.asarray(frame.xyz, dtype=np.float64)
    return matrix


def _motion_matrix(joint: Joint, value: float) -> Mat4:
    if joint.type == JointType.FIXED:
        return _identity()
    axis = _normalize(joint.axis)
    if joint.type == JointType.PRISMATIC:
        matrix = _identity()
        matrix[:3, 3] = axis * value
        return matrix
    return _axis_angle_matrix(axis, value)


def _rpy_matrix(rpy: Vec3) -> Mat4:
    roll, pitch, yaw = rpy
    cx, sx = math.cos(roll), math.sin(roll)
    cy, sy = math.cos(pitch), math.sin(pitch)
    cz, sz = math.cos(yaw), math.sin(yaw)
    rx = np.array(
        [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]],
        dtype=np.float64,
    )
    ry = np.array(
        [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]],
        dtype=np.float64,
    )
    rz = np.array(
        [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    matrix = _identity()
    matrix[:3, :3] = rz @ ry @ rx
    return matrix


def _axis_angle_matrix(axis: np.ndarray, angle: float) -> Mat4:
    x, y, z = axis
    c = math.cos(angle)
    s = math.sin(angle)
    one_c = 1.0 - c
    rotation = np.array(
        [
            [c + x * x * one_c, x * y * one_c - z * s, x * z * one_c + y * s],
            [y * x * one_c + z * s, c + y * y * one_c, y * z * one_c - x * s],
            [z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c],
        ],
        dtype=np.float64,
    )
    matrix = _identity()
    matrix[:3, :3] = rotation
    return matrix


def _normalize(axis: Vec3) -> np.ndarray:
    vector = np.asarray(axis, dtype=np.float64)
    length = float(np.linalg.norm(vector))
    if length <= 0.0:
        raise ValidationError("joint axis must be non-zero")
    return vector / length


def _fcl_transform(matrix: Mat4) -> object:
    rotation = np.ascontiguousarray(matrix[:3, :3], dtype=np.float64)
    translation = np.ascontiguousarray(matrix[:3, 3], dtype=np.float64)
    return fcl.Transform(rotation, translation)


def _transform_points(points: np.ndarray, matrix: Mat4) -> np.ndarray:
    hom = np.column_stack([points, np.ones(len(points), dtype=np.float64)])
    transformed = hom @ matrix.T
    return np.asarray(transformed[:, :3], dtype=np.float64)


def _contact_info(contact: object) -> ContactInfo:
    return ContactInfo(
        position=_array_to_vec3(getattr(contact, "pos", None)),
        normal=_array_to_vec3(getattr(contact, "normal", None)),
        depth=_optional_float(getattr(contact, "penetration_depth", None)),
    )


def _array_to_vec3(value: object) -> Vec3 | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if len(array) < 3:
        return None
    return (float(array[0]), float(array[1]), float(array[2]))


def _optional_float(value: object) -> float | None:
    if not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def _pair_key(part_a: str, part_b: str) -> tuple[str, str]:
    return (part_a, part_b) if part_a <= part_b else (part_b, part_a)
