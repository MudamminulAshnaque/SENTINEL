"""
Tests for the frontend-bridge endpoints (/api/conversations, /api/analyze)
and the services/frontend_adapter.py mapping. Mocked Groq, real security
engine — same pattern as the rest of the suite (mocked, no network).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from customer_intelligence.schemas.customer_intelligence import CustomerIntelligence

SAMPLE_CI = {
    "category": "Security Concern",
    "sub_issue": "Account Compromise Claim",
    "sentiment": "Negative",
    "emotion": "Fear/Urgency",
    "priority": "Critical",
    "resolution_status": "Unresolved",
    "customer_request": "Account verification",
    "summary": "Message claims the customer's account was compromised and urges immediate action.",
    "keywords": ["account compromised", "urgent", "verify"],
}


class _FakeExtractionResult:
    def __init__(self, ci_dict=SAMPLE_CI):
        self.data = CustomerIntelligence(**ci_dict)
        self.used_fallback = False
        self.attempts = 1


@pytest.fixture
def mocked_ci():
    with patch("main.extract_customer_intelligence", AsyncMock(return_value=_FakeExtractionResult())):
        yield


@pytest.fixture
async def client(mocked_ci):
    import main
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_api_analyze_shape(client):
    r = await client.post("/api/analyze", json={"text": "URGENT! Verify your password now: http://bit.ly/xyz"})
    assert r.status_code == 200
    body = r.json()
    assert "record" in body and "json" in body
    record = body["record"]
    for key in ("id", "channel", "ts", "customer", "messages", "support", "security", "action", "actionTone", "issues"):
        assert key in record
    for key in ("category", "sentiment", "emotion", "priority", "resolution", "summary"):
        assert key in record["support"]
    for key in ("threatScore", "risk", "threatTypes", "urls", "emails", "socialEngineering", "isThreat"):
        assert key in record["security"]


@pytest.mark.asyncio
async def test_api_analyze_detects_phishing_url(client):
    r = await client.post("/api/analyze", json={"text": "Your SBI account will be suspended. Verify now: http://bit.ly/sbi-verify"})
    record = r.json()["record"]
    assert record["security"]["isThreat"] is True
    assert record["security"]["risk"] in ("High", "Critical")
    assert len(record["security"]["urls"]) == 1
    assert record["security"]["urls"][0]["host"] == "bit.ly"


@pytest.mark.asyncio
async def test_api_analyze_credential_and_otp_names_match_frontend_contract(client):
    r = await client.post("/api/analyze", json={"text": "Please share your otp and enter your password to confirm your account."})
    techniques = r.json()["record"]["security"]["socialEngineering"]
    names = {t["name"] for t in techniques}
    # These exact strings are what frontend/js/app.js string-matches against.
    assert "Credential harvesting" in names
    assert "OTP / MFA bypass" in names


@pytest.mark.asyncio
async def test_api_conversations_sample_size(client):
    r = await client.get("/api/conversations", params={"size": "sample"})
    assert r.status_code == 200
    records = r.json()
    assert len(records) == 30
    assert all("support" in rec and "security" in rec for rec in records)


@pytest.mark.asyncio
async def test_api_conversations_invalid_size(client):
    r = await client.get("/api/conversations", params={"size": "huge"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_cors_header_present(client):
    r = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "*"
