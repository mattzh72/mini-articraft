"""House a mechanism inside a molded housing -- never bolt hardware onto a surface.

The pattern (a flip-lid canister here; the same pattern is a kettle's rear assembly,
a pedal bin's lid mechanism, a travel mug's flip cap):

  1. TANGENT CONTACT IS NOT ATTACHMENT. A piece resting on a curved surface touches
     at a point or a line -- zero area. That is touching, not fusion. Every attached
     piece must be embedded PAST the surface so the volumes overlap, and then welded:
     the weld bead fills the mismatch like filler metal, so pieces never need to
     conform to the surface they join.
  2. The moving part's socket is CARVED, not assembled. Bore a channel through the
     housing for the pivot barrel and cut a narrow slot for its arm
     (`boolean_difference`). The mechanism is voids in one solid -- no knuckles, no
     brackets, no separate pins.
  3. The moving part is ONE welded piece: lid + arm + barrel fused with `weld`.
  4. Clearances do the capturing. The barrel (r 5 mm) spins freely in the channel
     (r 6.5 mm) but cannot fit through the slot (4.5 mm) -- only the thin arm (3.5 mm)
     passes. Nothing fastens the lid; the carved geometry traps it, like a door
     hinge pin in its sleeve. The slot's angular span IS the swing range.
  5. The housing FAIRS into the body: lofted thin where it emerges from the wall,
     full depth at the pivot. Controls sit IN recesses cut into the housing, proud
     by a couple of millimetres -- never stuck onto a bare surface.
  6. `weld(..., trim=cavity)` removes anything that pokes through a hollow body's
     wall into the interior.
"""

from __future__ import annotations

import math

from mini_articraft.sdk import (
    ArticulatedObject,
    ArticulationType,
    BoxGeometry,
    CylinderGeometry,
    LatheGeometry,
    LoftGeometry,
    MotionLimits,
    Origin,
    RoundedBoxGeometry,
    TestContext,
    TestReport,
    boolean_difference,
    rounded_rect_profile,
    weld,
)

HINGE_Y, HINGE_Z = -0.049, 0.126  # the pivot axis, just behind the rim


def _slot_segment(angle_deg: float) -> BoxGeometry:
    """One segment of the slot the lid's arm swings through, radiating from the axis."""
    angle = math.radians(angle_deg)
    length = 0.024
    segment = BoxGeometry((0.030, length, 0.0045)).rotate_x(angle)
    return segment.translate(
        0.0, HINGE_Y + (length / 2) * math.cos(angle), HINGE_Z + (length / 2) * math.sin(angle)
    )


def _housing_ring(z: float, depth: float, center_y: float) -> list[tuple[float, float, float]]:
    points = rounded_rect_profile(0.052, depth, min(0.005, depth * 0.45), corner_segments=8)
    return [(x, y + center_y, z) for x, y in points]


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("flip_lid_canister")
    canister = model.part("canister")

    body = LatheGeometry(
        [
            (0.0, 0.0),
            (0.042, 0.0),
            (0.045, 0.003),
            (0.045, 0.117),
            (0.042, 0.120),
            (0.039, 0.120),
            (0.039, 0.009),
            (0.0, 0.009),
        ],
        segments=96,
        closed=True,
    )
    cavity = CylinderGeometry(0.0388, 0.112).translate(0.0, 0.0, 0.065)

    # Housing: lofted so it fairs into the wall -- thin at its base, full depth at the pivot.
    housing = LoftGeometry(
        [
            _housing_ring(0.070, 0.008, -0.044),
            _housing_ring(0.090, 0.016, -0.047),
            _housing_ring(0.110, 0.022, -0.0495),
            _housing_ring(0.128, 0.022, -0.0495),
            _housing_ring(0.134, 0.019, -0.049),
        ],
        cap=True,
        closed=True,
    )
    # Carve the mechanism: a channel for the barrel, a slot sector for the arm,
    # and a recess for the button. Voids, not hardware.
    channel = CylinderGeometry(0.0065, 0.038).rotate_y(math.pi / 2).translate(0.0, HINGE_Y, HINGE_Z)
    recess = RoundedBoxGeometry((0.020, 0.010, 0.014), 0.003).translate(0.0, -0.0555, 0.100)
    housing = boolean_difference(housing, channel)
    # Overlapping segments every 15 degrees carve one CONTINUOUS sector: discrete
    # cuts would leave webs between them that block the arm mid-swing.
    for angle in (-10.0, 0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 100.0):
        housing = boolean_difference(housing, _slot_segment(angle))
    housing = boolean_difference(housing, recess)

    # The housing is embedded into the body wall (volumes overlap -- no tangent
    # contact) and the weld bead fills the seam; trim keeps the cavity clean.
    canister.add(
        weld(body, housing, radius=0.006, tolerance=0.0015, trim=cavity),
        name="body_with_molded_housing",
        color=(0.82, 0.83, 0.85),
    )
    canister.add(
        RoundedBoxGeometry((0.016, 0.008, 0.010), 0.0025).translate(0.0, -0.054, 0.100),
        name="recessed_button",
        color=(0.85, 0.30, 0.25),
    )

    # The lid is ONE welded piece, authored relative to the hinge axis: disc over the
    # mouth, thin arm through the slot, barrel captured in the channel.
    lid = model.part("flip_lid")
    disc = CylinderGeometry(0.047, 0.007).translate(0.0, 0.049, -0.0025)
    arm = BoxGeometry((0.026, 0.030, 0.0035)).translate(0.0, 0.009, -0.0015)
    barrel = CylinderGeometry(0.005, 0.034).rotate_y(math.pi / 2)
    lid.add(
        weld(disc, arm, barrel, radius=0.003, tolerance=0.0015),
        name="lid_with_hinge_barrel",
        color=(0.25, 0.26, 0.28),
    )

    model.articulation(
        "lid_hinge",
        ArticulationType.REVOLUTE,
        canister,
        lid,
        origin=Origin(xyz=(0.0, HINGE_Y, HINGE_Z)),
        axis=(1.0, 0.0, 0.0),
        motion_limits=MotionLimits(effort=5.0, velocity=2.0, lower=0.0, upper=1.6),
    )
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    _, closed_hi = ctx.shape_world_bounds("flip_lid", "lid_with_hinge_barrel")
    with ctx.pose({"lid_hinge": 1.4}):
        _, open_hi = ctx.shape_world_bounds("flip_lid", "lid_with_hinge_barrel")
        ctx.check(
            "lid_swings_open_upward",
            open_hi[2] > closed_hi[2] + 0.05,
            "At an open pose the lid should rise well above its closed height.",
        )
    button_lo, _ = ctx.shape_world_bounds("canister", "recessed_button")
    ctx.check(
        "button_sits_recessed_in_housing",
        button_lo[1] > -0.062,
        "The button should sit inside the housing recess, not float off the surface.",
    )
    return ctx.report()
