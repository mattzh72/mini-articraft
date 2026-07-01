from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TypeAlias

from build123d import Shape

from mini_articraft.errors import ValidationError
from mini_articraft.sdk.joints import (
    ContinuousLimits,
    Frame,
    Joint,
    JointLimits,
    JointType,
    Vec3,
    as_position_limits,
    coerce_part_name,
)

Build123dShape: TypeAlias = Shape
Color: TypeAlias = tuple[float, float, float, float]
UNITS_TO_METERS = {
    "meters": 1.0,
    "centimeters": 0.01,
    "millimeters": 0.001,
    "inches": 0.0254,
    "feet": 0.3048,
}


@dataclass
class Part:
    name: str
    shape: Build123dShape
    color: Color | None = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("part name must be non-empty")
        if not isinstance(self.shape, Shape):
            raise ValidationError(f"part {self.name!r} shape must be a build123d Shape")
        if self.color is not None:
            self.color = _as_color(self.color, field=f"part {self.name!r} color")


PartRef: TypeAlias = str | Part


@dataclass
class ArticulatedObject:
    name: str
    units: str | None = None
    parts: list[Part] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("object name must be non-empty")
        self.units = _normalize_units(self.units)

    @property
    def meters_per_unit(self) -> float:
        return UNITS_TO_METERS[self.units]

    def part(self, name: str, shape: Build123dShape, *, color: Color | None = None) -> Part:
        part = Part(name=name, shape=shape, color=color)
        if any(existing.name == part.name for existing in self.parts):
            raise ValidationError(f"duplicate part name: {part.name!r}")
        self.parts.append(part)
        return part

    def _add_joint(
        self,
        name: str,
        joint_type: JointType,
        parent: PartRef,
        child: PartRef,
        *,
        frame: Frame | None = None,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: JointLimits | ContinuousLimits | None = None,
    ) -> Joint:
        joint = Joint(
            name=name,
            type=joint_type,
            parent=coerce_part_name(parent, field="parent"),
            child=coerce_part_name(child, field="child"),
            frame=frame or Frame(),
            axis=axis,
            limits=limits,
        )
        joint.validate()
        self.get_part(joint.parent)
        self.get_part(joint.child)
        if any(existing.name == joint.name for existing in self.joints):
            raise ValidationError(f"duplicate joint name: {joint.name!r}")
        self.joints.append(joint)
        return joint

    def fixed(
        self,
        name: str,
        parent: PartRef,
        child: PartRef,
        *,
        frame: Frame | None = None,
    ) -> Joint:
        return self._add_joint(name, JointType.FIXED, parent, child, frame=frame)

    def revolute(
        self,
        name: str,
        parent: PartRef,
        child: PartRef,
        *,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: tuple[float, float],
        frame: Frame | None = None,
    ) -> Joint:
        return self._add_joint(
            name,
            JointType.REVOLUTE,
            parent,
            child,
            frame=frame,
            axis=axis,
            limits=as_position_limits(limits, field=f"revolute joint {name!r} limits"),
        )

    def prismatic(
        self,
        name: str,
        parent: PartRef,
        child: PartRef,
        *,
        axis: Vec3 = (1.0, 0.0, 0.0),
        limits: tuple[float, float],
        frame: Frame | None = None,
    ) -> Joint:
        return self._add_joint(
            name,
            JointType.PRISMATIC,
            parent,
            child,
            frame=frame,
            axis=axis,
            limits=as_position_limits(limits, field=f"prismatic joint {name!r} limits"),
        )

    def continuous(
        self,
        name: str,
        parent: PartRef,
        child: PartRef,
        *,
        axis: Vec3 = (0.0, 0.0, 1.0),
        frame: Frame | None = None,
    ) -> Joint:
        return self._add_joint(
            name,
            JointType.CONTINUOUS,
            parent,
            child,
            frame=frame,
            axis=axis,
            limits=ContinuousLimits(),
        )

    def get_part(self, part: PartRef) -> Part:
        name = coerce_part_name(part, field="part")
        for existing in self.parts:
            if existing.name == name:
                return existing
        raise ValidationError(f"unknown part: {name!r}")

    def validate(self) -> None:
        if not self.parts:
            raise ValidationError("object must contain at least one part")

        part_names = {part.name for part in self.parts}
        joint_names = {joint.name for joint in self.joints}
        if len(part_names) != len(self.parts):
            raise ValidationError("part names must be unique")
        if len(joint_names) != len(self.joints):
            raise ValidationError("joint names must be unique")

        child_parent: dict[str, str] = {}
        children: dict[str, list[str]] = {name: [] for name in part_names}
        for joint in self.joints:
            joint.validate()
            for role, part in (("parent", joint.parent), ("child", joint.child)):
                if part not in part_names:
                    raise ValidationError(
                        f"joint {joint.name!r} references missing {role} part {part!r}"
                    )
            if joint.child in child_parent:
                raise ValidationError(
                    f"part {joint.child!r} has multiple parent joints: "
                    f"{child_parent[joint.child]!r} and {joint.name!r}"
                )
            child_parent[joint.child] = joint.name
            children[joint.parent].append(joint.child)

        if len(part_names) <= 1:
            return

        roots = sorted(part_names - set(child_parent))
        if not roots:
            raise ValidationError("object has no root part")
        if len(roots) > 1:
            raise ValidationError(f"object must have exactly one root part, found {roots}")

        visited: set[str] = set()
        stack = roots[:]
        while stack:
            part = stack.pop()
            if part in visited:
                continue
            visited.add(part)
            stack.extend(children[part])

        if visited != part_names:
            raise ValidationError(
                f"object contains unreachable parts: {sorted(part_names - visited)}"
            )


def _normalize_units(value: str | None) -> str:
    if value is None or not str(value).strip():
        raise ValidationError("ArticulatedObject must declare units")
    units = str(value).strip().lower()
    if units not in UNITS_TO_METERS:
        supported = ", ".join(sorted(UNITS_TO_METERS))
        raise ValidationError(f"unsupported units {value!r}; expected one of: {supported}")
    return units


def _as_color(value: tuple[float, ...], *, field: str) -> Color:
    try:
        raw = tuple(float(component) for component in value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must have 3 or 4 numeric values") from exc

    if len(raw) == 3:
        raw = raw + (1.0,)
    if len(raw) != 4:
        raise ValidationError(f"{field} must have 3 or 4 numeric values")
    if any(not math.isfinite(component) for component in raw):
        raise ValidationError(f"{field} values must be finite")
    if any(component < 0.0 or component > 1.0 for component in raw):
        raise ValidationError(f"{field} values must be between 0.0 and 1.0")
    return raw
