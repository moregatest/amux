from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_is_pid_alive_current_process() -> None:
    from amux.daemon import _is_pid_alive

    assert _is_pid_alive(os.getpid()) is True


def test_is_pid_alive_nonexistent_pid() -> None:
    from amux.daemon import _is_pid_alive

    # PID 2^22 is very unlikely to exist
    assert _is_pid_alive(4_194_304) is False


def test_state_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    from amux.daemon import _state_paths
    from amux.tmux_target import TmuxTarget

    monkeypatch.setenv("XDG_STATE_HOME", "/tmp/test-amux-state")
    target = TmuxTarget(socket_path=Path("/tmp/tmux-test/default"))

    state_path, pid_path = _state_paths(target)

    assert state_path.name == "state.json"
    assert pid_path.name == "daemon.pid"
    assert state_path.parent == pid_path.parent
    assert target.server_id in str(state_path)
