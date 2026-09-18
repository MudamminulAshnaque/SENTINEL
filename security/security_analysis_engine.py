"""
security_analysis.py
Security / Phishing / Social-Engineering detection module.

Public entry point: analyze_security(text: str) -> dict
Matches the "security_analysis" block of the team's JSON schema contract.

No external dependencies beyond Python's standard library.
"""

import re
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# 1. CONFIG: brand list, shorteners, keyword buckets
#    Tweak these lists freely — they're your "knowledge base".
# ---------------------------------------------------------------------------

KNOWN_BRANDS = [
    "paypal.com", "amazon.com", "google.com", "microsoft.com", "apple.com",
    "facebook.com", "instagram.com", "netflix.com", "flipkart.com",
    "sbi.co.in", "hdfcbank.com", "icicibank.com", "axisbank.com",
    "phonepe.com", "paytm.com", "gpay.com", "irctc.co.in", "whatsapp.com",
    # Added: more brands worth covering for an India-facing demo dataset
    "kotak.com", "yesbank.in", "pnbindia.in", "bankofbaroda.in",
    "myntra.com", "meesho.com", "swiggy.com", "zomato.com", "ola.com",
    "uber.com", "linkedin.com", "outlook.com", "yahoo.com", "dropbox.com",
    "gov.in", "incometax.gov.in", "uidai.gov.in",
]

URL_SHORTENERS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "adf.ly", "cutt.ly", "rebrand.ly", "shorturl.at",
]

SUSPICIOUS_PATH_KEYWORDS = [
    "verify", "secure", "login", "update-account", "confirm",
    "reset-password", "unlock", "validate", "account-review",
]

KEYWORD_BUCKETS = {
    "urgency": [
        "urgent", "immediately", "act now", "expires today", "right away",
        "suspended", "final notice", "within 24 hours", "asap",
    ],
    "fear_threat": [
        "compromised", "unauthorized access", "legal action", "account locked",
        "suspicious activity", "unusual login", "your account will be closed",
        "fraud detected", "detected fraud",
    ],
    "credential_harvesting": [
        "enter your password", "verify your username", "confirm your details",
        "enter your pin", "login credentials", "update your payment information",
        "confirm your identity", "verify your account", "confirm your account",
        "update your information", "enter your username", "net banking password",
        "share your password", "need your password", "provide your password",
        "give us your password", "banking password",
    ],
    "otp_harvesting": [
        # NOTE: bare "otp" is deliberately excluded from this list — a customer
        # saying "I'm not receiving my login OTP" is not a phishing attempt.
        # Bare "otp" is instead checked separately below with proximity to an
        # action verb (share/enter/provide/confirm), so only an actual
        # OTP-harvesting REQUEST gets flagged, not a normal OTP complaint.
        "one-time password", "verification code", "share the code",
        "enter the code sent", "6-digit code", "4-digit code", "cvv",
        "share your otp", "expiry date",
    ],
    "authority_impersonation": [
        "official", "bank team", "security department", "it support",
        "customer care team", "government", "law enforcement",
        "reserve bank", "tax department", "income tax", "cyber cell",
    ],
    "reward_or_threat_bait": [
        "you have won", "has won", "claim your prize", "congratulations you have been selected",
        "your account will be permanently deleted", "failure to comply",
        "avoid penalty", "final warning",
    ],
}

# Points each bucket contributes to the overall risk score when triggered
BUCKET_WEIGHTS = {
    "urgency": 15,
    "fear_threat": 15,
    "credential_harvesting": 25,
    "otp_harvesting": 25,
    "authority_impersonation": 10,
    "reward_or_threat_bait": 15,
}

LOOKALIKE_URL_WEIGHT = 40
LOOKALIKE_EMAIL_WEIGHT = 30
IP_URL_WEIGHT = 20
SHORTENER_WEIGHT = 10
SUSPICIOUS_PATH_WEIGHT = 10

# Action verbs that, when found near the word "otp", turn a harmless mention
# ("I didn't receive my OTP") into an actual harvesting request ("share your
# OTP with us"). Proximity-based instead of a flat keyword to avoid
# false-positiving on customers legitimately talking about their own OTP.
OTP_HARVESTING_ACTION_WORDS = [
    "share", "shared", "sharing", "enter", "entering", "provide", "providing",
    "confirm", "confirming", "send us", "sending us", "give us", "giving us",
    "read out", "tell us", "verify with",
]
OTP_PROXIMITY_WINDOW = 40  # characters of context checked on each side of "otp"

RISK_THRESHOLDS = [
    (70, "Critical"),
    (45, "High"),
    (20, "Medium"),
    (0, "Low"),
]

# ---------------------------------------------------------------------------
# 2. HELPERS
# ---------------------------------------------------------------------------

URL_REGEX = re.compile(r'(https?://[^\s"\'<>]+)', re.IGNORECASE)
EMAIL_REGEX = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
IP_HOST_REGEX = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')


def levenshtein(a: str, b: str) -> int:
    """Classic edit-distance. No library needed — ~10 lines of DP."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr_row = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr_row.append(min(
                prev_row[j] + 1,        # deletion
                curr_row[j - 1] + 1,    # insertion
                prev_row[j - 1] + cost  # substitution
            ))
        prev_row = curr_row
    return prev_row[-1]


def _best_substring_distance(haystack: str, needle: str):
    """
    Slides a window (sized close to `needle`'s length) across `haystack`
    and returns the smallest edit distance found. This catches brand names
    embedded inside longer fake domains, e.g. "paypal" inside
    "paypa1-security.example" — a plain whole-string compare would miss it
    because the fake domain is much longer than "paypal.com".
    """
    best = len(needle)  # worst case: no similarity at all
    for size in (len(needle) - 1, len(needle), len(needle) + 1):
        if size <= 0:
            continue
        for start in range(0, max(len(haystack) - size + 1, 1)):
            window = haystack[start:start + size]
            if not window:
                continue
            dist = levenshtein(window, needle)
            if dist < best:
                best = dist
    return best


def closest_brand_match(domain: str):
    """Return (brand, distance) for the closest known brand, or (None, None)."""
    domain = domain.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    best_brand, best_dist = None, None
    for brand in KNOWN_BRANDS:
        brand_core = brand.split(".")[0]  # "paypal.com" -> "paypal"
        dist = _best_substring_distance(domain, brand_core)
        if best_dist is None or dist < best_dist:
            best_brand, best_dist = brand, dist
    return best_brand, best_dist


def is_lookalike(domain: str, distance_threshold: int = 1):
    """
    Flags a domain as a lookalike if a known brand name appears, in
    near-matching form, somewhere inside it — while the domain itself
    is NOT that brand's real domain.
    distance_threshold=1 catches paypa1 vs paypal (1 char swap),
    micros0ft vs microsoft, amaz0n vs amazon, etc., while staying tight
    enough to avoid false positives on unrelated words.
    """
    domain_clean = domain.lower()
    if domain_clean.startswith("www."):
        domain_clean = domain_clean[4:]

    brand, dist = closest_brand_match(domain_clean)
    if brand is None:
        return False, None
    if domain_clean == brand:
        return False, None  # exact real domain = legitimate, not a lookalike
    if dist <= distance_threshold:
        return True, brand
    return False, None


# ---------------------------------------------------------------------------
# 3. URL ANALYSIS
# ---------------------------------------------------------------------------

def analyze_urls(text: str):
    urls_found = URL_REGEX.findall(text)
    results = []
    score = 0

    for url in urls_found:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        https_used = parsed.scheme == "https"
        is_ip = bool(IP_HOST_REGEX.match(domain.split(":")[0]))
        is_shortened = any(short in domain for short in URL_SHORTENERS)
        lookalike_flag, lookalike_target = is_lookalike(domain)
        suspicious_path = any(kw in path for kw in SUSPICIOUS_PATH_KEYWORDS)

        url_score = 0
        if lookalike_flag:
            url_score += LOOKALIKE_URL_WEIGHT
        if is_ip:
            url_score += IP_URL_WEIGHT
        if is_shortened:
            url_score += SHORTENER_WEIGHT
        if suspicious_path:
            url_score += SUSPICIOUS_PATH_WEIGHT
        if not https_used:
            url_score += 5

        score += url_score

        results.append({
            "full_url": url,
            "domain": domain,
            "https_used": https_used,
            "is_ip_address": is_ip,
            "is_shortened": is_shortened,
            "lookalike_flag": lookalike_flag,
            "lookalike_target": lookalike_target,
            "suspicious_path": suspicious_path,
            "risk_contribution": _score_to_label(url_score),
        })

    return results, score


# ---------------------------------------------------------------------------
# 4. EMAIL ANALYSIS
# ---------------------------------------------------------------------------

def analyze_emails(text: str):
    emails_found = EMAIL_REGEX.findall(text)
    results = []
    score = 0

    for email in emails_found:
        domain = email.split("@")[-1].lower()
        lookalike_flag, lookalike_target = is_lookalike(domain)

        email_score = LOOKALIKE_EMAIL_WEIGHT if lookalike_flag else 0
        score += email_score

        results.append({
            "email": email,
            "domain": domain,
            "lookalike_flag": lookalike_flag,
            "lookalike_target": lookalike_target,
            "risk_contribution": _score_to_label(email_score),
        })

    return results, score


# ---------------------------------------------------------------------------
# 5. SOCIAL ENGINEERING / KEYWORD BUCKET SCORING
# ---------------------------------------------------------------------------

def detect_otp_proximity_harvesting(text_lower: str):
    """
    Finds bare occurrences of "otp" and checks whether an action verb
    (share/enter/provide/confirm/...) appears within OTP_PROXIMITY_WINDOW
    characters on either side. Returns a list with one marker string if
    found, else an empty list. Keeps "I didn't get my OTP" (no nearby
    action verb) from being flagged, while still catching "enter your
    username, password and OTP" or "share your OTP with us".
    """
    for match in re.finditer(r'\botp\b', text_lower):
        start = max(0, match.start() - OTP_PROXIMITY_WINDOW)
        end = min(len(text_lower), match.end() + OTP_PROXIMITY_WINDOW)
        window = text_lower[start:end]
        if any(action in window for action in OTP_HARVESTING_ACTION_WORDS):
            return ["otp (harvesting context)"]
    return []


def analyze_keywords(text: str):
    text_lower = text.lower()
    triggered_techniques = []
    hits_by_bucket = {}
    score = 0

    for bucket, phrases in KEYWORD_BUCKETS.items():
        hits = [p for p in phrases if p in text_lower]
        hits_by_bucket[bucket] = hits

    # Bare "otp" is checked separately (proximity-based, see function above)
    # and merged into the same bucket so scoring/labels stay unified.
    hits_by_bucket["otp_harvesting"].extend(detect_otp_proximity_harvesting(text_lower))

    for bucket, hits in hits_by_bucket.items():
        if hits:
            score += BUCKET_WEIGHTS[bucket]
            triggered_techniques.append(_bucket_to_label(bucket))

    credential_request_detected = bool(hits_by_bucket["credential_harvesting"])
    otp_request_detected = bool(hits_by_bucket["otp_harvesting"])

    return {
        "triggered_techniques": triggered_techniques,
        "hits_by_bucket": hits_by_bucket,  # useful for your "explainability" demo
        "credential_request_detected": credential_request_detected,
        "otp_request_detected": otp_request_detected,
    }, score


def _bucket_to_label(bucket: str) -> str:
    return {
        "urgency": "Urgency",
        "fear_threat": "Fear Appeal",
        "credential_harvesting": "Credential Harvesting",
        "otp_harvesting": "OTP Request",
        "authority_impersonation": "Authority Impersonation",
        "reward_or_threat_bait": "Reward/Threat Bait",
    }[bucket]


# ---------------------------------------------------------------------------
# 6. RISK AGGREGATION
# ---------------------------------------------------------------------------

def _score_to_label(score: int) -> str:
    for threshold, label in RISK_THRESHOLDS:
        if score >= threshold:
            return label
    return "Low"


# ---------------------------------------------------------------------------
# 7. MAIN ENTRY POINT — this is what Person 1/3 will import and call
# ---------------------------------------------------------------------------

def analyze_security(text: str) -> dict:
    url_results, url_score = analyze_urls(text)
    email_results, email_score = analyze_emails(text)
    keyword_results, keyword_score = analyze_keywords(text)

    total_score = url_score + email_score + keyword_score
    risk_level = _score_to_label(total_score)

    any_lookalike = any(u["lookalike_flag"] for u in url_results) or \
                     any(e["lookalike_flag"] for e in email_results)

    threat_detected = total_score >= 20  # matches "Medium" and above
    if any_lookalike or keyword_results["otp_request_detected"] or keyword_results["credential_request_detected"]:
        threat_type = "Phishing"
    elif keyword_results["triggered_techniques"]:
        threat_type = "Social Engineering"
    else:
        threat_type = "None"

    return {
        "threat_detected": threat_detected,
        "threat_type": threat_type,
        "social_engineering": bool(keyword_results["triggered_techniques"]),
        "social_engineering_techniques": keyword_results["triggered_techniques"],
        "urls": url_results,
        "emails": email_results,
        "credential_request_detected": keyword_results["credential_request_detected"],
        "otp_request_detected": keyword_results["otp_request_detected"],
        "risk_score": total_score,       # raw number — handy for debugging/demo
        "risk_level": risk_level,
        "_debug_keyword_hits": keyword_results["hits_by_bucket"],  # remove before final demo if you want a cleaner output
    }


# ---------------------------------------------------------------------------
# 8. COMBINER — merges YOUR output with Person 1's customer_intelligence
#    output into the final "recommended_action" string + full record.
#    This is Module 9 ("Combined Intelligence") from the problem statement.
# ---------------------------------------------------------------------------

def decide_action(customer_intelligence: dict, security_analysis: dict) -> str:
    """
    Rule priority (highest wins):
      1. Critical security risk        -> escalate to security team, hard stop
      2. High security risk            -> flag for security review
      3. Critical customer priority
         (fraud/financial loss wording, even if security module scored low)
                                        -> escalate to security + support
      4. Unresolved + High priority    -> escalate to support supervisor
      5. Otherwise                     -> route to normal support queue
    Security concerns always outrank pure customer-support urgency, because
    a live phishing/credential-harvesting attempt is a bigger organizational
    risk than a slow refund.
    """
    risk_level = security_analysis.get("risk_level", "Low")
    threat_detected = security_analysis.get("threat_detected", False)
    priority = customer_intelligence.get("priority", "Low")
    resolution_status = customer_intelligence.get("resolution_status", "Unresolved")

    if risk_level == "Critical":
        return ("Escalate to security team immediately. Do not click any link "
                "or disclose credentials/OTP. Treat as an active phishing attempt.")

    if risk_level == "High" or (threat_detected and risk_level == "Medium"):
        return ("Flag for security team review before responding to the customer. "
                "Possible phishing/social-engineering attempt detected.")

    if priority == "Critical":
        return ("Escalate to security and payment/fraud investigation team — "
                "customer reports potential account compromise or financial loss.")

    if priority == "High" and resolution_status == "Unresolved":
        return "Escalate to a senior support agent — high-priority issue still unresolved."

    if priority in ("High", "Medium") and resolution_status == "Unresolved":
        return "Route to support queue with priority follow-up."

    return "Route to standard support queue for normal handling."


def combine_intelligence(conversation_id: str, raw_text: str,
                          customer_intelligence: dict,
                          security_analysis_result: dict) -> dict:
    """
    Convenience wrapper that assembles the FULL record matching the team's
    JSON schema contract in one call. Person 3 (frontend/integration) can
    import this directly instead of hand-building the merge every time.
    """
    return {
        "conversation_id": conversation_id,
        "raw_text": raw_text,
        "customer_intelligence": customer_intelligence,
        "security_analysis": security_analysis_result,
        "recommended_action": decide_action(customer_intelligence, security_analysis_result),
    }


# ---------------------------------------------------------------------------
# 8b. MULTI-TURN CONVERSATION SUPPORT
#     A real support conversation is a list of messages, not one string.
#     A phishing/social-engineering attempt can be buried several messages
#     in — e.g. a scammer builds rapport first, then asks for the OTP in
#     message 4. Running analyze_security() on the whole thread joined
#     together would still catch it, but you lose WHERE it happened, which
#     matters for the demo ("the threat appeared here, in message 3") and
#     for flows like WhatsApp/live-chat exports where messages come in as
#     a list already.
# ---------------------------------------------------------------------------

def analyze_conversation(messages: list, conversation_id: str = "CS-00000") -> dict:
    """
    messages: list of dicts like {"sender": "customer", "text": "..."}
              (sender is optional — only "text" is required)

    Returns:
      - per_message: security_analysis for each message, in order
      - highest_risk_message_index: which message drove the worst score
      - overall: a security_analysis block for the conversation as a whole,
                 combining per-message flags. This is the block that goes
                 into your JSON schema's "security_analysis" field.
    """
    per_message_results = []
    for i, msg in enumerate(messages):
        text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
        result = analyze_security(text)
        per_message_results.append({
            "message_index": i,
            "sender": msg.get("sender") if isinstance(msg, dict) else None,
            "text": text,
            "security_analysis": result,
        })

    if not per_message_results:
        overall = analyze_security("")  # empty-conversation edge case
        return {
            "conversation_id": conversation_id,
            "per_message": [],
            "highest_risk_message_index": None,
            "overall": overall,
        }

    # The conversation's overall risk = its single worst message, not an
    # average — one phishing message in a 20-message thread should still
    # trip a Critical alert, not get diluted by 19 normal messages.
    worst = max(per_message_results, key=lambda r: r["security_analysis"]["risk_score"])

    # Union: if ANY message in the thread flagged a technique/URL/email,
    # it belongs in the conversation-level summary — a security reviewer
    # needs the full picture, not just the worst single line.
    all_techniques = set()
    all_urls, all_emails = [], []
    any_credential, any_otp = False, False
    for r in per_message_results:
        sa = r["security_analysis"]
        all_techniques.update(sa["social_engineering_techniques"])
        all_urls.extend(sa["urls"])
        all_emails.extend(sa["emails"])
        any_credential = any_credential or sa["credential_request_detected"]
        any_otp = any_otp or sa["otp_request_detected"]

    overall = {
        "threat_detected": worst["security_analysis"]["threat_detected"],
        "threat_type": worst["security_analysis"]["threat_type"],
        "social_engineering": bool(all_techniques),
        "social_engineering_techniques": sorted(all_techniques),
        "urls": all_urls,
        "emails": all_emails,
        "credential_request_detected": any_credential,
        "otp_request_detected": any_otp,
        "risk_score": worst["security_analysis"]["risk_score"],
        "risk_level": worst["security_analysis"]["risk_level"],
        "first_flagged_at_message": worst["message_index"],
    }

    return {
        "conversation_id": conversation_id,
        "per_message": per_message_results,
        "highest_risk_message_index": worst["message_index"],
        "overall": overall,
    }


# ---------------------------------------------------------------------------
# 9. QUICK TEST — run this file directly: `python security_analysis.py`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    test_messages = [
        # The exact phishing example from the hackathon problem statement
        "URGENT! Your account has been compromised. Click this link immediately "
        "to secure your account and enter your username, password and OTP. "
        "http://paypa1-security.example/login",

        # A normal, non-security complaint (should score Low)
        "I was charged twice for my subscription this month. Please refund the extra payment.",

        # Email-based impersonation example from the doc
        "Please verify your account at http://paypa1-security.example/login. "
        "Contact our support team at support@paypa1-security.example",

        # Legit-looking message with a real brand domain (should NOT be flagged)
        "You can check your order status at https://www.amazon.com/orders",
    ]

    for i, msg in enumerate(test_messages, start=1):
        print(f"\n--- Test {i} ---")
        print("Input:", msg)
        result = analyze_security(msg)
        print(json.dumps(result, indent=2))

    # -----------------------------------------------------------------
    # Combined-record demo. In the real pipeline, `mock_customer_block`
    # comes from Person 1's analyze_customer_intelligence(text) function —
    # it's hardcoded here just so you can see combine_intelligence() work
    # end-to-end before that function exists.
    # -----------------------------------------------------------------
    print("\n--- Combined record demo (Test 1's message) ---")
    mock_customer_block = {
        "category": "Security Concern",
        "sentiment": "Negative",
        "emotion": "Fear/Urgency",
        "priority": "Critical",
        "resolution_status": "Unresolved",
        "summary": "Customer received a message claiming their account was "
                    "compromised, urging immediate action via a link.",
    }
    security_block = analyze_security(test_messages[0])
    full_record = combine_intelligence(
        conversation_id="CS-10245",
        raw_text=test_messages[0],
        customer_intelligence=mock_customer_block,
        security_analysis_result=security_block,
    )
    print(json.dumps(full_record, indent=2))

    # -----------------------------------------------------------------
    # Multi-turn conversation demo — the threat is buried in message 3,
    # not the first line. A scammer builds trust, then asks for the OTP.
    # -----------------------------------------------------------------
    print("\n--- Multi-turn conversation demo ---")
    thread = [
        {"sender": "customer", "text": "Hi, I noticed a strange login attempt on my account."},
        {"sender": "support", "text": "Thanks for reaching out, we're looking into it."},
        {"sender": "customer", "text": "URGENT please confirm your account by entering your OTP "
                                        "at http://paypa1-security.example/verify or it will be suspended"},
        {"sender": "support", "text": "We will never ask for your OTP over chat."},
    ]
    convo_result = analyze_conversation(thread, conversation_id="CS-99001")
    print("Highest risk message index:", convo_result["highest_risk_message_index"])
    print("Overall risk level:", convo_result["overall"]["risk_level"])
    print(json.dumps(convo_result["overall"], indent=2))
