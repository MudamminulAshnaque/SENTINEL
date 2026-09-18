"""
Real .eml parsing for the Email intake channel — stdlib only (Python's
`email` module), no third-party dependency added.

Given raw .eml bytes, extracts:
  - sender (From header)
  - subject (Subject header)
  - text (best-effort plain-text body)

Body extraction prefers a genuine text/plain part. If the message only has
an HTML body (common for real-world email), it's stripped down to text with
a minimal stdlib HTMLParser rather than pulled in as a new dependency
(no BeautifulSoup) — this is intentionally simple, not a full HTML-to-text
renderer, and callers get a `used_html_fallback` flag so the frontend can
show "extracted from HTML" if useful.

Malformed input raises EmlParseError with a message safe to show the user
directly (never a raw stack trace).
"""

from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser


class EmlParseError(Exception):
    """Raised for genuinely malformed or empty .eml input. Message is
    user-safe — no internal stack trace details."""


@dataclass
class ParsedEml:
    sender: str
    subject: str
    text: str
    used_html_fallback: bool


class _HtmlTextExtractor(HTMLParser):
    """Minimal stdlib HTML-to-text: strips tags, keeps visible text, drops
    <script>/<style> contents. Not a full renderer — good enough for
    extracting a phishing/support email's message body for NLP purposes."""

    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
        elif tag in ("br", "p", "div", "tr", "li"):
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    def get_text(self) -> str:
        text = " ".join(self._chunks)
        # Collapse runs of whitespace left over from the tag-based newlines above.
        return " ".join(text.split())


def _strip_html(html: str) -> str:
    extractor = _HtmlTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def parse_eml_bytes(raw_bytes: bytes) -> ParsedEml:
    """
    Parses raw .eml file bytes into sender/subject/text.

    Raises EmlParseError if the bytes aren't parseable as an email message,
    or if no usable body content could be extracted at all.
    """
    if not raw_bytes or not raw_bytes.strip():
        raise EmlParseError("The uploaded file is empty.")

    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    except Exception as e:
        raise EmlParseError(
            f"Could not parse this as a valid .eml file: {e}"
        ) from e

    sender = str(msg.get("From", "") or "").strip()
    subject = str(msg.get("Subject", "") or "").strip()

    used_html_fallback = False
    text = ""

    # Prefer a genuine plain-text part.
    plain_part = msg.get_body(preferencelist=("plain",))
    if plain_part is not None:
        try:
            text = plain_part.get_content().strip()
        except Exception:
            text = ""

    # Fall back to HTML, stripped to text, only if no plain part worked.
    if not text:
        html_part = msg.get_body(preferencelist=("html",))
        if html_part is not None:
            try:
                html_content = html_part.get_content()
                text = _strip_html(html_content).strip()
                used_html_fallback = bool(text)
            except Exception:
                text = ""

    if not text:
        raise EmlParseError(
            "No readable text or HTML body found in this .eml file — it may "
            "be empty, an attachment-only message, or use an unsupported "
            "encoding."
        )

    return ParsedEml(
        sender=sender,
        subject=subject,
        text=text,
        used_html_fallback=used_html_fallback,
    )
