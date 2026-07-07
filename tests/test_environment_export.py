from __future__ import annotations

import json
import math

from build123d import Box
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdValidation

from mini_articraft.environments.export import export_object
from mini_articraft.sdk import ArticulatedObject, Frame


def test_export_object_writes_valid_usdz_and_manifest(tmp_path) -> None:
    result = export_object(_hinge(), tmp_path)

    manifest = json.loads(result.manifest.read_text())
    stage = Usd.Stage.Open(str(result.usdz))

    assert result.usdz.exists()
    assert not (tmp_path / "parts").exists()
    assert result.usdz == tmp_path / "usdz" / "0000.usdz"
    assert manifest["files"] == {"usdz": "usdz/0000.usdz"}
    assert manifest["units"] == "meters"
    assert manifest["parts"][0]["color"] == [0.6, 0.6, 0.65, 1.0]

    assert stage.GetDefaultPrim().GetPath().pathString == "/World"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    assert UsdGeom.GetStageUpAxis(stage) == "Z"

    base = stage.GetPrimAtPath("/World/hinge/parts/base")
    assert base.GetTypeName() == "Mesh"
    assert base.HasAPI(UsdPhysics.RigidBodyAPI)
    assert tuple(
        round(float(v), 6) for v in base.GetAttribute("primvars:displayColor").Get()[0]
    ) == (
        0.6,
        0.6,
        0.65,
    )

    joint_prim = stage.GetPrimAtPath("/World/hinge/joints/base_to_door")
    joint = UsdPhysics.RevoluteJoint.Get(stage, joint_prim.GetPath())
    assert joint_prim.GetAttribute("mini_articraft:jointType").Get() == "revolute"
    assert tuple(joint_prim.GetAttribute("mini_articraft:axis").Get()) == (0.0, 1.0, 1.0)
    assert joint.GetAxisAttr().Get() == "X"
    assert _joint_x_axis(joint) == (-0.074758, 0.71704, 0.693012)
    assert math.isclose(joint.GetUpperLimitAttr().Get(), math.degrees(1.57), abs_tol=1e-5)

    validators = UsdValidation.ValidationRegistry().GetOrLoadValidatorsByName(
        [
            "usdUtilsValidators:UsdzPackageValidator",
            "usdGeomValidators:StageMetadataChecker",
            "usdValidation:CompositionErrorTest",
            "usdPhysicsValidators:RigidBodyChecker",
            "usdPhysicsValidators:PhysicsJointChecker",
            "usdPhysicsValidators:ArticulationChecker",
        ]
    )

    assert UsdValidation.ValidationContext(validators).Validate(stage) == []


def _hinge() -> ArticulatedObject:
    obj = ArticulatedObject("hinge", units="meters")
    base = obj.part("base", Box(1.0, 1.0, 0.2), color=(0.6, 0.6, 0.65))
    door = obj.part("door", Box(0.8, 0.1, 1.0), color=(0.2, 0.35, 0.8))
    obj.revolute(
        "base_to_door",
        base,
        door,
        frame=Frame(xyz=(0.0, 0.0, 0.2), rpy=(0.0, 0.2, 0.3)),
        axis=(0.0, 1.0, 1.0),
        limits=(0.0, 1.57),
    )
    return obj


def _joint_x_axis(joint: UsdPhysics.RevoluteJoint) -> tuple[float, float, float]:
    matrix = Gf.Matrix4d(1.0)
    matrix.SetRotate(joint.GetLocalRot0Attr().Get())
    vector = matrix.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0)).GetNormalized()
    x, y, z = (round(float(component), 6) for component in vector)
    return (x, y, z)
