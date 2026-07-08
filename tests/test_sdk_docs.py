from __future__ import annotations

import re
import runpy
import tomllib
from pathlib import Path

import mini_articraft.sdk as sdk
from mini_articraft import package_dir
from mini_articraft.sdk import ArticulatedObject, TestReport


def detailed_reference_paths(sdk_docs: Path) -> list[str]:
    return sorted(
        path.relative_to(sdk_docs).as_posix()
        for folder in ("common", "mesh")
        for path in sdk_docs.joinpath(folder).glob("*.md")
        if path.name != "00_quickstart.md"
    )


def test_quickstart_is_short_and_routes_to_targeted_references() -> None:
    sdk_docs = package_dir / "sdk" / "docs"
    quickstart = sdk_docs.joinpath("common", "00_quickstart.md").read_text()

    assert len(quickstart) < 5000
    for reference in [
        "docs/sdk/common/30_articulated_object.md",
        "docs/sdk/common/35_joints.md",
        "docs/sdk/common/40_testing.md",
        "docs/sdk/mesh/00_mesh_geometry.md",
        "docs/sdk/build123d/",
    ]:
        assert reference in quickstart
    assert "Read only the reference that applies" in quickstart
    assert "read every" not in quickstart.lower()


def test_quickstart_routes_every_detailed_sdk_reference() -> None:
    sdk_docs = package_dir / "sdk" / "docs"
    quickstart = sdk_docs.joinpath("common", "00_quickstart.md").read_text()

    for reference in detailed_reference_paths(sdk_docs):
        assert sdk_docs.joinpath(reference).is_file(), reference
        assert f"docs/sdk/{reference}" in quickstart, reference


def test_every_public_sdk_symbol_is_documented() -> None:
    sdk_docs = package_dir / "sdk" / "docs"
    reference_text = "\n".join(
        path.read_text(encoding="utf-8")
        for folder in ("common", "mesh")
        for path in sorted(sdk_docs.joinpath(folder).glob("*.md"))
    )

    missing = sorted(name for name in sdk.__all__ if f"`{name}`" not in reference_text)
    assert not missing


def test_key_apis_are_documented_by_their_owner_pages() -> None:
    sdk_docs = package_dir / "sdk" / "docs"
    expected = {
        "common/30_articulated_object.md": (
            "`ArticulatedObject`",
            "`Part`",
            "`part.add(...)`",
        ),
        "common/35_joints.md": (
            "`Origin`",
            "`MotionLimits`",
            "`model.articulation(...)`",
        ),
        "common/40_testing.md": (
            "`TestContext`",
            "`TestReport`",
            "`allow_overlap",
        ),
        "mesh/00_mesh_geometry.md": (
            "`MeshGeometry`",
            "`build123d_to_mesh`",
            "`ExtrudeWithHolesGeometry`",
        ),
        "mesh/10_profiles.md": (
            "`rounded_rect_profile`",
            "`superellipse_profile`",
            "`sample_catmull_rom_spline_3d`",
        ),
        "mesh/20_wires_and_sweeps.md": (
            "`WirePath`",
            "`PipeGeometry`",
            "`tube_network_from_paths`",
        ),
        "mesh/30_section_lofts.md": (
            "`SectionLoftSpec`",
            "`section_loft`",
            "`repair_loft`",
        ),
        "mesh/40_booleans_and_shells.md": (
            "`boolean_difference`",
            "`cut_opening_on_face`",
            "`partition_shell`",
        ),
    }

    for relative_path, names in expected.items():
        text = sdk_docs.joinpath(relative_path).read_text(encoding="utf-8")
        for name in names:
            assert name in text, f"{name} missing from {relative_path}"


def test_build123d_reference_tree_and_examples_are_available() -> None:
    root = package_dir / "sdk" / "docs" / "build123d"

    assert (root / "introduction.md").is_file()
    assert (root / "examples" / "benchy.py").is_file()
    assert (root / "examples" / "low_poly_benchy.stl").is_file()
    assert (root / "assets" / "ttt" / "ttt-23-t-24-curved_support.png").is_file()
    assert (root / "media" / "tea_cup.png").is_file()
    assert (root / "snippets" / "selector_example.py").is_file()
    assert not (root / "index.md").exists()


def test_all_backticked_sdk_doc_paths_resolve() -> None:
    sdk_docs_root = package_dir / "sdk" / "docs"
    text = "\n".join(path.read_text(encoding="utf-8") for path in sdk_docs_root.rglob("*.md"))
    pattern = re.compile(r"`(docs/sdk/[^`]+)`")

    for doc_path in sorted(set(pattern.findall(text))):
        if "{" in doc_path or "}" in doc_path or doc_path.endswith("/"):
            continue
        local_path = sdk_docs_root / Path(doc_path).relative_to("docs/sdk")
        assert local_path.exists(), doc_path


def test_relative_markdown_doc_links_resolve() -> None:
    sdk_docs = package_dir / "sdk" / "docs"
    pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")

    for relative_path in detailed_reference_paths(sdk_docs):
        source = sdk_docs / relative_path
        for target in pattern.findall(source.read_text(encoding="utf-8")):
            path_text = target.split("#", 1)[0]
            if not path_text.endswith(".md"):
                continue
            assert not Path(path_text).is_absolute(), (relative_path, target)
            assert source.parent.joinpath(path_text).is_file(), (relative_path, target)


def test_sdk_docs_and_examples_are_package_data() -> None:
    repo_root = package_dir.parents[1]
    pyproject = tomllib.loads(repo_root.joinpath("pyproject.toml").read_text())
    package_data = pyproject["tool"]["setuptools"]["package-data"]["mini_articraft"]

    for pattern in [
        "sdk/docs/common/*.md",
        "sdk/docs/mesh/*.md",
        "sdk/docs/examples/*.py",
        "sdk/docs/build123d/*.md",
        "sdk/docs/build123d/assets/*",
        "sdk/docs/build123d/assets/*/*",
        "sdk/docs/build123d/examples/*",
        "sdk/docs/build123d/media/*",
        "sdk/docs/build123d/snippets/*",
    ]:
        assert pattern in package_data


def test_all_new_sdk_examples_execute() -> None:
    examples = package_dir / "sdk" / "docs" / "examples"

    for path in sorted(examples.glob("*.py")):
        values = runpy.run_path(str(path))
        model = values["object_model"]
        report = values["run_tests"]()
        assert isinstance(model, ArticulatedObject), path.name
        model.validate()
        assert isinstance(report, TestReport), path.name
        assert report.passed, (path.name, report.failures)


def test_prompt_and_docs_state_the_new_authoring_contract() -> None:
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            package_dir / "prompts" / "system.md",
            package_dir / "prompts" / "task.md",
            package_dir / "sdk" / "docs" / "common" / "00_quickstart.md",
            package_dir / "sdk" / "docs" / "common" / "20_core_types.md",
            package_dir / "sdk" / "docs" / "common" / "35_joints.md",
        ]
    )

    for required in [
        "meters",
        "radians",
        "build123d",
        "MeshGeometry",
        "name=",
        "Origin",
        "MotionLimits",
        "realistic geometry",
        "primary mechanisms",
        "floating parts",
        "unintended overlaps",
    ]:
        assert required.lower() in text.lower()
    assert "thorough research pass" not in text.lower()
