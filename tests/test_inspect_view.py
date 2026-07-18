from __future__ import annotations

import numpy as np

from mini_articraft.agent.tools import result_item
from mini_articraft.agent.tools.inspect_view import (
    _Piece,
    _project,
    _resolve_probe,
    _separate,
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
    item = result_item("call_1", {"result": {"image_png_base64": "QUJD", "view": {"azimuth": 45}}})
    assert isinstance(item["output"], list)
    assert len(item["output"]) == 1
    assert item["output"][0]["type"] == "input_image"
    assert item["output"][0]["image_url"].startswith("data:image/png;base64,QUJD")


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


def test_separate_pushes_overlapping_labels_apart() -> None:
    # Two identical boxes stacked on the same spot must not overlap afterwards.
    a = {"x": 100.0, "y": 100.0, "w": 60.0, "h": 14.0}
    b = {"x": 100.0, "y": 100.0, "w": 60.0, "h": 14.0}
    _separate([a, b], size=720, pad=4.0)
    gap_x = max(a["x"], b["x"]) - min(a["x"] + a["w"], b["x"] + b["w"])
    gap_y = max(a["y"], b["y"]) - min(a["y"] + a["h"], b["y"] + b["h"])
    assert gap_x >= 0 or gap_y >= 0  # separated on at least one axis
    for box in (a, b):  # stayed inside the frame
        assert 2.0 <= box["x"] <= 720 - box["w"] - 2.0


def test_toggle_hides_inspect_view() -> None:
    import pytest

    from mini_articraft.agent import tools

    assert "inspect_view" in {s["name"] for s in tools.schemas(inspect_view=True)}
    assert "inspect_view" not in {s["name"] for s in tools.schemas(inspect_view=False)}
    with pytest.raises(ValueError):
        tools.get("inspect_view", inspect_view=False)
