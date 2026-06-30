from __future__ import annotations

from mini_articraft.compile_feedback import build_compile_report, compile_failure_signature
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
    assert signal["blocking"] is True
    assert compile_failure_signature(report)
    assert "<failures>" in report["signals_text"]
    assert "- FAILURE [compile_runtime] ValueError: bad loft" in report["signals_text"]


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


def test_compile_report_maps_test_failures_warnings_and_allowances() -> None:
    test_report = TestReport(
        passed=False,
        checks_run=3,
        checks=("prompt check", "fail_if_parts_collide_in_current_pose"),
        failures=(
            TestFailure("prompt check", "missing handle"),
            TestFailure(
                "fail_if_parts_collide_in_current_pose",
                "'drawer' vs 'frame': collided=True contacts=1",
            ),
        ),
        warnings=("thin wall",),
        allowances=("allow_overlap('shaft', 'hub'): intentional capture",),
    )

    report = build_compile_report(status="failure", test_report=test_report)
    kinds = [signal["kind"] for signal in report["signal_bundle"]["signals"]]

    assert kinds == ["test_warning", "allowed_overlap", "test_failure", "mesh_collision"]
    assert report["counts"] == {"failures": 2, "warnings": 1, "notes": 1}
    assert "<warnings>" in report["signals_text"]
    assert "<notes>" in report["signals_text"]
