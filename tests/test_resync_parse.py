from __future__ import annotations


def test_parse_list_panes_payload() -> None:
    from amux.resync import LIST_PANES_FORMAT, parse_list_panes_payload

    assert "#{pane_id}" in LIST_PANES_FORMAT

    payload = (
        "%1\t111\tbash\t/Users/alice\n"
        "%2\t222\tpython\t/Users/alice/proj\n"
    )

    panes = parse_list_panes_payload(payload)
    assert panes["%1"]["pid"] == 111
    assert panes["%1"]["command"] == "bash"
    assert panes["%1"]["cwd"] == "/Users/alice"

    assert panes["%2"]["pid"] == 222
    assert panes["%2"]["command"] == "python"
    assert panes["%2"]["cwd"] == "/Users/alice/proj"
