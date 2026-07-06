"""Mesh-backed articulated rig: the code the agent writes.

A rig is parts (chunks of the provided mesh + physics) + joints between them.
This is deliberately NOT the parametric CadQuery SDK: here geometry comes from a
reconstructed mesh, and the agent's job is to cull the mesh into parts and rig
joints, then emit USD (with friction/mass/limits) for simulation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import trimesh

Vec3 = tuple[float, float, float]


@dataclass
class PhysicsMaterial:
    static_friction: float = 0.5
    dynamic_friction: float = 0.5
    restitution: float = 0.0


@dataclass
class Part:
    name: str
    mesh: trimesh.Trimesh  # a culled chunk of the whole object, in the shared world frame
    mass: float = 1.0
    material: PhysicsMaterial = field(default_factory=PhysicsMaterial)
    color: Vec3 = (0.72, 0.6, 0.46)
    # convexDecomposition, NOT convexHull: a hull fills cavities, so drawers
    # physically can't slide into a hull-collided cabinet in sim
    collision: str = "convexDecomposition"


@dataclass
class Joint:
    name: str
    jtype: str  # "revolute" | "prismatic" | "fixed" | "continuous"
    parent: str
    child: str
    origin: Vec3  # a point on the joint axis, in the shared world frame
    axis: Vec3 = (0.0, 0.0, 1.0)  # unit direction of the axis
    lower: float = 0.0  # radians (revolute) or meters (prismatic)
    upper: float = 0.0
    damping: float = 0.0
    friction: float = 0.0

    def __post_init__(self) -> None:
        a = np.asarray(self.axis, float)
        n = np.linalg.norm(a)
        self.axis = tuple((a / n).tolist()) if n > 1e-9 else (0.0, 0.0, 1.0)


@dataclass
class Rig:
    name: str
    parts: list[Part] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    up_axis: str = "Z"
    meters_per_unit: float = 1.0

    def add_part(self, name: str, mesh: trimesh.Trimesh, *, mass: float = 1.0,
                 friction: float = 0.5, color: Vec3 = (0.72, 0.6, 0.46),
                 collision: str = "convexDecomposition") -> Part:
        p = Part(name=name, mesh=mesh, mass=mass,
                 material=PhysicsMaterial(static_friction=friction, dynamic_friction=friction),
                 color=color, collision=collision)
        self.parts.append(p)
        return p

    def add_joint(self, name: str, jtype: str, parent: str, child: str, *, origin: Vec3,
                  axis: Vec3 = (0.0, 0.0, 1.0), lower: float = 0.0, upper: float = 0.0,
                  damping: float = 0.0, friction: float = 0.0) -> Joint:
        j = Joint(name=name, jtype=jtype, parent=parent, child=child, origin=origin,
                  axis=axis, lower=lower, upper=upper, damping=damping, friction=friction)
        self.joints.append(j)
        return j

    # ---- convenience ----------------------------------------------------
    def part(self, name: str) -> Part:
        return next(p for p in self.parts if p.name == name)

    def base(self) -> Optional[str]:
        """The part that is never a joint child = the fixed root."""
        children = {j.child for j in self.joints}
        for p in self.parts:
            if p.name not in children:
                return p.name
        return self.parts[0].name if self.parts else None

    def to_usd(self, path: str) -> str:
        from .usd import write_usd
        return write_usd(self, path)

    def summary(self) -> str:
        lines = [f"Rig({self.name}): {len(self.parts)} parts, {len(self.joints)} joints, base={self.base()}"]
        for p in self.parts:
            lines.append(f"  part {p.name}: {len(p.mesh.faces)}f mass={p.mass} "
                         f"friction={p.material.static_friction} collision={p.collision}")
        for j in self.joints:
            lines.append(f"  joint {j.name} [{j.jtype}] {j.parent}->{j.child} "
                         f"axis={tuple(round(x,2) for x in j.axis)} "
                         f"origin={tuple(round(x,3) for x in j.origin)} "
                         f"limits=({round(math.degrees(j.lower)) if j.jtype in ('revolute','continuous') else j.lower},"
                         f"{round(math.degrees(j.upper)) if j.jtype in ('revolute','continuous') else j.upper})")
        return "\n".join(lines)
