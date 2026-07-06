"""Reconstruction -> articulation for mini-articraft.

Provided a whole-object mesh, the agent probes/culls it into parts and rigs
joints (with physics), then emits sim-ready USD. This is mesh-in -> code-out,
distinct from the parametric CadQuery SDK.
"""
from .rig import Joint, Part, PhysicsMaterial, Rig

__all__ = ["Rig", "Part", "Joint", "PhysicsMaterial"]
