from __future__ import annotations

import cadquery as cq
import pytest

import mini_articraft.sdk as sdk
from mini_articraft.sdk import (
    ArticulatedObject,
    Frame,
    ValidationError,
)


def shape() -> cq.Workplane:
    return cq.Workplane("XY").box(1.0, 1.0, 1.0)


def test_articulated_object_units_are_explicit_and_validated() -> None:
    assert ArticulatedObject("unit_test", units="millimeters").meters_per_unit == 0.001
    with pytest.raises(ValidationError, match="units"):
        ArticulatedObject("missing_units")
    with pytest.raises(ValidationError, match="unsupported units"):
        ArticulatedObject("bad_units", units="cubits")


def test_origin_is_not_public_sdk_api() -> None:
    assert not hasattr(sdk, "Origin")


def test_part_color_is_normalized_and_validated() -> None:
    obj = ArticulatedObject("color", units="meters")
    assert obj.part("base", shape(), color=(0.1, 0.2, 0.3)).color == (0.1, 0.2, 0.3, 1.0)
    with pytest.raises(ValidationError, match="between 0.0 and 1.0"):
        obj.part("bad", shape(), color=(1.2, 0.0, 0.0))


def test_valid_prismatic_object() -> None:
    obj = ArticulatedObject("drawer_slide", units="meters")
    obj.part("base", shape())
    drawer = obj.part("drawer", shape())

    obj.prismatic(
        "base_to_drawer",
        "base",
        drawer,
        axis=(1.0, 0.0, 0.0),
        limits=(-0.02, 0.20),
        frame=Frame(xyz=(0.0, 0.0, 0.02)),
    )

    obj.validate()
    assert obj.joints[0].type.value == "prismatic"
    assert obj.joints[0].frame == Frame(xyz=(0.0, 0.0, 0.02))
    assert obj.joints[0].limits is not None
    assert obj.joints[0].limits.lower == -0.02
    assert obj.joints[0].limits.upper == 0.20


def test_revolute_requires_limits_argument() -> None:
    obj = ArticulatedObject("bad_hinge", units="meters")
    base = obj.part("base", shape())
    door = obj.part("door", shape())

    with pytest.raises(TypeError):
        obj.revolute("base_to_door", base, door)


def test_revolute_limits_must_be_tuple() -> None:
    obj = ArticulatedObject("bad_fixed", units="meters")
    base = obj.part("base", shape())
    cover = obj.part("cover", shape())

    with pytest.raises(ValidationError, match="tuple"):
        obj.revolute("base_to_cover", base, cover, limits=[0.0, 1.0])


def test_continuous_joint_allows_unbounded_rotation() -> None:
    obj = ArticulatedObject("fan", units="meters")
    frame = obj.part("frame", shape())
    rotor = obj.part("rotor", shape())

    joint = obj.continuous("frame_to_rotor", frame, rotor)

    obj.validate()
    assert joint.type.value == "continuous"
    assert joint.limits is not None
    assert joint.limits.effort == 1.0
    assert joint.limits.velocity == 1.0


def test_continuous_joint_does_not_accept_manual_limits() -> None:
    obj = ArticulatedObject("bad_fan", units="meters")
    frame = obj.part("frame", shape())
    rotor = obj.part("rotor", shape())

    with pytest.raises(TypeError):
        obj.continuous("frame_to_rotor", frame, rotor, limits=(0.0, 1.0))


def test_validation_rejects_multiple_roots() -> None:
    obj = ArticulatedObject("two_roots", units="meters")
    obj.part("base", shape())
    obj.part("loose", shape())

    with pytest.raises(ValidationError, match="exactly one root"):
        obj.validate()


def test_duplicate_part_names_are_rejected() -> None:
    obj = ArticulatedObject("duplicate", units="meters")
    obj.part("base", shape())

    with pytest.raises(ValidationError, match="duplicate part name"):
        obj.part("base", shape())


def test_part_requires_cadquery_shape() -> None:
    obj = ArticulatedObject("bad_shape", units="meters")

    with pytest.raises(ValidationError, match="CadQuery"):
        obj.part("base", object())
