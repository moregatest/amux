from __future__ import annotations


def test_parse_empty_payload() -> None:
    from amux.resync import parse_list_panes_payload

    result = parse_list_panes_payload("")
    assert result == {}


def test_parse_blank_lines_are_skipped() -> None:
    from amux.resync import parse_list_panes_payload

    result = parse_list_panes_payload("\n\n\n")
    assert result == {}


def test_parse_malformed_lines_are_skipped() -> None:
    from amux.resync import parse_list_panes_payload

    payload = "bad-line-no-tabs\n%1\t111\tbash\t/tmp\n"
    result = parse_list_panes_payload(payload)
    assert len(result) == 1
    assert "%1" in result


def test_parse_invalid_pid_defaults_to_zero() -> None:
    from amux.resync import parse_list_panes_payload

    payload = "%1\tnot-a-number\tbash\t/tmp\n"
    result = parse_list_panes_payload(payload)
    assert result["%1"]["pid"] == 0
    assert result["%1"]["command"] == "bash"


def test_parse_extra_tab_fields_are_ignored() -> None:
    from amux.resync import parse_list_panes_payload

    payload = "%1\t111\tbash\t/tmp\textra-field\n"
    result = parse_list_panes_payload(payload)
    assert result["%1"]["pid"] == 111
    assert result["%1"]["cwd"] == "/tmp"
