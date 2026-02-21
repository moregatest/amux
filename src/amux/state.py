from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DaemonStatus:
    pid: int
    started_at: float
    tmux_state: str = "disconnected"  # connected|disconnected|reconnecting
    last_resync_at: float | None = None


@dataclass
class AmuxState:
    version: int = 1
    daemon: DaemonStatus | None = None
    panes: dict[str, dict[str, Any]] = field(default_factory=dict)
    watches: list[dict[str, Any]] = field(default_factory=list)
    groups: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_state(path: Path) -> AmuxState:
    if not path.exists():
        return AmuxState()

    data = json.loads(path.read_text(encoding="utf-8"))
    st = AmuxState(
        version=data.get("version", 1),
        panes=data.get("panes", {}),
        watches=data.get("watches", []),
        groups=data.get("groups", {}),
    )

    if (d := data.get("daemon")):
        st.daemon = DaemonStatus(
            pid=int(d["pid"]),
            started_at=float(d["started_at"]),
            tmux_state=str(d.get("tmux_state", "disconnected")),
            last_resync_at=(float(d["last_resync_at"]) if d.get("last_resync_at") is not None else None),
        )

    return st


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{int(time.time() * 1000)}")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def save_state(path: Path, st: AmuxState) -> None:
    payload: dict[str, Any] = {
        "version": st.version,
        "panes": st.panes,
        "watches": st.watches,
        "groups": st.groups,
        "daemon": (asdict(st.daemon) if st.daemon else None),
    }
    atomic_write_json(path, payload)
