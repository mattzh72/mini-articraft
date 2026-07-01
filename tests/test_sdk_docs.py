from __future__ import annotations

import re
import tomllib
from pathlib import Path

from mini_articraft import package_dir


def test_quickstart_router_lists_common_docs() -> None:
    sdk_docs_root = package_dir / "sdk" / "docs"
    quickstart = (sdk_docs_root / "common" / "00_quickstart.md").read_text(encoding="utf-8")
    common_doc_paths = sorted(
        f"docs/sdk/{path.relative_to(sdk_docs_root).as_posix()}"
        for path in (sdk_docs_root / "common").glob("*.md")
    )

    for doc_path in common_doc_paths:
        assert f"`{doc_path}`" in quickstart

    build123d_doc_paths = sorted(
        f"docs/sdk/{path.relative_to(sdk_docs_root).as_posix()}"
        for path in (sdk_docs_root / "build123d").glob("*.md")
    )

    for doc_path in build123d_doc_paths:
        assert f"`{doc_path}`" in quickstart


def test_build123d_docs_are_one_file_per_page_without_local_index() -> None:
    build123d_root = package_dir / "sdk" / "docs" / "build123d"

    assert not (build123d_root / "index.md").exists()
    assert not (build123d_root / "README.md").exists()
    assert not (build123d_root / "build123d_all_docs_llm.md").exists()
    assert not (build123d_root / "manifest.csv").exists()
    assert not (build123d_root / "manifest.json").exists()
    assert not (build123d_root / "images").exists()
    assert not (build123d_root / "markdown").exists()
    assert (build123d_root / "introduction.md").is_file()


def test_build123d_examples_are_available_as_reference_files() -> None:
    examples_root = package_dir / "sdk" / "docs" / "build123d" / "examples"

    assert (examples_root / "benchy.py").is_file()
    assert (examples_root / "bicycle_tire.py").is_file()
    assert (examples_root / "lego.py").is_file()
    assert (examples_root / "low_poly_benchy.stl").is_file()


def test_build123d_asset_and_code_references_are_local_files() -> None:
    sdk_docs_root = package_dir / "sdk" / "docs"
    build123d_root = sdk_docs_root / "build123d"

    assert (build123d_root / "assets" / "ttt" / "ttt-23-t-24-curved_support.png").is_file()
    assert (build123d_root / "assets" / "ttt" / "ttt-23-t-24-curved_support.py").is_file()
    assert (build123d_root / "media" / "tea_cup.png").is_file()
    assert (build123d_root / "snippets" / "selector_example.py").is_file()

    text = "\n".join(path.read_text(encoding="utf-8") for path in build123d_root.glob("*.md"))
    assert "not vendored" not in text

    local_reference_pattern = re.compile(
        r"`(docs/sdk/build123d/(?:assets|examples|media|snippets)/[^`]+)`"
    )
    for doc_path in sorted(set(local_reference_pattern.findall(text))):
        if "{" in doc_path or "}" in doc_path:
            continue
        local_path = sdk_docs_root / Path(doc_path).relative_to("docs/sdk")
        assert local_path.exists(), doc_path


def test_all_backticked_sdk_doc_paths_resolve() -> None:
    sdk_docs_root = package_dir / "sdk" / "docs"
    text = "\n".join(path.read_text(encoding="utf-8") for path in sdk_docs_root.rglob("*.md"))
    sdk_doc_path_pattern = re.compile(r"`(docs/sdk/[^`]+)`")

    for doc_path in sorted(set(sdk_doc_path_pattern.findall(text))):
        if "{" in doc_path or "}" in doc_path:
            continue
        local_path = sdk_docs_root / Path(doc_path).relative_to("docs/sdk")
        assert local_path.exists(), doc_path


def test_build123d_support_files_are_package_data() -> None:
    repo_root = package_dir.parents[1]
    pyproject = tomllib.loads(repo_root.joinpath("pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["mini_articraft"]

    for pattern in [
        "sdk/docs/build123d/*.md",
        "sdk/docs/build123d/assets/*",
        "sdk/docs/build123d/assets/*/*",
        "sdk/docs/build123d/examples/*",
        "sdk/docs/build123d/media/*",
        "sdk/docs/build123d/snippets/*",
    ]:
        assert pattern in package_data


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
