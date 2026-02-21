from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich import print

from .paths import amux_state_root
from .state import AmuxState, DaemonStatus, load_state, save_state
from .tmux_target import TmuxTarget, default_tmux_socket
from .tmux import TmuxControlClient, TmuxTimeoutError, is_output_line
from .resync import LIST_PANES_FORMAT, parse_list_panes_payload


daemon_app = typer.Typer(no_args_is_help=True, help="Manage the amux sidecar daemon")


def _state_paths(target: TmuxTarget) -> tuple[Path, Path]:
    root = amux_state_root() / target.server_id
    return root / "state.json", root / "daemon.pid"


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@daemon_app.command("start")
def start(
    tmux_socket: Path | None = typer.Option(None, "--tmux-socket", help="Path to tmux server socket"),
    foreground: bool = typer.Option(False, "--foreground", help="Run in foreground (for debugging)"),
) -> None:
    target = TmuxTarget(socket_path=tmux_socket or default_tmux_socket())
    state_path, pid_path = _state_paths(target)

    # If already running, no-op.
    if pid_path.exists():
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        if _is_pid_alive(pid):
            print(f"amux daemon already running (pid={pid}, server_id={target.server_id})")
            return
        pid_path.unlink(missing_ok=True)

    if foreground:
        run(tmux_socket=target.socket_path)
        return

    # Spawn a detached daemon runner process.
    cmd = [sys.executable, "-m", "amux", "daemon", "run", "--tmux-socket", str(target.socket_path)]
    log_path = pid_path.parent / "daemon.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "ab", buffering=0)

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=log_f,
        stderr=log_f,
        start_new_session=True,
    )

    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(p.pid) + "\n", encoding="utf-8")
    print(f"amux daemon started (pid={p.pid}, server_id={target.server_id})")


@daemon_app.command("stop")
def stop(
    tmux_socket: Path | None = typer.Option(None, "--tmux-socket", help="Path to tmux server socket"),
) -> None:
    target = TmuxTarget(socket_path=tmux_socket or default_tmux_socket())
    state_path, pid_path = _state_paths(target)

    if not pid_path.exists():
        print("amux daemon not running")
        return

    pid = int(pid_path.read_text(encoding="utf-8").strip())
    if not _is_pid_alive(pid):
        pid_path.unlink(missing_ok=True)
        print("amux daemon not running")
        return

    os.kill(pid, signal.SIGTERM)
    # Best-effort wait a bit.
    for _ in range(30):
        if not _is_pid_alive(pid):
            break
        time.sleep(0.1)

    pid_path.unlink(missing_ok=True)

    st = load_state(state_path)
    st.daemon = None
    save_state(state_path, st)

    print(f"amux daemon stopped (pid={pid})")


@daemon_app.command("status")
def status(
    tmux_socket: Path | None = typer.Option(None, "--tmux-socket", help="Path to tmux server socket"),
) -> None:
    target = TmuxTarget(socket_path=tmux_socket or default_tmux_socket())
    state_path, pid_path = _state_paths(target)

    pid: int | None = None
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except ValueError:
            pid = None

    st = load_state(state_path)

    alive = pid is not None and _is_pid_alive(pid)
    tmux_state = st.daemon.tmux_state if st.daemon else "unknown"

    print({
        "running": bool(alive),
        "pid": pid,
        "tmux_socket": str(target.socket_path),
        "server_id": target.server_id,
        "tmux_state": tmux_state,
        "state_path": str(state_path),
    })


@daemon_app.command("run")
def run(
    tmux_socket: Path | None = typer.Option(None, "--tmux-socket", help="Path to tmux server socket"),
) -> None:
    """Run the daemon loop in the foreground.

    This command is meant to be spawned by `amux daemon start`.
    """

    target = TmuxTarget(socket_path=tmux_socket or default_tmux_socket())
    state_path, _pid_path = _state_paths(target)

    st: AmuxState = load_state(state_path)
    st.daemon = DaemonStatus(pid=os.getpid(), started_at=time.time(), tmux_state="disconnected")
    save_state(state_path, st)

    def _handle_term(_signum: int, _frame: object) -> None:
        st2 = load_state(state_path)
        st2.daemon = None
        save_state(state_path, st2)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_term)
    signal.signal(signal.SIGINT, _handle_term)

    client: TmuxControlClient | None = None

    backoff = 1.0
    while True:
        try:
            if client is None:
                client = TmuxControlClient(socket_path=target.socket_path, response_timeout_s=5.0)
                client.start()

            # Resync panes on connect (best-effort).
            resp = client.command(f"list-panes -a -F '{LIST_PANES_FORMAT}'")
            panes = parse_list_panes_payload(resp.payload)

            st = load_state(state_path)
            if st.daemon:
                st.daemon.tmux_state = "connected"
                st.daemon.last_resync_at = time.time()
            st.panes = panes
            save_state(state_path, st)

            # Drain events while connected. In M1 we discard `%output` to avoid flooding.
            backoff = 1.0
            while True:
                line = client.poll_line() if client else None
                if line is None:
                    time.sleep(0.05)
                    continue
                if is_output_line(line):
                    continue
                # TODO(M1): handle lifecycle events.

        except (FileNotFoundError, RuntimeError):
            # tmux not installed or control-mode process exited.
            client = None
            st = load_state(state_path)
            if st.daemon:
                st.daemon.tmux_state = "disconnected"
            save_state(state_path, st)
            time.sleep(min(5.0, backoff))
            backoff = min(60.0, backoff * 1.2)
        except TmuxTimeoutError:
            # Command timed out; treat as reconnect-worthy.
            client = None
            st = load_state(state_path)
            if st.daemon:
                st.daemon.tmux_state = "reconnecting"
            save_state(state_path, st)
            time.sleep(min(5.0, backoff))
            backoff = min(60.0, backoff * 1.2)


@daemon_app.command("where")
def where(
    tmux_socket: Path | None = typer.Option(None, "--tmux-socket", help="Path to tmux server socket"),
) -> None:
    target = TmuxTarget(socket_path=tmux_socket or default_tmux_socket())
    state_path, pid_path = _state_paths(target)
    print({"state_path": str(state_path), "pid_path": str(pid_path), "server_id": target.server_id})
