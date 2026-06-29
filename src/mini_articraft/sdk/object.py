from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import cadquery as cq

from mini_articraft.errors import ValidationError
from mini_articraft.sdk.joints import (
    ContinuousLimits,
    Joint,
    JointLimits,
    JointType,
    LimitsLike,
    Origin,
    Vec3,
    axis_norm,
    coerce_limits,
    coerce_part_name,
)

CadQueryShape = cq.Workplane | cq.Shape | cq.Assembly


@dataclass
class Part:
    name: str
    shape: CadQueryShape
    meta: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("part name must be non-empty")
        if not isinstance(self.shape, (cq.Workplane, cq.Shape, cq.Assembly)):
            raise ValidationError(
                f"part {self.name!r} shape must be a CadQuery Workplane, Shape, or Assembly"
            )


@dataclass
class ArticulatedObject:
    name: str
    parts: list[Part] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("object name must be non-empty")

    @property
    def articulations(self) -> list[Joint]:
        return self.joints

    def part(
        self,
        name: str,
        shape: CadQueryShape,
        *,
        meta: dict[str, object] | None = None,
    ) -> Part:
        part = Part(name=name, shape=shape, meta=dict(meta or {}))
        if any(existing.name == part.name for existing in self.parts):
            raise ValidationError(f"duplicate part name: {part.name!r}")
        self.parts.append(part)
        return part

    def joint(
        self,
        name: str,
        joint_type: JointType | str,
        parent: str | Part,
        child: str | Part,
        *,
        origin: Origin | None = None,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: LimitsLike | None = None,
    ) -> Joint:
        parent_name = coerce_part_name(parent, field="parent")
        child_name = coerce_part_name(child, field="child")
        if parent_name == child_name:
            raise ValidationError("joint parent and child cannot match")
        self.get_part(parent_name)
        self.get_part(child_name)

        joint = Joint(
            name=name,
            type=joint_type,
            parent=parent_name,
            child=child_name,
            origin=origin or Origin(),
            axis=axis,
            limits=coerce_limits(limits),
        )
        _validate_joint(joint)
        if any(existing.name == joint.name for existing in self.joints):
            raise ValidationError(f"duplicate joint name: {joint.name!r}")
        self.joints.append(joint)
        return joint

    def articulation(
        self,
        name: str,
        articulation_type: JointType | str,
        parent: str | Part,
        child: str | Part,
        *,
        origin: Origin | None = None,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: LimitsLike | None = None,
    ) -> Joint:
        return self.joint(
            name,
            articulation_type,
            parent,
            child,
            origin=origin,
            axis=axis,
            limits=limits,
        )

    def fixed(
        self,
        name: str,
        parent: str | Part,
        child: str | Part,
        *,
        origin: Origin | None = None,
    ) -> Joint:
        return self.joint(name, JointType.FIXED, parent, child, origin=origin)

    def revolute(
        self,
        name: str,
        parent: str | Part,
        child: str | Part,
        *,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: LimitsLike,
        origin: Origin | None = None,
    ) -> Joint:
        return self.joint(
            name,
            JointType.REVOLUTE,
            parent,
            child,
            origin=origin,
            axis=axis,
            limits=limits,
        )

    def prismatic(
        self,
        name: str,
        parent: str | Part,
        child: str | Part,
        *,
        axis: Vec3 = (1.0, 0.0, 0.0),
        limits: LimitsLike,
        origin: Origin | None = None,
    ) -> Joint:
        return self.joint(
            name,
            JointType.PRISMATIC,
            parent,
            child,
            origin=origin,
            axis=axis,
            limits=limits,
        )

    def continuous(
        self,
        name: str,
        parent: str | Part,
        child: str | Part,
        *,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: ContinuousLimits,
        origin: Origin | None = None,
    ) -> Joint:
        return self.joint(
            name,
            JointType.CONTINUOUS,
            parent,
            child,
            origin=origin,
            axis=axis,
            limits=limits,
        )

    def get_part(self, part: str | Part) -> Part:
        name = coerce_part_name(part, field="part")
        for existing in self.parts:
            if existing.name == name:
                return existing
        raise ValidationError(f"unknown part: {name!r}")

    def root_parts(self) -> list[Part]:
        child_names = {joint.child for joint in self.joints}
        return [part for part in self.parts if part.name not in child_names]

    def validate(self) -> None:
        if not self.parts:
            raise ValidationError("object must contain at least one part")
        _validate_unique((part.name for part in self.parts), "part")
        _validate_unique((joint.name for joint in self.joints), "joint")

        part_names = {part.name for part in self.parts}
        child_to_joint: dict[str, Joint] = {}
        for joint in self.joints:
            if joint.parent not in part_names:
                raise ValidationError(
                    f"joint {joint.name!r} references missing parent part {joint.parent!r}"
                )
            if joint.child not in part_names:
                raise ValidationError(
                    f"joint {joint.name!r} references missing child part {joint.child!r}"
                )
            if joint.parent == joint.child:
                raise ValidationError(f"joint {joint.name!r} parent and child cannot match")
            if joint.child in child_to_joint:
                other = child_to_joint[joint.child]
                raise ValidationError(
                    f"part {joint.child!r} has multiple parent joints: "
                    f"{other.name!r} and {joint.name!r}"
                )
            child_to_joint[joint.child] = joint
            _validate_joint(joint)

        self._validate_connectivity(part_names)

    def _validate_connectivity(self, part_names: set[str]) -> None:
        if len(part_names) <= 1:
            return
        parent_to_children: dict[str, list[str]] = {name: [] for name in part_names}
        child_names: set[str] = set()
        for joint in self.joints:
            parent_to_children[joint.parent].append(joint.child)
            child_names.add(joint.child)

        roots = sorted(part_names - child_names)
        if not roots:
            raise ValidationError("object has no root part")
        if len(roots) > 1:
            raise ValidationError(f"object must have exactly one root part, found {roots}")

        visited: set[str] = set()
        stack = list(roots)
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(parent_to_children.get(current, []))

        if visited != part_names:
            missing = sorted(part_names - visited)
            raise ValidationError(f"object contains unreachable parts: {missing}")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "parts": [
                {
                    "name": part.name,
                    "shape_type": type(part.shape).__name__,
                    "meta": part.meta,
                }
                for part in self.parts
            ],
            "joints": [joint.to_dict() for joint in self.joints],
            "meta": self.meta,
        }


def _validate_unique(names: Iterable[str], kind: str) -> None:
    seen: set[str] = set()
    for name in names:
        if name in seen:
            raise ValidationError(f"{kind} names must be unique")
        seen.add(name)


def _validate_joint(joint: Joint) -> None:
    if joint.type == JointType.FIXED:
        if joint.limits is not None:
            raise ValidationError(f"fixed joint {joint.name!r} cannot have limits")
        return

    if joint.type in {JointType.REVOLUTE, JointType.PRISMATIC}:
        if axis_norm(joint.axis) == 0.0:
            raise ValidationError(f"joint {joint.name!r} axis must be non-zero")
        if not isinstance(joint.limits, JointLimits):
            raise ValidationError(f"joint {joint.name!r} must include limits")
        return

    if joint.type == JointType.CONTINUOUS:
        if axis_norm(joint.axis) == 0.0:
            raise ValidationError(f"joint {joint.name!r} axis must be non-zero")
        if not isinstance(joint.limits, ContinuousLimits):
            raise ValidationError(
                f"continuous joint {joint.name!r} must use ContinuousLimits"
            )
        return

    raise ValidationError(f"unsupported joint type: {joint.type}")
