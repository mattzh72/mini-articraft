from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any

from mini_articraft.environments.export import export_object
from mini_articraft.sdk import ArticulatedObject


def compile_run(run_dir: Path) -> dict[str, Any]:
    workspace = run_dir / "workspace"
    result_dir = run_dir / "result"
    pending_result_dir = run_dir / ".result_pending"

    payload = _compile_workspace(workspace, pending_result_dir)
    if payload["status"] == "success":
        _replace_tree(pending_result_dir, result_dir)
        payload["manifest"] = str(result_dir / "model.json")
        payload["parts"] = _retarget_part_paths(
            payload.get("parts", {}),
            old_root=pending_result_dir,
            new_root=result_dir,
        )
    else:
        _remove_tree(pending_result_dir)
    return payload


def _compile_workspace(workspace: Path, export_dir: Path) -> dict[str, Any]:
    _remove_tree(export_dir)
    export_dir.mkdir(parents=True)

    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    payload: dict[str, Any] = {
        "status": "error",
        "manifest": "",
        "parts": {},
        "error": "",
        "traceback": "",
    }

    previous_cwd = Path.cwd()
    sys.path.insert(0, str(workspace))
    try:
        os.chdir(workspace)
        with (
            contextlib.redirect_stdout(captured_stdout),
            contextlib.redirect_stderr(captured_stderr),
        ):
            globals_dict = runpy.run_path(str(workspace / "main.py"), run_name="__main__")
            object_model = globals_dict.get("object_model")
            if not isinstance(object_model, ArticulatedObject):
                raise TypeError("main.py must define object_model as an ArticulatedObject")
            result = export_object(object_model, export_dir)

        payload.update(
            {
                "status": "success",
                "manifest": str(result.manifest),
                "parts": {name: str(path) for name, path in result.parts.items()},
            }
        )
    except BaseException as exc:
        payload.update(
            {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        )
    finally:
        os.chdir(previous_cwd)
        if sys.path and sys.path[0] == str(workspace):
            sys.path.pop(0)

    payload["stdout"] = captured_stdout.getvalue()
    payload["stderr"] = captured_stderr.getvalue()
    return payload


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _replace_tree(source: Path, destination: Path) -> None:
    _remove_tree(destination)
    source.rename(destination)


def _retarget_part_paths(parts: object, *, old_root: Path, new_root: Path) -> dict[str, str]:
    if not isinstance(parts, dict):
        return {}
    retargeted: dict[str, str] = {}
    for name, raw_path in parts.items():
        try:
            relative = Path(str(raw_path)).resolve().relative_to(old_root.resolve())
        except ValueError:
            continue
        retargeted[str(name)] = str(new_root / relative)
    return retargeted


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        payload = {
            "status": "error",
            "manifest": "",
            "parts": {},
            "stdout": "",
            "stderr": "",
            "error": "Usage: mini-articraft-compile-run <run_dir>",
            "traceback": "",
        }
        print(json.dumps(payload))
        return 2

    payload = compile_run(Path(args[0]).resolve())
    print(json.dumps(payload))
    return 0 if payload["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
