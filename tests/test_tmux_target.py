from __future__ import annotations

import os
from pathlib import Path


def test_server_id_is_stable() -> None:
    from amux.tmux_target import TmuxTarget

    t1 = TmuxTarget(socket_path=Path("/tmp/tmux-501/default"))
    t2 = TmuxTarget(socket_path=Path("/tmp/tmux-501/default"))
    assert t1.server_id == t2.server_id
    assert len(t1.server_id) == 12


def test_server_id_differs_for_different_sockets() -> None:
    from amux.tmux_target import TmuxTarget

    t1 = TmuxTarget(socket_path=Path("/tmp/tmux-501/default"))
    t2 = TmuxTarget(socket_path=Path("/tmp/tmux-502/default"))
    assert t1.server_id != t2.server_id


def test_default_tmux_socket_from_env(monkeypatch: object) -> None:
    from amux.tmux_target import default_tmux_socket

    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("TMUX", "/tmp/tmux-501/default,12345,0")
    result = default_tmux_socket()
    assert result == Path("/tmp/tmux-501/default")
    mp.undo()


def test_default_tmux_socket_fallback(monkeypatch: object) -> None:
    from amux.tmux_target import default_tmux_socket

    import pytest

    mp = pytest.MonkeyPatch()
    mp.delenv("TMUX", raising=False)
    result = default_tmux_socket()
    uid = os.getuid()
    assert result == Path(f"/tmp/tmux-{uid}/default")
    mp.undo()
