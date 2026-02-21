from __future__ import annotations

import os
from pathlib import Path


def xdg_state_home() -> Path:
    # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")).expanduser()


def amux_state_root() -> Path:
    return xdg_state_home() / "amux"
