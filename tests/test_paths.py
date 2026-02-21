from __future__ import annotations

from pathlib import Path

import pytest


def test_xdg_state_home_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from amux.paths import xdg_state_home

    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    result = xdg_state_home()
    assert result == Path.home() / ".local" / "state"


def test_xdg_state_home_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    from amux.paths import xdg_state_home

    monkeypatch.setenv("XDG_STATE_HOME", "/custom/state")
    result = xdg_state_home()
    assert result == Path("/custom/state")


def test_amux_state_root(monkeypatch: pytest.MonkeyPatch) -> None:
    from amux.paths import amux_state_root

    monkeypatch.setenv("XDG_STATE_HOME", "/custom/state")
    result = amux_state_root()
    assert result == Path("/custom/state/amux")
