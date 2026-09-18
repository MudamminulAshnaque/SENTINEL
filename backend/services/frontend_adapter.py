"""
frontend_adapter.py

Maps the backend's REAL analysis output (Groq-backed CustomerIntelligence +
the real security_analysis_engine) into the JSON shape the SENTRY frontend
(`frontend/js/app.js`, `frontend/js/provider.js`) expects when it's pointed
at a live backend (`Sentry.API = "http://localhost:8000"`).

Why this file exists at all: the frontend ships its own complete, local
analysis engine (`frontend/js/engine.js`) that computes a much richer record
shape (confidence scores, urgency/resolution reasons, per-signal IOC
breakdowns, etc.) purely from heuristics running in the browser. The
backend's real contract (`customer_intelligence` / `security_analysis`) was
designed independently and doesn't carry all of those fields. This adapter
is the seam between the two: it takes what the backend genuinely knows and
maps it 1:1 wherever a field exists, and uses clearly-marked, documented
placeholders for the handful of frontend fields the backend has no real
source for (see PLACEHOLDER NOTE comments below). Nothing here is invented
to *look* more sophisticated than the backend actually is — every
placeholder is either an empty list/value or a simple, honest derivation
from a real field (e.g. mapping a priority label to a priority score using
the frontend's own published thresholds).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from customer_intelligence.schemas.customer_intelligence import CustomerIntelligence

# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# A customer reporting a scam they received is a support issue, not an
# attack on us. Ported directly from frontend/js/engine.js's own `reporting`
# regex so backend-sourced records get the same, tested behaviour.
REPORTING_REGEX = re.compile(
    r"(i (received|got|was sent)|someone sent me|is this (email|link|message) "
    r"(real|genuine|fake)|i think (this|it) (is|might be) a (scam|phish)|"
    r"received a (suspicious|fake))",
    re.IGNORECASE,
)

# Ported from frontend/js/engine.js's ISSUE_PATTERNS — same rule-based
# recurring-issue tagging, so the frontend's "Issues" view has real data to
# group by instead of coming back empty for every backend-sourced record.
ISSUE_PATTERNS = [
    ("Login failure", re.compile(r"(cannot|can't|unable to) (log ?in|sign ?in)|login (failed|failure|not working)|invalid credentials|account locked", re.I)),
    ("Payment failure", re.compile(r"(payment|transaction) (failed|failure)|money (was )?deducted|debited but|upi failed", re.I)),
    ("Duplicate charge", re.compile(r"charged twice|double charge|deducted twice|two times", re.I)),
    ("Refund delay", re.compile(r"refund (not received|pending|delayed)|still.{0,20}refund|waiting for.{0,15}refund", re.I)),
    ("Delivery delay", re.compile(r"not delivered|delivery (delay|delayed)|tracking has not|order.{0,20}(late|delayed)|courier", re.I)),
    ("OTP not received", re.compile(r"otp (is )?not (received|coming|arriving)|no otp|otp not delivered", re.I)),
    ("Password reset", re.compile(r"(reset|forgot) (my )?password|password reset (link|email)", re.I)),
    ("App crash / error", re.compile(r"crash|app (is )?not working|error every time|freeze|glitch", re.I)),
    ("Subscription auto-renew", re.compile(r"auto ?renew|renewed (even though|without)|cancel (my )?subscription", re.I)),
    ("Account takeover", re.compile(r"unauthori[sz]ed|someone (has )?accessed|without my permission|hacked|compromised", re.I)),
    ("Damaged product", re.compile(r"damaged|broken|defective|crushed", re.I)),
    ("Billing / invoice error", re.compile(r"invoice|gst|billing (error|problem)|wrong amount", re.I)),
    ("KYC verification", re.compile(r"kyc|verification pending|re-?kyc", re.I)),
    ("Data exposure", re.compile(r"data (leak|breach)|personal (details|data).{0,15}(leak|expos)", re.I)),
]

# Bucket labels the real engine emits -> the exact strings the frontend's
# own UI logic string-matches against (resultHtml / compact in app.js check
# for "Credential harvesting" and "OTP / MFA bypass" verbatim). Keeping
# these exact means the frontend's existing credential/OTP badges and
# "Phishing" threat-type inference work correctly on real backend data too.
TECHNIQUE_NAME_MAP = {
    "Urgency": "Urgency",
    "Fear Appeal": "Fear appeal",
    "Credential Harvesting": "Credential harvesting",
    "OTP Request": "OTP / MFA bypass",
    "Authority Impersonation": "Authority impersonation",
    "Reward/Threat Bait": "Reward / refund bait",
}

TECHNIQUE_WHY = {
    "Urgency": "Message pressures the recipient to act immediately, a classic tactic to short-circuit careful judgement.",
    "Fear appeal": "Message threatens a negative consequence (account loss, legal action) to provoke a panicked response.",
    "Credential harvesting": "Message asks the recipient to enter, share, or confirm a password or login credential.",
    "OTP / MFA bypass": "Message asks the recipient to share or enter a one-time password / verification code.",
    "Authority impersonation": "Message claims to be from a bank, government body, or official department.",
    "Reward / refund bait": "Message dangles a prize, refund, or reward to lure a click or reply.",
}

# per-bucket key used in security_analysis_engine's `_debug_keyword_hits`
BUCKET_KEY_MAP = {
    "Urgency": "urgency",
    "Fear appeal": "fear_threat",
    "Credential harvesting": "credential_harvesting",
    "OTP / MFA bypass": "otp_harvesting",
    "Authority impersonation": "authority_impersonation",
    "Reward / refund bait": "reward_or_threat_bait",
}

# Frontend's own published thresholds (engine.js: priorityLabel / riskLabel)
# used in reverse here only to give the UI's progress-bar meters a sane
# number to render — the label itself (the real signal) always comes
# straight from the backend.
_PRIORITY_SCORE = {"Critical": 85, "High": 60, "Medium": 35, "Low": 10}
_SENTIMENT_SCORE = {"Negative": -1, "Neutral": 0, "Positive": 1}
_RISK_CONTRIBUTION_SCORE = {"Critical": 85, "High": 55, "Medium": 30, "Low": 5}


def _iso_to_ms(ts: str | None) -> int:
    if not ts:
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return int(datetime.now(timezone.utc).timestamp() * 1000)


def _guess_customer(raw_text: str, conversation_id: str) -> str:
    m = EMAIL_REGEX.search(raw_text)
    return m.group(0) if m else f"customer ({conversation_id})"


def _issues_of(raw_text: str) -> list[str]:
    found = [name for name, pattern in ISSUE_PATTERNS if pattern.search(raw_text)]
    return found[:2] if found else ["Uncategorised"]


def _map_url(u: dict) -> dict:
    risk = _RISK_CONTRIBUTION_SCORE.get(u.get("risk_contribution"), 0)
    signals = []
    if u.get("lookalike_flag"):
        signals.append({"t": f"Lookalike of \u201c{u.get('lookalike_target')}\u201d", "w": 30})
    if u.get("is_shortened"):
        signals.append({"t": "Shortened URL — real destination is hidden", "w": 15})
    if u.get("is_ip_address"):
        signals.append({"t": "Uses a raw IP address instead of a domain", "w": 20})
    if u.get("suspicious_path"):
        signals.append({"t": "URL path contains a suspicious keyword (verify/login/confirm/…)", "w": 15})
    if not u.get("https_used"):
        signals.append({"t": "No HTTPS", "w": 5})
    domain = u.get("domain") or ""
    return {
        "url": u.get("full_url", ""),
        "host": domain,
        "proto": "https" if u.get("https_used") else "http",
        "tld": domain.split(".")[-1] if "." in domain else "",
        "risk": risk,
        "verdict": "Impersonation-likely" if risk >= 55 else ("Suspicious" if risk >= 30 else "Low concern"),
        "signals": signals,
    }


def _map_email(e: dict) -> dict:
    risk = _RISK_CONTRIBUTION_SCORE.get(e.get("risk_contribution"), 0)
    signals = []
    if e.get("lookalike_flag"):
        signals.append({"t": f"Sender domain looks like \u201c{e.get('lookalike_target')}\u201d", "w": 30})
    return {
        "address": e.get("email", ""),
        "domain": e.get("domain", ""),
        "risk": risk,
        "verdict": "Impersonation-likely" if risk >= 55 else ("Suspicious" if risk >= 30 else "Low concern"),
        "signals": signals,
    }


def _map_techniques(security: dict) -> list[dict]:
    hits = security.get("_debug_keyword_hits", {})
    out = []
    for raw_name in security.get("social_engineering_techniques", []):
        fe_name = TECHNIQUE_NAME_MAP.get(raw_name, raw_name)
        bucket_key = BUCKET_KEY_MAP.get(fe_name)
        bucket_hits = hits.get(bucket_key, []) if bucket_key else []
        out.append({
            "name": fe_name,
            "evidence": ", ".join(bucket_hits) if bucket_hits else raw_name,
            "why": TECHNIQUE_WHY.get(fe_name, "Rule-based social-engineering pattern matched in the message text."),
        })
    return out


def to_frontend_record(
    *,
    conversation_id: str,
    raw_text: str,
    timestamp: str | None,
    ci: CustomerIntelligence,
    security: dict,
    recommended_action: str,
    channel: str = "API",
) -> dict:
    """Builds one frontend-shaped record from real backend analysis output."""
    messages = [{"role": "customer", "text": raw_text}]

    threat_detected = bool(security.get("threat_detected", False))
    risk_level = security.get("risk_level", "Low")
    threat_score = max(0, min(100, int(security.get("risk_score", 0))))
    threat_type = security.get("threat_type", "None")
    threat_types = [] if threat_type in (None, "None") else [threat_type]
    reporting = bool(REPORTING_REGEX.search(raw_text))

    support = {
        "category": ci.category,
        # PLACEHOLDER: Groq-based extraction doesn't emit a numeric match
        # confidence (unlike the frontend's local heuristic classifier).
        # 1.0 signals "model-extracted", not a calibrated probability.
        "confidence": 1.0,
        "alternates": [],
        "sentiment": ci.sentiment,
        "sentimentScore": _SENTIMENT_SCORE.get(ci.sentiment, 0),
        "emotion": ci.emotion,
        "priority": ci.priority,
        "priorityScore": _PRIORITY_SCORE.get(ci.priority, 10),
        "urgencyReasons": [],
        "resolution": ci.resolution_status,
        "resolutionReasons": [],
        "summary": {
            "issue": ci.summary,
            "request": ci.customer_request,
            "actions": [],
            "amount": "",
            "ref": "",
            "status": ci.resolution_status,
            "turns": len(messages),
        },
    }

    security_block = {
        "threatScore": threat_score,
        "risk": risk_level,
        "threatTypes": threat_types,
        "urls": [_map_url(u) for u in security.get("urls", [])],
        "emails": [_map_email(e) for e in security.get("emails", [])],
        "socialEngineering": _map_techniques(security),
        "reporting": reporting,
        "isThreat": threat_detected,
    }

    action_tone = "ok" if (not threat_detected and ci.priority in ("Low", "Medium") and ci.resolution_status == "Resolved") else "warn"

    record = {
        "id": conversation_id,
        "channel": channel,
        "ts": _iso_to_ms(timestamp),
        "customer": _guess_customer(raw_text, conversation_id),
        "messages": messages,
        "support": support,
        "security": security_block,
        "action": recommended_action,
        "actionTone": action_tone,
    }
    record["issues"] = _issues_of(raw_text)
    return record


def to_compact_json(record: dict) -> dict:
    """Mirrors frontend/js/app.js's own compact() so the analyzer's raw-JSON
    panel looks identical regardless of whether the record came from the
    in-browser engine or this backend."""
    s, sec = record["support"], record["security"]
    return {
        "conversation_id": record["id"],
        "channel": record["channel"],
        "customer_intelligence": {
            "category": s["category"], "confidence": s["confidence"],
            "sentiment": s["sentiment"], "emotion": s["emotion"],
            "priority": s["priority"], "priority_score": s["priorityScore"],
            "resolution_status": s["resolution"],
            "summary": {
                "issue": s["summary"]["issue"], "customer_request": s["summary"]["request"],
                "actions_taken": s["summary"]["actions"], "amount": s["summary"]["amount"],
                "reference": s["summary"]["ref"], "current_status": s["resolution"],
            },
        },
        "security_intelligence": {
            "threat_detected": sec["isThreat"], "risk_level": sec["risk"], "threat_score": sec["threatScore"],
            "threat_types": sec["threatTypes"],
            "social_engineering": [{"technique": t["name"], "evidence": t["evidence"]} for t in sec["socialEngineering"]],
            "suspicious_urls": [{"url": u["url"], "domain": u["host"], "risk": u["risk"], "verdict": u["verdict"], "signals": [s["t"] for s in u["signals"]]} for u in sec["urls"]],
            "suspicious_emails": [{"address": e["address"], "domain": e["domain"], "risk": e["risk"], "verdict": e["verdict"], "signals": [s["t"] for s in e["signals"]]} for e in sec["emails"]],
            "credential_request": any(t["name"] == "Credential harvesting" for t in sec["socialEngineering"]),
            "otp_request": any(t["name"] == "OTP / MFA bypass" for t in sec["socialEngineering"]),
        },
        "recommended_action": record["action"],
    }
