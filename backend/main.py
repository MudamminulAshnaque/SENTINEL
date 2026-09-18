"""
FastAPI orchestration layer — Phase 6, plus a frontend-compatibility layer.

POST /analyze: runs customer_intelligence (Groq-backed) and security_analysis
(real rule-based phishing/social-engineering engine — see
services/security_analysis_engine.py) concurrently via asyncio.gather,
merges them into the AnalyzeResponse contract shape, and returns the full
JSON. This is the team's original contract endpoint — unchanged.

GET /health: pings Groq to confirm the backend can actually reach its LLM
provider, not just that the process is alive.

--- Frontend bridge (added) ---------------------------------------------
The SENTRY frontend (frontend/js/provider.js) expects a different contract
when pointed at a live backend:
    GET  /api/conversations?size=sample|large   -> array of frontend records
    POST /api/analyze {"text": "..."}            -> {"record": ..., "json": ...}
These two endpoints reuse the exact same real analysis (_run_analysis below)
and map the output into that shape via services/frontend_adapter.py. See
that file's docstring for exactly which fields are real vs. honest
placeholders.

NOTE on recommended_action: this field is top-level in the contract and
UNOWNED by either Person 1 or Person 2 — flag this with your team. The
derivation below is a reasonable placeholder (combines priority + risk_level)
but should be confirmed as a team decision, not assumed as final.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# customer_intelligence/ and security/ are sibling top-level folders (Person 1's
# and Person 2's modules), one level up from this file's repo layout:
#   sentinel/{backend,customer_intelligence,security,dashboard,data,docs}
# Adding the repo root to sys.path lets this file import them as ordinary
# packages without needing to run uvicorn from a different working directory —
# `cd backend && uvicorn main:app --reload` keeps working exactly as before.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from logging_config import get_logger
from customer_intelligence.schemas.customer_intelligence import CustomerIntelligence
from services.frontend_adapter import to_compact_json, to_frontend_record
from customer_intelligence.groq_extraction import ExtractionError, check_groq_health, extract_customer_intelligence
from security.security_analysis import extract_security_analysis
from routers.v1 import router as v1_router

logger = get_logger("nlp.main")

app = FastAPI(title="OmniShield NLP Service", version="0.1.0")

# The frontend is served from a different origin (e.g. http://localhost:5173
# via `python3 -m http.server`) than this API (http://localhost:8000), so
# the browser needs CORS headers to allow the cross-origin fetch() calls in
# frontend/js/provider.js. Wide open (*) is fine here: this is a local dev
# service with no cookies/auth to leak, not a production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # shared top-level data/ folder

# In-memory cache for /api/conversations: each analysed conversation costs a
# real Groq call, so we don't want to re-run 30-135 of them on every page
# load. Cleared on server restart. Keyed by "sample" / "large".
_conversations_cache: dict[str, list[dict]] = {}


class AnalyzeRequest(BaseModel):
    conversation_id: str
    raw_text: str
    timestamp: str | None = None  # ISO 8601; defaults to now if omitted


def _derive_recommended_action(ci: CustomerIntelligence, security: dict) -> str:
    """
    Placeholder derivation — UNOWNED FIELD, confirm with team before relying
    on this in production. Security risk takes precedence over customer
    priority since a real threat matters more than an unhappy customer.
    """
    risk = security.get("risk_level", "Low")
    if risk in ("Critical", "High"):
        return "Escalate to security team immediately. Do not click links or disclose credentials."
    if ci.priority == "Critical":
        return "Escalate to senior support immediately."
    if ci.priority == "High":
        return "Prioritize for prompt human follow-up."
    return "Handle through standard support queue."


async def _run_analysis(conversation_id: str, raw_text: str, channel: str = "ticket"):
    """Runs customer_intelligence + security_analysis concurrently. Shared by
    /analyze, /api/analyze, /api/conversations, and the /api/v1 router.
    Raises ExtractionError for genuine setup problems (e.g. missing
    GROQ_API_KEY) — callers turn that into an HTTP 503.

    `channel` only adjusts how the NLP prompt frames the input (see
    services/groq_extraction._CHANNEL_HINTS) — it does not change the
    security engine or the output schema."""
    return await asyncio.gather(
        extract_customer_intelligence(raw_text, conversation_id=conversation_id, channel=channel),
        extract_security_analysis(raw_text),
    )


@app.post("/analyze")
async def analyze(request: AnalyzeRequest) -> dict:
    start = time.perf_counter()

    # Run both blocks concurrently — this is the whole point of making
    # extract_customer_intelligence async: Person 2's call doesn't wait on ours.
    try:
        ci_result, security_result = await _run_analysis(request.conversation_id, request.raw_text)
    except ExtractionError as e:
        # Only reaches here for genuine setup problems (missing API key,
        # auth failure) — never for a bad model response, which is handled
        # internally via retry + fallback.
        logger.error("analyze_setup_error", extra={"conversation_id": request.conversation_id, "error": str(e)})
        raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")

    timestamp = request.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recommended_action = _derive_recommended_action(ci_result.data, security_result)

    # Internal-only field: exposes which raw keywords tripped each detection
    # bucket. Useful for debugging the engine, but shipping it in the public
    # contract response lets a caller reverse-engineer what to avoid saying
    # to dodge detection, so it's dropped here before the response goes out.
    public_security_result = {k: v for k, v in security_result.items() if k != "_debug_keyword_hits"}

    response = {
        "conversation_id": request.conversation_id,
        "raw_text": request.raw_text,
        "timestamp": timestamp,
        "customer_intelligence": ci_result.data.model_dump(),
        "security_analysis": public_security_result,
        "recommended_action": recommended_action,
    }

    latency_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "analyze_complete",
        extra={
            "conversation_id": request.conversation_id,
            "latency_ms": latency_ms,
            "ci_used_fallback": ci_result.used_fallback,
            "ci_attempts": ci_result.attempts,
        },
    )
    return response


@app.get("/health")
async def health() -> dict:
    groq_ok = await check_groq_health()
    return {
        "status": "ok" if groq_ok else "degraded",
        "groq_reachable": groq_ok,
    }


# ---------------------------------------------------------------------------
# Frontend bridge — GET /api/conversations, POST /api/analyze
# ---------------------------------------------------------------------------

class FrontendAnalyzeRequest(BaseModel):
    text: str


def _load_sample_conversations() -> list[dict]:
    path = DATA_DIR / "sample_conversations.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


async def _analyze_one_for_frontend(entry: dict, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore:  # cap concurrent Groq calls
        ci_result, security_result = await _run_analysis(entry["conversation_id"], entry["raw_text"])
    recommended_action = _derive_recommended_action(ci_result.data, security_result)
    return to_frontend_record(
        conversation_id=entry["conversation_id"],
        raw_text=entry["raw_text"],
        timestamp=entry.get("timestamp"),
        ci=ci_result.data,
        security=security_result,
        recommended_action=recommended_action,
        channel="Support",
    )


@app.get("/api/conversations")
async def api_conversations(size: str = "sample") -> list[dict]:
    """Frontend contract: returns an array of frontend-shaped records.

    `size=sample` analyses the original 30 curated conversations;
    `size=large` analyses the full 135-entry merged dataset. Every entry
    runs through the REAL customer_intelligence (Groq) + security_analysis
    (real engine) pipeline — this is genuine analysis, not canned fixtures.
    Results are cached in memory per process (each entry is a real, billed
    Groq call), so the first request for a given `size` is the slow one.
    """
    if size not in ("sample", "large"):
        raise HTTPException(status_code=400, detail="size must be 'sample' or 'large'")

    if size in _conversations_cache:
        return _conversations_cache[size]

    all_entries = _load_sample_conversations()
    entries = all_entries[:30] if size == "sample" else all_entries

    semaphore = asyncio.Semaphore(5)  # be polite to the Groq rate limit
    try:
        records = await asyncio.gather(*(_analyze_one_for_frontend(e, semaphore) for e in entries))
    except ExtractionError as e:
        logger.error("api_conversations_setup_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")

    _conversations_cache[size] = records
    return records


@app.post("/api/analyze")
async def api_analyze(request: FrontendAnalyzeRequest) -> dict:
    """Frontend contract: POST {text} -> {record, json}. Live-analyzer
    endpoint behind Sentry's 'paste a message' box."""
    conversation_id = "LIVE-" + str(int(time.time() * 1000))[-8:]
    try:
        ci_result, security_result = await _run_analysis(conversation_id, request.text)
    except ExtractionError as e:
        logger.error("api_analyze_setup_error", extra={"error": str(e)})
        raise HTTPException(status_code=503, detail=f"NLP service misconfigured: {e}")

    recommended_action = _derive_recommended_action(ci_result.data, security_result)
    record = to_frontend_record(
        conversation_id=conversation_id,
        raw_text=request.text,
        timestamp=None,
        ci=ci_result.data,
        security=security_result,
        recommended_action=recommended_action,
        channel="Live",
    )
    return {"record": record, "json": to_compact_json(record)}
