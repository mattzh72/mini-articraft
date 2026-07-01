from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdPhysics, UsdUtils

from mini_articraft.sdk._collision import MeshCollisionKernel, _build123d_shape, _rpy_matrix
from mini_articraft.sdk.joints import ContinuousLimits, Joint, JointLimits, JointType
from mini_articraft.sdk.object import ArticulatedObject, Part


@dataclass(frozen=True)
class ExportResult:
    root: Path
    manifest: Path
    usdz: Path


def export_object(
    obj: ArticulatedObject,
    output_dir: Path | str,
    *,
    mesh_tolerance: float = 0.001,
) -> ExportResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    obj.validate()

    usdz = root / "model.usdz"
    _write_usdz(obj, usdz, mesh_tolerance)

    manifest = root / "model.json"
    payload = _object_to_payload(obj) | {"files": {"usdz": usdz.relative_to(root).as_posix()}}
    manifest.write_text(json.dumps(payload, indent=2) + "\n")
    return ExportResult(root=root, manifest=manifest, usdz=usdz)


def _write_usdz(obj: ArticulatedObject, path: Path, mesh_tolerance: float) -> None:
    if mesh_tolerance <= 0.0 or not math.isfinite(mesh_tolerance):
        raise ValueError("mesh_tolerance must be a positive finite number")

    with tempfile.TemporaryDirectory(prefix="mini-articraft-usd-") as temp_dir:
        stage_path = Path(temp_dir) / "model.usdc"
        stage = Usd.Stage.CreateNew(str(stage_path))
        UsdGeom.SetStageMetersPerUnit(stage, obj.meters_per_unit)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

        world = UsdGeom.Xform.Define(stage, "/World")
        stage.SetDefaultPrim(world.GetPrim())

        object_path = f"/World/{_safe_name(obj.name)}"
        object_prim = UsdGeom.Xform.Define(stage, object_path).GetPrim()
        UsdPhysics.ArticulationRootAPI.Apply(object_prim)
        _attrs(object_prim, {"name": obj.name, "units": obj.units})

        part_paths = _write_parts(stage, f"{object_path}/parts", obj, mesh_tolerance)
        _write_joints(stage, f"{object_path}/joints", obj, part_paths)

        path.parent.mkdir(parents=True, exist_ok=True)
        stage.GetRootLayer().Save()
        if not UsdUtils.CreateNewUsdzPackage(str(stage_path), str(path)):
            raise RuntimeError(f"failed to create USDZ package: {path}")


def _write_parts(
    stage: Usd.Stage,
    scope_path: str,
    obj: ArticulatedObject,
    mesh_tolerance: float,
) -> dict[str, str]:
    UsdGeom.Scope.Define(stage, scope_path)
    transforms = MeshCollisionKernel(obj, mesh_tolerance=mesh_tolerance).world_transforms({})
    safe_names = _safe_name_map(part.name for part in obj.parts)
    paths: dict[str, str] = {}

    for part in obj.parts:
        path = f"{scope_path}/{safe_names[part.name]}"
        paths[part.name] = path
        points, faces = _mesh(part, mesh_tolerance)
        mesh = UsdGeom.Mesh.Define(stage, path)
        mesh.CreatePointsAttr(points)
        mesh.CreateFaceVertexCountsAttr([3] * len(faces))
        mesh.CreateFaceVertexIndicesAttr([i for face in faces for i in face])
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateExtentAttr(UsdGeom.Mesh.ComputeExtent(points))
        if part.color:
            mesh.CreateDisplayColorAttr([Gf.Vec3f(*part.color[:3])])
            mesh.CreateDisplayOpacityAttr([part.color[3]])

        prim = mesh.GetPrim()
        _attrs(prim, {"name": part.name})
        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdGeom.Xformable(prim).AddTransformOp().Set(_gf_matrix(transforms[part.name]))
    return paths


def _write_joints(
    stage: Usd.Stage,
    scope_path: str,
    obj: ArticulatedObject,
    part_paths: dict[str, str],
) -> None:
    UsdGeom.Scope.Define(stage, scope_path)
    safe_names = _safe_name_map(joint.name for joint in obj.joints)
    for joint in obj.joints:
        schema = _joint_schema(stage, f"{scope_path}/{safe_names[joint.name]}", joint)
        schema.CreateBody0Rel().SetTargets([part_paths[joint.parent]])
        schema.CreateBody1Rel().SetTargets([part_paths[joint.child]])
        _joint_attrs(schema.GetPrim(), joint)


def _joint_schema(stage: Usd.Stage, path: str, joint: Joint):
    if joint.type == JointType.FIXED:
        schema = UsdPhysics.FixedJoint.Define(stage, path)
        _set_joint_frames(schema, joint)
        return schema

    schema_type = (
        UsdPhysics.PrismaticJoint if joint.type == JointType.PRISMATIC else UsdPhysics.RevoluteJoint
    )
    schema = schema_type.Define(stage, path)
    schema.CreateAxisAttr("X")
    _set_joint_frames(schema, joint, rotate_axis=True)
    if isinstance(joint.limits, JointLimits):
        lower, upper = joint.limits.lower, joint.limits.upper
        if joint.type == JointType.REVOLUTE:
            # USD Physics revolute limits are degrees. The SDK stores radians.
            lower, upper = math.degrees(lower), math.degrees(upper)
        schema.CreateLowerLimitAttr(lower)
        schema.CreateUpperLimitAttr(upper)
    return schema


def _set_joint_frames(schema, joint: Joint, *, rotate_axis: bool = False) -> None:
    axis = _axis_matrix(joint.axis) if rotate_axis else Gf.Matrix4d(1.0)
    # Gf.Matrix4d composes in row-vector order, while the SDK transform stack is
    # column-vector order. Reverse composition so USD's X axis becomes the SDK
    # joint axis after the joint frame rotation.
    frame = axis * _gf_matrix(_rpy_matrix(joint.frame.rpy))
    schema.CreateLocalPos0Attr(Gf.Vec3f(*joint.frame.xyz))
    schema.CreateLocalRot0Attr(_quat(frame))
    schema.CreateLocalPos1Attr(Gf.Vec3f(0.0, 0.0, 0.0))
    schema.CreateLocalRot1Attr(_quat(axis))


def _joint_attrs(prim: Usd.Prim, joint: Joint) -> None:
    values = {
        "name": joint.name,
        "jointType": joint.type.value,
        "parent": joint.parent,
        "child": joint.child,
        "axis": Gf.Vec3d(*joint.axis),
        "frame:xyz": Gf.Vec3d(*joint.frame.xyz),
        "frame:rpy": Gf.Vec3d(*joint.frame.rpy),
    }
    if joint.limits:
        values |= {
            "limits:effort": joint.limits.effort,
            "limits:velocity": joint.limits.velocity,
        }
    if isinstance(joint.limits, JointLimits):
        values |= {"limits:lower": joint.limits.lower, "limits:upper": joint.limits.upper}
    _attrs(prim, values)


def _attrs(prim: Usd.Prim, values: dict[str, object]) -> None:
    types = {
        str: Sdf.ValueTypeNames.String,
        float: Sdf.ValueTypeNames.Double,
        Gf.Vec3d: Sdf.ValueTypeNames.Double3,
    }
    for name, value in values.items():
        prim.CreateAttribute(f"mini_articraft:{name}", types[type(value)], custom=True).Set(value)


def _mesh(part: Part, tolerance: float) -> tuple[list[Gf.Vec3f], list[tuple[int, int, int]]]:
    vertices, faces = _build123d_shape(part.shape).tessellate(tolerance)
    if not vertices or not faces:
        raise TypeError(f"part {part.name!r} produced no USD mesh triangles")
    return (
        [Gf.Vec3f(float(v.X), float(v.Y), float(v.Z)) for v in vertices],
        [tuple(int(i) for i in face) for face in faces],
    )


def _object_to_payload(obj: ArticulatedObject) -> dict[str, object]:
    return {
        "name": obj.name,
        "units": obj.units,
        "meters_per_unit": obj.meters_per_unit,
        "up_axis": "Z",
        "parts": [
            {"name": p.name, "shape_type": type(p.shape).__name__, "color": p.color}
            for p in obj.parts
        ],
        "joints": [
            {
                "name": j.name,
                "type": j.type.value,
                "parent": j.parent,
                "child": j.child,
                "frame": {"xyz": j.frame.xyz, "rpy": j.frame.rpy},
                "axis": j.axis,
                "limits": _limits(j.limits),
            }
            for j in obj.joints
        ],
    }


def _limits(limits: JointLimits | ContinuousLimits | None) -> dict[str, float] | None:
    if limits is None:
        return None
    values = {"effort": limits.effort, "velocity": limits.velocity}
    if isinstance(limits, JointLimits):
        values |= {"lower": limits.lower, "upper": limits.upper}
    return values


def _axis_matrix(axis: tuple[float, float, float]) -> Gf.Matrix4d:
    length = math.sqrt(sum(float(v) ** 2 for v in axis))
    if length <= 0.0:
        raise ValueError("joint axis must be non-zero")
    matrix = Gf.Matrix4d(1.0)
    matrix.SetRotate(
        Gf.Rotation(
            Gf.Vec3d(1.0, 0.0, 0.0),
            Gf.Vec3d(*(float(v) / length for v in axis)),
        )
    )
    return matrix


def _quat(matrix: Gf.Matrix4d) -> Gf.Quatf:
    return Gf.Quatf(matrix.ExtractRotationQuat())


def _gf_matrix(matrix) -> Gf.Matrix4d:
    rows = tuple(tuple(float(matrix[col, row]) for col in range(4)) for row in range(4))
    return Gf.Matrix4d(rows)


def _safe_name_map(names: object) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for raw in names:
        base = _safe_name(str(raw))
        name = base
        index = 2
        while name in used:
            name = f"{base}_{index}"
            index += 1
        result[str(raw)] = name
        used.add(name)
    return result


def _safe_name(value: str) -> str:
    return Tf.MakeValidIdentifier(value.strip()) or "item"
