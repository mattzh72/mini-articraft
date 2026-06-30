from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from mini_articraft.sdk import TestReport

Severity = Literal["failure", "warning", "note"]
Status = Literal["success", "failure"]

FailureSpec = tuple[str, str, str, str]
FAILURE_SPECS: dict[str, FailureSpec] = {
    "check_model_valid": (
        "model_validity",
        "QC_MODEL_VALIDITY",
        "Model validation failed.",
        "compiler",
    ),
    "check_single_root_part": (
        "single_root_policy",
        "QC_SINGLE_ROOT_POLICY",
        "Model must have exactly one root part.",
        "compiler",
    ),
}


@dataclass(frozen=True)
class CompileSignal:
    severity: Severity
    kind: str
    code: str
    summary: str
    details: str = ""
    blocking: bool = False
    source: str = "compiler"
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
                self.check_name or "",
            ]
        )
        object.__setattr__(self, "dedupe_key", hashlib.sha1(raw.encode()).hexdigest())


@dataclass(frozen=True)
class CompileSignalBundle:
    status: Status
    summary: str
    signals: tuple[CompileSignal, ...] = ()


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
    bundle = _bundle(status, error, report)
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
    if not any(signal["severity"] == "failure" for signal in bundle["signals"]):
        return None
    raw = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha1(raw).hexdigest()


def render_compile_signals(
    bundle: CompileSignalBundle,
    *,
    repeated: bool = False,
    failure_streak: int = 0,
) -> str:
    failures = _failures(bundle.signals)
    warnings = [signal for signal in bundle.signals if signal.severity == "warning"]
    notes = [signal for signal in bundle.signals if signal.severity == "note"]
    summary = bundle.summary
    if repeated and failures:
        summary += "\nThis failure matches the previous compile attempt."
    if failure_streak >= 3 and failures:
        summary += f"\nThis is compile failure {failure_streak} in a row."

    parts = ["<compile_signals>", "<summary>", summary, "</summary>"]
    _add_section(parts, "failures", "Failures (blocking):", failures)
    _add_section(parts, "warnings", "Warnings (non-blocking):", warnings)
    if failures or warnings:
        _add_section(parts, "notes", "Notes (informational):", notes)
    rules = _rules(failures, has_warnings=bool(warnings), repeated=repeated)
    if rules:
        parts += ["", "<response_rules>", "Suggested next steps:\n" + "\n".join(rules), "</response_rules>"]
    parts.append("</compile_signals>")
    return "\n".join(parts)


def _bundle(status: Status, error: str, report: dict[str, Any] | None) -> CompileSignalBundle:
    signals = _signals_from_report(report) if report else []
    if status == "failure" and not _failures(signals):
        signals.append(_runtime_signal(error))
    signals = list({signal.dedupe_key: signal for signal in signals}.values())
    return CompileSignalBundle(status, _summary(status, signals), tuple(signals))


def _signals_from_report(report: dict[str, Any]) -> list[CompileSignal]:
    signals = [
        CompileSignal("warning", "test_warning", "TEST_WARNING", str(w).splitlines()[0], str(w), source="tests")
        for w in report.get("warnings", [])
        if str(w).strip()
    ]
    signals += [_allowance_signal(str(a)) for a in report.get("allowances", []) if str(a).strip()]
    signals += [_failure_signal(str(f["name"]), str(f.get("details") or "")) for f in report.get("failures", [])]
    return signals


def _failure_signal(name: str, details: str) -> CompileSignal:
    lower = f"{name}\n{details}".lower()
    spec = FAILURE_SPECS.get(name)
    if spec is None and "isolated" in lower:
        spec = ("isolated_part", "QC_ISOLATED_PART", "Disconnected or isolated parts were found.", "compiler")
    if spec is None and "disconnected geometry islands" in lower:
        spec = (
            "disconnected_geometry",
            "QC_DISCONNECTED_GEOMETRY",
            "Disconnected geometry islands were found inside a part.",
            "compiler",
        )
    if spec is None and ("collide" in lower or "contacts=" in lower or "collided=true" in lower):
        spec = ("mesh_collision", "QC_MESH_COLLISION", "Mesh collision check found overlapping parts.", "compiler")
    if spec is None and ("distance=" in lower or "contact_tol=" in lower or "min_distance" in lower):
        spec = ("distance_or_contact", "TEST_DISTANCE_OR_CONTACT", "Distance or contact check failed.", "tests")
    kind, code, summary, source = spec or (
        "test_failure",
        "TEST_FAILURE",
        f"Authored test failed: {name}",
        "tests",
    )
    return CompileSignal("failure", kind, code, summary, details, True, source, name)


def _allowance_signal(text: str) -> CompileSignal:
    if text.startswith("allow_overlap("):
        kind, code, summary = "allowed_overlap", "NOTE_ALLOWED_OVERLAP", "Overlap allowance declared."
    elif text.startswith("allow_isolated_part("):
        kind, code, summary = (
            "allowed_isolated_part",
            "NOTE_ALLOWED_ISOLATED_PART",
            "Isolated-part allowance declared.",
        )
    else:
        kind, code, summary = "allowance", "ALLOWANCE", text
    return CompileSignal("note", kind, code, summary, text, source="tests")


def _runtime_signal(error: str) -> CompileSignal:
    text = error.strip() or "Compile execution failed."
    lower = text.lower()
    if "missing required `run_tests()`" in lower:
        return CompileSignal(
            "failure",
            "missing_run_tests",
            "COMPILE_MISSING_RUN_TESTS",
            "main.py must define run_tests().",
            text,
            True,
        )
    if "run_tests() must return testreport" in lower:
        return CompileSignal(
            "failure",
            "invalid_run_tests_report",
            "COMPILE_INVALID_RUN_TESTS_REPORT",
            "run_tests() must return TestReport.",
            text,
            True,
        )
    return CompileSignal("failure", "compile_runtime", "COMPILE_RUNTIME_FAILURE", text, blocking=True)


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
        "isolated_part": "compiler-owned connectivity checks found isolated parts.",
        "disconnected_geometry": "compiler-owned geometry checks found floating islands inside a part.",
        "mesh_collision": "compiler-owned mesh collision checks found overlapping parts.",
    }
    return issues.get(signal.kind, signal.summary)


def _rules(failures: list[CompileSignal], *, has_warnings: bool, repeated: bool) -> list[str]:
    if not failures:
        return ["- Warnings are not blocking, but they are design evidence."] if has_warnings else []
    kind = failures[0].kind
    if kind in {"compile_runtime", "missing_run_tests", "invalid_run_tests_report"}:
        rules = ["- Fix the compile/runtime error first; geometry checks are blocked until the script runs cleanly."]
    elif kind in {"single_root_policy", "model_validity"}:
        rules = ["- Fix the model structure first; local geometry tuning is secondary."]
    elif kind in {"isolated_part", "disconnected_geometry", "mesh_collision"}:
        rules = ["- Fix or explicitly justify the reported part relationship before adding more geometry."]
    else:
        rules = ["- Fix the named failing check before adding more geometry or tests."]
    if repeated:
        rules.append("- This failure repeated; inspect the reported signal details before another small tweak.")
    if has_warnings:
        rules.append("- Warnings are not blocking, but they are design evidence.")
    return rules


def _add_section(parts: list[str], tag: str, title: str, signals: list[CompileSignal]) -> None:
    if signals:
        parts += ["", f"<{tag}>", title, *[_signal_line(s) for s in signals], f"</{tag}>"]


def _signal_line(signal: CompileSignal) -> str:
    line = f"- {signal.severity.upper()} [{signal.kind}] {signal.summary}"
    if signal.details:
        line += "\n" + "\n".join(f"  {part}" if part else "" for part in signal.details.splitlines())
    return line


def _failures(signals: list[CompileSignal] | tuple[CompileSignal, ...]) -> list[CompileSignal]:
    priority = {
        "compile_runtime": 0,
        "missing_run_tests": 0,
        "invalid_run_tests_report": 0,
        "model_validity": 1,
        "single_root_policy": 1,
        "isolated_part": 2,
        "disconnected_geometry": 2,
        "mesh_collision": 2,
    }
    return sorted(
        [s for s in signals if s.severity == "failure"],
        key=lambda s: (priority.get(s.kind, 9), s.kind, s.summary),
    )


def _counts(signals: list[CompileSignal] | tuple[CompileSignal, ...]) -> dict[str, int]:
    return {name: sum(1 for s in signals if s.severity == severity) for name, severity in (
        ("failures", "failure"),
        ("warnings", "warning"),
        ("notes", "note"),
    )}


def _bundle_from_dict(value: dict[str, Any]) -> CompileSignalBundle:
    return CompileSignalBundle(
        status=value["status"],
        summary=value["summary"],
        signals=tuple(CompileSignal(**signal) for signal in value["signals"]),
    )


def _report_dict(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    return asdict(value) if isinstance(value, TestReport) else value
