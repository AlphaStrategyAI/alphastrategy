from pathlib import Path

import pytest

from alphastrategy.api.handlers import parse_multipart_file


def test_parse_multipart_file_reads_named_part():
    boundary = "----alphastrategy-test"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="gold.asb"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
        "ABC123"
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    filename, data = parse_multipart_file(
        f"multipart/form-data; boundary={boundary}",
        payload,
    )
    assert filename == "gold.asb"
    assert data == b"ABC123"


def test_parse_multipart_file_rejects_missing_file():
    boundary = "----alphastrategy-test"
    payload = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="note"\r\n\r\n'
        "x"
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")
    with pytest.raises(ValueError):
        parse_multipart_file(f"multipart/form-data; boundary={boundary}", payload)


def test_handlers_do_not_import_cgi():
    text = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "alphastrategy"
        / "api"
        / "handlers.py"
    ).read_text(encoding="utf-8")
    assert "import cgi" not in text
