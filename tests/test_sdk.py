from __future__ import annotations

import cadquery as cq
import pytest

from mini_articraft.sdk import (
    ArticulatedObject,
    ContinuousLimits,
    JointLimits,
    JointType,
    Origin,
    ValidationError,
    export_object,
)


def shape() -> cq.Workplane:
    return cq.Workplane("XY").box(1.0, 1.0, 1.0)


def test_valid_prismatic_object() -> None:
    obj = ArticulatedObject("drawer_slide")
    base = obj.part("base", shape())
    drawer = obj.part("drawer", shape())

    joint = obj.prismatic(
        "base_to_drawer",
        base,
        drawer,
        axis=(1.0, 0.0, 0.0),
        limits=(-0.02, 0.20),
        origin=Origin(xyz=(0.0, 0.0, 0.02)),
    )

    obj.validate()
    assert obj.root_parts() == [base]
    assert joint.normalized_axis == (1.0, 0.0, 0.0)
    assert obj.to_dict()["joints"][0]["type"] == JointType.PRISMATIC.value


def test_revolute_requires_limits() -> None:
    obj = ArticulatedObject("bad_hinge")
    base = obj.part("base", shape())
    door = obj.part("door", shape())

    with pytest.raises(ValidationError, match="must include limits"):
        obj.joint("base_to_door", "revolute", base, door)


def test_fixed_joint_rejects_limits() -> None:
    obj = ArticulatedObject("bad_fixed")
    base = obj.part("base", shape())
    cover = obj.part("cover", shape())

    with pytest.raises(ValidationError, match="cannot have limits"):
        obj.joint("base_to_cover", "fixed", base, cover, limits=JointLimits(0.0, 1.0))


def test_continuous_joint_allows_unbounded_rotation() -> None:
    obj = ArticulatedObject("fan")
    frame = obj.part("frame", shape())
    rotor = obj.part("rotor", shape())

    joint = obj.continuous("frame_to_rotor", frame, rotor, limits=ContinuousLimits(effort=2.0))

    obj.validate()
    assert joint.type == JointType.CONTINUOUS
    assert joint.to_dict()["limits"] == {"effort": 2.0, "velocity": 1.0}


def test_continuous_joint_rejects_bounded_limits() -> None:
    obj = ArticulatedObject("bad_fan")
    frame = obj.part("frame", shape())
    rotor = obj.part("rotor", shape())

    with pytest.raises(ValidationError, match="must use ContinuousLimits"):
        obj.joint("frame_to_rotor", "continuous", frame, rotor, limits=(-1.0, 1.0))


def test_continuous_joint_requires_limits() -> None:
    obj = ArticulatedObject("bad_fan")
    frame = obj.part("frame", shape())
    rotor = obj.part("rotor", shape())

    with pytest.raises(ValidationError, match="must use ContinuousLimits"):
        obj.joint("frame_to_rotor", "continuous", frame, rotor)


def test_validation_rejects_multiple_roots() -> None:
    obj = ArticulatedObject("two_roots")
    obj.part("base", shape())
    obj.part("loose", shape())

    with pytest.raises(ValidationError, match="exactly one root"):
        obj.validate()


def test_duplicate_part_names_are_rejected() -> None:
    obj = ArticulatedObject("duplicate")
    obj.part("base", shape())

    with pytest.raises(ValidationError, match="duplicate part name"):
        obj.part("base", shape())


def test_part_requires_cadquery_shape() -> None:
    obj = ArticulatedObject("bad_shape")

    with pytest.raises(ValidationError, match="CadQuery"):
        obj.part("base", object())


def test_export_object_writes_part_files_and_manifest(tmp_path) -> None:
    obj = ArticulatedObject("hinge")
    base = obj.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
    door = obj.part("door", cq.Workplane("XY").box(0.8, 0.1, 1.0))
    obj.revolute("base_to_door", base, door, axis=(0.0, 0.0, 2.0), limits=(0.0, 1.57))

    result = export_object(obj, tmp_path)

    assert result.manifest.exists()
    assert result.parts["base"].exists()
    assert result.parts["door"].exists()
    assert "parts/base.step" in result.manifest.read_text()
