from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import ClassVar, Iterator

from mini_articraft.errors import ValidationError
from mini_articraft.sdk._collision import CollisionQuery, DistanceQuery, MeshCollisionKernel, Vec3
from mini_articraft.sdk.joints import Joint, coerce_part_name
from mini_articraft.sdk.object import ArticulatedObject, PartRef

DEFAULT_MESH_TOLERANCE = 0.001
DEFAULT_CONTACT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class TestFailure:
    __test__: ClassVar[bool] = False

    name: str
    details: str


@dataclass(frozen=True)
class AllowedOverlap:
    link_a: str
    link_b: str
    reason: str
    elem_a: str | None = None
    elem_b: str | None = None


@dataclass(frozen=True)
class CollisionFinding:
    link_a: str
    link_b: str
    contacts: int
    max_depth: float | None = None
    normal: Vec3 | None = None
    position: Vec3 | None = None


@dataclass(frozen=True)
class DistanceFinding:
    link_a: str
    link_b: str
    distance: float
    nearest_a: Vec3 | None = None
    nearest_b: Vec3 | None = None
    collided: bool = False


@dataclass(frozen=True)
class TestReport:
    __test__: ClassVar[bool] = False

    passed: bool
    checks_run: int
    checks: tuple[str, ...]
    failures: tuple[TestFailure, ...]
    warnings: tuple[str, ...] = ()
    allowances: tuple[str, ...] = ()
    allowed_isolated_parts: tuple[str, ...] = ()
    allowed_overlaps: tuple[AllowedOverlap, ...] = ()


@dataclass
class TestContext:
    __test__: ClassVar[bool] = False

    model: ArticulatedObject
    seed: int = 0
    mesh_tolerance: float = DEFAULT_MESH_TOLERANCE

    checks_run: int = 0
    _checks: list[str] = field(default_factory=list)
    _failures: list[TestFailure] = field(default_factory=list)
    _warnings: list[str] = field(default_factory=list)
    _allowances: list[str] = field(default_factory=list)
    _allowed_isolated_parts: dict[str, str] = field(default_factory=dict)
    _allowed_overlaps: list[AllowedOverlap] = field(default_factory=list)
    _pose: dict[str, float] = field(default_factory=dict)
    _kernel_cache: MeshCollisionKernel | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, ArticulatedObject):
            raise ValidationError("TestContext model must be an ArticulatedObject")
        self.mesh_tolerance = float(self.mesh_tolerance)
        if self.mesh_tolerance <= 0.0 or not math.isfinite(self.mesh_tolerance):
            raise ValidationError("mesh_tolerance must be a positive finite number")

    def report(self) -> TestReport:
        failures = tuple(self._failures)
        return TestReport(
            passed=not failures,
            checks_run=int(self.checks_run),
            checks=tuple(self._checks),
            failures=failures,
            warnings=tuple(self._warnings),
            allowances=tuple(self._allowances),
            allowed_isolated_parts=tuple(self._allowed_isolated_parts),
            allowed_overlaps=tuple(self._allowed_overlaps),
        )

    def check(self, name: str, ok: bool, details: str = "") -> bool:
        return self._record(str(name), bool(ok), str(details or ""))

    def fail(self, name: str, details: str) -> bool:
        return self._record(str(name), False, str(details or ""))

    def warn(self, text: str) -> None:
        text = str(text or "").strip()
        if text:
            self._warnings.append(text)

    def allow_overlap(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        reason: str,
        elem_a: str | None = None,
        elem_b: str | None = None,
    ) -> None:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        link_a_name, link_b_name = _pair_key(link_a_name, link_b_name)
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("allow_overlap requires a non-empty reason")
        allowed = AllowedOverlap(link_a_name, link_b_name, reason, elem_a, elem_b)
        self._allowed_overlaps.append(allowed)
        elem_text = ""
        if elem_a is not None or elem_b is not None:
            elem_text = f", elem_a={elem_a!r}, elem_b={elem_b!r}"
        self._allowances.append(
            f"allow_overlap({link_a_name!r}, {link_b_name!r}{elem_text}): {reason}"
        )

    def allow_isolated_part(self, part: PartRef, *, reason: str) -> None:
        part_name = _part_name(part, field="part")
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("allow_isolated_part requires a non-empty reason")
        self._allowed_isolated_parts[part_name] = reason
        self._allowances.append(f"allow_isolated_part({part_name!r}): {reason}")

    @contextmanager
    def pose(
        self,
        joint_positions: Mapping[object, float] | None = None,
        **kwargs: float,
    ) -> Iterator[None]:
        previous = dict(self._pose)
        updates: dict[str, float] = {}
        joint_names = {joint.name for joint in self.model.joints}
        for key, value in dict(joint_positions or {}).items():
            joint_name = _joint_name(key)
            if joint_name not in joint_names:
                raise ValidationError(f"Unknown joint: {joint_name!r}")
            updates[joint_name] = float(value)
        for key, value in kwargs.items():
            joint_name = _joint_name(key)
            if joint_name not in joint_names:
                raise ValidationError(f"Unknown joint: {joint_name!r}")
            updates[joint_name] = float(value)
        try:
            self._pose.update(updates)
            yield
        finally:
            self._pose = previous

    def part_world_position(self, part: PartRef) -> Vec3 | None:
        return self._kernel().part_world_position(_part_name(part, field="part"), self._pose)

    def link_world_position(self, link: PartRef) -> Vec3 | None:
        return self.part_world_position(link)

    def expect_no_collision(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        name: str | None = None,
    ) -> bool:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        check_name = name or f"expect_no_collision({link_a_name},{link_b_name})"
        query = self._kernel().collision_between(link_a_name, link_b_name, self._pose)
        return self._record(check_name, not query.collided, _collision_details(query))

    def expect_collision(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        name: str | None = None,
    ) -> bool:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        check_name = name or f"expect_collision({link_a_name},{link_b_name})"
        query = self._kernel().collision_between(link_a_name, link_b_name, self._pose)
        return self._record(check_name, query.collided, _collision_details(query))

    def expect_contact(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        contact_tol: float = DEFAULT_CONTACT_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        check_name = name or f"expect_contact({link_a_name},{link_b_name})"
        result = self._kernel().distance_between(link_a_name, link_b_name, self._pose)
        contact_tol = _non_negative(contact_tol, "contact_tol")
        ok = result.collided or result.distance <= contact_tol
        return self._record(
            check_name,
            ok,
            f"{_distance_details(result)} contact_tol={contact_tol:.6g}",
        )

    def expect_distance(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        min_distance: float = 0.0,
        max_distance: float | None = None,
        name: str | None = None,
    ) -> bool:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        check_name = name or f"expect_distance({link_a_name},{link_b_name})"
        min_distance = _non_negative(min_distance, "min_distance")
        max_distance_value = None if max_distance is None else _non_negative(
            max_distance,
            "max_distance",
        )
        if max_distance_value is not None and max_distance_value < min_distance:
            return self._record(check_name, False, "max_distance must be >= min_distance")
        result = self._kernel().distance_between(link_a_name, link_b_name, self._pose)
        ok = result.distance >= min_distance
        if max_distance_value is not None:
            ok = ok and result.distance <= max_distance_value
        upper = "inf" if max_distance_value is None else f"{max_distance_value:.6g}"
        return self._record(
            check_name,
            ok,
            f"{_distance_details(result)} min_distance={min_distance:.6g} max_distance={upper}",
        )

    def expect_gap(
        self,
        positive_link: PartRef,
        negative_link: PartRef,
        *,
        axis: str,
        min_gap: float | None = None,
        max_gap: float | None = None,
        max_penetration: float | None = None,
        name: str | None = None,
    ) -> bool:
        positive_name = _part_name(positive_link, field="positive_link")
        negative_name = _part_name(negative_link, field="negative_link")
        axis_key = _axis_name(axis)
        check_name = name or f"expect_gap({positive_name},{negative_name},axis={axis_key})"
        positive_values = self._axis_values(positive_name, axis_key)
        negative_values = self._axis_values(negative_name, axis_key)
        gap = float(positive_values.min() - negative_values.max())
        if min_gap is None:
            max_penetration_value = 0.0 if max_penetration is None else _non_negative(
                max_penetration,
                "max_penetration",
            )
            min_gap_value = -max_penetration_value
        else:
            min_gap_value = float(min_gap)
            max_penetration_value = max(0.0, -min_gap_value)
        max_gap_value = None if max_gap is None else float(max_gap)
        if max_gap_value is not None and max_gap_value < min_gap_value:
            return self._record(check_name, False, "max_gap must be >= min_gap")
        ok = gap >= min_gap_value
        if max_gap_value is not None:
            ok = ok and gap <= max_gap_value
        upper = "inf" if max_gap_value is None else f"{max_gap_value:.6g}"
        return self._record(
            check_name,
            ok,
            f"mesh_gap_{axis_key}={gap:.6g} min_gap={min_gap_value:.6g} "
            f"max_gap={upper} max_penetration={max_penetration_value:.6g}",
        )

    def expect_within(
        self,
        inner_link: PartRef,
        outer_link: PartRef,
        *,
        axes: str | Sequence[str] = "xy",
        margin: float = 0.0,
        name: str | None = None,
    ) -> bool:
        inner_name = _part_name(inner_link, field="inner_link")
        outer_name = _part_name(outer_link, field="outer_link")
        axis_names = _axis_names(axes)
        check_name = name or f"expect_within({inner_name},{outer_name},axes={''.join(axis_names)})"
        margin = _non_negative(margin, "margin")
        ok = True
        details: list[str] = []
        for axis_key in axis_names:
            inner_values = self._axis_values(inner_name, axis_key)
            outer_values = self._axis_values(outer_name, axis_key)
            inner_min = float(inner_values.min())
            inner_max = float(inner_values.max())
            outer_min = float(outer_values.min())
            outer_max = float(outer_values.max())
            axis_ok = inner_min >= outer_min - margin and inner_max <= outer_max + margin
            ok = ok and axis_ok
            details.append(
                f"{axis_key}=({inner_min:.6g},{inner_max:.6g}) "
                f"within ({outer_min:.6g},{outer_max:.6g})"
            )
        return self._record(check_name, ok, " ".join(details) + f" margin={margin:.6g}")

    def expect_overlap(
        self,
        link_a: PartRef,
        link_b: PartRef,
        *,
        axes: str | Sequence[str] = "xy",
        min_overlap: float = 0.0,
        name: str | None = None,
    ) -> bool:
        link_a_name = _part_name(link_a, field="link_a")
        link_b_name = _part_name(link_b, field="link_b")
        axis_names = _axis_names(axes)
        check_name = name or f"expect_overlap({link_a_name},{link_b_name},axes={''.join(axis_names)})"
        min_overlap = _non_negative(min_overlap, "min_overlap")
        ok = True
        details: list[str] = []
        for axis_key in axis_names:
            values_a = self._axis_values(link_a_name, axis_key)
            values_b = self._axis_values(link_b_name, axis_key)
            overlap = min(float(values_a.max()), float(values_b.max())) - max(
                float(values_a.min()),
                float(values_b.min()),
            )
            axis_ok = overlap >= min_overlap
            ok = ok and axis_ok
            details.append(f"overlap_{axis_key}={overlap:.6g}")
        return self._record(
            check_name,
            ok,
            " ".join(details) + f" min_overlap={min_overlap:.6g}",
        )

    def check_model_valid(self) -> bool:
        try:
            self.model.validate()
        except Exception as exc:
            return self._record("check_model_valid", False, f"{type(exc).__name__}: {exc}")
        return self._record("check_model_valid", True)

    def check_single_root_part(self) -> bool:
        part_names = {part.name for part in self.model.parts}
        child_names = {joint.child for joint in self.model.joints}
        roots = sorted(part_names - child_names)
        if len(roots) != 1:
            return self._record(
                "check_single_root_part",
                False,
                f"Expected exactly one root part, found {len(roots)}: {roots!r}",
            )
        return self._record("check_single_root_part", True)

    def fail_if_isolated_parts(
        self,
        *,
        contact_tol: float = DEFAULT_CONTACT_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        contact_tol = _non_negative(contact_tol, "contact_tol")
        check_name = name or f"fail_if_isolated_parts(contact_tol={contact_tol:.6g})"
        part_names = [part.name for part in self.model.parts]
        if len(part_names) <= 1:
            return self._record(check_name, True)

        roots = _root_part_names(self.model)
        connected: dict[str, set[str]] = {part_name: set() for part_name in part_names}
        nearest: dict[str, DistanceQuery] = {}
        for distance in self._kernel().pair_distances(self._pose):
            part_a = distance.part_a
            part_b = distance.part_b
            if distance.collided or distance.distance <= contact_tol:
                connected[part_a].add(part_b)
                connected[part_b].add(part_a)
            for part in (part_a, part_b):
                current = nearest.get(part)
                if current is None or distance.distance < current.distance:
                    nearest[part] = distance

        reachable: set[str] = set()
        stack = list(roots)
        while stack:
            part_name = stack.pop()
            if part_name in reachable:
                continue
            reachable.add(part_name)
            stack.extend(sorted(connected.get(part_name, set()) - reachable))

        isolated = [
            part_name
            for part_name in part_names
            if part_name not in reachable and part_name not in self._allowed_isolated_parts
        ]
        if not isolated:
            return self._record(check_name, True)

        lines = []
        for part_name in isolated[:10]:
            distance = nearest.get(part_name)
            nearest_text = "nearest=unknown"
            if distance is not None:
                other = distance.part_b if distance.part_a == part_name else distance.part_a
                nearest_text = f"nearest={other!r} distance={distance.distance:.6g}"
            lines.append(f"- {part_name!r} is isolated; {nearest_text}")
        if len(isolated) > 10:
            lines.append(f"... ({len(isolated) - 10} more)")
        return self._record(check_name, False, "\n".join(lines))

    def fail_if_parts_collide_in_current_pose(
        self,
        *,
        ignore_adjacent: bool = True,
        name: str | None = None,
    ) -> bool:
        check_name = name or "fail_if_parts_collide_in_current_pose"
        ignored = self._allowed_overlap_keys()
        if ignore_adjacent:
            ignored |= {_pair_key(joint.parent, joint.child) for joint in self.model.joints}
        collisions = self._kernel().colliding_pairs(
            self._pose,
            allowed_pairs=ignored,
        )
        if not collisions:
            return self._record(check_name, True)

        lines = [_collision_details(collision) for collision in collisions[:10]]
        if len(collisions) > 10:
            lines.append(f"... ({len(collisions) - 10} more)")
        return self._record(check_name, False, "\n".join(lines))

    def _record(self, name: str, ok: bool, details: str = "") -> bool:
        self.checks_run += 1
        self._checks.append(name)
        if not ok:
            self._failures.append(TestFailure(name=name, details=details))
        return ok

    def _kernel(self) -> MeshCollisionKernel:
        if self._kernel_cache is None:
            self._kernel_cache = MeshCollisionKernel(self.model, mesh_tolerance=self.mesh_tolerance)
        return self._kernel_cache

    def _axis_values(self, part_name: str, axis: str):
        vertices = self._kernel().part_world_vertices(part_name, self._pose)
        return vertices[:, _axis_index(axis)]

    def _allowed_overlap_keys(self) -> set[tuple[str, str]]:
        return {_pair_key(item.link_a, item.link_b) for item in self._allowed_overlaps}


def _part_name(value: PartRef, *, field: str) -> str:
    return coerce_part_name(value, field=field)


def _joint_name(value: object) -> str:
    if isinstance(value, Joint):
        return value.name
    if isinstance(value, str):
        name = value.strip()
        if name:
            return name
    name = getattr(value, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    raise ValidationError("pose keys must be joint names or Joint objects")


def _axis_name(axis: str) -> str:
    axis = str(axis).strip().lower()
    if axis not in {"x", "y", "z"}:
        raise ValidationError("axis must be one of: x, y, z")
    return axis


def _axis_names(axes: str | Sequence[str]) -> tuple[str, ...]:
    if isinstance(axes, str):
        raw = list(axes.strip().lower())
    else:
        raw = [str(axis).strip().lower() for axis in axes]
    normalized = tuple(dict.fromkeys(_axis_name(axis) for axis in raw))
    if not normalized:
        raise ValidationError("axes must include at least one axis")
    return normalized


def _axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[axis]


def _non_negative(value: float, field: str) -> float:
    value = float(value)
    if value < 0.0 or not math.isfinite(value):
        raise ValidationError(f"{field} must be finite and non-negative")
    return value


def _collision_details(query: CollisionQuery) -> str:
    finding = _collision_finding(query)
    return (
        f"{finding.link_a!r} vs {finding.link_b!r}: collided={query.collided} "
        f"contacts={finding.contacts} max_depth={_format_optional(finding.max_depth)} "
        f"normal={finding.normal} position={finding.position}"
    )


def _distance_details(query: DistanceQuery) -> str:
    finding = DistanceFinding(
        link_a=query.part_a,
        link_b=query.part_b,
        distance=query.distance,
        nearest_a=query.nearest_a,
        nearest_b=query.nearest_b,
        collided=query.collided,
    )
    return (
        f"{finding.link_a!r} vs {finding.link_b!r}: distance={finding.distance:.6g} "
        f"collided={finding.collided} nearest_a={finding.nearest_a} nearest_b={finding.nearest_b}"
    )


def _collision_finding(query: CollisionQuery) -> CollisionFinding:
    contact = query.contacts[0] if query.contacts else None
    return CollisionFinding(
        link_a=query.part_a,
        link_b=query.part_b,
        contacts=len(query.contacts),
        max_depth=query.max_depth,
        normal=None if contact is None else contact.normal,
        position=None if contact is None else contact.position,
    )


def _format_optional(value: float | None) -> str:
    if value is None:
        return "unknown"
    return f"{value:.6g}"


def _root_part_names(model: ArticulatedObject) -> list[str]:
    part_names = {part.name for part in model.parts}
    child_names = {joint.child for joint in model.joints}
    return sorted(part_names - child_names)


def _pair_key(part_a: str, part_b: str) -> tuple[str, str]:
    return (part_a, part_b) if part_a <= part_b else (part_b, part_a)


__all__ = [
    "AllowedOverlap",
    "CollisionFinding",
    "DistanceFinding",
    "TestContext",
    "TestFailure",
    "TestReport",
]
