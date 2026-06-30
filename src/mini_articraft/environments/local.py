from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mini_articraft import package_dir
from mini_articraft.record import Record, append_conversation


class LocalEnvironmentConfig(BaseModel):
    output_dir: Path = Path("runs")
    timeout_seconds: float = 30.0


class LocalEnvironment:
    def __init__(self, **kwargs: Any):
        self.config = LocalEnvironmentConfig(**kwargs)

    def create_run(self, run_id: str) -> Path:
        run_id = _validate_run_id(run_id)
        run_dir = self.config.output_dir / run_id
        if run_dir.exists():
            raise FileExistsError(f"run already exists: {run_id}")

        (run_dir / "workspace").mkdir(parents=True)
        (run_dir / "result").mkdir()
        _link_sdk_docs(run_dir / "workspace")
        (run_dir / "conversation.jsonl").touch()
        Record(run_id=run_id).save(run_dir / "record.json")
        return run_dir

    def compile_path(self, run_dir: Path | str) -> dict[str, Any]:
        run_dir = Path(run_dir)
        workspace = run_dir / "workspace"

        if not (workspace / "main.py").is_file():
            result = _error_result(run_dir, error="workspace/main.py is required")
            self._record_compile(run_dir, result)
            return result

        result = self._run_worker(run_dir)
        self._record_compile(run_dir, result)
        return result

    def _run_worker(self, run_dir: Path) -> dict[str, Any]:
        args = [
            "uv",
            "run",
            "mini-articraft-compile-run",
            str(run_dir.resolve()),
        ]
        try:
            completed = subprocess.run(
                args,
                cwd=_project_root(),
                text=True,
                capture_output=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return _error_result(
                run_dir,
                error=f"compile timed out after {self.config.timeout_seconds:g}s",
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
            )

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return _error_result(
                run_dir,
                error="compile worker did not return JSON",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )

        if not isinstance(payload, dict):
            return _error_result(
                run_dir,
                error="compile worker returned invalid JSON",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )

        payload.setdefault("stdout", "")
        payload["stderr"] = str(payload.get("stderr", "")) + completed.stderr
        payload.setdefault("error", "")
        payload.setdefault("traceback", "")
        payload["returncode"] = completed.returncode
        return _with_paths(run_dir, payload)

    def _record_compile(self, run_dir: Path, result: dict[str, Any]) -> None:
        record = Record.load(run_dir / "record.json")
        record.run_id = run_dir.name
        record.status = str(result["status"])
        record.attempts += 1
        record.error = str(result.get("error") or "")
        if result["status"] == "success":
            record.result = "result/model.json"
        record.save(run_dir / "record.json")

        append_conversation(
            run_dir / "conversation.jsonl",
            {
                "role": "compiler",
                "status": result["status"],
                "error": result.get("error", ""),
            },
        )


def _validate_run_id(run_id: str) -> str:
    value = str(run_id).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("run_id must be a simple folder name")
    return value


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _link_sdk_docs(workspace: Path) -> None:
    docs_dir = workspace / "docs"
    docs_dir.mkdir()
    docs_dir.joinpath("sdk").symlink_to(package_dir / "sdk" / "docs", target_is_directory=True)


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _with_paths(run_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    workspace = run_dir / "workspace"
    result_dir = run_dir / "result"
    result["run_id"] = run_dir.name
    result["run"] = str(run_dir)
    result["workspace"] = str(workspace)
    result["entrypoint"] = str(workspace / "main.py")
    result["result"] = str(result_dir)
    return result


def _error_result(
    run_dir: Path,
    *,
    error: str,
    stdout: str = "",
    stderr: str = "",
    returncode: int | None = None,
) -> dict[str, Any]:
    return _with_paths(
        run_dir,
        {
            "status": "error",
            "manifest": "",
            "parts": {},
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
            "traceback": "",
            "returncode": returncode,
        },
    )
