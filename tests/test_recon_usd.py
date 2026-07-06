"""The recon backbone: mesh-backed rig -> sim-ready USD with physics."""
from __future__ import annotations

import math

import trimesh
from pxr import Usd, UsdGeom, UsdPhysics

from mini_articraft.recon import Rig


def _cabinet_rig() -> Rig:
    body = trimesh.creation.box(extent=[0.40, 0.50, 0.60])
    body.apply_translation([0, 0, 0.30])
    door = trimesh.creation.box(extent=[0.02, 0.48, 0.58])
    door.apply_translation([0.205, 0, 0.30])
    rig = Rig(name="cabinet")
    rig.add_part("body", body, mass=5.0, friction=0.6)
    rig.add_part("door", door, mass=1.0, friction=0.5)
    rig.add_joint("door_hinge", "revolute", "body", "door",
                  origin=(0.205, -0.24, 0.30), axis=(0, 0, 1),
                  lower=0.0, upper=math.radians(95))
    return rig


def test_rig_base_is_non_child():
    assert _cabinet_rig().base() == "body"


def test_emits_valid_physics_usd(tmp_path):
    out = str(tmp_path / "cabinet.usda")
    _cabinet_rig().to_usd(out)

    stage = Usd.Stage.Open(out)
    assert stage is not None

    bodies = [p.GetName() for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    assert set(bodies) == {"body", "door"}

    joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.RevoluteJoint)]
    assert len(joints) == 1
    j = UsdPhysics.RevoluteJoint(joints[0])
    assert round(j.GetUpperLimitAttr().Get()) == 95

    mats = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.MaterialAPI)]
    frictions = {round(UsdPhysics.MaterialAPI(p).GetStaticFrictionAttr().Get(), 2) for p in mats}
    assert frictions == {0.6, 0.5}

    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z
