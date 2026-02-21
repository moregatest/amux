# amux

Agent-aware Terminal Multiplexer — a **tmux sidecar daemon** that makes tmux panes feel like manageable AI agents.

## Status

Early scaffold (Phase B / v0.1 in progress).

## Prerequisites

- tmux (currently tested on **tmux 3.6a**)
- uv (Python 3.12)

## Install / Run

### Option 1: Run from the repo (recommended for now)

```bash
cd amux
uv sync

# start background daemon (1 daemon ↔ 1 tmux server)
uv run amux daemon start
uv run amux daemon status
uv run amux daemon stop
```

### Option 2: Foreground (debug)

```bash
cd amux
uv run amux daemon start --foreground
```

## Usage notes

### tmux server selection

By default amux targets:
- the tmux server from `$TMUX` if you start it inside tmux; otherwise
- `/tmp/tmux-$UID/default`

To target a specific server:

```bash
uv run amux daemon start --tmux-socket /path/to/tmux.sock
uv run amux daemon status --tmux-socket /path/to/tmux.sock
```

### Where does it store state?

```bash
uv run amux daemon where
```

This prints the `server_id`, `state.json` path, and `daemon.pid` path.

---

## Troubleshooting

### `tmux_state` stays `disconnected`

Common causes:
- tmux server is not running (no sessions)
- wrong socket path

Things to try:

```bash
tmux -V
ls -la /tmp/tmux-$UID/ || true

# Start a tmux server (creates the default socket)
# (This will attach; exit/detach as you like)
tmux new -s amux-test
```

Then re-check:

```bash
cd amux
uv run amux daemon status
```

### Wrong tmux socket

If you have multiple tmux servers/sockets, be explicit:

```bash
uv run amux daemon start --tmux-socket /path/to/tmux.sock
uv run amux daemon status --tmux-socket /path/to/tmux.sock
```

### Daemon started but `running=false`

- Check the daemon log:

```bash
uv run amux daemon where
# then tail the log next to pid/state:
# ~/.local/state/amux/<server_id>/daemon.log
```

### Reset amux state (safe)

Stop the daemon, then delete its state directory:

```bash
uv run amux daemon stop
uv run amux daemon where
# rm -rf ~/.local/state/amux/<server_id>/
```

(We intentionally keep state per `server_id` so multiple daemons don't collide.)

## Design

See `docs/design/phase-b.md`. (Kept in-repo so it doesn't rot.)
