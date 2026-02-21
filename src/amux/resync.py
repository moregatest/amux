from __future__ import annotations

from typing import Any

# tmux 3.6a fields.
# We use tab as a delimiter to avoid ambiguity in paths/commands.
LIST_PANES_FORMAT = "#{pane_id}\t#{pane_pid}\t#{pane_current_command}\t#{pane_current_path}"


def parse_list_panes_payload(payload: str) -> dict[str, dict[str, Any]]:
    """Parse `list-panes -a -F <format>` payload into a dict keyed by pane_id."""

    panes: dict[str, dict[str, Any]] = {}

    for raw_line in payload.splitlines():
        line = raw_line.strip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            # Best-effort: ignore malformed lines.
            continue
        pane_id, pid_s, cmd, cwd = parts[0], parts[1], parts[2], parts[3]
        try:
            pid = int(pid_s)
        except ValueError:
            pid = 0
        panes[pane_id] = {"pid": pid, "command": cmd, "cwd": cwd}

    return panes
