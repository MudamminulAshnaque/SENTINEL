"""
/api/v1 router — the contract the React/TS frontend (sentinel-frontend_v2)
actually calls.

Endpoints, matching src/services/api.ts exactly:
    GET   /api/v1/health
    POST  /api/v1/analyze        {channel, text, subject?, sender?, recipient?}
    POST  /api/v1/scan-url       {url}
    POST  /api/v1/parse-eml      multipart file upload (.eml)
    GET   /api/v1/tickets
    PATCH /api/v1/tickets/{id}   {status}
    GET   /api/v1/metrics

Every one of these runs the REAL pipeline — Groq-backed customer_intelligence
plus the rule-based security engine. Nothing here returns canned fixtures.

PERFORMANCE NOTE (important for a live demo):
GET /tickets analyses real conversations, and each one is a billed Groq call.
The first request is therefore slow. Results are cached in-process, so warm it
up BEFORE you present:  curl http://localhost:8000/api/v1/tickets
TICKET_LIMIT controls how many are analysed; 30 keeps first-load near a minute
on a normal connection. Raise it only if you have time to spare.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from logging_config import get_logger
from services.eml_parser import EmlParseError, parse_eml_bytes
from customer_intelligence.groq_extraction import ExtractionError, check_groq_health
from security.security_analysis import extract_security_analysis
from services.v2_adapter import _map_url, to_dual_analysis, to_metrics, to_ticket

logger = get_logger("nlp.v1")

router = APIRouter(prefix="/api/v1", tags=["v2-frontend"])

DATA_DIR = Path(__file__).parent.parent / "data"

# How many conversations to analyse for the ticket queue. Each is a real Groq
# call — raising this raises first-load time roughly linearly.
TICKET_LIMIT = 30

# Max concurrent Groq calls. Matches the semaphore already used in main.py.
CONCURRENCY = 5

_tickets_cache: list[dict] | None = None
_metrics_cache: dict | None = None
_mean_detect_ms: float = 0.0

# Ticket status overrides from PATCH. In-memory only — cleared on restart.
_status_overrides: dict[str, str] = {}


# --------------------------------------------------------------------------
# Request models
# --------------------------------------------------------------------------

class V1AnalyzeRequest(BaseModel):
    channel: str = "ticket"
    text: str
    subject: str | None = None
    sender: str | None = None
    recipient: str | None = None


class V1ScanUrlRequest(BaseModel):
    url: str


class V1TicketStatusPatch(BaseModel):
    status: str


# --------------------------------------------------------------------------
# Shared analysis helper
#
# Imported lazily from main to avoid a circular import at module load time:
# main.py imports this router, so this module cannot import main at top level.
# --------------------------------------------------------------------------

async def _analyse(conversation_id: str, raw_text: str, channel: str = "ticket"):
    from main import _derive_recommended_action, _run_analysis
    ci_result, security = await _run_analysis(conversation_id, raw_text, channel=channel)
    action = _derive_recommended_action(ci_result.data, security)
    return ci_result.data, security, action


def _load_conversations() -> list[dict]:
    with (DATA_DIR / "sample_conversations.json").open(encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# GET /api/v1/health
# --------------------------------------------------------------------------

@router.get("/health")
async def v1_health() -> dict:
    """The frontend only checks response.ok, but returns real detail so the
    config modal's latency readout means something."""
    groq_ok = await check_groq_health()
    return {
        "status": "ok" if groq_ok else "degraded",
        "groq_reachable": groq_ok,
        "version": "v1",
    }


# --------------------------------------------------------------------------
# POST /api/v1/analyze  ->  DualAnalysisResult
# --------------------------------------------------------------------------

@router.post("/analyze")
async def v1_analyze(request: V1AnalyzeRequest) -> dict:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    conversation_id = "LIVE-" + str(int(time.time() * 1000))[-8:]
    channel = request.channel or "ticket"
    start = time.perf_counter()
    try:
        ci, security, action = await _analyse(conversation_id, request.text, channel=channel)
    except ExtractionError as e:
        logger.error("v1_analyze_setup_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info("v1_analyze_complete", extra={"conversation_id": conversation_id,
                                              "latency_ms": latency_ms})

    return to_dual_analysis(
        conversation_id=conversation_id,
        raw_text=request.text,
        timestamp=None,
        ci=ci,
        security=security,
        recommended_action=action,
        channel=channel,
        sender=request.sender,
        recipient=request.recipient,
        subject=request.subject,
    )


# --------------------------------------------------------------------------
# POST /api/v1/scan-url  ->  UrlForensicItem
# --------------------------------------------------------------------------

@router.post("/scan-url")
async def v1_scan_url(request: V1ScanUrlRequest) -> dict:
    """Runs the real URL analyser over a bare URL.

    The engine extracts URLs from free text, so the URL is passed as a
    one-line message body. Network-dependent forensics (WHOIS age, geo-IP,
    redirect chain) are NOT available — see v2_adapter._map_url.
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url must not be empty")

    security = await extract_security_analysis(url)
    urls = security.get("urls", [])
    if not urls:
        raise HTTPException(status_code=422,
                            detail="No parseable URL found in the supplied value.")

    return _map_url(urls[0])


# --------------------------------------------------------------------------
# POST /api/v1/parse-eml  ->  {sender, subject, text, used_html_fallback}
# --------------------------------------------------------------------------

_MAX_EML_SIZE_BYTES = 5 * 1024 * 1024  # 5MB — generous for a text email, guards against abuse


@router.post("/parse-eml")
async def v1_parse_eml(file: UploadFile = File(...)) -> dict:
    """
    Parses an uploaded .eml file into {sender, subject, text}, using
    Python's stdlib email module (see services/eml_parser.py) — no
    third-party dependency.

    This does NOT run the NLP/security analysis itself — it only extracts
    the fields. The frontend populates its existing sender/subject/content
    inputs from the response and the user still triggers /analyze
    separately, so they can review/edit before analysis runs.

    Known limitation: the stdlib email parser is lenient. A non-.eml file
    (e.g. a .txt or renamed file) may "parse" as a bodiless or garbled
    message rather than being cleanly rejected. The filename-extension
    check below is a first line of defense, not a guarantee.
    """
    if file.filename and not file.filename.lower().endswith(".eml"):
        raise HTTPException(
            status_code=400,
            detail=f"Expected a .eml file, got '{file.filename}'. "
                   "Only .eml (RFC 822 email) files are supported.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > _MAX_EML_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(raw_bytes)} bytes). "
                   f"Max supported size is {_MAX_EML_SIZE_BYTES} bytes.",
        )

    try:
        parsed = parse_eml_bytes(raw_bytes)
    except EmlParseError as e:
        logger.warning("parse_eml_failed", extra={"eml_filename": file.filename, "error": str(e)})
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(
        "parse_eml_success",
        extra={
            "eml_filename": file.filename,
            "used_html_fallback": parsed.used_html_fallback,
            "text_length": len(parsed.text),
        },
    )
    return {
        "sender": parsed.sender,
        "subject": parsed.subject,
        "text": parsed.text,
        "used_html_fallback": parsed.used_html_fallback,
    }


# --------------------------------------------------------------------------
# GET /api/v1/tickets  ->  SupportTicketItem[]
# --------------------------------------------------------------------------

async def _build_tickets() -> list[dict]:
    global _mean_detect_ms

    entries = _load_conversations()[:TICKET_LIMIT]
    semaphore = asyncio.Semaphore(CONCURRENCY)
    durations: list[float] = []

    async def one(entry: dict) -> dict:
        async with semaphore:
            t0 = time.perf_counter()
            ci, security, action = await _analyse(entry["conversation_id"], entry["raw_text"])
            durations.append((time.perf_counter() - t0) * 1000)
        return to_ticket(
            conversation_id=entry["conversation_id"],
            raw_text=entry["raw_text"],
            timestamp=entry.get("timestamp"),
            ci=ci,
            security=security,
            recommended_action=action,
            channel="ticket",
        )

    tickets = await asyncio.gather(*(one(e) for e in entries))
    _mean_detect_ms = sum(durations) / len(durations) if durations else 0.0
    return list(tickets)


@router.get("/tickets")
async def v1_tickets() -> list[dict]:
    global _tickets_cache
    if _tickets_cache is None:
        try:
            _tickets_cache = await _build_tickets()
        except ExtractionError as e:
            logger.error("v1_tickets_setup_error", extra={"error": str(e)})
            raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")

    # Apply any in-session status changes made from the UI.
    return [
        {**t, "status": _status_overrides.get(t["id"], t["status"])}
        for t in _tickets_cache
    ]


# --------------------------------------------------------------------------
# PATCH /api/v1/tickets/{ticket_id}
# --------------------------------------------------------------------------

_VALID_STATUSES = {"OPEN", "IN_REVIEW", "QUARANTINED", "RESOLVED", "ESCALATED_SECOPS"}


@router.patch("/tickets/{ticket_id}")
async def v1_patch_ticket(ticket_id: str, patch: V1TicketStatusPatch) -> dict:
    if patch.status not in _VALID_STATUSES:
        raise HTTPException(status_code=400,
                            detail=f"status must be one of {sorted(_VALID_STATUSES)}")
    _status_overrides[ticket_id] = patch.status
    return {"id": ticket_id, "status": patch.status}


# --------------------------------------------------------------------------
# GET /api/v1/metrics  ->  ExecutiveMetrics
# --------------------------------------------------------------------------

@router.get("/metrics")
async def v1_metrics() -> dict:
    """Aggregated from the same real analyses that back /tickets, so the
    dashboard numbers and the queue always agree."""
    global _tickets_cache, _metrics_cache

    if _tickets_cache is None:
        try:
            _tickets_cache = await _build_tickets()
        except ExtractionError as e:
            logger.error("v1_metrics_setup_error", extra={"error": str(e)})
            raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")
        _metrics_cache = None

    if _metrics_cache is None:
        _metrics_cache = to_metrics(_tickets_cache, _mean_detect_ms)

    return _metrics_cache
