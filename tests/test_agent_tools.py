from __future__ import annotations

import asyncio
import base64
import shlex
import sys

import pytest

from mini_articraft.agent.tools import ToolContext, get, schemas
from mini_articraft.environments.local import LocalEnvironment


def run(awaitable):
    return asyncio.run(awaitable)


def context(tmp_path) -> ToolContext:
    env = LocalEnvironment(output_dir=tmp_path)
    run_dir = env.create_run("tools")
    return ToolContext(env, run_dir, run_dir / "workspace")


def test_tool_schemas_include_prompting_guidance() -> None:
    by_name = {tool["name"]: tool for tool in schemas()}
    exec_props = by_name["exec_command"]["parameters"]["properties"]
    stdin_props = by_name["write_stdin"]["parameters"]["properties"]
    edit_props = by_name["edit"]["parameters"]["properties"]

    assert "session ID for ongoing interaction" in by_name["exec_command"]["description"]
    assert exec_props["command"]["description"] == "Shell command to execute."
    assert (
        exec_props["max_output_tokens"]["description"]
        == "Output token budget. Defaults to 10000 tokens; larger requests may be capped by policy."
    )
    assert (
        stdin_props["chars"]["description"]
        == "Bytes to write to stdin. Defaults to empty, which polls without writing."
    )
    assert "appears exactly once" in edit_props["old_text"]["description"]


def test_read_rejects_path_escape(tmp_path) -> None:
    ctx = context(tmp_path)

    with pytest.raises(ValueError, match="inside"):
        run(get("read").run(ctx, {"path": "../outside.txt"}))


def test_read_text_with_offset_and_limit(tmp_path) -> None:
    ctx = context(tmp_path)
    ctx.workspace.joinpath("notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = run(get("read").run(ctx, {"path": "notes.txt", "offset": 2, "limit": 1}))

    assert result == {"path": "notes.txt", "text": "L2: two"}


def test_read_can_open_symlinked_sdk_docs(tmp_path) -> None:
    ctx = context(tmp_path)

    result = run(
        get("read").run(
            ctx,
            {"path": "docs/sdk/common/20_core_types.md", "offset": 1, "limit": 1},
        )
    )

    assert result["path"] == "docs/sdk/common/20_core_types.md"
    assert result["text"] == "L1: ---"


def test_read_image_returns_metadata_and_base64(tmp_path) -> None:
    ctx = context(tmp_path)
    ctx.workspace.joinpath("image.png").write_bytes(b"\x89PNG\r\n")

    result = run(get("read").run(ctx, {"path": "image.png"}))

    assert result["path"] == "image.png"
    assert result["mime_type"] == "image/png"
    assert result["bytes"] == 6
    assert result["base64"] == base64.b64encode(b"\x89PNG\r\n").decode("ascii")


def test_edit_replaces_unique_text(tmp_path) -> None:
    ctx = context(tmp_path)
    path = ctx.workspace / "main.py"
    path.write_text("old\n", encoding="utf-8")

    result = run(get("edit").run(ctx, {"path": "main.py", "old_text": "old", "new_text": "new"}))

    assert result == {"path": "main.py", "replaced": 1}
    assert path.read_text(encoding="utf-8") == "new\n"


def test_edit_fails_when_text_is_not_unique(tmp_path) -> None:
    ctx = context(tmp_path)
    ctx.workspace.joinpath("main.py").write_text("x\nx\n", encoding="utf-8")

    with pytest.raises(ValueError, match="2 times"):
        run(get("edit").run(ctx, {"path": "main.py", "old_text": "x", "new_text": "y"}))


def test_edit_rejects_symlinked_sdk_docs(tmp_path) -> None:
    ctx = context(tmp_path)

    with pytest.raises(ValueError, match="inside"):
        run(
            get("edit").run(
                ctx,
                {
                    "path": "docs/sdk/common/20_core_types.md",
                    "old_text": "Core Types",
                    "new_text": "Core Values",
                },
            )
        )


def test_write_creates_parent_dirs(tmp_path) -> None:
    ctx = context(tmp_path)

    result = run(get("write").run(ctx, {"path": "parts/main.py", "content": "x"}))

    assert result == {"path": "parts/main.py", "bytes": 1}
    assert ctx.workspace.joinpath("parts", "main.py").read_text(encoding="utf-8") == "x"


def test_write_rejects_symlinked_sdk_docs(tmp_path) -> None:
    ctx = context(tmp_path)

    with pytest.raises(ValueError, match="inside"):
        run(get("write").run(ctx, {"path": "docs/sdk/common/new.md", "content": "x"}))


def test_create_run_links_sdk_docs(tmp_path) -> None:
    ctx = context(tmp_path)

    link = ctx.workspace / "docs" / "sdk"
    assert link.is_symlink()
    assert link.joinpath("common", "00_quickstart.md").is_file()


def test_exec_command_reports_output_and_return_code(tmp_path) -> None:
    ctx = context(tmp_path)

    result = run(get("exec_command").run(ctx, {"command": "printf hi; exit 3"}))

    assert result["stdout"] == "hi"
    assert result["stderr"] == ""
    assert result["returncode"] == 3
    assert result["session_id"] is None
    assert result["running"] is False


def test_exec_command_reports_timeout(tmp_path) -> None:
    ctx = context(tmp_path)
    command = f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(2)'"

    result = run(get("exec_command").run(ctx, {"command": command, "timeout": 0.1}))

    assert result["timed_out"] is True
    assert result["running"] is False


def test_exec_command_rejects_cwd_outside_run_dir(tmp_path) -> None:
    ctx = context(tmp_path)

    with pytest.raises(ValueError, match="run directory"):
        run(get("exec_command").run(ctx, {"command": "pwd", "cwd": str(tmp_path)}))


def test_exec_command_returns_session_and_write_stdin_polls(tmp_path) -> None:
    ctx = context(tmp_path)
    command = f"{shlex.quote(sys.executable)} -c 'import time; time.sleep(.4); print(\"late\")'"

    async def exercise() -> tuple[dict[str, object], dict[str, object]]:
        first = await get("exec_command").run(ctx, {"command": command, "yield_time_ms": 50})
        second = await get("write_stdin").run(
            ctx,
            {"session_id": first["session_id"], "yield_time_ms": 1000},
        )
        return first, second

    first, second = run(exercise())

    assert first["running"] is True
    assert first["session_id"] is not None
    assert second["stdout"] == "late\n"
    assert second["returncode"] == 0


def test_write_stdin_sends_input(tmp_path) -> None:
    ctx = context(tmp_path)
    command = f"{shlex.quote(sys.executable)} -c 'import sys; print(sys.stdin.readline().strip().upper())'"

    async def exercise() -> tuple[dict[str, object], dict[str, object]]:
        first = await get("exec_command").run(ctx, {"command": command, "yield_time_ms": 50})
        second = await get("write_stdin").run(
            ctx,
            {"session_id": first["session_id"], "chars": "hello\n", "yield_time_ms": 1000},
        )
        return first, second

    _first, second = run(exercise())

    assert second["stdout"] == "HELLO\n"
    assert second["returncode"] == 0


def test_exec_command_truncates_output_middle(tmp_path) -> None:
    ctx = context(tmp_path)

    result = run(
        get("exec_command").run(
            ctx,
            {"command": "printf 0123456789abcdefghij", "max_output_tokens": 3},
        )
    )

    assert result["stdout"] == "012345…8 chars truncated…efghij"


def test_compile_tool_compiles_workspace(tmp_path) -> None:
    ctx = context(tmp_path)
    ctx.workspace.joinpath("main.py").write_text(
        """
import cadquery as cq

from mini_articraft.sdk import ArticulatedObject

object_model = ArticulatedObject("box")
object_model.part("base", cq.Workplane("XY").box(1, 1, 1))
""",
        encoding="utf-8",
    )

    result = run(get("compile").run(ctx, {}))

    assert result["status"] == "success"
    assert ctx.compiled_revision == ctx.revision
