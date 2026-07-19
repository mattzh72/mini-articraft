from __future__ import annotations

from itertools import pairwise

import numpy as np

from mini_articraft.agent.tools import result_item
from mini_articraft.agent.tools.inspect_view import (
    _eye,
    _framing,
    _Piece,
    _pixel_ray,
    _project,
    _raycast,
    _resolve_probe,
    _scene,
    _stack_ys,
    render_png,
)
from mini_articraft.sdk import ArticulatedObject, BoxGeometry

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _model() -> ArticulatedObject:
    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.10)), name="cube", color=(0.5, 0.5, 0.6))
    return model


def test_render_png_produces_a_png() -> None:
    png = render_png(
        _model(), azimuth=45, elevation=20, zoom=1.0, target=None, only=None, pose=None
    )
    assert png[:8] == _PNG_MAGIC


def test_render_only_isolates_a_shape() -> None:
    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.10)), name="cube", color=(0.5, 0.5, 0.6))
    body.add(BoxGeometry((0.05, 0.05, 0.05)).translate(0.2, 0.0, 0.0), name="cube2")
    png = render_png(
        model, azimuth=30, elevation=10, zoom=0.6, target="cube", only=["cube"], pose=None
    )
    assert png[:8] == _PNG_MAGIC


def test_result_item_emits_image_content_for_a_render() -> None:
    item = result_item("call_1", {"result": {"image_png_base64": "QUJD"}})
    assert isinstance(item["output"], list)
    assert len(item["output"]) == 1
    assert item["output"][0]["type"] == "input_image"
    assert item["output"][0]["image_url"].startswith("data:image/png;base64,QUJD")


def test_result_item_rides_probe_data_alongside_the_image() -> None:
    hit = {"shape": "cube", "point": [0.0, -0.05, 0.0]}
    item = result_item("call_1", {"result": {"image_png_base64": "QUJD", "probe_hit": hit}})
    assert isinstance(item["output"], list)
    assert len(item["output"]) == 2
    assert item["output"][0]["type"] == "input_text" and "cube" in item["output"][0]["text"]
    assert item["output"][1]["type"] == "input_image"


def test_result_item_stays_text_without_an_image() -> None:
    item = result_item("call_2", {"result": {"status": "ok"}})
    assert isinstance(item["output"], str)


def test_project_maps_center_to_middle_and_drops_behind_camera() -> None:
    center = np.zeros(3)
    eye = np.array([0.0, -1.0, 0.0])
    at_center = _project(center, eye, center, 720)
    assert at_center is not None
    px, py, depth = at_center
    assert abs(px - 360) < 1 and abs(py - 360) < 1 and depth > 0
    assert _project(np.array([0.0, -2.0, 0.0]), eye, center, 720) is None  # behind eye


def test_resolve_probe_by_name_and_point() -> None:
    piece = _Piece(
        name="cube",
        vertices=np.array([[0.0, 0.0, 0.0], [0.2, 0.2, 0.2]]),
        faces=np.zeros((0, 3), dtype=np.int64),
        normals=np.zeros((2, 3)),
        color=(0.5, 0.5, 0.5),
    )
    by_name = _resolve_probe([piece], "cube")
    assert by_name is not None
    assert np.allclose(by_name[0], [0.1, 0.1, 0.1]) and "0.100" in by_name[1]
    by_point = _resolve_probe([piece], [1.0, 2.0, 3.0])
    assert by_point is not None and np.allclose(by_point[0], [1.0, 2.0, 3.0])
    assert _resolve_probe([piece], "missing") is None


def test_stack_ys_keeps_order_and_min_gap() -> None:
    line_h = 20.0
    # Five labels whose anchors bunch near the same y must spread out in order.
    ys = _stack_ys([100.0, 105.0, 110.0, 115.0, 120.0], size=720, line_h=line_h)
    assert ys == sorted(ys)  # reading order preserved
    for a, b in pairwise(ys):
        assert b - a >= line_h - 1e-6  # no overlap
    # A stack that would overrun the bottom is shifted up to fit.
    tall = _stack_ys([700.0, 705.0, 710.0], size=720, line_h=line_h)
    assert tall[-1] + line_h <= 720


def test_pixel_ray_inverts_project() -> None:
    eye = np.array([0.3, -0.5, 0.4])
    center = np.array([0.0, 0.0, 0.1])
    point = np.array([0.04, 0.02, 0.15])
    projected = _project(point, eye, center, size=1)  # size=1 -> px,py are normalized u,v
    assert projected is not None
    origin, direction = _pixel_ray(projected[0], projected[1], eye, center)
    # The ray from the eye through that pixel must pass through the original point.
    to_point = point - origin
    distance = np.linalg.norm(to_point - (to_point @ direction) * direction)
    assert distance < 1e-9


def test_probe_px_raycasts_to_the_right_shape() -> None:
    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.10)), name="cube", color=(0.5, 0.5, 0.6))
    body.add(BoxGeometry((0.04, 0.04, 0.04)).translate(0.2, 0.0, 0.0), name="nub")
    pieces = _scene(model, only=None, pose=None)
    center, radius = _framing(pieces, target=None, zoom=1.0, model=model, only=None, pose=None)
    eye = _eye(center, radius, azimuth=45, elevation=20)
    # The image center looks at the framing center, which the big cube occupies.
    origin, direction = _pixel_ray(0.5, 0.5, eye, center)
    hit = _raycast(pieces, origin, direction)
    assert hit is not None and hit["shape"] == "cube"
    assert abs(max(abs(v) for v in hit["point"]) - 0.05) < 1e-3  # on the box surface
    miss_origin, miss_direction = _pixel_ray(0.02, 0.02, eye, center)  # image corner: sky
    assert _raycast(pieces, miss_origin, miss_direction) is None


def test_toggle_hides_inspect_view() -> None:
    import pytest

    from mini_articraft.agent import tools

    assert "inspect_view" in {s["name"] for s in tools.schemas(inspect_view=True)}
    assert "inspect_view" not in {s["name"] for s in tools.schemas(inspect_view=False)}
    with pytest.raises(ValueError):
        tools.get("inspect_view", inspect_view=False)
