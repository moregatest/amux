from __future__ import annotations

import selectors
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def is_output_line(line: str) -> bool:
    """True if this tmux control-mode line is a `%output` event.

    In M1 we discard these lines to avoid flooding.
    """

    return line.startswith("%output ")


@dataclass(frozen=True, slots=True)
class ControlLine:
    """A minimally-parsed tmux control-mode line."""

    kind: str  # begin|end|other
    raw: str
    command_id: int | None = None
    command: str | None = None

    @staticmethod
    def parse(line: str) -> "ControlLine":
        line = line.rstrip("\n")

        if line.startswith("%begin "):
            # %begin <id> <command...>
            # Example: %begin 17 list-panes -a
            rest = line[len("%begin ") :]
            parts = rest.split(" ", 1)
            cmd_id = int(parts[0])
            cmd = parts[1] if len(parts) > 1 else ""
            return ControlLine(kind="begin", raw=line, command_id=cmd_id, command=cmd)

        if line.startswith("%end "):
            rest = line[len("%end ") :].strip()
            cmd_id = int(rest) if rest else 0
            return ControlLine(kind="end", raw=line, command_id=cmd_id)

        return ControlLine(kind="other", raw=line)


@dataclass(frozen=True, slots=True)
class CommandResponse:
    command_id: int
    command: str
    payload: str


class TmuxTimeoutError(TimeoutError):
    """Raised when a `%begin/%end` response block did not complete in time."""


def wait_for_response(
    collector: "ResponseCollector",
    poll_line: Callable[[], str | None],
    *,
    timeout_s: float,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> CommandResponse:
    """Wait for the active response to finish (or for a new one to arrive).

    `poll_line()` should be non-blocking and return a line (without requiring a
    trailing newline) or None if no data is currently available.

    On timeout the collector is reset so future commands can proceed.
    """

    deadline = monotonic() + timeout_s
    while monotonic() < deadline:
        line = poll_line()
        if line is None:
            sleep(0.001)
            continue
        resp = collector.feed_line(line)
        if resp is not None:
            return resp
    collector.reset()
    raise TmuxTimeoutError(f"tmux control-mode response timed out after {timeout_s}s")


class ResponseCollector:
    """Collect `%begin/%end` bounded responses.

    Note: tmux may emit async control-mode events while a response is in-flight.
    For v0.1 we keep the collector simple: while collecting, we only include
    non-control, non-%output lines in the payload.
    """

    def __init__(self) -> None:
        self._active_id: int | None = None
        self._active_command: str | None = None
        self._buf: list[str] = []

    @property
    def active(self) -> bool:
        return self._active_id is not None

    def reset(self) -> None:
        self._active_id = None
        self._active_command = None
        self._buf = []

    def feed_line(self, line: str) -> CommandResponse | None:
        line = line.rstrip("\n")

        if is_output_line(line):
            return None

        cl = ControlLine.parse(line)

        if cl.kind == "begin":
            self._active_id = int(cl.command_id or 0)
            self._active_command = cl.command or ""
            self._buf = []
            return None

        if cl.kind == "end" and self._active_id is not None:
            if int(cl.command_id or 0) != self._active_id:
                # Unexpected end; ignore.
                return None
            payload = "\n".join(self._buf)
            if payload:
                payload += "\n"
            resp = CommandResponse(
                command_id=self._active_id,
                command=self._active_command or "",
                payload=payload,
            )
            self.reset()
            return resp

        if self._active_id is not None:
            # While collecting: include plain lines and command output.
            # Async control-mode events usually look like "%window-add ...".
            # Heuristic: ignore lines starting with '%' where the next char is not a digit.
            if line.startswith("%") and len(line) > 1 and not line[1].isdigit():
                return None
            self._buf.append(line)

        return None


class TmuxControlClient:
    """A small tmux control-mode client (M1).

    It keeps a long-lived `tmux -C` subprocess and can run commands by waiting
    for `%begin/%end` responses.
    """

    def __init__(self, *, socket_path: Path, response_timeout_s: float = 5.0) -> None:
        self.socket_path = socket_path
        self.response_timeout_s = response_timeout_s
        self._p: subprocess.Popen[str] | None = None
        self._selector: selectors.BaseSelector | None = None
        self._collector = ResponseCollector()

    def start(self) -> None:
        if self._p is not None:
            return

        self._p = subprocess.Popen(
            ["tmux", "-C", "-S", str(self.socket_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert self._p.stdout is not None
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._p.stdout, selectors.EVENT_READ)

    def close(self) -> None:
        if self._selector is not None:
            try:
                self._selector.close()
            except Exception:
                pass
            self._selector = None

        if self._p is not None:
            try:
                self._p.terminate()
            except Exception:
                pass
            self._p = None

        self._collector.reset()

    def poll_line(self) -> str | None:
        if self._p is None or self._selector is None:
            return None
        if self._p.poll() is not None:
            return None
        assert self._p.stdout is not None

        events = self._selector.select(timeout=0)
        if not events:
            return None
        line = self._p.stdout.readline()
        if not line:
            return None
        return line.rstrip("\n")

    def command(self, cmd: str) -> CommandResponse:
        if self._p is None:
            raise RuntimeError("client not started")
        if self._p.poll() is not None:
            raise RuntimeError("tmux control-mode process exited")
        assert self._p.stdin is not None

        self._p.stdin.write(cmd + "\n")
        self._p.stdin.flush()

        return wait_for_response(self._collector, self.poll_line, timeout_s=self.response_timeout_s)
