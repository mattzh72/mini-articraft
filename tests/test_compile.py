from __future__ import annotations

import json

import pytest

from mini_articraft.environments.local import LocalEnvironment
from mini_articraft.record import read_conversation


def write_main(run_dir, code: str) -> None:
    run_dir.joinpath("workspace", "main.py").write_text(code, encoding="utf-8")


def test_compile_path_compiles_existing_run_directory(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("drawer")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("drawer", units="meters")
    base = model.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
    drawer = model.part("drawer", cq.Workplane("XY").box(0.8, 0.8, 0.2))
    model.fixed("base_to_drawer", base, drawer)
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    ctx.expect_contact("base", "drawer")
    return ctx.report()
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "success"
    assert result["entrypoint"] == str(run_dir / "workspace" / "main.py")
    assert result["manifest"] == str(run_dir / "result" / "model.json")
    assert result["usdz"] == str(run_dir / "result" / "model.usdz")
    assert run_dir.joinpath("result", "model.usdz").is_file()
    assert result["compile_report"]["status"] == "success"
    assert result["compile_report"]["counts"] == {"failures": 0, "warnings": 0, "notes": 0}
    assert "<compile_signals>" in result["compile_report"]["signals_text"]

    manifest = json.loads(run_dir.joinpath("result", "model.json").read_text())
    assert manifest["name"] == "drawer"

    record = json.loads(run_dir.joinpath("record.json").read_text())
    assert record == {
        "run_id": "drawer",
        "status": "success",
        "attempts": 1,
        "error": "",
        "result": "result/model.usdz",
        "cost": 0.0,
        "token_usage": {},
    }

    conversation = read_conversation(run_dir / "conversation.jsonl")
    assert conversation == [{"error": "", "role": "compiler", "status": "success"}]


def test_compile_path_supports_workspace_modules(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("multi")
    run_dir.joinpath("workspace", "parts").mkdir()
    write_main(
        run_dir,
        """
from mini_articraft.sdk import TestContext, TestReport
from parts.drawer import build_object_model

object_model = build_object_model()


def run_tests() -> TestReport:
    return TestContext(object_model).report()
""",
    )
    run_dir.joinpath("workspace", "parts", "drawer.py").write_text(
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject


def build_object_model():
    model = ArticulatedObject("helper_module_drawer", units="meters")
    model.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
    return model
""",
        encoding="utf-8",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "success"
    assert result["usdz"] == str(run_dir / "result" / "model.usdz")


def test_create_run_requires_new_simple_run_id(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)

    env.create_run("one")

    with pytest.raises(FileExistsError):
        env.create_run("one")
    with pytest.raises(ValueError):
        env.create_run("../escape")


def test_compile_path_requires_workspace_main_py(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("missing")

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert result["error"] == "workspace/main.py is required"
    assert result["compile_report"]["status"] == "failure"


def test_compile_path_reports_missing_object_model(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("bad")
    write_main(run_dir, "not_object_model = object()")

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "object_model" in result["error"]
    assert "ArticulatedObject" in result["error"]


def test_compile_path_requires_run_tests(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("missing_tests")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("box", units="meters")
object_model.part("base", cq.Workplane("XY").box(1.0, 1.0, 1.0))
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "run_tests" in result["error"]


def test_compile_path_requires_run_tests_report(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("bad_tests")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("box", units="meters")
object_model.part("base", cq.Workplane("XY").box(1.0, 1.0, 1.0))


def run_tests():
    return None
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "TestReport" in result["error"]


def test_compile_path_fails_authored_test_failure(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("authored_failure")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport

object_model = ArticulatedObject("box", units="meters")
object_model.part("base", cq.Workplane("XY").box(1.0, 1.0, 1.0))


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    ctx.fail("prompt-specific check", "missing feature")
    return ctx.report()
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "prompt-specific check" in result["error"]
    assert result["test_report"]["failures"][0]["name"] == "prompt-specific check"


def test_compile_path_fails_baseline_collision_between_non_adjacent_parts(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("collision_failure")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Frame, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("collision_failure", units="meters")
    root = model.part("root", cq.Workplane("XY").box(3.0, 3.0, 0.1))
    part_a = model.part("part_a", cq.Workplane("XY").box(1.0, 1.0, 1.0))
    part_b = model.part("part_b", cq.Workplane("XY").box(1.0, 1.0, 1.0))
    model.fixed("root_to_a", root, part_a, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    model.fixed("root_to_b", root, part_b, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    return TestContext(object_model).report()
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "fail_if_parts_collide_in_current_pose" in result["error"]
    assert "part_a" in result["error"]
    assert "part_b" in result["error"]
    assert result["usdz"] == str(run_dir / "result" / "model.usdz")
    assert run_dir.joinpath("result", "model.usdz").is_file()


def test_compile_path_fails_disconnected_geometry_inside_part(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("disconnected_geometry")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("disconnected_geometry", units="meters")
    left = cq.Workplane("XY").box(1.0, 1.0, 1.0).val()
    right = cq.Workplane("XY").box(1.0, 1.0, 1.0).translate((1.2, 0.0, 0.0)).val()
    model.part("base", cq.Compound.makeCompound([left, right]))
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    return TestContext(object_model).report()
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "fail_if_part_contains_disconnected_geometry_islands" in result["error"]
    assert "solid_002 nearest=solid_001 distance=0.2" in result["error"]
    signal = result["compile_report"]["signal_bundle"]["signals"][0]
    assert signal["kind"] == "disconnected_geometry"
    assert signal["code"] == "QC_DISCONNECTED_GEOMETRY"
    assert result["compile_report"]["counts"] == {"failures": 1, "warnings": 0, "notes": 0}


def test_compile_path_honors_authored_overlap_allowance(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("allowed_collision")
    write_main(
        run_dir,
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject, Frame, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("allowed_collision", units="meters")
    root = model.part("root", cq.Workplane("XY").box(3.0, 3.0, 0.1))
    shaft = model.part("shaft", cq.Workplane("XY").box(1.0, 1.0, 1.0))
    hub = model.part("hub", cq.Workplane("XY").box(1.0, 1.0, 1.0))
    model.fixed("root_to_shaft", root, shaft, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    model.fixed("root_to_hub", root, hub, frame=Frame(xyz=(0.0, 0.0, 0.55)))
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    ctx.allow_overlap("shaft", "hub", reason="shaft is intentionally captured in the hub")
    ctx.expect_collision("shaft", "hub")
    return ctx.report()
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "success"
    assert result["test_report"]["allowances"] == [
        "allow_overlap('hub', 'shaft'): shaft is intentionally captured in the hub"
    ]


def test_compile_path_reports_timeout(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path, timeout_seconds=0.2)
    run_dir = env.create_run("slow")
    write_main(run_dir, "while True:\n    pass\n")

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "timed out" in result["error"]
    assert result["compile_report"]["status"] == "failure"
