from __future__ import annotations

import typer
from rich import print

from .daemon import daemon_app

app = typer.Typer(no_args_is_help=True, help="amux — agent-aware tmux sidecar")
app.add_typer(daemon_app, name="daemon")


@app.command("version")
def version() -> None:
    from . import __version__

    print(__version__)


def main() -> None:
    app()
