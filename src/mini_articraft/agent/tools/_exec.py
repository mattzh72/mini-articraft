from __future__ import annotations

import asyncio
import contextlib
import os
import secrets
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mini_articraft.agent.tools._core import ToolContext, scoped_path

DEFAULT_YIELD_TIME_MS = 10_000
MAX_YIELD_TIME_MS = 30_000
MAX_OUTPUT_TOKENS = 10_000
MAX_OUTPUT_BYTES = 1024 * 1024


class OutputBuffer:
    def __init__(self) -> None:
        self._head_budget = MAX_OUTPUT_BYTES // 2
        self._tail_budget = MAX_OUTPUT_BYTES - self._head_budget
        self._head = bytearray()
        self._tail = bytearray()
        self._omitted = 0
        self._lock = asyncio.Lock()

    async def append(self, chunk: bytes) -> None:
        async with self._lock:
            if len(self._head) < self._head_budget:
                head = chunk[: self._head_budget - len(self._head)]
                self._head.extend(head)
                chunk = chunk[len(head) :]
            if not chunk:
                return
            if len(chunk) >= self._tail_budget:
                self._omitted += len(self._tail) + len(chunk) - self._tail_budget
                self._tail = bytearray(chunk[-self._tail_budget :])
                return
            self._tail.extend(chunk)
            overflow = len(self._tail) - self._tail_budget
            if overflow > 0:
                del self._tail[:overflow]
                self._omitted += overflow

    async def drain(self) -> tuple[bytes, int]:
        async with self._lock:
            data = bytes(self._head + self._tail)
            omitted = self._omitted
            self._head.clear()
            self._tail.clear()
            self._omitted = 0
            return data, omitted


@dataclass
class ExecSession:
    session_id: int
    proc: asyncio.subprocess.Process
    run_dir: Path
    stdout: OutputBuffer
    stderr: OutputBuffer
    output_event: asyncio.Event
    started_at: float
    output_closed: int = 0

    def alive(self) -> bool:
        return self.proc.returncode is None


class ExecManager:
    def __init__(self) -> None:
        self._next_session_id = 1
        self._sessions: dict[int, ExecSession] = {}

    async def start(self, context: ToolContext, args: dict[str, Any]) -> ExecSession:
        cwd = _cwd(context, args.get("cwd"))
        command = [
            _shell(args.get("shell")),
            "-lc" if _bool(args.get("login"), default=True) else "-c",
            str(args["command"]),
        ]
        (context.run_dir / ".tmp").mkdir(exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=_env(context, command[0]),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        session = ExecSession(
            session_id=self._allocate(),
            proc=proc,
            run_dir=context.run_dir.resolve(),
            stdout=OutputBuffer(),
            stderr=OutputBuffer(),
            output_event=asyncio.Event(),
            started_at=time.perf_counter(),
        )
        self._sessions[session.session_id] = session
        assert proc.stdout is not None
        assert proc.stderr is not None
        asyncio.create_task(_read_stream(session, proc.stdout, session.stdout))
        asyncio.create_task(_read_stream(session, proc.stderr, session.stderr))
        return session

    def get(self, context: ToolContext, session_id: int) -> ExecSession:
        session = self._sessions.get(session_id)
        if session is None or session.run_dir != context.run_dir.resolve():
            raise ValueError(f"unknown exec session: {session_id}")
        return session

    def release(self, session: ExecSession) -> None:
        self._sessions.pop(session.session_id, None)

    def _allocate(self) -> int:
        session_id = self._next_session_id
        self._next_session_id += 1
        return session_id


MANAGER = ExecManager()


async def collect(session: ExecSession, args: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    deadline = started + _yield_time(args)
    stdout: list[bytes] = []
    stderr: list[bytes] = []
    omitted = 0
    while True:
        out, out_omitted = await session.stdout.drain()
        err, err_omitted = await session.stderr.drain()
        if out or err:
            stdout.append(out)
            stderr.append(err)
            omitted += out_omitted + err_omitted
            continue
        if not session.alive() and session.output_closed == 2:
            break
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        session.output_event.clear()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(session.output_event.wait(), timeout=remaining)

    timed_out = session.alive() and _hit_timeout(started, args)
    if timed_out:
        _kill_process_group(session.proc)
        await session.proc.wait()
        out, out_omitted = await session.stdout.drain()
        err, err_omitted = await session.stderr.drain()
        stdout.append(out)
        stderr.append(err)
        omitted += out_omitted + err_omitted

    if not session.alive():
        MANAGER.release(session)

    return {
        "chunk_id": secrets.token_hex(3),
        "stdout": _decode(b"".join(stdout), args.get("max_output_tokens")),
        "stderr": _decode(b"".join(stderr), args.get("max_output_tokens")),
        "returncode": session.proc.returncode,
        "session_id": session.session_id if session.alive() else None,
        "running": session.alive(),
        "timed_out": timed_out,
        "wall_time_seconds": round(time.perf_counter() - started, 4),
        "omitted_bytes": omitted,
    }


async def write(session: ExecSession, chars: str) -> None:
    if not chars:
        return
    if not session.alive() or session.proc.stdin is None:
        raise ValueError(f"stdin is closed for exec session: {session.session_id}")
    if chars == "\x03":
        _interrupt_process_group(session.proc)
        return
    session.proc.stdin.write(chars.encode("utf-8"))
    await session.proc.stdin.drain()


def session_id(value: object) -> int:
    try:
        session_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("session_id must be a positive integer") from exc
    if session_id < 1:
        raise ValueError("session_id must be a positive integer")
    return session_id


async def _read_stream(
    session: ExecSession,
    stream: asyncio.StreamReader,
    buffer: OutputBuffer,
) -> None:
    try:
        while chunk := await stream.read(8192):
            await buffer.append(chunk)
            session.output_event.set()
    finally:
        session.output_closed += 1
        session.output_event.set()


def _cwd(context: ToolContext, raw: object) -> Path:
    if raw is None or str(raw).strip() == "":
        return context.workspace.resolve()
    path = scoped_path(context.workspace, str(raw), "run workspace")
    if not path.is_dir():
        raise ValueError("cwd must be a directory inside the run workspace")
    return path


def _env(context: ToolContext, shell: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    env["SHELL"] = shell
    env["TMPDIR"] = str(context.run_dir / ".tmp")
    env["MINI_ARTICRAFT_RUN_DIR"] = str(context.run_dir)
    env["MINI_ARTICRAFT_WORKSPACE_DIR"] = str(context.workspace)
    return env


def _shell(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return os.environ.get("SHELL") or "/bin/sh"


def _bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _yield_time(args: dict[str, Any]) -> float:
    if args.get("timeout") is not None:
        return max(0.0, float(args["timeout"]))
    raw = args.get("yield_time_ms")
    try:
        value = int(raw) if raw is not None else DEFAULT_YIELD_TIME_MS
    except (TypeError, ValueError):
        value = DEFAULT_YIELD_TIME_MS
    return max(0.0, min(value, MAX_YIELD_TIME_MS) / 1000)


def _hit_timeout(started: float, args: dict[str, Any]) -> bool:
    return args.get("timeout") is not None and (
        time.perf_counter() - started >= float(args["timeout"])
    )


def _decode(data: bytes, max_output_tokens: object) -> str:
    text = data.decode("utf-8", errors="replace")
    budget = _char_budget(max_output_tokens)
    if len(text) <= budget:
        return text
    left = text[: budget // 2]
    right = text[-(budget - len(left)) :]
    return f"{left}…{len(text) - budget} chars truncated…{right}"


def _char_budget(raw_tokens: object) -> int:
    try:
        tokens = int(raw_tokens) if raw_tokens is not None else MAX_OUTPUT_TOKENS
    except (TypeError, ValueError):
        tokens = MAX_OUTPUT_TOKENS
    return max(0, min(MAX_OUTPUT_BYTES, tokens * 4))


def _interrupt_process_group(proc: asyncio.subprocess.Process) -> None:
    pid = proc.pid
    if pid is None:
        return
    try:
        os.killpg(pid, signal.SIGINT)
    except (AttributeError, ProcessLookupError):
        with contextlib.suppress(ProcessLookupError):
            proc.send_signal(signal.SIGINT)


def _kill_process_group(proc: asyncio.subprocess.Process) -> None:
    pid = proc.pid
    if pid is None:
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except (AttributeError, ProcessLookupError):
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
