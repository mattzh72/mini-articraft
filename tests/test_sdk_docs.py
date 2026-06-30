from __future__ import annotations

from mini_articraft.agent.sdk_docs import load_sdk_docs, render_sdk_quickstart_context


def test_sdk_docs_all_have_frontmatter_and_unique_names() -> None:
    docs = load_sdk_docs()

    assert docs
    assert len({doc.name for doc in docs}) == len(docs)
    assert all(doc.description for doc in docs)
    assert all(doc.workspace_path.as_posix().startswith("docs/sdk/") for doc in docs)


def test_render_sdk_quickstart_context_includes_inventory_without_frontmatter() -> None:
    text = render_sdk_quickstart_context()

    assert text.startswith("# SDK Quickstart")
    assert "## Reference Inventory" in text
    assert "`docs/sdk/common/35_joints.md`" in text
    assert "`docs/sdk/cadquery/35_cadquery.md`" in text
    assert "name: sdk-quickstart" not in text
    assert "metadata:" not in text
