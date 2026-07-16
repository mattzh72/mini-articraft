from __future__ import annotations

import numpy as np
import pytest

from mini_articraft.sdk import BoxGeometry, SphereGeometry, weld


def test_weld_two_overlapping_boxes_is_one_solid() -> None:
    a = BoxGeometry((0.05, 0.02, 0.02))
    b = BoxGeometry((0.02, 0.05, 0.02)).translate(0.02, 0.0, 0.0)
    result = weld(a, b, radius=0.005)
    assert result.vertices and result.faces
    assert result.is_watertight
    # a single connected component (one blended solid, not two)
    assert result.to_trimesh().body_count == 1


def test_weld_grows_a_fillet_beyond_the_hard_union() -> None:
    a = BoxGeometry((0.04, 0.02, 0.02))
    b = SphereGeometry(0.014).translate(0.02, 0.0, 0.0)
    welded = weld(a, b, radius=0.006)
    # the smooth blend adds clay at the joint, so the welded solid is larger in
    # bounds along the join axis than either input on its own.
    bmin, bmax = welded.bounds
    assert bmax[0] - bmin[0] > 0.04
    assert welded.is_watertight


def test_weld_requires_two_solids() -> None:
    with pytest.raises(ValueError):
        weld(BoxGeometry((0.02, 0.02, 0.02)))


def test_weld_rejects_bad_radius() -> None:
    a = BoxGeometry((0.02, 0.02, 0.02))
    b = BoxGeometry((0.02, 0.02, 0.02)).translate(0.01, 0.0, 0.0)
    with pytest.raises(ValueError):
        weld(a, b, radius=0.0)


def test_weld_rejects_non_meshgeometry() -> None:
    with pytest.raises(TypeError):
        weld(BoxGeometry((0.02, 0.02, 0.02)), np.zeros((3, 3)))
