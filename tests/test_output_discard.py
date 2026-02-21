from __future__ import annotations


def test_output_lines_are_discarded_and_do_not_block_responses() -> None:
    from amux.tmux import ResponseCollector, wait_for_response

    collector = ResponseCollector()

    lines = iter(
        [
            "%output %1 noisy 1",
            "%output %1 noisy 2",
            "%begin 3 list-panes",
            "%output %1 still noisy",
            "%1\t123\tbash\t/tmp",
            "%end 3",
        ]
    )

    def poll() -> str | None:
        try:
            return next(lines)
        except StopIteration:
            return None

    t = {"now": 0.0}

    def monotonic() -> float:
        # advance enough to make progress but not hit the timeout
        t["now"] += 0.001
        return t["now"]

    resp = wait_for_response(
        collector,
        poll,
        timeout_s=0.2,
        monotonic=monotonic,
        sleep=lambda _s: None,
    )
    assert resp.command_id == 3
    assert resp.payload == "%1\t123\tbash\t/tmp\n"
