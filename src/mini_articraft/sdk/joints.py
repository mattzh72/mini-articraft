from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import sqrt
from typing import Sequence, Union

from mini_articraft.errors import ValidationError

Vec3 = tuple[float, float, float]


class JointType(str, Enum):
    FIXED = "fixed"
    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"


def as_vec3(value: Sequence[float], *, field: str) -> Vec3:
    if len(value) != 3:
        raise ValidationError(f"{field} must have 3 values")
    return (float(value[0]), float(value[1]), float(value[2]))


def _coerce_joint_type(value: JointType | str) -> JointType:
    try:
        return value if isinstance(value, JointType) else JointType(str(value))
    except ValueError as exc:
        raise ValidationError(f"Unknown joint type: {value}") from exc


def coerce_part_name(value: str | object, *, field: str) -> str:
    name = value if isinstance(value, str) else getattr(value, "name", None)
    if not isinstance(name, str):
        raise ValidationError(f"{field} must be a part name or Part")
    name = name.strip()
    if not name:
        raise ValidationError(f"{field} must be non-empty")
    return name


def axis_norm(axis: Vec3) -> float:
    return sqrt(sum(value * value for value in axis))


@dataclass(frozen=True)
class Origin:
    xyz: Vec3 = (0.0, 0.0, 0.0)
    rpy: Vec3 = (0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "xyz", as_vec3(self.xyz, field="origin.xyz"))
        object.__setattr__(self, "rpy", as_vec3(self.rpy, field="origin.rpy"))


@dataclass(frozen=True)
class JointLimits:
    lower: float
    upper: float
    effort: float = 1.0
    velocity: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower", float(self.lower))
        object.__setattr__(self, "upper", float(self.upper))
        object.__setattr__(self, "effort", float(self.effort))
        object.__setattr__(self, "velocity", float(self.velocity))
        if self.lower > self.upper:
            raise ValidationError("joint limit lower value cannot exceed upper value")
        if self.effort <= 0.0:
            raise ValidationError("joint limit effort must be positive")
        if self.velocity <= 0.0:
            raise ValidationError("joint limit velocity must be positive")

    def to_dict(self) -> dict[str, float]:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "effort": self.effort,
            "velocity": self.velocity,
        }


@dataclass(frozen=True)
class ContinuousLimits:
    effort: float = 1.0
    velocity: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "effort", float(self.effort))
        object.__setattr__(self, "velocity", float(self.velocity))
        if self.effort <= 0.0:
            raise ValidationError("continuous joint effort must be positive")
        if self.velocity <= 0.0:
            raise ValidationError("continuous joint velocity must be positive")

    def to_dict(self) -> dict[str, float]:
        return {
            "effort": self.effort,
            "velocity": self.velocity,
        }


LimitsLike = Union[JointLimits, ContinuousLimits, Sequence[float]]


def coerce_limits(value: LimitsLike | None) -> JointLimits | None:
    if value is None:
        return None
    if isinstance(value, (JointLimits, ContinuousLimits)):
        return value
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValidationError("limits must be JointLimits or a (lower, upper) pair")
    if len(value) != 2:
        raise ValidationError("limits must be a (lower, upper) pair")
    return JointLimits(lower=value[0], upper=value[1])


@dataclass(frozen=True)
class Joint:
    name: str
    type: JointType | str
    parent: str
    child: str
    origin: Origin = Origin()
    axis: Vec3 = (0.0, 0.0, 1.0)
    limits: JointLimits | ContinuousLimits | None = None

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ValidationError("joint name must be non-empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "type", _coerce_joint_type(self.type))
        object.__setattr__(self, "parent", coerce_part_name(self.parent, field="parent"))
        object.__setattr__(self, "child", coerce_part_name(self.child, field="child"))
        object.__setattr__(self, "axis", as_vec3(self.axis, field="joint.axis"))
        object.__setattr__(self, "limits", coerce_limits(self.limits))

    @property
    def normalized_axis(self) -> Vec3:
        norm = axis_norm(self.axis)
        if norm == 0.0:
            return self.axis
        return (self.axis[0] / norm, self.axis[1] / norm, self.axis[2] / norm)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "type": self.type.value,
            "parent": self.parent,
            "child": self.child,
            "origin": {"xyz": self.origin.xyz, "rpy": self.origin.rpy},
            "axis": self.axis,
            "limits": None if self.limits is None else self.limits.to_dict(),
        }
