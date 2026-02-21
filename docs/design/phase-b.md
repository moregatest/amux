# amux — Phase B (tmux sidecar) Design

Date: 2026-02-21

## Scope for v0.1

Primary loop (minimal daily-usable):

- **M1**: daemon + pane state map (foundation)
- **M2**: pane output watch (single-line regex) + actions
- **M3**: notification bridge (macOS + Linux)

Deferred (but design should not block): M4 task groups, M5 JSON API + status integration, M6 pane label.

## Decisions (locked)

### Daemon lifecycle
- Daemon is **independent and long-lived**; tmux availability is a sub-state.
- tmux connection state: `connected | disconnected | reconnecting`.
- When tmux becomes available again, daemon performs a **full resync** before resuming incremental event handling.

### Single tmux server per daemon
- One daemon instance manages **exactly one** tmux server (socket).
- To manage another tmux server, start another daemon with a different `--tmux-socket`.
- `server_id` is derived from the tmux socket path (hash prefix) for namespacing.

### Persistence
- **State file is authoritative**.
- tmux user options (`@amux_*`) are best-effort backup / interop (not the source of truth).

### Pattern matching (M2, v0.1)
- **Single-line regex only**.
- Per-rule cooldown to avoid notification spam.

### macOS notifications (M3)
- Prefer `terminal-notifier` when available.
- Fallback to `osascript` when not.

## Data model (high-level)

### PaneState (conceptual)
- `pane_id` (e.g. `%5`)
- `pid` (int)
- `command` (string)
- `cwd` (string)
- amux extensions: `agent`, `task`, `status`, `group`, `tags`

### State file layout
- `~/.local/state/amux/<server_id>/state.json` (or `$XDG_STATE_HOME`).

## tmux integration

- Communication:
  - **control mode** (`tmux -C`) for event subscription + command responses
  - `list-panes -F` / `display-message -p` for resync + queries
  - `pipe-pane` for output capture (M2)

## Open questions (tracked)

- Multi-daemon discovery UX
- Optional OSC passthrough
- tmux compatibility matrix (for now: tested on tmux 3.6a)
