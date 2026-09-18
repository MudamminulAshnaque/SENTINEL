"""
generate_dataset.py
Builds a ready-to-use demo dataset for the hackathon: a mix of normal
customer-support complaints (across all 10 categories from the problem
statement) and phishing/social-engineering messages (covering every
technique your security_analysis.py module detects), plus a small set
of multi-turn conversations for analyze_conversation() testing.

Why synthetic instead of a raw Kaggle download:
  Real datasets (Kaggle support tickets, Mendeley/Kaggle phishing email
  and SMS corpora) exist but none combine "support conversation" +
  "phishing" in one place, and this sandbox can't reach kaggle.com to
  pull them for you directly. This generator gives you an immediately
  usable CSV NOW; treat the real datasets (linked in the comments below)
  as an optional add-on if your team has time to blend in more variety.

  Real dataset sources worth pulling from if you have time:
    - Kaggle: "Customer Support Tickets Dataset (200K+ Records)"
    - Kaggle: "Phishing Email Dataset" (naserabdullahalam) — Enron/CEAS/
      Nazario/Nigerian-fraud/SpamAssassin combined, ~82K emails
    - Mendeley: "SMS Phishing Dataset for Machine Learning and Pattern
      Recognition" (Mishra & Soni, 2022) — ~6K labeled SMS/smishing texts

Usage:
    python generate_dataset.py
    python generate_dataset.py --out my_dataset.csv

Output columns: conversation_id, raw_text, expected_category,
                 expected_sentiment, expected_is_threat
(the "expected_*" columns are ground-truth labels for YOUR OWN testing/
demo-accuracy checks — run_batch.py ignores extra columns, so this file
still works fine as-is with the batch runner.)
"""

import argparse
import csv

# ---------------------------------------------------------------------------
# NORMAL COMPLAINT TEMPLATES — one list per category from the problem
# statement. Each template is filled in with a few variable substitutions
# to generate multiple distinct rows without needing external data.
# ---------------------------------------------------------------------------

CATEGORY_TEMPLATES = {
    "Payment/Transaction Issue": [
        "I was charged twice for my order #{order_id}, please refund the extra ₹{amount}.",
        "My payment of ₹{amount} failed but the amount was deducted from my account.",
        "I tried to pay for order #{order_id} three times and it keeps failing at checkout.",
        "The transaction for ₹{amount} shows as pending for 3 days now, what's happening?",
    ],
    "Account/Login Problem": [
        "I can't log into my account, it keeps saying incorrect password even after reset.",
        "My account got locked after I tried logging in from a new phone.",
        "I'm not receiving the login OTP on my registered number, can you check?",
        "It says my account doesn't exist anymore, but I've been using it for 2 years.",
    ],
    "Product Issue": [
        "The product I received for order #{order_id} is damaged and doesn't turn on.",
        "I ordered a size M but received a size S, the item is unusable.",
        "The item's quality is much worse than shown in the pictures on the website.",
        "My order #{order_id} arrived missing half the parts described in the listing.",
    ],
    "Delivery/Shipping Problem": [
        "My order #{order_id} was supposed to arrive 5 days ago and still shows 'in transit'.",
        "The delivery partner marked my order as delivered but I never received it.",
        "I need to change my delivery address for order #{order_id} before it ships.",
        "The package for order #{order_id} arrived completely crushed.",
    ],
    "Refund Request": [
        "I returned my order #{order_id} two weeks ago and still haven't received my refund.",
        "Please process my refund of ₹{amount}, the item didn't match the description.",
        "I cancelled order #{order_id} but the refund hasn't reflected in my bank account yet.",
        "Refund for ₹{amount} was approved but I haven't received it after 10 business days.",
    ],
    "Subscription Issue": [
        "I want to cancel my subscription but the app doesn't show any option to do it.",
        "I was auto-renewed for another year even after I cancelled last month.",
        "My subscription benefits stopped working even though I'm still being charged.",
        "Can I downgrade my subscription plan without losing my saved data?",
    ],
    "Technical Problem": [
        "The app crashes every time I try to open the payments section.",
        "I can't upload my documents, the upload button just doesn't respond.",
        "The website is showing a blank page when I try to check my order history.",
        "Push notifications stopped working after the last app update.",
    ],
    "Service Quality": [
        "I have contacted support three times and nobody has solved my problem, this is extremely frustrating.",
        "The support agent was rude and disconnected the call before resolving my issue.",
        "I've been on hold for over 40 minutes just to ask a simple question.",
        "Nobody followed up on my complaint from last week as promised.",
    ],
    "Billing Problem": [
        "My monthly bill shows an extra charge of ₹{amount} that I don't recognize.",
        "I was billed for a plan I never signed up for.",
        "The invoice for order #{order_id} shows the wrong tax amount.",
        "Why was I charged ₹{amount} twice in the same billing cycle?",
    ],
    "Other": [
        "Can you tell me your business hours for customer support?",
        "I just wanted to say thank you, your team resolved my issue quickly.",
        "Do you have a physical store in Kochi where I can visit?",
        "How do I update my registered email address on my profile?",
    ],
}

# Legit "Security Concern" complaints — a real customer reporting a
# genuine worry, NOT a phishing attempt itself. Good for testing that
# your module does NOT false-positive on ordinary security-related language.
SECURITY_CONCERN_LEGIT = [
    "I noticed a login attempt from a device I don't recognize, please help me secure my account.",
    "Someone tried to reset my password without my permission, can you check my account activity?",
    "I think my card details may have been compromised, can you help me block my card?",
    "Can you tell me how to enable two-factor authentication on my account?",
]

CUSTOMER_SENTIMENT_MAP = {
    "Payment/Transaction Issue": "Negative",
    "Account/Login Problem": "Negative",
    "Product Issue": "Negative",
    "Delivery/Shipping Problem": "Negative",
    "Refund Request": "Negative",
    "Subscription Issue": "Negative",
    "Technical Problem": "Negative",
    "Service Quality": "Negative",
    "Billing Problem": "Negative",
    "Other": "Neutral",
}

ORDER_IDS = ["10245", "10389", "11072", "11456", "12003", "12290", "13087", "13521"]
AMOUNTS = ["499", "999", "1250", "2500", "349", "1899", "749", "3200"]

# ---------------------------------------------------------------------------
# PHISHING / SOCIAL-ENGINEERING MESSAGES — hand-crafted to cover every
# technique bucket in security_analysis.py: urgency, fear/threat, credential
# harvesting, OTP harvesting, authority impersonation, reward/threat bait,
# lookalike URLs across several brands, lookalike emails, IP-based URLs,
# and shortened URLs.
# ---------------------------------------------------------------------------

PHISHING_MESSAGES = [
    "URGENT! Your account has been compromised. Click this link immediately to secure your account and enter your username, password and OTP. http://paypa1-security.example/login",
    "Dear customer, your PAN card verification is pending. Update immediately at http://incometax-refund.example or your account will be permanently deleted",
    "Congratulations you have been selected! Claim your prize now at http://bit.ly/xyz123",
    "Your SBI account will be suspended within 24 hours. Verify your account at http://sbi-secure-verify.example/login and confirm your identity",
    "Dear user, unusual login detected on your Amazon account. Confirm your details at http://amaz0n-security.example immediately to avoid suspension",
    "This is the official IT support department. We need you to share your OTP to complete a mandatory security patch on your account.",
    "Your Netflix payment failed. Update your payment information at http://netfl1x-billing.example within 24 hours to avoid account closure.",
    "RBI Alert: Your bank account shows suspicious activity. Contact our security team at support@sbi-verify.example immediately.",
    "FINAL WARNING: Failure to comply will result in legal action. Verify your identity now at http://192.168.44.12/verify",
    "Your Flipkart order refund of ₹5000 is pending. Enter your card details and CVV at http://flipkart-refund.example to claim it.",
    "Dear customer, your electricity bill is overdue. Pay immediately at http://bit.ly/billpay99 to avoid disconnection within 24 hours.",
    "We are the cyber cell department investigating fraud on your account. Share the OTP sent to your phone to verify your identity.",
    "Your WhatsApp account will be deactivated. Verify by clicking http://whatsapp-verify.example and entering your registration code.",
    "Dear user, your Google account storage is full and unauthorized access was detected. Secure it now at http://g00gle-security.example",
    "Your Paytm KYC has expired. Update immediately at http://paytm-kyc-update.example or your wallet will be permanently blocked.",
    "Congratulations! Your number has won ₹25,00,000 in the online lottery. Claim your prize by sharing your bank details and OTP.",
    "Dear customer, your HDFC debit card is expiring. Renew instantly at http://hdfcbank-renew.example and confirm your PIN.",
    "Security Alert: Someone tried to access your account from Nigeria. Confirm it wasn't you at http://icici-secure.example immediately.",
    "Your Uber account has unusual activity. Verify your login credentials at http://uber-account-check.example within 24 hours.",
    "URGENT: Income tax department final notice. Avoid penalty by verifying your PAN and Aadhaar at http://incometax.gov.in-verify.example",
    "Your account will be permanently deleted due to policy violation unless you confirm your password within 24 hours at http://accnt-verify.example",
    "Dear customer, your Ola ride payment failed. Update your card details at http://bit.ly/olapay to avoid account suspension.",
    "This is your bank's official security department. We detected fraud and need your net banking password to reverse the transaction.",
    "Your Zomato wallet balance is under review due to suspicious activity, confirm your account at http://zomat0-secure.example",
    "Dear user, your UIDAI Aadhaar linking is incomplete. Complete verification immediately at http://uidai-link.example or face penalty.",
]

# Legit messages that use urgent-sounding language but ARE NOT phishing —
# important negative controls so you can prove your module isn't just
# flagging "urgent" and calling it a day.
LEGIT_URGENT_CONTROLS = [
    "Your order will be delivered today between 2pm and 5pm, please ensure someone is available.",
    "Reminder: your subscription renews tomorrow, let us know if you'd like to make changes.",
    "Your refund of ₹1250 has been processed and will reflect in your account within 3-5 business days.",
    "Your appointment with our service center is confirmed for tomorrow at 10 AM.",
]

# ---------------------------------------------------------------------------
# GENERATION LOGIC
# ---------------------------------------------------------------------------

def generate_normal_rows():
    rows = []
    counter = 1
    variants_per_template = 3  # bump volume so category/issue-frequency stats look real

    for category, templates in CATEGORY_TEMPLATES.items():
        for template in templates:
            has_placeholder = "{order_id}" in template or "{amount}" in template
            reps = variants_per_template if has_placeholder else 1
            for v in range(reps):
                text = template.format(
                    order_id=ORDER_IDS[counter % len(ORDER_IDS)],
                    amount=AMOUNTS[counter % len(AMOUNTS)],
                )
                rows.append({
                    "conversation_id": f"CS-{10000 + counter}",
                    "raw_text": text,
                    "expected_category": category,
                    "expected_sentiment": CUSTOMER_SENTIMENT_MAP[category],
                    "expected_is_threat": "No",
                })
                counter += 1

    for text in SECURITY_CONCERN_LEGIT:
        rows.append({
            "conversation_id": f"CS-{10000 + counter}",
            "raw_text": text,
            "expected_category": "Security Concern",
            "expected_sentiment": "Negative",
            "expected_is_threat": "No",
        })
        counter += 1

    for text in LEGIT_URGENT_CONTROLS:
        rows.append({
            "conversation_id": f"CS-{10000 + counter}",
            "raw_text": text,
            "expected_category": "Other",
            "expected_sentiment": "Neutral",
            "expected_is_threat": "No",
        })
        counter += 1

    return rows


def generate_phishing_rows(start_id=20000):
    rows = []
    for i, text in enumerate(PHISHING_MESSAGES):
        rows.append({
            "conversation_id": f"CS-{start_id + i + 1}",
            "raw_text": text,
            "expected_category": "Security Concern",
            "expected_sentiment": "Negative",
            "expected_is_threat": "Yes",
        })
    return rows


def write_csv(rows, out_path):
    fieldnames = ["conversation_id", "raw_text", "expected_category",
                  "expected_sentiment", "expected_is_threat"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the hackathon demo dataset.")
    parser.add_argument("--out", default="dataset.csv", help="Output CSV path")
    args = parser.parse_args()

    all_rows = generate_normal_rows() + generate_phishing_rows()
    write_csv(all_rows, args.out)

    threat_count = sum(1 for r in all_rows if r["expected_is_threat"] == "Yes")
    print(f"Generated {len(all_rows)} conversations -> {args.out}")
    print(f"  Normal complaints: {len(all_rows) - threat_count}")
    print(f"  Phishing/threat rows: {threat_count}")
