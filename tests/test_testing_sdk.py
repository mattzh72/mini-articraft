from __future__ import annotations

import pytest
from build123d import Box, Compound, Pos, Shape

import mini_articraft.sdk._collision as collision_kernel
from mini_articraft.errors import ValidationError
from mini_articraft.sdk import (
    AllowedOverlap,
    ArticulatedObject,
    Frame,
    TestContext,
)


def box(size: float = 1.0) -> Shape:
    return Box(size, size, size)


def compound_boxes(offset: float) -> Compound:
    first = Box(1.0, 1.0, 1.0)
    second = Pos(X=offset) * Box(1.0, 1.0, 1.0)
    return Compound(children=[first, second])


def test_report_records_checks_warnings_and_allowances() -> None:
    model = ArticulatedObject("report", units="meters")
    model.part("base", box())
    ctx = TestContext(model)

    ctx.check("custom pass", True)
    ctx.warn("non-blocking note")
    ctx.allow_isolated_part("base", reason="display stand")
    ctx.allow_overlap("base", "base", reason="self allowance is only recorded")

    report = ctx.report()

    assert report.passed
    assert report.checks == ("custom pass",)
    assert report.warnings == ("non-blocking note",)
    assert report.allowances == (
        "allow_isolated_part('base'): display stand",
        "allow_overlap('base', 'base'): self allowance is only recorded",
    )
    assert report.allowed_isolated_parts == ("base",)
    assert report.allowed_overlaps == (
        AllowedOverlap("base", "base", "self allowance is only recorded"),
    )


def test_expect_collision_and_no_collision_use_mesh_queries() -> None:
    model = ArticulatedObject("collisions", units="meters")
    root = model.part("root", box(0.1))
    left = model.part("left", box())
    far = model.part("far", box())
    overlapping = model.part("overlapping", box())
    model.fixed("root_to_left", root, left)
    model.fixed("root_to_far", root, far, frame=Frame(xyz=(3.0, 0.0, 0.0)))
    model.fixed("root_to_overlapping", root, overlapping, frame=Frame(xyz=(0.25, 0.0, 0.0)))
    ctx = TestContext(model)

    assert ctx.expect_no_collision("left", "far")
    assert ctx.expect_collision("left", "overlapping")

    report = ctx.report()
    assert report.passed
    assert report.checks == (
        "expect_no_collision(left,far)",
        "expect_collision(left,overlapping)",
    )


def test_expect_distance_and_contact_use_fcl_distance() -> None:
    model = ArticulatedObject("distance", units="meters")
    left = model.part("left", box())
    right = model.part("right", box())
    model.fixed("left_to_right", left, right, frame=Frame(xyz=(2.0, 0.0, 0.0)))
    ctx = TestContext(model)

    assert ctx.expect_distance("left", "right", min_distance=0.99, max_distance=1.01)
    assert not ctx.expect_contact("left", "right", contact_tol=0.1)

    report = ctx.report()
    assert not report.passed
    assert report.failures[0].name == "expect_contact(left,right)"
    assert "distance=1" in report.failures[0].details


def test_mesh_cache_uses_shape_identity() -> None:
    model = ArticulatedObject("cache", units="meters")
    left = model.part("left", box())
    right = model.part("right", box())
    model.fixed("left_to_right", left, right, frame=Frame(xyz=(3.0, 0.0, 0.0)))
    ctx = TestContext(model)

    assert ctx.expect_no_collision("left", "right")

    right.shape = box(6.0)

    assert ctx.expect_collision("left", "right")
    assert ctx.report().passed


def test_expect_gap_and_within_use_mesh_vertex_projections() -> None:
    model = ArticulatedObject("projections", units="meters")
    outer = model.part("outer", box(3.0))
    inner = model.part("inner", box(1.0))
    right = model.part("right", box(1.0))
    model.fixed("outer_to_inner", outer, inner)
    model.fixed("outer_to_right", outer, right, frame=Frame(xyz=(2.0, 0.0, 0.0)))
    ctx = TestContext(model)

    assert ctx.expect_within("inner", "outer", axes="xyz")
    assert ctx.expect_gap("right", "inner", axis="x", min_gap=0.99, max_gap=1.01)

    assert ctx.report().passed


def test_pose_rejects_unknown_joint_name() -> None:
    model = ArticulatedObject("pose", units="meters")
    model.part("base", box())
    ctx = TestContext(model)

    with pytest.raises(ValidationError, match="Unknown joint"), ctx.pose(missing=1.0):
        pass


def test_pose_context_changes_mesh_collision_state_and_restores() -> None:
    model = ArticulatedObject("pose", units="meters")
    base = model.part("base", box())
    slider = model.part("slider", box())
    model.prismatic(
        "base_to_slider",
        base,
        slider,
        axis=(1.0, 0.0, 0.0),
        limits=(-1.5, 0.0),
        frame=Frame(xyz=(2.0, 0.0, 0.0)),
    )
    ctx = TestContext(model)

    assert ctx.expect_no_collision("base", "slider")
    rest_position = ctx.part_world_position("slider")
    with ctx.pose({"base_to_slider": -1.25}):
        posed_position = ctx.part_world_position("slider")
        assert ctx.expect_collision("base", "slider")
    restored_position = ctx.part_world_position("slider")

    assert rest_position == restored_position
    assert posed_position is not None and rest_position is not None
    assert posed_position[0] < rest_position[0]
    assert ctx.report().passed


def test_baseline_collision_check_uses_fcl_broadphase_manager(monkeypatch) -> None:
    real_manager = collision_kernel.fcl.DynamicAABBTreeCollisionManager
    calls = {"created": 0, "collide": 0}

    class SpyManager:
        def __init__(self) -> None:
            calls["created"] += 1
            self._inner = real_manager()

        def registerObjects(self, objects):
            return self._inner.registerObjects(objects)

        def setup(self):
            return self._inner.setup()

        def collide(self, data, callback):
            calls["collide"] += 1
            return self._inner.collide(data, callback)

    monkeypatch.setattr(collision_kernel.fcl, "DynamicAABBTreeCollisionManager", SpyManager)

    model = ArticulatedObject("manager", units="meters")
    root = model.part("root", Box(3.0, 3.0, 0.1))
    part_a = model.part("part_a", box())
    part_b = model.part("part_b", box())
    model.fixed("root_to_a", root, part_a, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    model.fixed("root_to_b", root, part_b, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    ctx = TestContext(model)

    assert not ctx.fail_if_parts_collide_in_current_pose()

    assert calls == {"created": 1, "collide": 1}
    assert "part_a" in ctx.report().failures[0].details
    assert "part_b" in ctx.report().failures[0].details


def test_allow_overlap_suppresses_only_baseline_collision() -> None:
    model = ArticulatedObject("allowance", units="meters")
    root = model.part("root", Box(3.0, 3.0, 0.1))
    shaft = model.part("shaft", box())
    hub = model.part("hub", box())
    model.fixed("root_to_shaft", root, shaft, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    model.fixed("root_to_hub", root, hub, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    ctx = TestContext(model)

    ctx.allow_overlap("shaft", "hub", reason="captured shaft")
    assert ctx.fail_if_parts_collide_in_current_pose()
    assert not ctx.expect_no_collision("shaft", "hub")

    report = ctx.report()
    assert not report.passed
    assert report.failures[0].name == "expect_no_collision(shaft,hub)"


def test_fail_if_part_contains_disconnected_geometry_islands_records_failure() -> None:
    model = ArticulatedObject("disconnected", units="meters")
    model.part("base", compound_boxes(1.2))
    ctx = TestContext(model)

    assert not ctx.fail_if_part_contains_disconnected_geometry_islands()

    report = ctx.report()
    assert not report.passed
    assert report.failures[0].name == (
        "fail_if_part_contains_disconnected_geometry_islands(contact_tol=1e-06)"
    )
    assert "Disconnected geometry islands detected" in report.failures[0].details
    assert "part='base' connected=1/2" in report.failures[0].details
    assert "solid_002 nearest=solid_001 distance=0.2" in report.failures[0].details


def test_fail_if_part_contains_disconnected_geometry_islands_allows_contacting_solids() -> None:
    model = ArticulatedObject("connected", units="meters")
    model.part("base", compound_boxes(1.0))
    ctx = TestContext(model)

    assert ctx.fail_if_part_contains_disconnected_geometry_islands()
    assert ctx.report().passed
