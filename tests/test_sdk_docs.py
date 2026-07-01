from __future__ import annotations

from mini_articraft import package_dir


def test_quickstart_router_lists_common_docs_and_build123d_entrypoint() -> None:
    sdk_docs_root = package_dir / "sdk" / "docs"
    quickstart = (sdk_docs_root / "common" / "00_quickstart.md").read_text(encoding="utf-8")
    common_doc_paths = sorted(
        f"docs/sdk/{path.relative_to(sdk_docs_root).as_posix()}"
        for path in (sdk_docs_root / "common").glob("*.md")
    )

    for doc_path in common_doc_paths:
        assert f"`{doc_path}`" in quickstart

    for doc_path in [
        "docs/sdk/build123d/index.md",
        "docs/sdk/build123d/markdown/build_part.md",
        "docs/sdk/build123d/markdown/build_sketch.md",
        "docs/sdk/build123d/markdown/objects.md",
        "docs/sdk/build123d/markdown/operations.md",
        "docs/sdk/build123d/markdown/assemblies.md",
        "docs/sdk/build123d/markdown/import_export.md",
        "docs/sdk/build123d/markdown/direct_api_reference.md",
    ]:
        assert f"`{doc_path}`" in quickstart


def test_build123d_index_lists_every_upstream_markdown_page() -> None:
    build123d_root = package_dir / "sdk" / "docs" / "build123d"
    index = (build123d_root / "index.md").read_text(encoding="utf-8")

    for path in sorted((build123d_root / "markdown").glob("*.md")):
        doc_path = path.relative_to(build123d_root).as_posix()
        assert f"]({doc_path})" in index


def test_prompt_and_docs_state_sdk_authoring_contract() -> None:
    prompts_root = package_dir / "prompts"
    docs_root = package_dir / "sdk" / "docs" / "common"
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            prompts_root / "system.md",
            prompts_root / "task.md",
            docs_root / "00_quickstart.md",
            docs_root / "20_core_types.md",
            docs_root / "30_articulated_object.md",
            docs_root / "35_joints.md",
        ]
    )

    for required in [
        'units="meters"',
        "from build123d import *",
        "Use `Frame`, not `Origin`",
        "build123d `Shape`",
        "color=",
        "Generated scripts must author a Python SDK object",
    ]:
        assert required in text

    for hidden_export_detail in ["USD", "USDZ", "model.usdz", "OpenUSD", "pxr"]:
        assert hidden_export_detail not in text
