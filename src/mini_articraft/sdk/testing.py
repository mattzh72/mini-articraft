from __future__ import annotations

import math
import statistics
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import ClassVar, cast

from mini_articraft.errors import ValidationError
from mini_articraft.sdk._collision import (
    Bounds,
    CollisionQuery,
    DistanceQuery,
    GeometryConnectivityFinding,
    MeshCollisionKernel,
    Vec3,
    _pair_key,
)
from mini_articraft.sdk.joints import Articulation
from mini_articraft.sdk.object import ArticulatedObject, Part, PartRef

DEFAULT_MESH_TOLERANCE = 0.001
DEFAULT_CONTACT_TOLERANCE = 1e-6
DEFAULT_OVERLAP_TOLERANCE = 0.005
DEFAULT_OVERLAP_VOLUME_TOLERANCE = 5e-7


@dataclass(frozen=True)
class TestFailure:
    __test__: ClassVar[bool] = False

    name: str
    details: str


@dataclass(frozen=True)
class AllowedOverlap:
    part_a: str
    part_b: str
    reason: str
    shape_a: str
    shape_b: str


@dataclass(frozen=True)
class DistanceFinding:
    part_a: str
    part_b: str
    shape_a: str | None
    shape_b: str | None
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
            checks_run=self.checks_run,
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
        if text and text not in self._warnings:
            self._warnings.append(text)

    def allow_overlap(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        reason: str,
        shape_a: str,
        shape_b: str,
    ) -> None:
        part_a_name = _part_name(part_a, field_name="part_a")
        part_b_name = _part_name(part_b, field_name="part_b")
        self.model.get_part(part_a_name)
        self.model.get_part(part_b_name)
        shape_a = str(shape_a).strip()
        shape_b = str(shape_b).strip()
        self.model.get_part(part_a_name).get_shape(shape_a)
        self.model.get_part(part_b_name).get_shape(shape_b)
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("allow_overlap requires a non-empty reason")

        part_a_name, part_b_name, shape_a, shape_b = _canonical_selectors(
            part_a_name, part_b_name, shape_a, shape_b
        )
        allowed = AllowedOverlap(part_a_name, part_b_name, reason, shape_a, shape_b)
        self._allowed_overlaps.append(allowed)
        shape_text = f", shape_a={shape_a!r}, shape_b={shape_b!r}"
        self._allowances.append(
            f"allow_overlap({part_a_name!r}, {part_b_name!r}{shape_text}): {reason}"
        )

    def allow_isolated_part(self, part: PartRef, *, reason: str) -> None:
        part_name = _part_name(part, field_name="part")
        self.model.get_part(part_name)
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("allow_isolated_part requires a non-empty reason")
        self._allowed_isolated_parts[part_name] = reason
        self._allowances.append(f"allow_isolated_part({part_name!r}): {reason}")

    @contextmanager
    def pose(
        self,
        articulation_positions: Mapping[object, float] | None = None,
        **kwargs: float,
    ) -> Iterator[None]:
        previous = dict(self._pose)
        updates: dict[str, float] = {}
        articulation_names = {item.name for item in self.model.articulations}
        for key, value in dict(articulation_positions or {}).items():
            name = _articulation_name(key)
            if name not in articulation_names:
                raise ValidationError(f"unknown articulation: {name!r}")
            updates[name] = _finite(value, "articulation position")
        for key, value in kwargs.items():
            name = _articulation_name(key)
            if name not in articulation_names:
                raise ValidationError(f"unknown articulation: {name!r}")
            updates[name] = _finite(value, "articulation position")
        try:
            self._pose.update(updates)
            yield
        finally:
            self._pose = previous

    def part_world_position(self, part: PartRef) -> Vec3:
        return self._kernel().part_world_position(_part_name(part, field_name="part"), self._pose)

    def part_world_bounds(self, part: PartRef) -> Bounds:
        return self._kernel().part_world_bounds(_part_name(part, field_name="part"), self._pose)

    def shape_world_bounds(self, part: PartRef, shape: str) -> Bounds:
        return self._kernel().shape_world_bounds(
            _part_name(part, field_name="part"), shape, self._pose
        )

    def distance_between(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
    ) -> DistanceFinding:
        result = self._distance_query(part_a, part_b, shape_a=shape_a, shape_b=shape_b)
        return DistanceFinding(
            part_a=result.part_a,
            part_b=result.part_b,
            shape_a=result.shape_a,
            shape_b=result.shape_b,
            distance=result.distance,
            nearest_a=result.nearest_a,
            nearest_b=result.nearest_b,
            collided=result.collided,
        )

    def expect_no_collision(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
        name: str | None = None,
    ) -> bool:
        query = self._collision_query(part_a, part_b, shape_a=shape_a, shape_b=shape_b)
        check_name = name or _check_name("expect_no_collision", query)
        return self._record(check_name, not query.collided, _collision_details(query))

    def expect_collision(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
        name: str | None = None,
    ) -> bool:
        query = self._collision_query(part_a, part_b, shape_a=shape_a, shape_b=shape_b)
        check_name = name or _check_name("expect_collision", query)
        return self._record(check_name, query.collided, _collision_details(query))

    def expect_contact(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
        contact_tol: float = DEFAULT_CONTACT_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        result = self._distance_query(part_a, part_b, shape_a=shape_a, shape_b=shape_b)
        contact_tol = _non_negative(contact_tol, "contact_tol")
        check_name = name or _check_name("expect_contact", result)
        return self._record(
            check_name,
            result.collided or result.distance <= contact_tol,
            f"{_distance_details(result)} contact_tol={contact_tol:.6g}",
        )

    def expect_distance(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
        min_distance: float = 0.0,
        max_distance: float | None = None,
        name: str | None = None,
    ) -> bool:
        result = self._distance_query(part_a, part_b, shape_a=shape_a, shape_b=shape_b)
        min_distance = _non_negative(min_distance, "min_distance")
        maximum = None if max_distance is None else _non_negative(max_distance, "max_distance")
        check_name = name or _check_name("expect_distance", result)
        if maximum is not None and maximum < min_distance:
            return self._record(check_name, False, "max_distance must be >= min_distance")
        ok = result.distance >= min_distance and (maximum is None or result.distance <= maximum)
        upper = "inf" if maximum is None else f"{maximum:.6g}"
        return self._record(
            check_name,
            ok,
            f"{_distance_details(result)} min_distance={min_distance:.6g} max_distance={upper}",
        )

    def expect_gap(
        self,
        positive_part: PartRef,
        negative_part: PartRef,
        *,
        axis: str,
        positive_shape: str | None = None,
        negative_shape: str | None = None,
        min_gap: float | None = None,
        max_gap: float | None = None,
        max_penetration: float | None = None,
        name: str | None = None,
    ) -> bool:
        positive_name = _part_name(positive_part, field_name="positive_part")
        negative_name = _part_name(negative_part, field_name="negative_part")
        axis_name = _axis_name(axis)
        positive_bounds = self._bounds(positive_name, positive_shape)
        negative_bounds = self._bounds(negative_name, negative_shape)
        axis_index = _axis_index(axis_name)
        gap = positive_bounds[0][axis_index] - negative_bounds[1][axis_index]
        if min_gap is None:
            penetration = (
                0.0
                if max_penetration is None
                else _non_negative(max_penetration, "max_penetration")
            )
            minimum = -penetration
        else:
            minimum = _finite(min_gap, "min_gap")
            penetration = max(0.0, -minimum)
        maximum = None if max_gap is None else _finite(max_gap, "max_gap")
        selectors = _selector_text(
            positive_shape=positive_shape,
            negative_shape=negative_shape,
        )
        check_name = name or (
            f"expect_gap({positive_name},{negative_name},axis={axis_name}{selectors})"
        )
        if maximum is not None and maximum < minimum:
            return self._record(check_name, False, "max_gap must be >= min_gap")
        ok = gap >= minimum and (maximum is None or gap <= maximum)
        upper = "inf" if maximum is None else f"{maximum:.6g}"
        return self._record(
            check_name,
            ok,
            f"mesh_gap_{axis_name}={gap:.6g} min_gap={minimum:.6g} "
            f"max_gap={upper} max_penetration={penetration:.6g}",
        )

    def expect_within(
        self,
        inner_part: PartRef,
        outer_part: PartRef,
        *,
        inner_shape: str | None = None,
        outer_shape: str | None = None,
        axes: str | Sequence[str] = "xy",
        margin: float = 0.0,
        name: str | None = None,
    ) -> bool:
        inner_name = _part_name(inner_part, field_name="inner_part")
        outer_name = _part_name(outer_part, field_name="outer_part")
        inner_bounds = self._bounds(inner_name, inner_shape)
        outer_bounds = self._bounds(outer_name, outer_shape)
        axis_names = _axis_names(axes)
        margin = _non_negative(margin, "margin")
        selectors = _selector_text(inner_shape=inner_shape, outer_shape=outer_shape)
        check_name = name or (
            f"expect_within({inner_name},{outer_name},axes={''.join(axis_names)}{selectors})"
        )
        ok = True
        details: list[str] = []
        for axis_name in axis_names:
            index = _axis_index(axis_name)
            axis_ok = (
                inner_bounds[0][index] >= outer_bounds[0][index] - margin
                and inner_bounds[1][index] <= outer_bounds[1][index] + margin
            )
            ok = ok and axis_ok
            details.append(
                f"{axis_name}=({inner_bounds[0][index]:.6g},{inner_bounds[1][index]:.6g}) "
                f"within ({outer_bounds[0][index]:.6g},{outer_bounds[1][index]:.6g})"
            )
        return self._record(check_name, ok, " ".join(details) + f" margin={margin:.6g}")

    def expect_overlap(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None = None,
        shape_b: str | None = None,
        axes: str | Sequence[str] = "xy",
        min_overlap: float = 0.0,
        name: str | None = None,
    ) -> bool:
        part_a_name = _part_name(part_a, field_name="part_a")
        part_b_name = _part_name(part_b, field_name="part_b")
        bounds_a = self._bounds(part_a_name, shape_a)
        bounds_b = self._bounds(part_b_name, shape_b)
        axis_names = _axis_names(axes)
        minimum = _non_negative(min_overlap, "min_overlap")
        selectors = _selector_text(shape_a=shape_a, shape_b=shape_b)
        check_name = name or (
            f"expect_overlap({part_a_name},{part_b_name},axes={''.join(axis_names)}{selectors})"
        )
        ok = True
        details: list[str] = []
        for axis_name in axis_names:
            index = _axis_index(axis_name)
            overlap = min(bounds_a[1][index], bounds_b[1][index]) - max(
                bounds_a[0][index], bounds_b[0][index]
            )
            ok = ok and overlap >= minimum
            details.append(f"overlap_{axis_name}={overlap:.6g}")
        return self._record(check_name, ok, " ".join(details) + f" min_overlap={minimum:.6g}")

    def check_model_valid(self) -> bool:
        try:
            self.model.validate()
        except Exception as exc:
            return self._record("check_model_valid", False, f"{type(exc).__name__}: {exc}")
        return self._record("check_model_valid", True)

    def check_single_root_part(self) -> bool:
        roots = _root_part_names(self.model)
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
        check_name = name or (
            "fail_if_isolated_parts()"
            if contact_tol == DEFAULT_CONTACT_TOLERANCE
            else f"fail_if_isolated_parts(contact_tol={contact_tol:.4g})"
        )
        part_names = [part.name for part in self.model.parts]
        if len(part_names) <= 1:
            return self._record(check_name, True)

        adjacency: dict[str, set[str]] = {part_name: set() for part_name in part_names}
        distances = self._kernel().pair_distances(self._pose)
        for distance in distances:
            if distance.collided or distance.distance <= contact_tol:
                adjacency[distance.part_a].add(distance.part_b)
                adjacency[distance.part_b].add(distance.part_a)

        reachable = _reachable(_root_part_names(self.model), adjacency)
        floating = set(part_names) - reachable
        groups = _groups(floating, adjacency)
        remaining = [
            group
            for group in groups
            if not all(part_name in self._allowed_isolated_parts for part_name in group)
        ]
        allowed = [group for group in groups if group not in remaining]
        if allowed:
            allowed_names = sorted(part_name for group in allowed for part_name in group)
            self.warn(
                "Isolated parts detected but allowed by justification: "
                + ", ".join(repr(item) for item in allowed_names)
            )
        if not remaining:
            return self._record(check_name, True)

        lines: list[str] = []
        for group in remaining[:10]:
            nearest_text = "nearest=unknown"
            candidates = [
                item
                for item in distances
                if (
                    (item.part_a in group and item.part_b in reachable)
                    or (item.part_b in group and item.part_a in reachable)
                )
            ]
            if candidates:
                distance = min(candidates, key=lambda item: item.distance)
                root_part = distance.part_b if distance.part_a in group else distance.part_a
                nearest_text = (
                    f"nearest_root_part={root_part!r} nearest_gap={distance.distance:.6g}m"
                )
            lines.append(f"floating_group={sorted(group)!r} {nearest_text}")
        return self._record(
            check_name,
            False,
            "Isolated parts detected (physically disconnected from the root):\n" + "\n".join(lines),
        )

    def fail_if_part_contains_disconnected_geometry_islands(
        self,
        *,
        contact_tol: float = DEFAULT_CONTACT_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        return self._check_disconnected_geometry(contact_tol=contact_tol, name=name, warn=False)

    def warn_if_part_contains_disconnected_geometry_islands(
        self,
        *,
        contact_tol: float = DEFAULT_CONTACT_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        return self._check_disconnected_geometry(contact_tol=contact_tol, name=name, warn=True)

    def warn_if_absurd_dimensions(
        self,
        *,
        max_dimension: float = 1000.0,
        outlier_ratio: float = 100.0,
        name: str | None = None,
    ) -> bool:
        maximum = _non_negative(max_dimension, "max_dimension")
        ratio = _non_negative(outlier_ratio, "outlier_ratio")
        check_name = name or "warn_if_absurd_dimensions()"
        spans: list[tuple[str, str, float]] = []
        for part in self.model.parts:
            for shape in part._iter_shapes():
                bounds = self.shape_world_bounds(part, shape.name)
                span = max(bounds[1][axis] - bounds[0][axis] for axis in range(3))
                spans.append((part.name, shape.name, span))
        positive = [span for _part, _shape, span in spans if span > 0.0]
        median = statistics.median(positive) if positive else 0.0
        warnings: list[str] = []
        for part_name, shape_name, span in spans:
            if span > maximum:
                warnings.append(f"absurd dimension: {part_name!r}/{shape_name!r} spans {span:.4g}m")
            elif median > 0.0 and ratio > 0.0 and span > median * ratio:
                warnings.append(
                    f"extreme scale outlier: {part_name!r}/{shape_name!r} spans {span:.4g}m "
                    f"while median shape span is {median:.4g}m"
                )
        if warnings:
            self.warn("Scale warning:\n" + "\n".join(warnings[:10]))
        return self._record(check_name, True)

    def fail_if_parts_overlap_in_current_pose(
        self,
        *,
        overlap_tol: float = DEFAULT_OVERLAP_TOLERANCE,
        overlap_volume_tol: float = DEFAULT_OVERLAP_VOLUME_TOLERANCE,
        name: str | None = None,
    ) -> bool:
        overlap_tol = _non_negative(overlap_tol, "overlap_tol")
        volume_tol = _non_negative(overlap_volume_tol, "overlap_volume_tol")
        check_name = name or (
            "fail_if_parts_overlap_in_current_pose()"
            if (
                overlap_tol == DEFAULT_OVERLAP_TOLERANCE
                and volume_tol == DEFAULT_OVERLAP_VOLUME_TOLERANCE
            )
            else (
                "fail_if_parts_overlap_in_current_pose("
                f"overlap_tol={overlap_tol:.4g},overlap_volume_tol={volume_tol:.4g})"
            )
        )
        overlaps = self._kernel().meaningful_overlaps(
            self._pose,
            overlap_tol=overlap_tol,
            overlap_volume_tol=volume_tol,
        )
        allowed: list[CollisionQuery] = []
        remaining: list[CollisionQuery] = []
        for query in overlaps:
            (allowed if self._overlap_is_allowed(query) else remaining).append(query)
        if allowed:
            self.warn(
                "Overlaps detected but allowed by justification: "
                f"{len(allowed)} named shape pair(s)."
            )
        if not remaining:
            return self._record(check_name, True)

        representative: dict[tuple[str, str], CollisionQuery] = {}
        for query in remaining:
            key = _pair_key(query.part_a, query.part_b)
            current = representative.get(key)
            if current is None or _overlap_rank(query) > _overlap_rank(current):
                representative[key] = query
        details = [_collision_details(representative[key]) for key in sorted(representative)]
        return self._record(
            check_name,
            False,
            "Part overlaps detected "
            f"(overlap_tol={overlap_tol:.4g}, overlap_volume_tol={volume_tol:.4g}):\n"
            + "\n".join(details[:10]),
        )

    def _check_disconnected_geometry(
        self,
        *,
        contact_tol: float,
        name: str | None,
        warn: bool,
    ) -> bool:
        contact_tol = _non_negative(contact_tol, "contact_tol")
        prefix = (
            "warn_if_part_contains_disconnected_geometry_islands"
            if warn
            else "fail_if_part_contains_disconnected_geometry_islands"
        )
        check_name = name or f"{prefix}(contact_tol={contact_tol:.6g})"
        findings = self._kernel().disconnected_geometry_islands(contact_tol=contact_tol)
        if not findings:
            return self._record(check_name, True)
        lines = [_geometry_connectivity_details(finding) for finding in findings[:10]]
        details = "Disconnected geometry islands detected:\n" + "\n".join(lines)
        if warn:
            self.warn(details)
            return self._record(check_name, True)
        return self._record(check_name, False, details)

    def _collision_query(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None,
        shape_b: str | None,
    ) -> CollisionQuery:
        return self._kernel().collision_between(
            _part_name(part_a, field_name="part_a"),
            _part_name(part_b, field_name="part_b"),
            self._pose,
            shape_a=shape_a,
            shape_b=shape_b,
        )

    def _distance_query(
        self,
        part_a: PartRef,
        part_b: PartRef,
        *,
        shape_a: str | None,
        shape_b: str | None,
    ) -> DistanceQuery:
        return self._kernel().distance_between(
            _part_name(part_a, field_name="part_a"),
            _part_name(part_b, field_name="part_b"),
            self._pose,
            shape_a=shape_a,
            shape_b=shape_b,
        )

    def _bounds(self, part_name: str, shape_name: str | None) -> Bounds:
        if shape_name is None:
            return self._kernel().part_world_bounds(part_name, self._pose)
        return self._kernel().shape_world_bounds(part_name, shape_name, self._pose)

    def _overlap_is_allowed(self, query: CollisionQuery) -> bool:
        if query.shape_a is None or query.shape_b is None:
            return False
        part_a, part_b, shape_a, shape_b = _canonical_selectors(
            query.part_a, query.part_b, query.shape_a, query.shape_b
        )
        for allowance in self._allowed_overlaps:
            if allowance.part_a != part_a or allowance.part_b != part_b:
                continue
            if allowance.shape_a == shape_a and allowance.shape_b == shape_b:
                return True
        return False

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


def _part_name(value: PartRef, *, field_name: str) -> str:
    raw = value.name if isinstance(value, Part) else value
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError(f"{field_name} must be a part name or Part")
    return raw.strip()


def _articulation_name(value: object) -> str:
    raw = value.name if isinstance(value, Articulation) else value
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError("pose keys must be articulation names or Articulation objects")
    return raw.strip()


def _canonical_selectors(
    part_a: str,
    part_b: str,
    shape_a: str,
    shape_b: str,
) -> tuple[str, str, str, str]:
    if part_a <= part_b:
        return part_a, part_b, shape_a, shape_b
    return part_b, part_a, shape_b, shape_a


def _axis_name(axis: str) -> str:
    value = str(axis).strip().lower()
    if value not in {"x", "y", "z"}:
        raise ValidationError("axis must be one of: x, y, z")
    return value


def _axis_names(axes: str | Sequence[str]) -> tuple[str, ...]:
    raw = list(axes.strip().lower()) if isinstance(axes, str) else list(axes)
    normalized = tuple(dict.fromkeys(_axis_name(str(axis)) for axis in raw))
    if not normalized:
        raise ValidationError("axes must include at least one axis")
    return normalized


def _axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[axis]


def _finite(value: object, field_name: str) -> float:
    try:
        result = float(cast(str, value))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValidationError(f"{field_name} must be finite")
    return result


def _non_negative(value: object, field_name: str) -> float:
    result = _finite(value, field_name)
    if result < 0.0:
        raise ValidationError(f"{field_name} must be non-negative")
    return result


def _collision_details(query: CollisionQuery) -> str:
    contact = query.contacts[0] if query.contacts else None
    overlap = query.overlap_depth or (0.0, 0.0, 0.0)
    return (
        f"pair=({query.part_a!r},{query.part_b!r}) "
        f"shape_a={query.shape_a!r} shape_b={query.shape_b!r} collided={query.collided} "
        f"contacts={len(query.contacts)} max_depth={_format_optional(query.max_depth)} "
        f"overlap_depth=({overlap[0]:.4g},{overlap[1]:.4g},{overlap[2]:.4g}) "
        f"overlap_volume={query.overlap_volume:.4g} "
        f"normal={None if contact is None else contact.normal} "
        f"position={None if contact is None else contact.position}"
    )


def _distance_details(query: DistanceQuery) -> str:
    return (
        f"pair=({query.part_a!r},{query.part_b!r}) "
        f"shape_a={query.shape_a!r} shape_b={query.shape_b!r} "
        f"distance={query.distance:.6g} collided={query.collided} "
        f"nearest_a={query.nearest_a} nearest_b={query.nearest_b}"
    )


def _geometry_connectivity_details(finding: GeometryConnectivityFinding) -> str:
    return (
        f"part={finding.part!r} connected={finding.connected}/{finding.total} "
        f"contact_tol={finding.contact_tol:.6g} "
        f"disconnected=[{', '.join(finding.disconnected)}]"
    )


def _check_name(prefix: str, query: CollisionQuery | DistanceQuery) -> str:
    selectors = ""
    if query.shape_a is not None or query.shape_b is not None:
        selectors = f",shape_a={query.shape_a},shape_b={query.shape_b}"
    return f"{prefix}({query.part_a},{query.part_b}{selectors})"


def _selector_text(**selectors: str | None) -> str:
    values = [f"{name}={value}" for name, value in selectors.items() if value is not None]
    return "" if not values else "," + ",".join(values)


def _format_optional(value: float | None) -> str:
    return "unknown" if value is None else f"{value:.6g}"


def _root_part_names(model: ArticulatedObject) -> list[str]:
    part_names = {part.name for part in model.parts}
    child_names = {item.child for item in model.articulations}
    return sorted(part_names - child_names)


def _reachable(roots: list[str], adjacency: dict[str, set[str]]) -> set[str]:
    found: set[str] = set()
    stack = list(roots)
    while stack:
        part_name = stack.pop()
        if part_name in found:
            continue
        found.add(part_name)
        stack.extend(sorted(adjacency.get(part_name, set()) - found))
    return found


def _groups(names: set[str], adjacency: dict[str, set[str]]) -> list[set[str]]:
    remaining = set(names)
    groups: list[set[str]] = []
    while remaining:
        start = min(remaining)
        group = _reachable([start], adjacency) & names
        groups.append(group)
        remaining -= group
    return groups


def _overlap_rank(query: CollisionQuery) -> tuple[float, float]:
    depth = query.overlap_depth or (0.0, 0.0, 0.0)
    return min(depth), query.overlap_volume


__all__ = [
    "AllowedOverlap",
    "DistanceFinding",
    "TestContext",
    "TestFailure",
    "TestReport",
]
