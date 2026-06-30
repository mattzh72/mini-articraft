from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

from mini_articraft.errors import ValidationError

Vec3: TypeAlias = tuple[float, float, float]


class JointType(StrEnum):
    FIXED = "fixed"
    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"


def as_vec3(value: Sequence[float], *, field: str) -> Vec3:
    try:
        x, y, z = value
        return (float(x), float(y), float(z))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must have 3 numeric values") from exc


def coerce_part_name(value: str | object, *, field: str) -> str:
    name = value if isinstance(value, str) else getattr(value, "name", None)
    if not isinstance(name, str):
        raise ValidationError(f"{field} must be a part name or Part")

    name = name.strip()
    if not name:
        raise ValidationError(f"{field} must be non-empty")
    return name


@dataclass
class Origin:
    xyz: Vec3 = (0.0, 0.0, 0.0)
    rpy: Vec3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        self.xyz = as_vec3(self.xyz, field="origin.xyz")
        self.rpy = as_vec3(self.rpy, field="origin.rpy")


@dataclass
class JointLimits:
    lower: float
    upper: float
    effort: float = 1.0
    velocity: float = 1.0

    def __post_init__(self) -> None:
        self.lower = float(self.lower)
        self.upper = float(self.upper)
        self.effort = _positive(self.effort, "joint limit effort")
        self.velocity = _positive(self.velocity, "joint limit velocity")
        if self.lower > self.upper:
            raise ValidationError("joint limit lower value cannot exceed upper value")


@dataclass
class ContinuousLimits:
    effort: float = 1.0
    velocity: float = 1.0

    def __post_init__(self) -> None:
        self.effort = _positive(self.effort, "continuous joint effort")
        self.velocity = _positive(self.velocity, "continuous joint velocity")


def as_position_limits(value: tuple[float, float], *, field: str) -> JointLimits:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValidationError(f"{field} must be a (lower, upper) tuple")
    lower, upper = value
    return JointLimits(lower=lower, upper=upper)


@dataclass(eq=False)
class Joint:
    name: str
    type: JointType
    parent: str
    child: str
    origin: Origin = field(default_factory=Origin)
    axis: Vec3 = (0.0, 0.0, 1.0)
    limits: JointLimits | ContinuousLimits | None = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValidationError("joint name must be non-empty")
        if not isinstance(self.origin, Origin):
            raise ValidationError("joint origin must be an Origin")
        if not isinstance(self.type, JointType):
            raise ValidationError("joint type must be a JointType")

        self.parent = coerce_part_name(self.parent, field="parent")
        self.child = coerce_part_name(self.child, field="child")
        self.axis = as_vec3(self.axis, field="joint.axis")

    def validate(self) -> None:
        if self.parent == self.child:
            raise ValidationError(f"joint {self.name!r} parent and child cannot match")
        if self.type == JointType.FIXED:
            if self.limits is not None:
                raise ValidationError(f"fixed joint {self.name!r} cannot have limits")
            return

        if not any(self.axis):
            raise ValidationError(f"joint {self.name!r} axis must be non-zero")
        if self.type == JointType.CONTINUOUS:
            if not isinstance(self.limits, ContinuousLimits):
                raise ValidationError(f"continuous joint {self.name!r} must use ContinuousLimits")
            return
        if not isinstance(self.limits, JointLimits):
            raise ValidationError(f"joint {self.name!r} must include limits")


def _positive(value: object, field: str) -> float:
    value = float(value)
    if value <= 0.0:
        raise ValidationError(f"{field} must be positive")
    return value
