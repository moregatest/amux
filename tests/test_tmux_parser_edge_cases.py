from __future__ import annotations


def test_control_line_parse_begin_no_command() -> None:
    from amux.tmux import ControlLine

    cl = ControlLine.parse("%begin 5 ")
    assert cl.kind == "begin"
    assert cl.command_id == 5
    assert cl.command == ""


def test_control_line_parse_end_with_whitespace() -> None:
    from amux.tmux import ControlLine

    cl = ControlLine.parse("%end 42  ")
    assert cl.kind == "end"
    assert cl.command_id == 42


def test_response_collector_mismatched_end_id() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    c.feed_line("%begin 1 list-panes")
    c.feed_line("data")
    # %end with a different ID should be ignored
    resp = c.feed_line("%end 99")
    assert resp is None
    # collector should still be active
    assert c.active is True

    # correct end should work
    resp = c.feed_line("%end 1")
    assert resp is not None
    assert resp.payload == "data\n"


def test_response_collector_end_without_begin() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    # %end without a prior %begin should be ignored
    resp = c.feed_line("%end 1")
    assert resp is None
    assert c.active is False


def test_response_collector_empty_payload() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    c.feed_line("%begin 1 list-panes")
    resp = c.feed_line("%end 1")
    assert resp is not None
    # empty payload should be an empty string, not a trailing newline
    assert resp.payload == ""


def test_response_collector_multiple_sequential_responses() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()

    c.feed_line("%begin 1 cmd-a")
    c.feed_line("alpha")
    resp1 = c.feed_line("%end 1")

    c.feed_line("%begin 2 cmd-b")
    c.feed_line("beta")
    resp2 = c.feed_line("%end 2")

    assert resp1 is not None and resp1.command == "cmd-a"
    assert resp2 is not None and resp2.command == "cmd-b"
    assert resp1.payload == "alpha\n"
    assert resp2.payload == "beta\n"


def test_response_collector_begin_overwrites_previous() -> None:
    from amux.tmux import ResponseCollector

    c = ResponseCollector()
    c.feed_line("%begin 1 old-cmd")
    c.feed_line("stale data")
    # a new %begin should reset the collector
    c.feed_line("%begin 2 new-cmd")
    c.feed_line("fresh data")
    resp = c.feed_line("%end 2")

    assert resp is not None
    assert resp.command == "new-cmd"
    assert resp.payload == "fresh data\n"
