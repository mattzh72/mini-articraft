from __future__ import annotations

from mini_articraft.compile_feedback import (
    build_compile_report,
    compile_failure_signature,
    render_compile_report,
)
from mini_articraft.sdk import TestFailure, TestReport


def test_compile_report_clean_success_uses_articraft_style_block() -> None:
    report = build_compile_report(status="success")

    assert report["counts"] == {"failures": 0, "warnings": 0, "notes": 0}
    assert report["signal_bundle"]["summary"] == (
        "status=success failures=0 warnings=0 notes=0\nCompile passed cleanly."
    )
    assert report["signals_text"] == (
        "<compile_signals>\n"
        "<summary>\n"
        "status=success failures=0 warnings=0 notes=0\n"
        "Compile passed cleanly.\n"
        "</summary>\n"
        "</compile_signals>"
    )


def test_compile_report_classifies_runtime_errors() -> None:
    report = build_compile_report(status="failure", error="ValueError: bad loft")

    signal = report["signal_bundle"]["signals"][0]
    assert signal["kind"] == "compile_runtime"
    assert signal["group"] == "build"
    assert signal["blocking"] is True
    assert compile_failure_signature(report)
    assert "<failures>" in report["signals_text"]
    assert "- FAILURE [compile_runtime] ValueError: bad loft" in report["signals_text"]


def test_runtime_signal_includes_one_sanitized_workspace_frame() -> None:
    report = build_compile_report(
        status="failure",
        error="NameError: name 'missing' is not defined",
        traceback_text=(
            "Traceback (most recent call last):\n"
            '  File "/private/repo/src/mini_articraft/environments/worker.py", line 1, in run\n'
            "    runpy.run_path(path)\n"
            '  File "/private/runs/demo/workspace/helpers/body.py", line 12, in build\n'
            "    return missing\n"
            "NameError: name 'missing' is not defined\n"
        ),
    )

    signal = report["signal_bundle"]["signals"][0]
    assert signal["details"] == "location=helpers/body.py:12 in build"
    assert signal["details"].count("NameError") == 0
    assert "/private/runs" not in report["signals_text"]


def test_compile_report_classifies_required_run_tests_errors() -> None:
    missing = build_compile_report(
        status="failure",
        error="ValueError: Missing required `run_tests()` in main.py.",
    )
    invalid = build_compile_report(
        status="failure",
        error="ValueError: run_tests() must return TestReport (got NoneType)",
    )

    assert missing["signal_bundle"]["signals"][0]["kind"] == "missing_run_tests"
    assert invalid["signal_bundle"]["signals"][0]["kind"] == "invalid_run_tests_report"


def test_compile_report_classifies_timeout_with_specific_guidance() -> None:
    report = build_compile_report(
        status="failure",
        error=(
            "Compile timed out after 900s while loading main.py and building the model. "
            "The worker and its child processes were stopped."
        ),
    )

    signal = report["signal_bundle"]["signals"][0]
    assert signal["kind"] == "compile_timeout"
    assert signal["code"] == "COMPILE_TIMEOUT"
    assert "Inspect the phase named in the timeout" in report["signals_text"]
    assert "coarser tolerance" in report["signals_text"]


def test_compile_report_classifies_runtime_unknown_shape_as_missing_geometry() -> None:
    report = build_compile_report(
        status="failure",
        error="ValidationError: unknown shape 'hinge_boss' on part 'frame'",
    )

    signal = report["signal_bundle"]["signals"][0]
    assert signal["kind"] == "missing_exact_geometry"
    assert signal["code"] == "TEST_MISSING_EXACT_GEOMETRY"
    assert signal["source"] == "tests"


def test_compile_report_maps_test_failures_warnings_and_allowances() -> None:
    test_report = TestReport(
        passed=False,
        checks_run=3,
        checks=("prompt check", "fail_if_parts_overlap_in_current_pose()"),
        failures=(
            TestFailure("prompt check", "missing handle"),
            TestFailure(
                "fail_if_parts_overlap_in_current_pose()",
                "'drawer' vs 'frame': collided=True contacts=1",
            ),
        ),
        warnings=("thin wall",),
        allowances=(
            "allow_overlap('shaft', 'hub', shape_a='steel', shape_b='liner'): intentional capture",
        ),
    )

    report = build_compile_report(status="failure", test_report=test_report)
    kinds = [signal["kind"] for signal in report["signal_bundle"]["signals"]]

    assert kinds == ["real_overlap", "test_failure", "test_warning", "allowed_overlap"]
    assert report["counts"] == {"failures": 2, "warnings": 1, "notes": 1}
    assert "<warnings>" in report["signals_text"]
    assert "<notes>" in report["signals_text"]


def test_compile_report_maps_disconnected_geometry_warning() -> None:
    test_report = TestReport(
        passed=True,
        checks_run=1,
        checks=("warn_if_part_contains_disconnected_geometry_islands(contact_tol=1e-06)",),
        failures=(),
        warnings=(
            "Disconnected geometry islands detected:\n"
            "part='base' connected=1/2 contact_tol=1e-06 "
            "disconnected=[solid_002 nearest=solid_001 distance=0.2]",
        ),
    )

    report = build_compile_report(status="success", test_report=test_report)
    signal = report["signal_bundle"]["signals"][0]

    assert signal["kind"] == "disconnected_geometry"
    assert signal["code"] == "WARN_DISCONNECTED_GEOMETRY"
    assert signal["severity"] == "warning"
    assert signal["blocking"] is False


def test_compile_report_classifies_named_geometry_contact_and_scale() -> None:
    test_report = TestReport(
        passed=False,
        checks_run=2,
        checks=("contact", "named shape"),
        failures=(
            TestFailure(
                "contact",
                "'lid' vs 'body': distance=0.015 collided=False contact_tol=1e-06",
            ),
            TestFailure("named shape", "missing exact geometry for shape_b='boss'"),
        ),
        warnings=("Scale warning:\nabsurd dimension: 'base'/'body' spans 2000m",),
    )

    report = build_compile_report(status="failure", test_report=test_report)
    signals = report["signal_bundle"]["signals"]

    assert [signal["kind"] for signal in signals] == [
        "missing_exact_geometry",
        "exact_contact_gap",
        "geometry_scale",
    ]
    assert signals[2]["group"] == "design"


def test_compile_failure_signature_and_rendering_are_stable() -> None:
    left = build_compile_report(
        status="failure",
        test_report=TestReport(
            passed=False,
            checks_run=2,
            checks=("b", "a"),
            failures=(TestFailure("b", "bad b"), TestFailure("a", "bad a")),
            warnings=("warning one",),
        ),
    )
    right = build_compile_report(
        status="failure",
        test_report=TestReport(
            passed=False,
            checks_run=2,
            checks=("a", "b"),
            failures=(TestFailure("a", "bad a"), TestFailure("b", "bad b")),
            warnings=("a different warning",),
        ),
    )

    assert compile_failure_signature(left) == compile_failure_signature(right)
    rendered = render_compile_report(left, repeated=True, failure_streak=3)["signals_text"]
    assert "This failure matches the previous compile attempt." in rendered
    assert "This is compile failure 3 in a row." in rendered
    assert "`exec_command` inspection" in rendered
