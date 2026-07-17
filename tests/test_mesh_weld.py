from __future__ import annotations

import numpy as np
import pytest

from mini_articraft.sdk import (
    BoxGeometry,
    CylinderGeometry,
    SnapRefused,
    SphereGeometry,
    snap_to,
    weld,
)


def test_weld_two_overlapping_boxes_is_one_solid() -> None:
    a = BoxGeometry((0.05, 0.02, 0.02))
    b = BoxGeometry((0.02, 0.05, 0.02)).translate(0.02, 0.0, 0.0)
    result = weld(a, b)
    assert result.vertices and result.faces
    assert result.is_watertight
    # a single connected component (one fused solid, not two)
    assert result.to_trimesh().body_count == 1


def test_weld_keeps_exact_input_bounds() -> None:
    # a boolean union keeps the exact surfaces, so bounds match the outer extent of
    # the inputs -- it never grows a fillet the way the old smooth weld did.
    a = BoxGeometry((0.04, 0.02, 0.02))
    b = SphereGeometry(0.014).translate(0.02, 0.0, 0.0)
    welded = weld(a, b)
    (a_min, a_max), (b_min, b_max) = a.bounds, b.bounds
    w_min, w_max = welded.bounds
    # a boolean union stays within the inputs' own extent -- it never grows a fillet
    # (tolerance well below any fillet, above manifold's re-meshing noise)
    assert w_max[0] == pytest.approx(max(a_max[0], b_max[0]), abs=1e-6)
    assert w_min[0] == pytest.approx(min(a_min[0], b_min[0]), abs=1e-6)
    assert welded.is_watertight


def test_weld_trim_removes_stub_in_hollow_cavity() -> None:
    outer = BoxGeometry((0.10, 0.08, 0.08))
    cavity = BoxGeometry((0.08, 0.06, 0.06))
    from mini_articraft.sdk import boolean_difference

    shell = boolean_difference(outer, cavity)
    prot = (
        CylinderGeometry(0.01, 0.06, radial_segments=24)
        .rotate_y(np.pi / 2)
        .translate(0.045, 0.0, 0.0)
    )
    without_trim = weld(shell, prot)
    with_trim = weld(shell, prot, trim=cavity)
    assert with_trim.to_trimesh().volume < without_trim.to_trimesh().volume
    assert with_trim.is_watertight


def test_weld_requires_two_solids() -> None:
    with pytest.raises(ValueError):
        weld(BoxGeometry((0.02, 0.02, 0.02)))


def test_weld_rejects_non_meshgeometry() -> None:
    with pytest.raises(TypeError):
        weld(BoxGeometry((0.02, 0.02, 0.02)), np.zeros((3, 3)))  # pyright: ignore[reportArgumentType]


def test_snap_to_closes_a_small_gap() -> None:
    body = SphereGeometry(0.05, width_segments=32, height_segments=16)
    spout = (
        CylinderGeometry(0.012, 0.05, radial_segments=24)
        .rotate_y(np.pi / 2)
        .translate(0.085, 0.0, 0.0)
    )
    moved = snap_to(body, spout, overlap=0.004, max_move=0.05)
    fused = weld(body, moved)
    assert fused.is_watertight
    assert fused.to_trimesh().body_count == 1


def test_snap_to_refuses_a_move_beyond_max() -> None:
    barrel = CylinderGeometry(0.008, 0.02, radial_segments=16).rotate_y(np.pi / 2)
    cap = SphereGeometry(0.02, width_segments=16, height_segments=8).translate(0.0, 0.03, 0.0)
    with pytest.raises(SnapRefused):
        snap_to(barrel, cap, overlap=0.003, max_move=0.005)


def test_snap_to_axis_constrains_direction() -> None:
    body = BoxGeometry((0.06, 0.06, 0.02))
    piece = BoxGeometry((0.01, 0.01, 0.02)).translate(0.02, 0.05, 0.0)
    before = piece.to_trimesh().vertices.mean(axis=0)
    moved = snap_to(body, piece, overlap=0.002, max_move=0.06, axis="y")
    after = moved.to_trimesh().vertices.mean(axis=0)
    assert after[0] == pytest.approx(before[0], abs=1e-9)  # x unchanged
    assert after[2] == pytest.approx(before[2], abs=1e-9)  # z unchanged
    assert after[1] < before[1]  # moved in -y toward the body
