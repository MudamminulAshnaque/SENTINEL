from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

import main
from services.eml_parser import EmlParseError, parse_eml_bytes

client = TestClient(main.app)


def _make_eml(sender: str, subject: str, body: str, html: bool = False) -> bytes:
    msg = EmailMessage()
    msg["From"] = sender
    msg["Subject"] = subject
    if html:
        msg.set_content(body, subtype="html")
    else:
        msg.set_content(body)
    return bytes(msg)


# --------------------------------------------------------------------------
# Parser unit tests (no HTTP layer)
# --------------------------------------------------------------------------

def test_parse_plain_text_email():
    raw = _make_eml("alerts@example.com", "Test Subject", "Hello world, this is the body.")
    result = parse_eml_bytes(raw)
    assert result.sender == "alerts@example.com"
    assert result.subject == "Test Subject"
    assert "Hello world" in result.text
    assert result.used_html_fallback is False


def test_parse_html_only_email_falls_back_and_strips_script():
    raw = _make_eml(
        "billing@example.com", "Payment failed",
        "<html><body><p>Payment <b>failed</b>.</p><script>track();</script></body></html>",
        html=True,
    )
    result = parse_eml_bytes(raw)
    assert result.used_html_fallback is True
    assert "track()" not in result.text
    assert "Payment" in result.text and "failed" in result.text


def test_empty_bytes_raises():
    with pytest.raises(EmlParseError):
        parse_eml_bytes(b"")


def test_valid_headers_no_body_raises():
    raw = _make_eml("a@b.com", "No body", "")
    with pytest.raises(EmlParseError):
        parse_eml_bytes(raw)


# --------------------------------------------------------------------------
# Endpoint tests (full HTTP layer via TestClient)
# --------------------------------------------------------------------------

def test_endpoint_accepts_valid_eml():
    raw = _make_eml(
        "alerts@paypa1-security.example", "URGENT: Verify your account",
        "Your account has been compromised. Enter your OTP: http://paypa1-security.example/login",
    )
    resp = client.post("/api/v1/parse-eml", files={"file": ("test.eml", raw, "message/rfc822")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sender"] == "alerts@paypa1-security.example"
    assert body["used_html_fallback"] is False


def test_endpoint_rejects_wrong_extension():
    resp = client.post("/api/v1/parse-eml", files={"file": ("notanemail.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_endpoint_rejects_empty_file():
    resp = client.post("/api/v1/parse-eml", files={"file": ("empty.eml", b"", "message/rfc822")})
    assert resp.status_code == 422


def test_endpoint_rejects_oversized_file():
    big_raw = _make_eml("a@b.com", "big", "x" * (6 * 1024 * 1024))
    resp = client.post("/api/v1/parse-eml", files={"file": ("big.eml", big_raw, "message/rfc822")})
    assert resp.status_code == 413
