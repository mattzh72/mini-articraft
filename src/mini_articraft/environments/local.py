from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from mini_articraft import package_dir
from mini_articraft.compile_feedback import build_compile_report_from_payload, empty_compile_payload
from mini_articraft.record import Record
from mini_articraft.settings import DEFAULT_OUTPUT_DIR


class LocalEnvironmentConfig(BaseModel):
    output_dir: Path = DEFAULT_OUTPUT_DIR
    timeout_seconds: float = 300.0


DEFAULT_MAIN_PY = """from build123d import Box

from mini_articraft.sdk import ArticulatedObject, TestContext, TestReport


def build_object_model() -> ArticulatedObject:
    model = ArticulatedObject("object")
    base = model.part("base")
    base.add(Box(0.2, 0.2, 0.1), name="body", color=(0.7, 0.7, 0.72))
    return model


object_model = build_object_model()


def run_tests() -> TestReport:
    ctx = TestContext(object_model)
    return ctx.report()
"""


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
        run_dir.joinpath("workspace", "main.py").write_text(DEFAULT_MAIN_PY, encoding="utf-8")
        (run_dir / "conversation.jsonl").touch()
        Record(run_id=run_id).save(run_dir / "record.json")
        return run_dir

    def compile_path(self, run_dir: Path | str) -> dict[str, Any]:
        run_dir = Path(run_dir)
        workspace = run_dir / "workspace"

        if not (workspace / "main.py").is_file():
            result = _error_result(run_dir, error="workspace/main.py is required")
            self._record_compile(run_dir)
            return result

        result = self._run_worker(run_dir)
        self._record_compile(run_dir)
        return result

    def _run_worker(self, run_dir: Path) -> dict[str, Any]:
        args = [
            sys.executable,
            "-m",
            "mini_articraft.environments.worker",
            str(run_dir.resolve()),
        ]
        completed = _run_isolated_process(
            args,
            cwd=_project_root(),
            timeout_seconds=self.config.timeout_seconds,
        )
        if completed.timed_out:
            return _error_result(
                run_dir,
                error=f"compile timed out after {self.config.timeout_seconds:g}s",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
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
        payload["compile_report"] = build_compile_report_from_payload(payload)
        return _with_paths(run_dir, payload)

    def _record_compile(self, run_dir: Path) -> None:
        record = Record.load(run_dir / "record.json")
        record.run_id = run_dir.name
        record.attempts += 1
        record.save(run_dir / "record.json")


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


@dataclass(frozen=True)
class _ProcessResult:
    stdout: str
    stderr: str
    returncode: int | None
    timed_out: bool = False


def _run_isolated_process(
    args: list[str],
    *,
    cwd: Path,
    timeout_seconds: float,
) -> _ProcessResult:
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        stdout, stderr = _stop_timed_out_worker(proc)
        return _ProcessResult(stdout, stderr, proc.returncode, timed_out=True)
    return _ProcessResult(stdout, stderr, proc.returncode)


def _stop_timed_out_worker(proc: subprocess.Popen[str]) -> tuple[str, str]:
    _signal_worker_group(proc, signal.SIGTERM)
    try:
        return proc.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        _signal_worker_group(proc, signal.SIGKILL)
        return proc.communicate()


def _signal_worker_group(proc: subprocess.Popen[str], sig: signal.Signals) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        return


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
    payload = empty_compile_payload(error=error, stdout=stdout, stderr=stderr)
    payload["returncode"] = returncode
    payload["compile_report"] = build_compile_report_from_payload(payload)
    return _with_paths(run_dir, payload)
