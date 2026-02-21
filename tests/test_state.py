from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    from amux.state import AmuxState, DaemonStatus, load_state, save_state

    state_path = tmp_path / "state.json"
    st = AmuxState(
        version=1,
        daemon=DaemonStatus(pid=42, started_at=1000.5, tmux_state="connected", last_resync_at=1001.0),
        panes={"%0": {"pid": 100, "command": "bash", "cwd": "/tmp"}},
    )
    save_state(state_path, st)

    loaded = load_state(state_path)
    assert loaded.version == 1
    assert loaded.daemon is not None
    assert loaded.daemon.pid == 42
    assert loaded.daemon.started_at == 1000.5
    assert loaded.daemon.tmux_state == "connected"
    assert loaded.daemon.last_resync_at == 1001.0
    assert loaded.panes["%0"]["pid"] == 100
    assert loaded.panes["%0"]["command"] == "bash"


def test_load_state_missing_file(tmp_path: Path) -> None:
    from amux.state import AmuxState, load_state

    st = load_state(tmp_path / "nonexistent.json")
    assert st.version == 1
    assert st.daemon is None
    assert st.panes == {}
    assert st.watches == []
    assert st.groups == {}


def test_load_state_no_daemon_key(tmp_path: Path) -> None:
    from amux.state import load_state

    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"version": 1, "panes": {}}), encoding="utf-8")
    st = load_state(state_path)
    assert st.daemon is None
    assert st.panes == {}


def test_save_state_creates_parent_dirs(tmp_path: Path) -> None:
    from amux.state import AmuxState, save_state

    state_path = tmp_path / "deep" / "nested" / "state.json"
    save_state(state_path, AmuxState())
    assert state_path.exists()


def test_save_state_daemon_none(tmp_path: Path) -> None:
    from amux.state import AmuxState, load_state, save_state

    state_path = tmp_path / "state.json"
    st = AmuxState(daemon=None)
    save_state(state_path, st)

    loaded = load_state(state_path)
    assert loaded.daemon is None


def test_atomic_write_json_replaces_existing(tmp_path: Path) -> None:
    from amux.state import atomic_write_json

    path = tmp_path / "test.json"
    atomic_write_json(path, {"a": 1})
    atomic_write_json(path, {"b": 2})

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"b": 2}
    assert "a" not in data


def test_load_state_last_resync_at_null(tmp_path: Path) -> None:
    from amux.state import load_state

    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({
        "version": 1,
        "daemon": {"pid": 1, "started_at": 1.0, "tmux_state": "connected", "last_resync_at": None},
        "panes": {},
    }), encoding="utf-8")

    st = load_state(state_path)
    assert st.daemon is not None
    assert st.daemon.last_resync_at is None
