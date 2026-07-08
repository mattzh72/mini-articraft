from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

from mini_articraft.sdk import TestReport

Severity = Literal["failure", "warning", "note"]
Status = Literal["success", "failure"]
SignalGroup = Literal["build", "qc", "design", "hygiene"]


@dataclass(frozen=True)
class CompileSignal:
    severity: Severity
    kind: str
    code: str
    summary: str
    details: str = ""
    blocking: bool = False
    source: str = "compiler"
    group: SignalGroup = "qc"
    check_name: str | None = None
    dedupe_key: str = ""

    def __post_init__(self) -> None:
        if self.dedupe_key:
            return
        raw = "\n".join(
            [
                self.severity,
                self.kind,
                self.code,
                self.summary,
                self.details,
                str(self.blocking),
                self.source,
                self.group,
                self.check_name or "",
            ]
        )
        object.__setattr__(self, "dedupe_key", hashlib.sha1(raw.encode()).hexdigest())


@dataclass(frozen=True)
class CompileSignalBundle:
    status: Status
    summary: str
    signals: tuple[CompileSignal, ...] = ()


def empty_compile_payload(*, error: str = "", stdout: str = "", stderr: str = "") -> dict[str, Any]:
    return {
        "status": "error",
        "manifest": "",
        "usdz": "",
        "test_report": None,
        "stdout": stdout,
        "stderr": stderr,
        "error": error,
        "traceback": "",
    }


def build_compile_report_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    status: Status = "success" if payload["status"] == "success" else "failure"
    return build_compile_report(
        status=status,
        error=str(payload.get("error") or ""),
        traceback_text=str(payload.get("traceback") or ""),
        stdout=str(payload.get("stdout") or ""),
        stderr=str(payload.get("stderr") or ""),
        returncode=payload.get("returncode"),
        test_report=payload.get("test_report"),
    )


def build_compile_report(
    *,
    status: Status,
    error: str = "",
    traceback_text: str = "",
    stdout: str = "",
    stderr: str = "",
    returncode: object = None,
    test_report: object = None,
) -> dict[str, Any]:
    report = _report_dict(test_report)
    bundle = _bundle(status, error, report, traceback_text=traceback_text)
    return {
        "status": status,
        "error": error,
        "traceback": traceback_text,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": returncode,
        "counts": _counts(bundle.signals),
        "test_report": report,
        "signal_bundle": asdict(bundle),
        "signals_text": render_compile_signals(bundle),
    }


def render_compile_report(
    report: dict[str, Any],
    *,
    repeated: bool = False,
    failure_streak: int = 0,
) -> dict[str, Any]:
    rendered = dict(report)
    rendered["signals_text"] = render_compile_signals(
        _bundle_from_dict(report["signal_bundle"]),
        repeated=repeated,
        failure_streak=failure_streak,
    )
    return rendered


def compile_failure_signature(report: dict[str, Any]) -> str | None:
    bundle = report["signal_bundle"]
    failures = [signal for signal in bundle["signals"] if signal["severity"] == "failure"]
    if not failures:
        return None
    failures.sort(
        key=lambda signal: (
            signal.get("kind", ""),
            signal.get("source", ""),
            signal.get("check_name") or "",
            signal.get("summary", ""),
            signal.get("details", ""),
        )
    )
    raw = json.dumps(failures, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha1(raw).hexdigest()


def render_compile_signals(
    bundle: CompileSignalBundle,
    *,
    repeated: bool = False,
    failure_streak: int = 0,
) -> str:
    failures = _failures(bundle.signals)
    warnings = _ordered_signals(bundle.signals, "warning")
    notes = _ordered_signals(bundle.signals, "note")
    summary = bundle.summary
    if repeated and failures:
        summary += "\nThis failure matches the previous compile attempt."
    if failure_streak >= 3 and failures:
        summary += f"\nThis is compile failure {failure_streak} in a row."

    parts = ["<compile_signals>", "<summary>", summary, "</summary>"]
    _add_section(parts, "failures", "Failures (blocking):", failures)
    _add_section(parts, "warnings", "Warnings (non-blocking):", warnings)
    if notes:
        _add_section(parts, "notes", "Notes (informational):", notes)
    rules = _rules(
        failures,
        has_warnings=bool(warnings),
        repeated=repeated,
        failure_streak=failure_streak,
    )
    if rules:
        parts += [
            "",
            "<response_rules>",
            "Suggested next steps:\n" + "\n".join(rules),
            "</response_rules>",
        ]
    parts.append("</compile_signals>")
    return "\n".join(parts)


def _bundle(
    status: Status,
    error: str,
    report: dict[str, Any] | None,
    *,
    traceback_text: str = "",
) -> CompileSignalBundle:
    signals = _signals_from_report(report) if report else []
    if status == "failure" and not _failures(signals):
        signals.append(_runtime_signal(error, traceback_text=traceback_text))
    signals = sorted(
        {signal.dedupe_key: signal for signal in signals}.values(),
        key=_signal_sort_key,
    )
    return CompileSignalBundle(status, _summary(status, signals), tuple(signals))


def _signals_from_report(report: dict[str, Any]) -> list[CompileSignal]:
    signals = [
        _warning_signal(str(item)) for item in report.get("warnings", []) if str(item).strip()
    ]
    signals += [_allowance_signal(str(a)) for a in report.get("allowances", []) if str(a).strip()]
    signals += [
        _failure_signal(str(f["name"]), str(f.get("details") or ""))
        for f in report.get("failures", [])
    ]
    return signals


def _warning_signal(text: str) -> CompileSignal:
    stripped = text.strip()
    lower = stripped.lower()
    headline = stripped.splitlines()[0]
    if any(
        marker in lower
        for marker in (
            "non-finite or absurd geometry dimensions",
            "geometry outlier dimensions",
            "geometry scale",
            "scale warning",
        )
    ):
        return CompileSignal(
            "warning",
            "geometry_scale",
            "WARN_GEOMETRY_SCALE",
            headline,
            stripped,
            source="compiler",
            group="design",
        )
    if lower.startswith("overlaps detected but allowed by justification"):
        return CompileSignal(
            "note",
            "allowed_overlap",
            "NOTE_ALLOWED_OVERLAP",
            "Overlap findings were allowed by justification.",
            stripped,
            source="tests",
            group="qc",
        )
    if lower.startswith("isolated parts detected but allowed by justification"):
        return CompileSignal(
            "note",
            "allowed_isolated_part",
            "NOTE_ALLOWED_ISOLATED_PART",
            "Isolated-part findings were allowed by justification.",
            stripped,
            source="tests",
            group="design",
        )
    if "disconnected geometry" in lower or lower.startswith(
        "warn_if_part_contains_disconnected_geometry_islands("
    ):
        return CompileSignal(
            "warning",
            "disconnected_geometry",
            "WARN_DISCONNECTED_GEOMETRY",
            "A part contains disconnected geometry that should be inspected.",
            stripped,
            source="tests",
            group="qc",
        )
    return CompileSignal(
        "warning",
        "test_warning",
        "TEST_WARNING",
        headline,
        stripped,
        source="tests",
        group="qc",
    )


def _failure_signal(name: str, details: str) -> CompileSignal:
    lower = f"{name}\n{details}".lower()
    if name == "check_model_valid":
        return _failure(
            "model_validity",
            "QC_MODEL_VALIDITY",
            "Compiler model validation failed.",
            name,
            details,
            source="compiler",
            group="build",
        )
    if name == "check_single_root_part":
        return _failure(
            "single_root_policy",
            "QC_SINGLE_ROOT_POLICY",
            "The model must have exactly one root part.",
            name,
            details,
            source="compiler",
            group="build",
        )
    if "missing exact geometry" in lower or "missing named geometry" in lower:
        return _failure(
            "missing_exact_geometry",
            "TEST_MISSING_EXACT_GEOMETRY",
            "A check references named geometry that is not present.",
            name,
            details,
        )
    if (
        "disconnected geometry islands" not in lower
        and "contact_tol=" in lower
        and ("distance=" in lower or "min_distance=" in lower)
    ):
        return _failure(
            "exact_contact_gap",
            "TEST_EXACT_CONTACT_GAP",
            "A contact check found a gap where contact was expected.",
            name,
            details,
        )
    if (
        name in {"fail_if_isolated_parts", "fail_if_isolated_parts()"}
        or name.startswith("fail_if_isolated_parts(")
        or "isolated parts detected" in lower
    ):
        source = (
            "compiler"
            if name in {"fail_if_isolated_parts", "fail_if_isolated_parts()"}
            else "tests"
        )
        code = "QC_ISOLATED_PART" if source == "compiler" else "TEST_ISOLATED_PART"
        return _failure(
            "isolated_part",
            code,
            "Floating or disconnected parts were found.",
            name,
            details,
            source=source,
        )
    if any(
        marker in lower
        for marker in (
            "part overlaps detected",
            "collided=true",
            "fail_if_parts_overlap",
        )
    ):
        source = (
            "compiler"
            if name
            in {
                "fail_if_parts_overlap_in_current_pose()",
            }
            else "tests"
        )
        code = "QC_REAL_OVERLAP" if source == "compiler" else "TEST_REAL_OVERLAP"
        return _failure(
            "real_overlap",
            code,
            "A mesh check found overlapping parts.",
            name,
            details,
            source=source,
        )
    return _failure(
        "test_failure",
        "TEST_FAILURE",
        f"Authored test failed: {name}",
        name,
        details,
    )


def _failure(
    kind: str,
    code: str,
    summary: str,
    check_name: str,
    details: str,
    *,
    source: str = "tests",
    group: SignalGroup = "qc",
) -> CompileSignal:
    return CompileSignal(
        "failure",
        kind,
        code,
        summary,
        details,
        blocking=True,
        source=source,
        group=group,
        check_name=check_name,
    )


def _allowance_signal(text: str) -> CompileSignal:
    if text.startswith("allow_overlap("):
        kind, code, summary = (
            "allowed_overlap",
            "NOTE_ALLOWED_OVERLAP",
            "Overlap allowance declared.",
        )
    elif text.startswith("allow_isolated_part("):
        kind, code, summary = (
            "allowed_isolated_part",
            "NOTE_ALLOWED_ISOLATED_PART",
            "Isolated-part allowance declared.",
        )
    else:
        kind, code, summary = "allowance", "ALLOWANCE", text
    group: SignalGroup = "design" if kind == "allowed_isolated_part" else "qc"
    return CompileSignal(
        "note",
        kind,
        code,
        summary,
        text,
        source="tests",
        group=group,
    )


def _runtime_signal(error: str, *, traceback_text: str = "") -> CompileSignal:
    text = error.strip() or "Compile execution failed."
    details = _runtime_details(text, traceback_text)
    lower = text.lower()
    if any(
        marker in lower
        for marker in ("unknown shape", "missing named geometry", "missing exact geometry")
    ):
        return CompileSignal(
            "failure",
            "missing_exact_geometry",
            "TEST_MISSING_EXACT_GEOMETRY",
            "A check references named geometry that is not present.",
            details,
            blocking=True,
            source="tests",
            group="qc",
        )
    if "missing required `run_tests()`" in lower:
        return CompileSignal(
            "failure",
            "missing_run_tests",
            "COMPILE_MISSING_RUN_TESTS",
            "main.py must define run_tests().",
            details,
            blocking=True,
            group="build",
        )
    if "run_tests() must return testreport" in lower:
        return CompileSignal(
            "failure",
            "invalid_run_tests_report",
            "COMPILE_INVALID_RUN_TESTS_REPORT",
            "run_tests() must return TestReport.",
            details,
            blocking=True,
            group="build",
        )
    location = _user_traceback_location(traceback_text)
    return CompileSignal(
        "failure",
        "compile_runtime",
        "COMPILE_RUNTIME_FAILURE",
        text,
        f"location={location}" if location is not None else "",
        blocking=True,
        group="build",
    )


def _runtime_details(error: str, traceback_text: str) -> str:
    location = _user_traceback_location(traceback_text)
    return error if location is None else f"{error}\nlocation={location}"


def _user_traceback_location(traceback_text: str) -> str | None:
    found: str | None = None
    pattern = re.compile(r'^\s*File "([^"]+)", line (\d+)(?:, in ([^\n]+))?', re.MULTILINE)
    for match in pattern.finditer(traceback_text):
        raw_path, line, function = match.groups()
        normalized = raw_path.replace("\\", "/")
        marker = "/workspace/"
        if marker in normalized:
            path = normalized.rsplit(marker, 1)[1]
        elif normalized == "main.py" or normalized.endswith("/main.py"):
            path = "main.py"
        else:
            continue
        found = f"{path}:{line}"
        if function:
            found += f" in {function.strip()}"
    return found


def _summary(status: Status, signals: list[CompileSignal]) -> str:
    counts = _counts(signals)
    header = f"status={status} failures={counts['failures']} warnings={counts['warnings']} notes={counts['notes']}"
    if first := next(iter(_failures(signals)), None):
        return f"{header}\nPrimary issue: {_primary_issue(first)}"
    if counts["warnings"]:
        return f"{header}\nPrimary issue: compile passed with warnings."
    return f"{header}\nCompile passed cleanly."


def _primary_issue(signal: CompileSignal) -> str:
    issues = {
        "missing_run_tests": "generated script is missing required run_tests().",
        "invalid_run_tests_report": "run_tests() returned the wrong type.",
        "single_root_policy": "compiler-owned root policy failed.",
        "model_validity": "compiler-owned model validation failed.",
        "isolated_part": (
            "compiler-owned connectivity checks found isolated parts."
            if signal.source == "compiler"
            else "an authored test found isolated parts."
        ),
        "real_overlap": "mesh checks found overlapping parts that need classification.",
        "missing_exact_geometry": "a check references missing named geometry.",
        "exact_contact_gap": "a contact check found separation where contact was expected.",
        "test_failure": "a required authored test failed.",
    }
    return issues.get(signal.kind, signal.summary)


def _rules(
    failures: list[CompileSignal],
    *,
    has_warnings: bool,
    repeated: bool,
    failure_streak: int,
) -> list[str]:
    if not failures:
        return (
            [
                "- Warnings are design evidence. Do not remove or simplify prompt-critical geometry just to clear them."
            ]
            if has_warnings
            else []
        )
    kind = failures[0].kind
    if kind in {"compile_runtime", "missing_run_tests", "invalid_run_tests_report"}:
        rules = [
            "- Fix the compile or runtime error first. Geometry checks are blocked until the script runs."
        ]
    elif kind in {"single_root_policy", "model_validity"}:
        rules = ["- Fix the model structure first. Local geometry tuning comes after that."]
    elif kind == "isolated_part":
        rules = [
            "- Repair the reported support path, or add a precise allowance when the separation is intentional."
        ]
    elif kind == "real_overlap":
        rules = [
            "- Decide whether the reported overlap is intentional embedding or an unintended collision.",
            "- Preserve prompt-critical visible geometry while repairing or allowing the exact reported pair.",
        ]
    elif kind == "missing_exact_geometry":
        rules = [
            "- Restore the named geometry or update the dependent check in the same edit. This does not call for a broad geometry rewrite."
        ]
    elif kind == "exact_contact_gap":
        rules = [
            "- This is a gap, not an overlap. Verify the tested pair, then repair its geometry or placement."
        ]
    else:
        rules = ["- Fix the named failing check before adding more geometry or tests."]
    if failure_streak >= 3:
        rules.append(f"- The repair loop has continued. {_inspection_advice(kind)}")
    elif repeated:
        rules.append(f"- This failure repeated. {_inspection_advice(kind)}")
    if has_warnings:
        rules.append(
            "- Warnings are design evidence. Do not remove or simplify prompt-critical geometry just to clear them."
        )
    return rules


def _inspection_advice(kind: str) -> str:
    if kind in {"compile_runtime", "missing_run_tests", "invalid_run_tests_report"}:
        return "Use one short `exec_command` inspection of the exception location or API before editing."
    if kind in {"single_root_policy", "model_validity"}:
        return "Use one short `exec_command` inspection of the model structure before editing."
    return "Use one short `exec_command` inspection of the named geometry or support path before editing."


def _add_section(parts: list[str], tag: str, title: str, signals: list[CompileSignal]) -> None:
    if signals:
        parts += ["", f"<{tag}>", title, *[_signal_line(s) for s in signals], f"</{tag}>"]


def _signal_line(signal: CompileSignal) -> str:
    line = f"- {signal.severity.upper()} [{signal.kind}] {signal.summary}"
    if signal.details:
        line += "\n" + "\n".join(
            f"  {part}" if part else "" for part in signal.details.splitlines()
        )
    return line


def _failures(signals: list[CompileSignal] | tuple[CompileSignal, ...]) -> list[CompileSignal]:
    return _ordered_signals(signals, "failure")


def _ordered_signals(
    signals: list[CompileSignal] | tuple[CompileSignal, ...],
    severity: Severity,
) -> list[CompileSignal]:
    return sorted(
        (signal for signal in signals if signal.severity == severity),
        key=_signal_sort_key,
    )


def _signal_sort_key(signal: CompileSignal) -> tuple[int, int, str, str, str, str]:
    severity_priority = {"failure": 0, "warning": 1, "note": 2}
    failure_priority = {
        "compile_runtime": 0,
        "missing_run_tests": 0,
        "invalid_run_tests_report": 0,
        "model_validity": 1,
        "single_root_policy": 1,
        "isolated_part": 2 if signal.source == "compiler" else 6,
        "real_overlap": 2 if signal.source == "compiler" else 5,
        "missing_exact_geometry": 3,
        "exact_contact_gap": 4,
        "test_failure": 7,
    }
    kind_priority = failure_priority.get(signal.kind, 20)
    return (
        severity_priority[signal.severity],
        kind_priority,
        signal.kind,
        signal.check_name or "",
        signal.summary,
        signal.details,
    )


def _counts(signals: list[CompileSignal] | tuple[CompileSignal, ...]) -> dict[str, int]:
    return {
        name: sum(1 for s in signals if s.severity == severity)
        for name, severity in (
            ("failures", "failure"),
            ("warnings", "warning"),
            ("notes", "note"),
        )
    }


def _bundle_from_dict(value: dict[str, Any]) -> CompileSignalBundle:
    return CompileSignalBundle(
        status=value["status"],
        summary=value["summary"],
        signals=tuple(CompileSignal(**signal) for signal in value["signals"]),
    )


def _report_dict(value: object) -> dict[str, Any] | None:
    if isinstance(value, TestReport):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return None
