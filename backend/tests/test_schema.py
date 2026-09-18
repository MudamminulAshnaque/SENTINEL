import pytest
from pydantic import ValidationError

from customer_intelligence.schemas.customer_intelligence import AnalyzeResponse, CustomerIntelligence

VALID_SAMPLE = {
    "category": "Security Concern",
    "sub_issue": "Account Compromise Claim",
    "sentiment": "Negative",
    "emotion": "Fear/Urgency",
    "priority": "Critical",
    "resolution_status": "Unresolved",
    "customer_request": "Account verification",
    "summary": "Message claims the customer's account was compromised and urges immediate action.",
    "keywords": ["account compromised", "urgent", "verify", "OTP"],
}


def test_valid_sample_from_contract_doc_passes():
    ci = CustomerIntelligence(**VALID_SAMPLE)
    assert ci.category == "Security Concern"
    assert ci.priority == "Critical"


def test_invalid_enum_value_rejected():
    bad = {**VALID_SAMPLE, "priority": "Very High"}
    with pytest.raises(ValidationError):
        CustomerIntelligence(**bad)


def test_missing_required_field_rejected():
    bad = {k: v for k, v in VALID_SAMPLE.items() if k != "sentiment"}
    with pytest.raises(ValidationError):
        CustomerIntelligence(**bad)


def test_hallucinated_extra_field_rejected():
    bad = {**VALID_SAMPLE, "made_up_field": "oops"}
    with pytest.raises(ValidationError):
        CustomerIntelligence(**bad)


def test_keywords_normalized_to_lowercase():
    ci = CustomerIntelligence(**{**VALID_SAMPLE, "keywords": ["URGENT", "Verify"]})
    assert ci.keywords == ["urgent", "verify"]


def test_emotion_none_is_valid_string_not_python_none():
    ci = CustomerIntelligence(**{**VALID_SAMPLE, "emotion": "None"})
    assert ci.emotion == "None"


def test_emotion_empty_string_rejected():
    with pytest.raises(ValidationError):
        CustomerIntelligence(**{**VALID_SAMPLE, "emotion": ""})


def test_summary_over_three_sentences_gets_trimmed_not_rejected():
    long_summary = "First sentence. Second sentence. Third sentence. Fourth sentence should be dropped."
    ci = CustomerIntelligence(**{**VALID_SAMPLE, "summary": long_summary})
    sentence_count = ci.summary.count(".") + ci.summary.count("!") + ci.summary.count("?")
    assert sentence_count <= 3


def test_full_analyze_response_validates_against_contract_example():
    """Mirrors the exact example payload from the team's contract doc."""
    payload = {
        "conversation_id": "CS-10245",
        "raw_text": (
            "URGENT! Your account has been compromised. Click this link immediately "
            "to secure your account and enter your username, password and OTP. "
            "http://paypa1-security.example/login"
        ),
        "timestamp": "2026-09-18T10:30:00Z",
        "customer_intelligence": VALID_SAMPLE,
        "security_analysis": {
            "threat_detected": True,
            "threat_type": "Phishing",
            "social_engineering": True,
            "social_engineering_techniques": ["Urgency", "Credential Harvesting", "OTP Request"],
            "urls": [
                {
                    "full_url": "http://paypa1-security.example/login",
                    "domain": "paypa1-security.example",
                    "https_used": False,
                    "is_ip_address": False,
                    "is_shortened": False,
                    "lookalike_flag": True,
                    "lookalike_target": "paypal.com",
                    "risk_contribution": "High",
                }
            ],
            "emails": [],
            "credential_request_detected": True,
            "otp_request_detected": True,
            "risk_level": "Critical",
        },
        "recommended_action": "Escalate to security team immediately. Do not click link or disclose credentials.",
    }
    parsed = AnalyzeResponse(**payload)
    assert parsed.customer_intelligence.category == "Security Concern"
    assert parsed.recommended_action.startswith("Escalate")
