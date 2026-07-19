"""Tests for the tape CLI (scripts/tape.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from harness import GOOD_MAIN_PY, ReplayHarness, calls, text, tool_call

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "tape.py"


def cli(*args: str, root: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args, "--root", str(root)],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    root = tmp_path / "cassettes"
    library = ReplayHarness(root)
    library.set(
        "box",
        [
            {"meta": {"prompt": "a simple box"}},
            calls(tool_call("write", {"path": "main.py", "content": GOOD_MAIN_PY})),
            calls(tool_call("compile")),
            text("done", cost=0.25),
        ],
    )
    library.set("promptless", [text("hi")])
    return root


def test_list_shows_recordings_and_prompts(library_root: Path, tmp_path: Path) -> None:
    result = cli("list", root=library_root, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "box: 3 exchange(s)" in result.stdout
    assert "prompt='a simple box'" in result.stdout
    assert "promptless: 1 exchange(s)" in result.stdout


def test_show_prints_exchanges(library_root: Path, tmp_path: Path) -> None:
    result = cli("show", "box", root=library_root, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert 'meta: {"prompt": "a simple box"}' in result.stdout
    assert "tools=['write']" in result.stdout
    assert "tools=['compile']" in result.stdout
    assert "text='done'" in result.stdout


def test_replay_replays_a_recorded_generation(library_root: Path, tmp_path: Path) -> None:
    result = cli(
        "replay", "box", "--output-dir", str(tmp_path / "runs"), root=library_root, cwd=tmp_path
    )

    assert result.returncode == 0, result.stderr
    assert "turns=3" in result.stdout
    assert "status=success" in result.stdout
    assert "cost=$0.2500" in result.stdout
    run_dirs = list((tmp_path / "runs").glob("tape-box-*"))
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "result" / "usdz" / "0000.usdz").is_file()


def test_replay_requires_a_prompt_without_metadata(library_root: Path, tmp_path: Path) -> None:
    result = cli("replay", "promptless", root=library_root, cwd=tmp_path)

    assert result.returncode != 0
    assert "no recorded prompt" in result.stderr


def test_erase_removes_a_recording(library_root: Path, tmp_path: Path) -> None:
    result = cli("erase", "promptless", root=library_root, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "erased promptless" in result.stdout
    assert not (library_root / "promptless.jsonl").exists()

    missing = cli("erase", "promptless", root=library_root, cwd=tmp_path)
    assert missing.returncode != 0
    assert "unknown tape" in missing.stderr
