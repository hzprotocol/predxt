import json

from predxt.cli import main


def test_parse_fixture_outputs_jsonl(capsys):
    exit_code = main(
        [
            "parse-fixture",
            "--venue",
            "polymarket",
            "--jsonl",
            "tests/fixtures/polymarket_order_books.json",
        ]
    )

    assert exit_code == 0
    first_line = capsys.readouterr().out.splitlines()[0]
    payload = json.loads(first_line)
    assert payload["message"]["venue"] == "polymarket"
    assert payload["message"]["event_type"] == "book"
    assert payload["typed_event"]["event_type"] == "book"


def test_cli_help(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "read-only prediction market" in capsys.readouterr().out.lower()
