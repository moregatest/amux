from __future__ import annotations

import pytest


def test_is_output_line() -> None:
    from amux.tmux import is_output_line

    assert is_output_line("%output %1 hello") is True
    assert is_output_line("%output %1 ") is True
    assert is_output_line("%begin 123 list-panes") is False
    assert is_output_line("%end 123") is False
    assert is_output_line("%window-add @1") is False


def test_control_line_parse_begin_end() -> None:
    from amux.tmux import ControlLine

    b = ControlLine.parse("%begin 17 list-panes -a")
    assert b.kind == "begin"
    assert b.command_id == 17
    assert b.command == "list-panes -a"

    e = ControlLine.parse("%end 17")
    assert e.kind == "end"
    assert e.command_id == 17


def test_control_line_parse_other() -> None:
    from amux.tmux import ControlLine

    x = ControlLine.parse("%window-add @1")
    assert x.kind == "other"
    assert x.raw == "%window-add @1"


def test_response_collector_collects_begin_end_payload() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    assert c.feed_line("%begin 9 list-panes") is None
    assert c.feed_line("%output %1 this should be discarded") is None
    assert c.feed_line("%1 1234 bash") is None
    resp = c.feed_line("%end 9")

    assert resp is not None
    assert resp.command_id == 9
    assert resp.command == "list-panes"
    assert resp.payload == "%1 1234 bash\n"


def test_response_collector_ignores_unrelated_events_during_collection() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    c.feed_line("%begin 1 list-sessions")
    # other control-mode events may happen while we are collecting the response;
    # for v0.1 we just keep them out of the payload.
    c.feed_line("%window-add @7")
    c.feed_line("hello")
    resp = c.feed_line("%end 1")

    assert resp is not None
    assert resp.payload == "hello\n"
