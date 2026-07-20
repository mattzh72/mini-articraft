from __future__ import annotations

import pytest

from mini_articraft.agent import tools
from mini_articraft.agent.tools.critique import _grid, _prompt, _render_views
from mini_articraft.sdk import ArticulatedObject, BoxGeometry

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _model() -> ArticulatedObject:
    model = ArticulatedObject("t")
    body = model.part("body")
    body.add(BoxGeometry((0.10, 0.10, 0.10)), name="cube", color=(0.5, 0.5, 0.6))
    return model


def test_prompt_includes_goal_question_and_coloring() -> None:
    text = _prompt("a red mug", "is the handle attached?", colored=True)
    assert "a red mug" in text
    assert "is the handle attached?" in text
    assert "distinct bright color" in text
    # Without a question or coloring, neither clause appears.
    plain = _prompt("a red mug", None, colored=False)
    assert "builder specifically asks" not in plain
    assert "distinct bright color" not in plain


def test_grid_composes_tiles_into_one_png() -> None:
    tile = _render_views(_model(), {"target": "cube"})  # one focused frame
    sheet = _grid([tile, tile, tile, tile])
    assert sheet[:8] == _PNG_MAGIC


def test_render_views_default_is_a_grid_png() -> None:
    png = _render_views(_model(), {})
    assert png[:8] == _PNG_MAGIC


def test_toggle_hides_critique() -> None:
    assert "critique" in {s["name"] for s in tools.schemas(critique=True)}
    assert "critique" not in {s["name"] for s in tools.schemas(critique=False)}
    with pytest.raises(ValueError):
        tools.get("critique", critique=False)
