"""Live/e2e generation tests backed by the cassette lane.

Default: always live (real model). Cassettes are opt-in via flags:

    uv run pytest tests/test_live_generation.py --replay
    OPENAI_API_KEY=... uv run pytest tests/test_live_generation.py --record

Cassette names default to the test function name
(``cassette_model("latest")`` for an explicit name).
"""

from __future__ import annotations

from pathlib import Path

from harness import WarmEnvironment, run_scenario


def test_box_generation(cassette_model, tmp_path: Path) -> None:
    with cassette_model() as model:
        artifacts = run_scenario(
            "a simple box",
            model=model,
            env=WarmEnvironment(output_dir=tmp_path),
        )
    assert artifacts.record.status == "success"
    assert artifacts.record.result.endswith(".usdz")
