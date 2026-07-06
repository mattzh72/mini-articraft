"""Emit a Rig to USD with physics: rigid bodies + mesh colliders + PhysicsMaterial
(friction) + revolute/prismatic joints (axis, limits). Sim-ready for Isaac/USD.
"""
from __future__ import annotations

import math

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

from .rig import Rig


def _quat_x_to(axis) -> Gf.Quatf:
    """Quaternion (w, xyz) rotating the joint's local +X onto `axis`."""
    a = np.array([1.0, 0.0, 0.0])
    b = np.asarray(axis, float)
    b = b / (np.linalg.norm(b) + 1e-12)
    d = float(np.dot(a, b))
    if d > 0.999999:
        return Gf.Quatf(1.0, Gf.Vec3f(0, 0, 0))
    if d < -0.999999:
        perp = np.cross(a, [0, 1, 0])
        perp = perp / np.linalg.norm(perp)
        return Gf.Quatf(0.0, Gf.Vec3f(*perp.tolist()))
    c = np.cross(a, b)
    s = math.sqrt((1.0 + d) * 2.0)
    q = c / s
    return Gf.Quatf(s / 2.0, Gf.Vec3f(float(q[0]), float(q[1]), float(q[2])))


def _add_mesh(stage, parent_path: str, part) -> str:
    m = part.mesh
    V = np.asarray(m.vertices, dtype=float)
    F = np.asarray(m.faces, dtype=int)
    mesh_path = f"{parent_path}/geom"
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)
    mesh.CreatePointsAttr([Gf.Vec3f(*p) for p in V.tolist()])
    mesh.CreateFaceVertexCountsAttr([3] * len(F))
    mesh.CreateFaceVertexIndicesAttr(F.flatten().tolist())
    mesh.CreateDisplayColorAttr([Gf.Vec3f(*part.color)])
    mesh.CreateDoubleSidedAttr(True)
    return mesh_path


def write_usd(rig: Rig, path: str) -> str:
    stage = Usd.Stage.CreateNew(path) if not path else Usd.Stage.CreateNew(path)
    UsdGeom.SetStageMetersPerUnit(stage, rig.meters_per_unit)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z if rig.up_axis.upper() == "Z" else UsdGeom.Tokens.y)

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdPhysics.Scene.Define(stage, "/World/physicsScene")

    # shared physics materials (dedup by friction)
    mats: dict[float, str] = {}
    def material_for(friction: float, restitution: float) -> str:
        key = round(friction, 4)
        if key in mats:
            return mats[key]
        mpath = f"/World/materials/mat_{str(key).replace('.', '_')}"
        UsdGeom.Scope.Define(stage, "/World/materials")
        mat = UsdShade.Material.Define(stage, mpath)
        api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
        api.CreateStaticFrictionAttr(friction)
        api.CreateDynamicFrictionAttr(friction)
        api.CreateRestitutionAttr(restitution)
        mats[key] = mpath
        return mpath

    # parts -> rigid bodies with mesh collider + mass + material
    for p in rig.parts:
        xf_path = f"/World/{p.name}"
        xf = UsdGeom.Xform.Define(stage, xf_path)
        UsdPhysics.RigidBodyAPI.Apply(xf.GetPrim())
        massapi = UsdPhysics.MassAPI.Apply(xf.GetPrim())
        massapi.CreateMassAttr(float(p.mass))
        mesh_path = _add_mesh(stage, xf_path, p)
        mesh_prim = stage.GetPrimAtPath(mesh_path)
        UsdPhysics.CollisionAPI.Apply(mesh_prim)
        if p.collision != "none":
            mc = UsdPhysics.MeshCollisionAPI.Apply(mesh_prim)
            mc.CreateApproximationAttr(p.collision)
        mpath = material_for(p.material.static_friction, p.material.restitution)
        UsdShade.MaterialBindingAPI(mesh_prim).Bind(
            UsdShade.Material(stage.GetPrimAtPath(mpath)),
            bindingStrength=UsdShade.Tokens.weakerThanDescendants,
            materialPurpose="physics",
        )

    # anchor the base to the world with a fixed joint
    base = rig.base()
    if base is not None:
        fj = UsdPhysics.FixedJoint.Define(stage, f"/World/{base}_anchor")
        fj.CreateBody1Rel().SetTargets([f"/World/{base}"])

    # joints
    for j in rig.joints:
        jpath = f"/World/joints/{j.name}"
        UsdGeom.Scope.Define(stage, "/World/joints")
        if j.jtype == "prismatic":
            joint = UsdPhysics.PrismaticJoint.Define(stage, jpath)
        elif j.jtype == "fixed":
            joint = UsdPhysics.FixedJoint.Define(stage, jpath)
        else:  # revolute / continuous
            joint = UsdPhysics.RevoluteJoint.Define(stage, jpath)
        joint.CreateBody0Rel().SetTargets([f"/World/{j.parent}"])
        joint.CreateBody1Rel().SetTargets([f"/World/{j.child}"])
        # bodies are Xforms at identity (mesh in world coords) -> local frame == world
        origin = Gf.Vec3f(*[float(x) for x in j.origin])
        rot = _quat_x_to(j.axis)
        if j.jtype not in ("fixed",):
            joint.CreateAxisAttr("X")  # local +X; localRot orients it onto j.axis
        joint.CreateLocalPos0Attr(origin)
        joint.CreateLocalPos1Attr(origin)
        joint.CreateLocalRot0Attr(rot)
        joint.CreateLocalRot1Attr(rot)
        if j.jtype in ("revolute",):
            joint.CreateLowerLimitAttr(math.degrees(j.lower))
            joint.CreateUpperLimitAttr(math.degrees(j.upper))
        elif j.jtype == "prismatic":
            joint.CreateLowerLimitAttr(float(j.lower))
            joint.CreateUpperLimitAttr(float(j.upper))
        # (continuous = revolute with no limit attrs)

    stage.GetRootLayer().Save()
    return path
