from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import sys
import traceback
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from mini_articraft.compile_feedback import build_compile_report_from_payload
from mini_articraft.environments.export import export_object
from mini_articraft.sdk import ArticulatedObject, TestContext, TestFailure, TestReport


def compile_run(run_dir: Path) -> dict[str, Any]:
    workspace = run_dir / "workspace"
    result_dir = run_dir / "result"
    pending_result_dir = run_dir / ".result_pending"

    payload = _compile_workspace(workspace, pending_result_dir)
    if payload["status"] == "success":
        _replace_tree(pending_result_dir, result_dir)
        payload["manifest"] = str(result_dir / "model.json")
        payload["usdz"] = str(result_dir / "model.usdz")
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
        "usdz": "",
        "test_report": None,
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
            authored_report = _run_required_tests(globals_dict)
            baseline_report = _run_baseline_tests(object_model, authored_report)
            test_report = _merge_test_reports(authored_report, baseline_report)
            _raise_for_failed_test_report(test_report)
            result = export_object(object_model, export_dir)

        payload.update(
            {
                "status": "success",
                "manifest": str(result.manifest),
                "usdz": str(result.usdz),
                "test_report": _serialize_test_report(test_report),
            }
        )
    except BaseException as exc:
        test_report = getattr(exc, "test_report", None)
        payload.update(
            {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "test_report": _serialize_test_report(test_report)
                if isinstance(test_report, TestReport)
                else None,
            }
        )
    finally:
        os.chdir(previous_cwd)
        if sys.path and sys.path[0] == str(workspace):
            sys.path.pop(0)

    payload["stdout"] = captured_stdout.getvalue()
    payload["stderr"] = captured_stderr.getvalue()
    payload["compile_report"] = build_compile_report_from_payload(payload)
    return payload


def _run_required_tests(globals_dict: dict[str, Any]) -> TestReport:
    run_tests = globals_dict.get("run_tests")
    if not callable(run_tests):
        raise ValueError(
            "Missing required `run_tests()` in main.py. "
            "Add a top-level `def run_tests() -> TestReport:` and return `ctx.report()`."
        )

    report = run_tests()
    if not isinstance(report, TestReport):
        raise ValueError(f"run_tests() must return TestReport (got {type(report).__name__})")
    return report


def _run_baseline_tests(obj: ArticulatedObject, authored_report: TestReport) -> TestReport:
    ctx = TestContext(obj)
    for part_name in authored_report.allowed_isolated_parts:
        ctx.allow_isolated_part(
            part_name,
            reason="carried over from authored run_tests() allowance",
        )
    for overlap in authored_report.allowed_overlaps:
        ctx.allow_overlap(
            overlap.link_a,
            overlap.link_b,
            reason=overlap.reason,
            elem_a=overlap.elem_a,
            elem_b=overlap.elem_b,
        )

    ctx.check_model_valid()
    ctx.check_single_root_part()
    preliminary = ctx.report()
    if not preliminary.passed:
        return _without_allowance_notes(preliminary)

    ctx.fail_if_isolated_parts()
    ctx.fail_if_part_contains_disconnected_geometry_islands()
    ctx.fail_if_parts_collide_in_current_pose()
    return _without_allowance_notes(ctx.report())


def _without_allowance_notes(report: TestReport) -> TestReport:
    return replace(
        report,
        allowances=(),
        allowed_isolated_parts=(),
        allowed_overlaps=(),
    )


def _merge_test_reports(authored_report: TestReport, baseline_report: TestReport) -> TestReport:
    checks: list[str] = []
    seen_checks: set[str] = set()
    for report in (authored_report, baseline_report):
        for check in report.checks:
            if check not in seen_checks:
                seen_checks.add(check)
                checks.append(check)

    failures: list[TestFailure] = []
    seen_failures: set[tuple[str, str]] = set()
    for report in (authored_report, baseline_report):
        for failure in report.failures:
            key = (failure.name, failure.details)
            if key not in seen_failures:
                seen_failures.add(key)
                failures.append(failure)

    warnings: list[str] = []
    seen_warnings: set[str] = set()
    for report in (authored_report, baseline_report):
        for warning in report.warnings:
            if warning not in seen_warnings:
                seen_warnings.add(warning)
                warnings.append(warning)

    allowances: list[str] = []
    seen_allowances: set[str] = set()
    for allowance in authored_report.allowances:
        if allowance not in seen_allowances:
            seen_allowances.add(allowance)
            allowances.append(allowance)

    return TestReport(
        passed=not failures,
        checks_run=len(checks),
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
        allowances=tuple(allowances),
        allowed_isolated_parts=authored_report.allowed_isolated_parts,
        allowed_overlaps=authored_report.allowed_overlaps,
    )


def _raise_for_failed_test_report(report: TestReport) -> None:
    if report.passed:
        return
    lines = ["SDK tests failed:"]
    for failure in report.failures[:10]:
        lines.append(f"- {failure.name}: {failure.details}")
    if len(report.failures) > 10:
        lines.append(f"... ({len(report.failures) - 10} more)")
    exc = ValueError("\n".join(lines))
    setattr(exc, "test_report", report)
    raise exc


def _serialize_test_report(report: TestReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return _jsonable(asdict(report))


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def _replace_tree(source: Path, destination: Path) -> None:
    _remove_tree(destination)
    source.rename(destination)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        payload = {
            "status": "error",
            "manifest": "",
            "usdz": "",
            "test_report": None,
            "stdout": "",
            "stderr": "",
            "error": "Usage: mini-articraft-compile-run <run_dir>",
            "traceback": "",
        }
        payload["compile_report"] = build_compile_report_from_payload(payload)
        print(json.dumps(payload))
        return 2

    payload = compile_run(Path(args[0]).resolve())
    print(json.dumps(payload))
    return 0 if payload["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
