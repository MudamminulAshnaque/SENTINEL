"""
customer_intelligence extraction — full pipeline.

Phase 1: CustomerIntelligence Pydantic model enforces the contract.
Phase 2: System prompt + Groq call (json_object mode).
Phase 3: On validation failure, one corrective retry with the model's own
         bad output + the exact error, then a safe fallback object if that
         also fails — this function never raises for a bad model response.
Phase 4: Timeout + exponential backoff around TRANSIENT API errors (rate
         limits, connection drops, 5xxs) — distinct from the Phase 3
         validation-retry, which is about bad *content*, not a broken
         connection. Structured JSON logging on every call. A health check
         function for the /health endpoint.

Two different kinds of "retry" happen here and they are NOT the same thing:
  - _call_groq_with_backoff retries a SINGLE message exchange when the
    network/API itself is flaky (timeout, 429, 500). This is invisible to
    the caller — it either eventually returns content or raises
    TransientAPIError.
  - extract_customer_intelligence retries with a CORRECTED PROMPT when the
    API call succeeded but the model's content didn't satisfy the schema.
    This is a semantic retry, not a network retry.

A genuine setup error (missing/invalid API key, bad request shape) is
NEITHER of these — it raises ExtractionError immediately, because retrying
or silently falling back would mask a broken deployment.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass

import groq
from dotenv import load_dotenv
from groq import AsyncGroq
from pydantic import ValidationError

from .logging_config import get_logger, now_ms
from .schemas.customer_intelligence import CustomerIntelligence

load_dotenv()

logger = get_logger("nlp.extraction")

MODEL = "openai/gpt-oss-20b"  # verify this is still live on your Groq account
CALL_TIMEOUT_SECONDS = 8.0
MAX_TRANSIENT_ATTEMPTS = 2  # attempts per message-exchange, for network-layer retry
BACKOFF_BASE_SECONDS = 1.0  # 1s, then 2s, then 4s...

# Exceptions worth retrying at the network layer — all indicate a transient
# condition (rate limit, connection blip, server-side 5xx, our own timeout),
# not a problem with the request itself.
_TRANSIENT_EXCEPTIONS = (
    asyncio.TimeoutError,
    groq.APITimeoutError,
    groq.APIConnectionError,
    groq.RateLimitError,
    groq.InternalServerError,
)

_SCHEMA_BLOCK = """\
Return ONLY a single JSON object with exactly these fields. No markdown fences, \
no commentary, no explanation before or after — just the JSON object.

{
  "category": one of ["Payment/Transaction Issue", "Account/Login Problem", "Product Issue", "Delivery/Shipping Problem", "Refund Request", "Subscription Issue", "Technical Problem", "Service Quality", "Billing Problem", "Security Concern", "Other"],
  "sub_issue": string (free text, specific sub-classification within category),
  "sentiment": one of ["Positive", "Neutral", "Negative"],
  "emotion": one of ["Anger", "Frustration", "Satisfaction", "Confusion", "Urgency", "Disappointment", "Fear/Urgency", "None"],
  "priority": one of ["Low", "Medium", "High", "Critical"],
  "resolution_status": one of ["Resolved", "Unresolved", "In Progress"],
  "customer_request": string (what the customer is asking for),
  "summary": string (1-3 sentences, plain text),
  "keywords": array of lowercase strings
}

Every field is REQUIRED — never omit a key. If emotion is not applicable, use \
the string "None" (not null, not omitted).
"""

_FEW_SHOT_EXAMPLES = """\
Example 1
Input: "I was charged twice for my subscription this month, please refund the duplicate charge."
Output: {"category": "Billing Problem", "sub_issue": "Duplicate charge", "sentiment": "Negative", "emotion": "Frustration", "priority": "Medium", "resolution_status": "Unresolved", "customer_request": "Refund of duplicate subscription charge", "summary": "Customer reports being charged twice for their subscription this month and requests a refund for the duplicate charge.", "keywords": ["duplicate charge", "subscription", "refund"]}

Example 2
Input: "URGENT! Your account has been compromised. Click this link immediately to secure your account and enter your username, password and OTP. http://paypa1-security.example/login"
Output: {"category": "Security Concern", "sub_issue": "Account Compromise Claim", "sentiment": "Negative", "emotion": "Fear/Urgency", "priority": "Critical", "resolution_status": "Unresolved", "customer_request": "Account verification", "summary": "Message claims the customer's account was compromised and urges immediate action via a link, requesting credentials and OTP.", "keywords": ["account compromised", "urgent", "verify", "otp"]}

Example 3
Input: "Thanks so much, the replacement part arrived today and everything works perfectly now!"
Output: {"category": "Product Issue", "sub_issue": "Replacement part received", "sentiment": "Positive", "emotion": "Satisfaction", "priority": "Low", "resolution_status": "Resolved", "customer_request": "None — confirming resolution", "summary": "Customer confirms the replacement part arrived and resolved the issue.", "keywords": ["replacement part", "resolved"]}
"""

SYSTEM_PROMPT = (
    "You are a customer support intelligence extraction engine. "
    "Given a raw customer message, extract structured intelligence about it.\n\n"
    f"{_SCHEMA_BLOCK}\n"
    f"{_FEW_SHOT_EXAMPLES}"
)

# Short, channel-specific context appended to the system prompt. This does
# NOT change the schema or the output contract — only how the model reads
# the incoming text, since a live-chat fragment and a formal email read very
# differently for the same underlying issue. Falls back to a neutral hint
# for any channel not listed (e.g. an unrecognized value from the frontend).
_CHANNEL_HINTS: dict[str, str] = {
    "email": (
        "Context: this text is the body of a support EMAIL. Expect a more "
        "formal register, possible greeting/signoff, and a single self-"
        "contained issue."
    ),
    "chat": (
        "Context: this text is a LIVE CHAT transcript, possibly informal or "
        "abbreviated, and may contain multiple short back-and-forth turns "
        "concatenated together. The customer expects a fast resolution."
    ),
    "ticket": (
        "Context: this text is a formally submitted SUPPORT TICKET. Treat "
        "it as a single, deliberately-written issue report."
    ),
    "social": (
        "Context: this text is a SOCIAL MEDIA message or DM. Expect terse, "
        "informal language, possible emojis or abbreviations, and be alert "
        "to the reputational visibility of a public complaint."
    ),
    "contact_form": (
        "Context: this text was submitted via a structured CONTACT FORM and "
        "may lack conversational framing (greeting, signoff) since it was "
        "typed into a fixed field."
    ),
    "url_scan": (
        "Context: this submission is primarily a URL or link with minimal "
        "surrounding text — focus extraction on whatever customer intent, "
        "if any, is expressed around the link."
    ),
}
_DEFAULT_CHANNEL_HINT = (
    "Context: the source channel for this message is unspecified — extract "
    "based on the content alone."
)


def _build_system_prompt(channel: str) -> str:
    hint = _CHANNEL_HINTS.get(channel, _DEFAULT_CHANNEL_HINT)
    return f"{SYSTEM_PROMPT}\n{hint}"


class ExtractionError(Exception):
    """Setup/config failures only (missing API key, auth failure, bad
    request shape) — never raised for a bad or slow model response."""


class TransientAPIError(Exception):
    """All network-layer retries exhausted. Caller falls back rather than raising."""


@dataclass
class ExtractionResult:
    data: CustomerIntelligence
    attempts: int                  # semantic (validation) attempts: 1 or 2
    used_fallback: bool
    raw_error: str | None = None
    latency_ms: float | None = None


def _get_client() -> AsyncGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ExtractionError(
            "GROQ_API_KEY is not set. Create a .env file from .env.example "
            "in the project root and add your key."
        )
    return AsyncGroq(api_key=api_key)


def _fallback_customer_intelligence() -> CustomerIntelligence:
    """Safe default when extraction fails entirely. Medium/Unresolved (not
    Low/Resolved) so it stays visible for manual review rather than
    quietly disappearing into a queue or falsely reading as handled."""
    return CustomerIntelligence(
        category="Other",
        sub_issue="Automated extraction failed",
        sentiment="Neutral",
        emotion="None",
        priority="Medium",
        resolution_status="Unresolved",
        customer_request="Unable to determine — flagged for manual review",
        summary="Automated NLP extraction failed for this message. Flagged for manual review.",
        keywords=["extraction-failed", "manual-review-required"],
    )


async def _call_groq_with_backoff(messages: list[dict], temperature: float) -> str:
    """
    One message-exchange, resilient to transient network/API failures.
    Retries up to MAX_TRANSIENT_ATTEMPTS times with exponential backoff.
    Raises TransientAPIError only after all attempts are exhausted.

    Non-transient errors (AuthenticationError, BadRequestError,
    PermissionDeniedError) are NOT retried — they indicate a broken
    deployment or malformed request, and retrying won't fix that.
    """
    client = _get_client()
    last_exc: Exception | None = None

    for attempt in range(1, MAX_TRANSIENT_ATTEMPTS + 1):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                ),
                timeout=CALL_TIMEOUT_SECONDS,
            )
            return response.choices[0].message.content
        except _TRANSIENT_EXCEPTIONS as e:
            last_exc = e
            logger.info(
                "groq_transient_error",
                extra={"attempt": attempt, "error": str(e), "error_type": type(e).__name__},
            )
            if attempt < MAX_TRANSIENT_ATTEMPTS:
                await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
        except (groq.AuthenticationError, groq.PermissionDeniedError) as e:
            raise ExtractionError(f"Groq authentication/permission error: {e}") from e
        except groq.BadRequestError as e:
            raise ExtractionError(f"Groq rejected the request: {e}") from e

    raise TransientAPIError(f"Groq unreachable after {MAX_TRANSIENT_ATTEMPTS} attempts: {last_exc}")


def _parse_and_validate(content: str) -> CustomerIntelligence:
    data = json.loads(content)
    return CustomerIntelligence(**data)


async def extract_customer_intelligence(
    raw_text: str, conversation_id: str = "", channel: str = "ticket"
) -> ExtractionResult:
    """
    Full pipeline: network-resilient call -> validate -> corrective retry
    on bad content -> safe fallback if still failing. Only raises
    ExtractionError for genuine setup problems.

    `channel` (email/chat/ticket/social/contact_form/url_scan) only adjusts
    the system prompt's framing of the input — it never changes the output
    schema or the extraction contract.
    """
    start = now_ms()
    messages = [
        {"role": "system", "content": _build_system_prompt(channel)},
        {"role": "user", "content": raw_text},
    ]

    # --- Attempt 1 ---
    try:
        content_1 = await _call_groq_with_backoff(messages, temperature=0.2)
    except TransientAPIError as e:
        latency = now_ms() - start
        logger.warning(
            "extraction_fallback_transient",
            extra={"conversation_id": conversation_id, "channel": channel, "attempts": 0, "latency_ms": latency, "error": str(e)},
        )
        return ExtractionResult(
            data=_fallback_customer_intelligence(), attempts=0, used_fallback=True,
            raw_error=str(e), latency_ms=latency,
        )

    try:
        result = _parse_and_validate(content_1)
        latency = now_ms() - start
        logger.info(
            "extraction_success",
            extra={"conversation_id": conversation_id, "channel": channel, "attempts": 1, "latency_ms": latency},
        )
        return ExtractionResult(data=result, attempts=1, used_fallback=False, latency_ms=latency)
    except (json.JSONDecodeError, ValidationError) as first_error:
        error_detail = str(first_error)

    # --- Attempt 2: corrective retry (semantic, not network) ---
    correction_messages = messages + [
        {"role": "assistant", "content": content_1},
        {
            "role": "user",
            "content": (
                f"Your previous response was invalid: {error_detail}\n\n"
                "Return ONLY a corrected JSON object matching the schema exactly. "
                "No markdown fences, no commentary — just the corrected JSON object."
            ),
        },
    ]
    try:
        content_2 = await _call_groq_with_backoff(correction_messages, temperature=0.0)
    except TransientAPIError as e:
        latency = now_ms() - start
        logger.warning(
            "extraction_fallback_transient_on_retry",
            extra={"conversation_id": conversation_id, "channel": channel, "attempts": 1, "latency_ms": latency, "error": str(e)},
        )
        return ExtractionResult(
            data=_fallback_customer_intelligence(), attempts=1, used_fallback=True,
            raw_error=f"{error_detail} | transient on retry: {e}", latency_ms=latency,
        )

    try:
        result = _parse_and_validate(content_2)
        latency = now_ms() - start
        logger.info(
            "extraction_success_on_retry",
            extra={"conversation_id": conversation_id, "channel": channel, "attempts": 2, "latency_ms": latency},
        )
        return ExtractionResult(data=result, attempts=2, used_fallback=False, latency_ms=latency)
    except (json.JSONDecodeError, ValidationError) as second_error:
        latency = now_ms() - start
        combined_error = f"{error_detail} | {second_error}"
        logger.warning(
            "extraction_fallback_validation",
            extra={"conversation_id": conversation_id, "channel": channel, "attempts": 2, "latency_ms": latency, "error": combined_error},
        )
        return ExtractionResult(
            data=_fallback_customer_intelligence(), attempts=2, used_fallback=True,
            raw_error=combined_error, latency_ms=latency,
        )


async def check_groq_health() -> bool:
    """Trivial ping for the /health endpoint. Returns False rather than
    raising, so a health check never itself takes the health endpoint down."""
    try:
        client = _get_client()
        await asyncio.wait_for(
            client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            ),
            timeout=5.0,
        )
        return True
    except Exception as e:
        logger.warning("groq_health_check_failed", extra={"error": str(e)})
        return False
