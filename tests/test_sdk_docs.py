from __future__ import annotations

from mini_articraft.agent.sdk_docs import SDK_DOCS_ROOT, render_sdk_context


def test_render_sdk_context_preloads_quickstart_and_testing() -> None:
    text = render_sdk_context()

    assert text.startswith("## docs/sdk/common/00_quickstart.md")
    assert "# SDK quickstart" in text
    assert "## docs/sdk/common/40_testing.md" in text
    assert "# Testing" in text
    assert not text.removeprefix("## docs/sdk/common/00_quickstart.md\n\n").startswith("---")
    assert "description:" not in text


def test_quickstart_router_lists_every_sdk_doc() -> None:
    quickstart = (SDK_DOCS_ROOT / "common" / "00_quickstart.md").read_text(encoding="utf-8")
    doc_paths = sorted(
        f"docs/sdk/{path.relative_to(SDK_DOCS_ROOT).as_posix()}"
        for path in SDK_DOCS_ROOT.rglob("*.md")
    )

    for doc_path in doc_paths:
        assert f"`{doc_path}`" in quickstart
