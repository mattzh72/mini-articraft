from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

import cadquery as cq

from mini_articraft.errors import ValidationError
from mini_articraft.sdk.joints import (
    ContinuousLimits,
    Joint,
    JointType,
    LimitsLike,
    Origin,
    Vec3,
    coerce_part_name,
)

CadQueryShape: TypeAlias = cq.Workplane | cq.Shape | cq.Assembly
_CADQUERY_TYPES = (cq.Workplane, cq.Shape, cq.Assembly)


@dataclass
class Part:
    name: str
    shape: CadQueryShape

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("part name must be non-empty")
        if not isinstance(self.shape, _CADQUERY_TYPES):
            raise ValidationError(
                f"part {self.name!r} shape must be a CadQuery Workplane, Shape, or Assembly"
            )


PartRef: TypeAlias = str | Part


@dataclass
class ArticulatedObject:
    name: str
    parts: list[Part] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("object name must be non-empty")

    def part(self, name: str, shape: CadQueryShape) -> Part:
        part = Part(name=name, shape=shape)
        if any(existing.name == part.name for existing in self.parts):
            raise ValidationError(f"duplicate part name: {part.name!r}")
        self.parts.append(part)
        return part

    def joint(
        self,
        name: str,
        joint_type: JointType | str,
        parent: PartRef,
        child: PartRef,
        *,
        origin: Origin | None = None,
        axis: Vec3 = (0.0, 0.0, 1.0),
        limits: LimitsLike | None = None,
    ) -> Joint:
        joint = Joint(
            name=name,
            type=joint_type,
            parent=coerce_part_name(parent, field="parent"),
            child=coerce_part_name(child, field="child"),
            origin=origin or Origin(),
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
        origin: Origin | None = None,
    ) -> Joint:
        return self.joint(name, JointType.FIXED, parent, child, origin=origin)

    def revolute(
        self,
        name: str,
        parent: PartRef,
        child: PartRef,
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
        parent: PartRef,
        child: PartRef,
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
        parent: PartRef,
        child: PartRef,
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

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "parts": [
                {"name": part.name, "shape_type": type(part.shape).__name__} for part in self.parts
            ],
            "joints": [joint.to_dict() for joint in self.joints],
        }
