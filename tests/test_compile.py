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

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("drawer")
base = object_model.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
drawer = object_model.part("drawer", cq.Workplane("XY").box(0.8, 0.8, 0.2))
object_model.fixed("base_to_drawer", base, drawer)
""",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "success"
    assert result["entrypoint"] == str(run_dir / "workspace" / "main.py")
    assert result["manifest"] == str(run_dir / "result" / "model.json")
    assert set(result["parts"]) == {"base", "drawer"}

    manifest = json.loads(run_dir.joinpath("result", "model.json").read_text())
    assert manifest["name"] == "drawer"

    record = json.loads(run_dir.joinpath("record.json").read_text())
    assert record == {
        "run_id": "drawer",
        "status": "success",
        "attempts": 1,
        "error": "",
        "workspace": "workspace",
        "entrypoint": "workspace/main.py",
        "result": "result/model.json",
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
from parts.drawer import build_object_model

object_model = build_object_model()
""",
    )
    run_dir.joinpath("workspace", "parts", "drawer.py").write_text(
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject


def build_object_model():
    model = ArticulatedObject("helper_module_drawer")
    model.part("base", cq.Workplane("XY").box(1.0, 1.0, 0.2))
    return model
""",
        encoding="utf-8",
    )

    result = env.compile_path(run_dir)

    assert result["status"] == "success"
    assert set(result["parts"]) == {"base"}


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


def test_compile_path_reports_missing_object_model(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("bad")
    write_main(run_dir, "not_object_model = object()")

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "object_model" in result["error"]
    assert "ArticulatedObject" in result["error"]


def test_compile_path_reports_timeout(tmp_path) -> None:
    env = LocalEnvironment(output_dir=tmp_path, timeout_seconds=0.2)
    run_dir = env.create_run("slow")
    write_main(run_dir, "while True:\n    pass\n")

    result = env.compile_path(run_dir)

    assert result["status"] == "error"
    assert "timed out" in result["error"]
