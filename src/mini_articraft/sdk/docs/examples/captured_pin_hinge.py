"""A captured-pin hinge: barrel integral to the lid, pin in the base, stays connected open.

A hinged lid, door, or laptop pivots on a barrel that wraps a pin. Model it as two
clean pieces, not a pile of lugs and tongues:

  1. The PIN belongs to the stationary part (`base`): a thin cylinder on the hinge axis.
  2. The BARREL belongs to the moving part (`lid`) and is INTEGRAL to it -- it overlaps
     the lid's own body, so it is part of the lid, not a separate floating knuckle.
  3. The barrel wraps the pin (a captured pin): declare that one intended cross-part
     overlap with `allow_overlap`.
  4. Put the articulation origin exactly on the pin axis, so the barrel stays centered
     on the pin through the whole swing -- the lid never separates when it opens.

Keep the hinge above/behind the body so the barrel does not dip into the base. This is
the clean alternative to bridging a lid to a body with support lugs and blend blocks.
"""

from __future__ import annotations

import math

from mini_articraft.sdk import (
    ArticulatedObject,
    ArticulationType,
    BoxGeometry,
    CylinderGeometry,
    MotionLimits,
    Origin,
    TestContext,
    TestReport,
)

PIN_Y = 0.082
PIN_Z = 0.092


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("hinged_box")

    base = model.part("base")
    base.add(
        BoxGeometry((0.20, 0.15, 0.08)).translate(0.0, 0.0, 0.04),
        name="box_body",
        color=(0.30, 0.32, 0.36),
    )
    # Stationary pin on the hinge axis, held above/behind the body's rear-top edge.
    base.add(
        CylinderGeometry(0.006, 0.19, radial_segments=32)
        .rotate_y(math.pi / 2)
        .translate(0.0, PIN_Y, PIN_Z),
        name="hinge_pin",
        color=(0.10, 0.10, 0.11),
    )

    lid = model.part("lid")
    # The lid part is authored in a local frame whose origin sits at the hinge origin
    # (the pin). So the barrel is at the local origin, and the plate is offset forward
    # of the pin (-y) to cover the top.
    lid.add(
        BoxGeometry((0.19, 0.175, 0.012)).translate(0.0, -PIN_Y, 0.088 - PIN_Z),
        name="lid_plate",
        color=(0.62, 0.64, 0.68),
    )
    # Barrel is INTEGRAL to the lid (overlaps the plate) and wraps the pin at the origin.
    lid.add(
        CylinderGeometry(0.011, 0.16, radial_segments=32).rotate_y(math.pi / 2),
        name="lid_hinge_barrel",
        color=(0.62, 0.64, 0.68),
    )

    model.articulation(
        "lid_hinge",
        ArticulationType.REVOLUTE,
        base,
        lid,
        origin=Origin(xyz=(0.0, PIN_Y, PIN_Z)),
        axis=(-1.0, 0.0, 0.0),  # positive motion lifts the front of the lid upward
        motion_limits=MotionLimits(lower=0.0, upper=1.9),
    )
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    ctx.allow_overlap(
        "lid",
        "base",
        shape_a="lid_hinge_barrel",
        shape_b="hinge_pin",
        reason="The lid's hinge barrel is captured around the base's stationary pin.",
    )
    ctx.expect_collision(
        "base",
        "lid",
        shape_a="hinge_pin",
        shape_b="lid_hinge_barrel",
        name="barrel_captures_the_pin",
    )
    # The barrel is part of the lid, not a floating knuckle.
    ctx.expect_collision(
        "lid",
        "lid",
        shape_a="lid_plate",
        shape_b="lid_hinge_barrel",
        name="barrel_is_integral_to_the_lid",
    )
    # The lid must stay attached to the base through the whole open sweep.
    ctx.fail_if_articulation_separates_child()
    return ctx.report()
