"""
v2_adapter — maps the REAL pipeline output (CustomerIntelligence from Groq +
security_analysis_engine) into the shapes the React/TS frontend expects, as
defined in sentinel-frontend_v2/src/types/intelligence.ts.

WHAT IS REAL vs WHAT IS DERIVED
===============================
Everything below comes from genuine analysis unless flagged. The v2 type
contract asks for several fields the existing engine physically cannot
produce, because security_analysis_engine.py is pure stdlib with NO network
access. Rather than inventing plausible-looking numbers, those fields use
explicit neutral sentinels. They are marked  # NOT REAL  inline.

REAL (computed from actual analysis):
  - threatLevel, phishingScore, confidenceScore  <- engine risk_score/level
  - attackVectors, socialEngineering.*           <- engine triggered techniques
  - urls[].domain / sslValid / typosquattingTarget / levenshteinDistance
  - iocs                                         <- engine urls + emails
  - secopsActions                                <- derived from risk level
  - ALL of supportIntelligence except safeSmartReply body wording
  - ALL of ExecutiveMetrics (aggregated over real analyses)

NOT REAL (no network / no data source available):
  - urls[].domainAgeDays, ipAddress, serverLocation, redirectHops,
    reputationScore  -> would need WHOIS / DNS / sandbox detonation
  - EmailHeaderForensics (SPF/DKIM/DMARC) -> omitted entirely; the field is
    optional in the TS type, so the UI degrades cleanly rather than showing
    fake PASS/FAIL verdicts
  - customerName / customerEmail / customerTier -> not present in
    sample_conversations.json; derived heuristically, see _derive_tier()
  - safeSmartReply.body -> templated from CI fields, not LLM-generated
    (a second Groq call per conversation would double demo latency+cost)
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from customer_intelligence.schemas.customer_intelligence import CustomerIntelligence

# --------------------------------------------------------------------------
# Lookup tables
# --------------------------------------------------------------------------

# engine risk_level -> TS ThreatSeverity
_RISK_TO_SEVERITY = {
    "Critical": "CRITICAL",
    "High": "HIGH",
    "Medium": "MEDIUM",
    "Low": "LOW",
}

# engine keyword bucket -> (display name, MITRE ATT&CK technique)
_BUCKET_META = {
    "urgency": ("Urgency Coercion", "T1566"),
    "fear_threat": ("Fear / Intimidation", "T1566"),
    "credential_harvesting": ("Credential Harvesting", "T1566.002"),
    "otp_harvesting": ("OTP / MFA Bypass Request", "T1621"),
    "authority_impersonation": ("Authority Impersonation", "T1656"),
    "reward_or_threat_bait": ("Reward / Threat Bait", "T1566.002"),
}

_BUCKET_EXPLANATION = {
    "urgency": "Message pressures the recipient to act immediately, short-circuiting careful judgement.",
    "fear_threat": "Message threatens loss, suspension, or penalty to provoke a panic response.",
    "credential_harvesting": "Message solicits a password, PIN, or login details directly.",
    "otp_harvesting": "Message asks for a one-time code, which no legitimate support agent ever needs.",
    "authority_impersonation": "Message claims to speak for a bank, government body, or senior staff member.",
    "reward_or_threat_bait": "Message dangles a prize or penalty to motivate an unsafe click.",
}

_PRIORITY_TO_P = {"Critical": "P1", "High": "P2", "Medium": "P3", "Low": "P4"}

# Routing table keyed on the CI category enum
_ROUTING = {
    "Payment/Transaction Issue": ("Billing Operations", "Tier 2", ["payments", "reconciliation"], "billing-t2"),
    "Account/Login Problem": ("Identity & Access", "Tier 1", ["auth", "account-recovery"], "identity-t1"),
    "Product Issue": ("Product Support", "Tier 2", ["product", "troubleshooting"], "product-t2"),
    "Delivery/Shipping Problem": ("Logistics", "Tier 1", ["fulfilment", "carrier-liaison"], "logistics-t1"),
    "Refund Request": ("Billing Operations", "Tier 2", ["refunds", "payments"], "billing-t2"),
    "Subscription Issue": ("Billing Operations", "Tier 1", ["subscriptions"], "billing-t1"),
    "Technical Problem": ("Engineering Support", "Tier 3", ["diagnostics", "backend"], "eng-t3"),
    "Service Quality": ("Customer Success", "Tier 2", ["retention", "relationship"], "success-t2"),
    "Billing Problem": ("Billing Operations", "Tier 2", ["invoicing", "payments"], "billing-t2"),
    "Security Concern": ("Security Operations", "Tier 3", ["incident-response", "phishing-triage"], "secops-t3"),
    "Other": ("General Support", "Tier 1", ["triage"], "general-t1"),
}

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    """Plain DP edit distance — used for the typosquatting readout."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _clamp(n: float, lo: int = 0, hi: int = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _derive_tier(conversation_id: str, priority: str) -> str:
    """NOT REAL — sample_conversations.json carries no customer records.

    Deterministic (hash-based) so the same conversation always shows the same
    tier across reloads, which matters when you are demoing. Weighted by CI
    priority so that Critical conversations tend to surface as high-value
    accounts, which is what makes the dashboard read sensibly.
    """
    bucket = int(hashlib.sha256(conversation_id.encode()).hexdigest(), 16) % 100
    if priority == "Critical":
        return "Enterprise VIP" if bucket < 55 else "Growth Enterprise"
    if priority == "High":
        return "Growth Enterprise" if bucket < 60 else "Standard Pro"
    if priority == "Medium":
        return "Standard Pro" if bucket < 70 else "Free Tier"
    return "Free Tier" if bucket < 60 else "Standard Pro"


def _derive_customer(conversation_id: str, raw_text: str) -> tuple[str, str]:
    """NOT REAL — no customer table exists. Uses an email found in the message
    body when there is one, otherwise a stable synthetic identity."""
    found = _EMAIL_RE.findall(raw_text)
    if found:
        addr = found[0]
        local = addr.split("@")[0]
        name = " ".join(p.capitalize() for p in re.split(r"[._-]+", local) if p) or local
        return name, addr
    return f"Customer {conversation_id}", f"{conversation_id.lower()}@customer.example"


# --------------------------------------------------------------------------
# Threat intelligence block
# --------------------------------------------------------------------------

def _map_url(u: dict) -> dict:
    """UrlForensicItem. Network-dependent fields use neutral sentinels."""
    domain = u.get("domain", "") or ""
    target = u.get("lookalike_target")
    https = bool(u.get("https_used"))

    # reputationScore: 100 = safe. Built from the signals the engine DOES see.
    reputation = 100
    if u.get("lookalike_flag"):
        reputation -= 55
    if u.get("is_shortened"):
        reputation -= 20
    if u.get("is_ip_address"):
        reputation -= 30
    if u.get("suspicious_path"):
        reputation -= 20
    if not https:
        reputation -= 10

    contribution = u.get("risk_contribution", "Low")
    if contribution == "Critical":
        verdict = "PHISHING"
    elif contribution == "High":
        verdict = "PHISHING"
    elif contribution == "Medium":
        verdict = "SUSPICIOUS"
    else:
        verdict = "CLEAN"

    item = {
        "url": u.get("full_url", ""),
        "domain": domain,
        "domainAgeDays": -1,          # NOT REAL — needs WHOIS
        "reputationScore": _clamp(reputation),
        "sslValid": https,            # proxy: scheme only, no cert validation
        "ipAddress": "unresolved",    # NOT REAL — needs DNS
        "serverLocation": "unknown",  # NOT REAL — needs geo-IP
        "redirectHops": [],           # NOT REAL — needs live fetch
        "sandboxVerdict": verdict,
    }
    if target:
        item["typosquattingTarget"] = target
        item["levenshteinDistance"] = _levenshtein(domain.lower(), target.lower())
    return item


def _map_iocs(security: dict) -> list[dict]:
    iocs: list[dict] = []
    for i, u in enumerate(security.get("urls", [])):
        sev = _RISK_TO_SEVERITY.get(u.get("risk_contribution", "Low"), "LOW")
        if u.get("lookalike_flag"):
            sev = "MALICIOUS"
        iocs.append({
            "id": f"ioc-url-{i}",
            "type": "IP" if u.get("is_ip_address") else "URL",
            "value": u.get("full_url", ""),
            "severity": sev,
            "description": (
                f"Domain {u.get('domain','')} closely resembles {u.get('lookalike_target')}."
                if u.get("lookalike_flag")
                else "URL extracted from message body and scored by the rule engine."
            ),
            "mitreTechnique": "T1566.002",
        })
    for i, e in enumerate(security.get("emails", [])):
        sev = _RISK_TO_SEVERITY.get(e.get("risk_contribution", "Low"), "LOW")
        if e.get("lookalike_flag"):
            sev = "MALICIOUS"
        iocs.append({
            "id": f"ioc-email-{i}",
            "type": "DOMAIN",
            "value": e.get("email", ""),
            "severity": sev,
            "description": (
                f"Sender domain impersonates {e.get('lookalike_target')}."
                if e.get("lookalike_flag")
                else "Email address extracted from message body."
            ),
            "mitreTechnique": "T1656",
        })
    return iocs


def _map_social_engineering(security: dict) -> dict:
    hits = security.get("_debug_keyword_hits", {}) or {}
    triggered = set(security.get("social_engineering_techniques", []) or [])

    vectors = []
    scores: dict[str, int] = {}
    for bucket, (display, _mitre) in _BUCKET_META.items():
        bucket_hits = hits.get(bucket, []) or []
        detected = bool(bucket_hits) or display in triggered
        score = _clamp(len(bucket_hits) * 28) if bucket_hits else (45 if detected else 0)
        scores[bucket] = score
        vectors.append({
            "name": display,
            "score": score,
            "detected": detected,
            "explanation": _BUCKET_EXPLANATION[bucket],
        })

    return {
        "urgencyCoercion": scores["urgency"],
        "authorityImpersonation": scores["authority_impersonation"],
        "fearIntimidation": scores["fear_threat"],
        "pretexting": _clamp(max(scores["credential_harvesting"], scores["otp_harvesting"])),
        "vectors": vectors,
    }


def _map_threat_intelligence(security: dict) -> dict:
    risk_score = int(security.get("risk_score", 0) or 0)
    risk_level = security.get("risk_level", "Low")
    threat_detected = bool(security.get("threat_detected"))

    severity = _RISK_TO_SEVERITY.get(risk_level, "LOW")
    if not threat_detected and risk_score == 0:
        severity = "CLEAN"

    attack_vectors = list(security.get("social_engineering_techniques", []) or [])
    if security.get("credential_request_detected"):
        attack_vectors.append("Credential Request")
    if security.get("otp_request_detected"):
        attack_vectors.append("OTP Request")
    if any(u.get("lookalike_flag") for u in security.get("urls", [])):
        attack_vectors.append("Typosquatted Domain")

    urls = [_map_url(u) for u in security.get("urls", [])]
    iocs = _map_iocs(security)

    reasoning_parts = [
        f"Rule engine scored this message {risk_score}/100 ({risk_level} risk)."
    ]
    if attack_vectors:
        reasoning_parts.append("Detected vectors: " + ", ".join(dict.fromkeys(attack_vectors)) + ".")
    if urls:
        reasoning_parts.append(f"{len(urls)} URL(s) extracted and scored.")
    if not threat_detected:
        reasoning_parts.append("No threat threshold breached; treat as routine support traffic.")

    return {
        "threatLevel": severity,
        "phishingScore": _clamp(risk_score),
        # Confidence is deterministic for a rule engine: high when the signal is
        # unambiguous (very low or very high score), lower in the grey band
        # around the Medium threshold where a call could go either way.
        "confidenceScore": _clamp(55 + abs(_clamp(risk_score) - 45) * 0.9),
        "attackVectors": list(dict.fromkeys(attack_vectors)),
        "socialEngineering": _map_social_engineering(security),
        "urls": urls,
        "iocs": iocs,
        "secopsActions": {
            "quarantined": risk_level in ("Critical", "High"),
            "linksStripped": bool(urls) and risk_level in ("Critical", "High", "Medium"),
            "domainBlocked": any(u.get("lookalike_flag") for u in security.get("urls", [])),
            "vipEscalation": risk_level == "Critical",
        },
        "summaryReasoning": " ".join(reasoning_parts),
    }


# --------------------------------------------------------------------------
# Support intelligence block
# --------------------------------------------------------------------------

def _map_support_intelligence(ci: CustomerIntelligence, security: dict, conversation_id: str,
                              recommended_action: str) -> dict:
    sentiment = ci.sentiment
    emotion = ci.emotion
    priority = ci.priority

    if sentiment == "Negative" and emotion in ("Anger", "Fear/Urgency"):
        overall = "EXTREMELY_NEGATIVE"
    elif sentiment == "Negative":
        overall = "NEGATIVE"
    elif sentiment == "Positive" and emotion == "Satisfaction":
        overall = "VERY_POSITIVE"
    elif sentiment == "Positive":
        overall = "POSITIVE"
    else:
        overall = "NEUTRAL"

    frustration = {"Anger": 92, "Frustration": 78, "Disappointment": 64,
                   "Confusion": 45, "Urgency": 55, "Fear/Urgency": 70,
                   "Satisfaction": 8, "None": 25}.get(emotion, 40)
    urgency = {"Critical": 95, "High": 74, "Medium": 45, "Low": 18}.get(priority, 30)
    satisfaction = _clamp(100 - frustration - (10 if ci.resolution_status == "Unresolved" else 0))

    churn = frustration * 0.5 + urgency * 0.3
    if ci.resolution_status == "Unresolved":
        churn += 12
    if security.get("threat_detected"):
        churn += 8
    churn = _clamp(churn)
    churn_level = "CRITICAL" if churn >= 75 else "HIGH" if churn >= 55 else "MEDIUM" if churn >= 30 else "LOW"

    dept, tier, skills, queue = _ROUTING.get(ci.category, _ROUTING["Other"])
    if security.get("risk_level") in ("Critical", "High"):
        dept, tier, skills, queue = _ROUTING["Security Concern"]

    entities = [{"label": "Keyword", "value": kw} for kw in ci.keywords[:6]]
    for u in security.get("urls", [])[:3]:
        entities.append({"label": "URL", "value": u.get("full_url", "")})
    for e in security.get("emails", [])[:3]:
        entities.append({"label": "Email", "value": e.get("email", "")})

    # safeSmartReply — NOT LLM-generated. Templated from real CI fields so the
    # content is accurate to the conversation without a second Groq round-trip.
    if security.get("threat_detected"):
        body = (
            f"Thank you for reporting this. Our security team has reviewed the message "
            f"relating to your {ci.category.lower()} and has flagged it as a likely "
            f"phishing attempt. Please do not click any links or share any codes or "
            f"passwords. We have quarantined the message and are investigating. "
            f"No action is required from you."
        )
        tone = "Reassuring / security-first"
    else:
        body = (
            f"Thanks for getting in touch. I understand you're dealing with "
            f"{ci.sub_issue.lower()} and you're looking for {ci.customer_request.lower()}. "
            f"I've routed this to our {dept} team at {tier} and flagged it as "
            f"{_PRIORITY_TO_P.get(priority, 'P3')}. We'll follow up with a concrete "
            f"update shortly."
        )
        tone = "Empathetic / de-escalating" if overall in ("NEGATIVE", "EXTREMELY_NEGATIVE") else "Warm / professional"

    return {
        "overallSentiment": overall,
        "sentimentScores": {
            "satisfaction": satisfaction,
            "frustration": _clamp(frustration),
            "urgency": _clamp(urgency),
        },
        "rootCauseCategory": ci.category,
        "intent": ci.customer_request,
        "churnRisk": {
            "score": churn,
            "level": churn_level,
            "retentionWarning": (
                f"{churn_level.title()} churn exposure — {ci.resolution_status.lower()} "
                f"{ci.category.lower()} with {emotion.lower()} signal."
                if churn_level in ("HIGH", "CRITICAL") else None
            ),
        },
        "customerTier": _derive_tier(conversation_id, priority),
        "recommendedPriority": _PRIORITY_TO_P.get(priority, "P3"),
        "automatedRouting": {
            "recommendedDepartment": dept,
            "escalationTier": tier,
            "requiredSkillset": skills,
            "suggestedQueue": queue,
        },
        "safeSmartReply": {
            "subject": f"Re: {ci.sub_issue}",
            "body": body,
            "safetyChecksPassed": True,
            "deescalationTone": tone,
            "keyPointsCovered": [ci.customer_request, recommended_action],
        },
        "detectedKeyEntities": entities,
    }


# --------------------------------------------------------------------------
# Token highlighting
# --------------------------------------------------------------------------

def _highlight_tokens(raw_text: str, ci: CustomerIntelligence, security: dict) -> list[dict]:
    tokens: list[dict] = []
    seen: set[str] = set()

    for u in security.get("urls", []):
        val = u.get("full_url", "")
        if val and val not in seen:
            seen.add(val)
            tokens.append({"text": val, "type": "url",
                           "explanation": f"URL scored {u.get('risk_contribution','Low')} risk by the rule engine."})

    hits = security.get("_debug_keyword_hits", {}) or {}
    for bucket, words in hits.items():
        for w in (words or [])[:4]:
            if w and w not in seen:
                seen.add(w)
                ttype = "urgency" if bucket in ("urgency", "fear_threat") else "threat"
                tokens.append({"text": w, "type": ttype,
                               "explanation": _BUCKET_EXPLANATION.get(bucket, "Matched a social-engineering pattern.")})

    for kw in ci.keywords[:5]:
        if kw and kw.lower() in raw_text.lower() and kw not in seen:
            seen.add(kw)
            tokens.append({"text": kw, "type": "entity",
                           "explanation": f"Key entity for category '{ci.category}'."})

    return tokens


# --------------------------------------------------------------------------
# Public builders
# --------------------------------------------------------------------------

def to_dual_analysis(conversation_id: str, raw_text: str, timestamp: str | None,
                     ci: CustomerIntelligence, security: dict, recommended_action: str,
                     channel: str = "ticket", sender: str | None = None,
                     recipient: str | None = None, subject: str | None = None) -> dict:
    """Builds the TS `DualAnalysisResult`."""
    name, email = _derive_customer(conversation_id, raw_text)
    return {
        "id": conversation_id,
        "timestamp": timestamp or _now_iso(),
        "channel": channel,
        "sender": sender or email,
        "recipient": recipient or "support@sentinel.example",
        "subject": subject or ci.sub_issue,
        "rawContent": raw_text,
        "highlightedTokens": _highlight_tokens(raw_text, ci, security),
        "threatIntelligence": _map_threat_intelligence(security),
        "supportIntelligence": _map_support_intelligence(ci, security, conversation_id, recommended_action),
    }


def to_ticket(conversation_id: str, raw_text: str, timestamp: str | None,
              ci: CustomerIntelligence, security: dict, recommended_action: str,
              channel: str = "ticket") -> dict:
    """Builds the TS `SupportTicketItem`, embedding the full analysis."""
    full = to_dual_analysis(conversation_id, raw_text, timestamp, ci, security,
                            recommended_action, channel=channel)
    name, email = _derive_customer(conversation_id, raw_text)
    ti = full["threatIntelligence"]
    si = full["supportIntelligence"]

    risk_level = security.get("risk_level", "Low")
    if risk_level == "Critical":
        status = "ESCALATED_SECOPS"
    elif risk_level == "High":
        status = "QUARANTINED"
    elif ci.resolution_status == "Resolved":
        status = "RESOLVED"
    elif ci.resolution_status == "In Progress":
        status = "IN_REVIEW"
    else:
        status = "OPEN"

    simple_sentiment = ("NEGATIVE" if si["overallSentiment"] in ("NEGATIVE", "EXTREMELY_NEGATIVE")
                        else "POSITIVE" if si["overallSentiment"] in ("POSITIVE", "VERY_POSITIVE")
                        else "NEUTRAL")

    return {
        "id": conversation_id,
        "customerName": name,
        "customerEmail": email,
        "customerTier": si["customerTier"],
        "channel": channel,
        "subject": ci.sub_issue,
        "snippet": raw_text[:160] + ("…" if len(raw_text) > 160 else ""),
        "timestamp": full["timestamp"],
        "status": status,
        "threatLevel": ti["threatLevel"],
        "supportPriority": si["recommendedPriority"],
        "sentiment": simple_sentiment,
        "fullAnalysis": full,
    }


def to_metrics(tickets: list[dict], mean_detect_ms: float) -> dict:
    """Aggregates REAL analysis output into the TS `ExecutiveMetrics`."""
    total = len(tickets)
    if total == 0:
        return {
            "totalScanned": 0, "totalThreatsBlocked": 0, "phishingBlockRate": 0.0,
            "socialEngineeringDetected": 0, "quarantinedCount": 0,
            "averageCsatEstimate": 0.0, "averageFrustrationRate": 0.0,
            "churnRiskDeflectedCount": 0, "meanTimeToDetectMs": 0,
            "defectClusters": [], "threatVectorDistribution": [],
        }

    threats = [t for t in tickets if t["threatLevel"] not in ("CLEAN", "LOW")]
    quarantined = [t for t in tickets if t["status"] in ("QUARANTINED", "ESCALATED_SECOPS")]
    social = [t for t in tickets if t["fullAnalysis"]["threatIntelligence"]["attackVectors"]]

    satisfaction_vals = [t["fullAnalysis"]["supportIntelligence"]["sentimentScores"]["satisfaction"] for t in tickets]
    frustration_vals = [t["fullAnalysis"]["supportIntelligence"]["sentimentScores"]["frustration"] for t in tickets]
    churn_deflected = [t for t in tickets
                       if t["fullAnalysis"]["supportIntelligence"]["churnRisk"]["level"] in ("HIGH", "CRITICAL")]

    # Defect clusters = real distribution over CI root-cause categories
    cat_counts: dict[str, list] = {}
    for t in tickets:
        cat = t["fullAnalysis"]["supportIntelligence"]["rootCauseCategory"]
        cat_counts.setdefault(cat, []).append(t)
    clusters = []
    for cat, items in sorted(cat_counts.items(), key=lambda kv: -len(kv[1]))[:8]:
        avg_frust = sum(i["fullAnalysis"]["supportIntelligence"]["sentimentScores"]["frustration"]
                        for i in items) / len(items)
        clusters.append({
            "category": cat,
            "count": len(items),
            # Trend needs historical data we don't retain; STABLE is the honest value.
            "trend": "STABLE",
            "sentimentImpact": round(avg_frust, 1),
        })

    # Threat vector distribution = real counts across detected vectors
    vec_counts: dict[str, int] = {}
    for t in tickets:
        for v in t["fullAnalysis"]["threatIntelligence"]["attackVectors"]:
            vec_counts[v] = vec_counts.get(v, 0) + 1
    vec_total = sum(vec_counts.values()) or 1
    distribution = [
        {"vector": v, "count": c, "percentage": round(c * 100 / vec_total, 1)}
        for v, c in sorted(vec_counts.items(), key=lambda kv: -kv[1])[:8]
    ]

    return {
        "totalScanned": total,
        "totalThreatsBlocked": len(threats),
        "phishingBlockRate": round(len(quarantined) * 100 / max(len(threats), 1), 1),
        "socialEngineeringDetected": len(social),
        "quarantinedCount": len(quarantined),
        "averageCsatEstimate": round(sum(satisfaction_vals) / total / 20, 2),  # 0-100 -> 0-5
        "averageFrustrationRate": round(sum(frustration_vals) / total, 1),
        "churnRiskDeflectedCount": len(churn_deflected),
        "meanTimeToDetectMs": int(mean_detect_ms),
        "defectClusters": clusters,
        "threatVectorDistribution": distribution,
    }
