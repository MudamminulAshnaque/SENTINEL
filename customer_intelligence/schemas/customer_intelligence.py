"""
Pydantic schemas for the /analyze endpoint's shared JSON contract.

Person 1 (NLP) owns CustomerIntelligence.
Person 2 (Security) owns SecurityAnalysis (defined in schemas/security_analysis.py —
not built here, only referenced for the merged AnalyzeResponse model).

Design notes (see team discussion):
- Enums are modeled as Literal[...] rather than enum.Enum for simplicity, since
  nothing here needs to iterate over valid values programmatically.
- `emotion` is REQUIRED, not Optional — "None" is a valid literal string value,
  not Python's None. Every field must always be present per the contract
  ("Never omit a key — Person 3's frontend will break if fields randomly
  disappear").
- `summary` sentence-count ("1-3 sentences") and `keywords` casing
  ("lowercase preferred") are soft/normalizing validators, not hard
  rejections — LLM output is inconsistent enough on these that hard-rejecting
  would burn retry budget on cosmetic issues rather than real schema
  violations (wrong enum, missing field).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------------------------
# Enum-like literals (case-sensitive, must match the contract doc exactly)
# --------------------------------------------------------------------------

Category = Literal[
    "Payment/Transaction Issue",
    "Account/Login Problem",
    "Product Issue",
    "Delivery/Shipping Problem",
    "Refund Request",
    "Subscription Issue",
    "Technical Problem",
    "Service Quality",
    "Billing Problem",
    "Security Concern",
    "Other",
]

Sentiment = Literal["Positive", "Neutral", "Negative"]

Emotion = Literal[
    "Anger",
    "Frustration",
    "Satisfaction",
    "Confusion",
    "Urgency",
    "Disappointment",
    "Fear/Urgency",
    "None",
]

Priority = Literal["Low", "Medium", "High", "Critical"]

ResolutionStatus = Literal["Resolved", "Unresolved", "In Progress"]


# --------------------------------------------------------------------------
# customer_intelligence block (Person 1 owns this)
# --------------------------------------------------------------------------

class CustomerIntelligence(BaseModel):
    model_config = ConfigDict(extra="forbid")  # catch stray/hallucinated fields from the LLM immediately

    category: Category
    sub_issue: str = Field(..., description="Free-text sub-classification within category")
    sentiment: Sentiment
    emotion: Emotion
    priority: Priority
    resolution_status: ResolutionStatus
    customer_request: str = Field(..., description="What the customer is asking for, free text")
    summary: str = Field(..., description="1-3 sentence plain-text summary")
    keywords: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def _soft_check_summary_length(cls, v: str) -> str:
        # Soft guideline only: count sentence-ending punctuation, don't reject.
        # If it's wildly over spec (e.g. a paragraph dump), trim to first 3
        # sentences rather than failing validation outright.
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", v.strip()) if s]
        if len(sentences) > 3:
            v = " ".join(sentences[:3])
        return v

    @field_validator("keywords")
    @classmethod
    def _normalize_keyword_casing(cls, v: list[str]) -> list[str]:
        # "lowercase preferred" -> normalize rather than reject.
        return [kw.lower().strip() for kw in v if kw and kw.strip()]

    @field_validator("category", "sentiment", "emotion", "priority", "resolution_status", mode="before")
    @classmethod
    def _reject_blank(cls, v):
        # Catch the common LLM failure mode of returning "" for a required enum
        # field before it silently passes through as an invalid Literal.
        if isinstance(v, str) and not v.strip():
            raise ValueError("enum field cannot be empty string")
        return v


# --------------------------------------------------------------------------
# Minimal placeholder for Person 2's block, so this file can validate the
# FULL merged contract locally without waiting on their implementation.
# Replace this import with the real thing once Person 2 ships
# schemas/security_analysis.py — do NOT extend this stub with real fields,
# that's their block to own.
# --------------------------------------------------------------------------

class _SecurityAnalysisPlaceholder(BaseModel):
    """Temporary stand-in. Swap for Person 2's real SecurityAnalysis model."""
    model_config = ConfigDict(extra="allow")  # accept whatever shape Person 2 is currently producing


# --------------------------------------------------------------------------
# Full /analyze response contract (top-level)
# --------------------------------------------------------------------------

class AnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    raw_text: str
    timestamp: str  # ISO 8601, e.g. "2026-09-18T10:30:00Z"

    customer_intelligence: CustomerIntelligence
    security_analysis: _SecurityAnalysisPlaceholder

    recommended_action: str = Field(
        ..., description="1 sentence, human-readable. Unowned field — flag ownership with team."
    )


if __name__ == "__main__":
    # Quick smoke test against the contract doc's example payload.
    sample = {
        "category": "Security Concern",
        "sub_issue": "Account Compromise Claim",
        "sentiment": "Negative",
        "emotion": "Fear/Urgency",
        "priority": "Critical",
        "resolution_status": "Unresolved",
        "customer_request": "Account verification",
        "summary": (
            "Message claims the customer's account was compromised and urges "
            "immediate action via a link, requesting credentials and OTP."
        ),
        "keywords": ["account compromised", "urgent", "verify", "OTP"],
    }
    ci = CustomerIntelligence(**sample)
    print(ci.model_dump_json(indent=2))
