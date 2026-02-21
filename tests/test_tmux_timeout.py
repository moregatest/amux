from __future__ import annotations

import pytest


def test_wait_for_response_times_out_and_collector_can_continue() -> None:
    from amux.tmux import ResponseCollector, TmuxTimeoutError, wait_for_response

    # Fake monotonic clock that advances by 0.05s per call.
    t = {"now": 0.0}

    def monotonic() -> float:
        t["now"] += 0.05
        return t["now"]

    def sleep(_s: float) -> None:
        return None

    # Start a response, but never provide an %end.
    collector = ResponseCollector()
    collector.feed_line("%begin 1 list-sessions")

    def poll_none() -> str | None:
        return None

    with pytest.raises(TmuxTimeoutError):
        wait_for_response(collector, poll_none, timeout_s=0.2, monotonic=monotonic, sleep=sleep)

    assert collector.active is False

    # Now provide a complete response; the client should still work.
    lines = iter(["%begin 2 list-windows", "one", "%end 2"])

    def poll_next() -> str | None:
        try:
            return next(lines)
        except StopIteration:
            return None

    resp = wait_for_response(collector, poll_next, timeout_s=0.2, monotonic=monotonic, sleep=sleep)
    assert resp.command_id == 2
    assert resp.command == "list-windows"
    assert resp.payload == "one\n"
