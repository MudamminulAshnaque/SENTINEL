import json

import pytest

import customer_intelligence.groq_extraction as ge
from customer_intelligence.schemas.customer_intelligence import CustomerIntelligence

VALID_JSON = json.dumps({
    "category": "Billing Problem", "sub_issue": "Duplicate charge", "sentiment": "Negative",
    "emotion": "Frustration", "priority": "Medium", "resolution_status": "Unresolved",
    "customer_request": "Refund", "summary": "Test summary.", "keywords": ["test"],
})

INVALID_JSON_BAD_ENUM = json.dumps({
    "category": "Very High", "sub_issue": "x", "sentiment": "Negative", "emotion": "None",
    "priority": "Low", "resolution_status": "Resolved", "customer_request": "x",
    "summary": "x", "keywords": [],
})


@pytest.mark.asyncio
async def test_first_try_success(monkeypatch):
    async def fake_call(messages, temperature):
        return VALID_JSON
    monkeypatch.setattr(ge, "_call_groq_with_backoff", fake_call)

    result = await ge.extract_customer_intelligence("test text", conversation_id="CS-A")
    assert result.attempts == 1
    assert result.used_fallback is False
    assert isinstance(result.data, CustomerIntelligence)


@pytest.mark.asyncio
async def test_validation_failure_then_corrective_retry_succeeds(monkeypatch):
    calls = {"n": 0}

    async def fake_call(messages, temperature):
        calls["n"] += 1
        return INVALID_JSON_BAD_ENUM if calls["n"] == 1 else VALID_JSON

    monkeypatch.setattr(ge, "_call_groq_with_backoff", fake_call)

    result = await ge.extract_customer_intelligence("test text", conversation_id="CS-B")
    assert result.attempts == 2
    assert result.used_fallback is False
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_both_attempts_invalid_falls_back(monkeypatch):
    async def fake_call(messages, temperature):
        return "not even json"
    monkeypatch.setattr(ge, "_call_groq_with_backoff", fake_call)

    result = await ge.extract_customer_intelligence("test text", conversation_id="CS-C")
    assert result.used_fallback is True
    assert result.data.category == "Other"
    assert result.data.priority == "Medium"  # visible for review, not silently Low
    assert result.raw_error is not None


@pytest.mark.asyncio
async def test_transient_error_on_first_call_falls_back_immediately(monkeypatch):
    async def fake_call(messages, temperature):
        raise ge.TransientAPIError("simulated network failure")
    monkeypatch.setattr(ge, "_call_groq_with_backoff", fake_call)

    result = await ge.extract_customer_intelligence("test text", conversation_id="CS-D")
    assert result.used_fallback is True
    assert result.attempts == 0  # never even got a first successful exchange


@pytest.mark.asyncio
async def test_transient_error_on_retry_falls_back(monkeypatch):
    calls = {"n": 0}

    async def fake_call(messages, temperature):
        calls["n"] += 1
        if calls["n"] == 1:
            return INVALID_JSON_BAD_ENUM
        raise ge.TransientAPIError("network died on retry")

    monkeypatch.setattr(ge, "_call_groq_with_backoff", fake_call)

    result = await ge.extract_customer_intelligence("test text", conversation_id="CS-E")
    assert result.used_fallback is True
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_missing_api_key_raises_extraction_error(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ge.ExtractionError):
        ge._get_client()


@pytest.mark.asyncio
async def test_health_check_returns_false_on_failure(monkeypatch):
    def fake_get_client():
        raise ge.ExtractionError("no key")
    monkeypatch.setattr(ge, "_get_client", fake_get_client)

    healthy = await ge.check_groq_health()
    assert healthy is False
