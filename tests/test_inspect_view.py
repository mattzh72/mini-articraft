from __future__ import annotations

from mini_articraft.agent.tools import result_item
from mini_articraft.agent.tools.inspect_view import render_png
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
