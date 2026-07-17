"""Seat a radial array of blades into a hub disk, then weld into one solid rotor.

A fan, turbine, propeller, or spoked wheel is one piece of one material, with many
blades radiating from a center. Two things make it read as a single solid rotor:

  1. SEAT the roots. Build a solid `hub_disk` (a cylinder) and place each blade so its
     inner end sits a real margin INSIDE the disk radius -- the root buries into the
     hub. Matching a root to a tapering cone's surface only grazes it and leaves a gap;
     burying it into a wide disk seats the blade.
  2. WELD them. Because the blades and hub share one material, `weld` fuses the buried
     roots and the disk into ONE seamless solid (an exact boolean union). weld needs
     the overlap from step 1 -- it fuses an overlap, it cannot close a gap.

This is the radial version of "extend the piece's own end into the body and fuse it":
the blade's own root reaches into the hub, no separate collar. (A differently colored
protrusion -- e.g. a black handle on a steel body -- cannot weld without losing its
color, so it stays an overlapping shape; a same-material rotor should weld.)
"""

from __future__ import annotations

import math

from mini_articraft.sdk import (
    ArticulatedObject,
    BoxGeometry,
    CylinderGeometry,
    MeshGeometry,
    TestContext,
    TestReport,
    weld,
)


def _seated_blade_ring(
    *,
    count: int,
    disk_radius: float,
    r_inner: float,
    r_tip: float,
    chord: float,
    thickness: float,
) -> MeshGeometry:
    # r_inner is deliberately well inside disk_radius, so every root buries into the hub.
    assert r_inner < disk_radius, "blade root must start inside the disk radius to seat"
    blades: MeshGeometry | None = None
    length = r_tip - r_inner
    for index in range(count):
        angle = 2.0 * math.pi * index / count
        blade = (
            BoxGeometry((length, chord, thickness))
            .translate((r_inner + r_tip) / 2.0, 0.0, 0.0)
            .rotate_z(angle)
        )
        blades = blade if blades is None else blades.merge(blade)
    assert blades is not None
    return blades


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("bladed_rotor")
    rotor = model.part("rotor")

    disk_radius = 0.10
    hub_disk = CylinderGeometry(disk_radius, 0.05, radial_segments=64)
    blades = _seated_blade_ring(
        count=10,
        disk_radius=disk_radius,
        r_inner=0.05,  # 0.05 < 0.10 disk radius -> roots buried 0.05 into the hub
        r_tip=0.24,
        chord=0.05,
        thickness=0.012,
    )

    # One material: weld the seated roots and the disk into a single solid rotor.
    rotor.add(weld(hub_disk, blades), name="hub_with_blades", color=(0.72, 0.73, 0.75))
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    _, hi = ctx.shape_world_bounds("rotor", "hub_with_blades")
    ctx.check(
        "blades_reach_out_from_the_hub",
        hi[0] > 0.20,
        "The welded blades should extend to the tip radius as one solid rotor.",
    )
    return ctx.report()
