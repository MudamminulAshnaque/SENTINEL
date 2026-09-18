# JSON Schema Contract — `/analyze`

This is the shared response shape the whole team builds against:
`customer_intelligence` (Person 1), `security_analysis` (Person 2), and
`recommended_action` (unowned — see note at the bottom), consumed by the
`dashboard` (Person 3).

Backing code:
- `customer_intelligence/schemas/customer_intelligence.py` — Pydantic model, source of truth for the `customer_intelligence` block
- `security/security_analysis_engine.py` — source of truth for the `security_analysis` block
- `backend/main.py` — merges both into the full response below

## Top-level response

```json
{
  "conversation_id": "CS-10245",
  "raw_text": "the original message text",
  "timestamp": "2026-09-18T10:30:00Z",
  "customer_intelligence": { ... },
  "security_analysis": { ... },
  "recommended_action": "Escalate to security team immediately. Do not click links or disclose credentials."
}
```

## `customer_intelligence` block (Person 1)

| Field | Type | Notes |
|---|---|---|
| `category` | enum | One of: `Payment/Transaction Issue`, `Account/Login Problem`, `Product Issue`, `Delivery/Shipping Problem`, `Refund Request`, `Subscription Issue`, `Technical Problem`, `Service Quality`, `Billing Problem`, `Security Concern`, `Other` |
| `sub_issue` | string | Free-text sub-classification within the category |
| `sentiment` | enum | `Positive` / `Neutral` / `Negative` |
| `emotion` | enum | `Anger`, `Frustration`, `Satisfaction`, `Confusion`, `Urgency`, `Disappointment`, `Fear/Urgency`, `None` (the string `"None"`, not null — this field is always present) |
| `priority` | enum | `Low` / `Medium` / `High` / `Critical` |
| `resolution_status` | enum | `Resolved` / `Unresolved` / `In Progress` |
| `customer_request` | string | What the customer is asking for |
| `summary` | string | 1–3 sentence plain-text summary |
| `keywords` | string[] | Lowercase-normalized |

Every field is always present — the frontend should never need to handle a
missing key.

## `security_analysis` block (Person 2)

```json
{
  "threat_detected": true,
  "threat_type": "Phishing",
  "social_engineering": true,
  "social_engineering_techniques": ["Urgency", "Fear Appeal", "Credential Harvesting", "OTP Request"],
  "urls": [
    {
      "full_url": "http://paypa1-security.example/login",
      "domain": "paypa1-security.example",
      "https_used": false,
      "is_ip_address": false,
      "is_shortened": false,
      "lookalike_flag": true,
      "lookalike_target": "paypal.com",
      "suspicious_path": true,
      "risk_contribution": "High"
    }
  ],
  "emails": [
    {
      "email": "support@paypa1-security.example",
      "domain": "paypa1-security.example",
      "lookalike_flag": true,
      "lookalike_target": "paypal.com",
      "risk_contribution": "Medium"
    }
  ],
  "credential_request_detected": true,
  "otp_request_detected": true,
  "risk_score": 135,
  "risk_level": "Critical"
}
```

Field notes:
- `threat_type` is one of `"Phishing"`, `"Social Engineering"`, or `"None"`.
- `threat_detected` is `true` once `risk_score >= 20` (i.e. `risk_level` is `Medium` or above).
- `risk_level` is one of `Low` / `Medium` / `High` / `Critical`, derived from `risk_score` (Critical ≥ 70, High ≥ 45, Medium ≥ 20, else Low).
- `urls[].risk_contribution` / `emails[].risk_contribution` use the same four labels, scoped to that one URL/email's own contribution to the score — not the overall `risk_level`.
- **`_debug_keyword_hits`** (which keyword text matched each detection bucket) exists internally in the engine's raw output for debugging, but is stripped out by `backend/main.py` before the `/analyze` response goes out, so it does **not** appear in the public contract. Don't rely on it being there.

## `recommended_action`

A single human-readable sentence. **This field is unowned** — nobody on the
team was assigned it in the original contract doc. `backend/main.py`
currently derives it from `security_analysis.risk_level` +
`customer_intelligence.priority` (security risk takes precedence). Treat
this as a placeholder and confirm the final logic/ownership with the team
before demo day.

## Example: full merged response

```json
{
  "conversation_id": "CS-10245",
  "raw_text": "URGENT! Your account has been compromised. Click this link immediately to secure your account and enter your username, password and OTP. http://paypa1-security.example/login",
  "timestamp": "2026-09-18T10:30:00Z",
  "customer_intelligence": {
    "category": "Security Concern",
    "sub_issue": "Account Compromise Claim",
    "sentiment": "Negative",
    "emotion": "Fear/Urgency",
    "priority": "Critical",
    "resolution_status": "Unresolved",
    "customer_request": "Account verification",
    "summary": "Message claims the customer's account was compromised and urges immediate action via a link, requesting credentials and OTP.",
    "keywords": ["account compromised", "urgent", "verify", "otp"]
  },
  "security_analysis": {
    "threat_detected": true,
    "threat_type": "Phishing",
    "social_engineering": true,
    "social_engineering_techniques": ["Urgency", "Fear Appeal", "Credential Harvesting", "OTP Request"],
    "urls": [{
      "full_url": "http://paypa1-security.example/login",
      "domain": "paypa1-security.example",
      "https_used": false,
      "is_ip_address": false,
      "is_shortened": false,
      "lookalike_flag": true,
      "lookalike_target": "paypal.com",
      "suspicious_path": true,
      "risk_contribution": "High"
    }],
    "emails": [],
    "credential_request_detected": true,
    "otp_request_detected": true,
    "risk_score": 135,
    "risk_level": "Critical"
  },
  "recommended_action": "Escalate to security team immediately. Do not click links or disclose credentials."
}
```
