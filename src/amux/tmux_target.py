from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TmuxTarget:
    socket_path: Path

    @property
    def server_id(self) -> str:
        # Stable-ish identifier; path is enough for v0.1.
        h = hashlib.sha256(str(self.socket_path).encode("utf-8")).hexdigest()
        return h[:12]


def default_tmux_socket() -> Path:
    # If started inside tmux, $TMUX looks like: "/tmp/tmux-501/default,12345,0"
    tmux = os.environ.get("TMUX")
    if tmux:
        socket = tmux.split(",", 1)[0]
        return Path(socket)

    uid = os.getuid()
    return Path(f"/tmp/tmux-{uid}/default")
