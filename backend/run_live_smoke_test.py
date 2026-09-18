"""
Run this against the REAL Groq API (needs a valid .env with GROQ_API_KEY)
to sanity-check actual model behavior. Unlike tests/test_extraction.py
(fully mocked, no network needed), this makes real calls and costs real
API usage.

Usage:
    python run_live_smoke_test.py                  # runs the 4 built-in samples
    python run_live_smoke_test.py --dataset         # runs the full sample dataset
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from customer_intelligence.groq_extraction import extract_customer_intelligence

BUILT_IN_SAMPLES = [
    "I was charged twice for my subscription this month, please refund the duplicate charge.",
    "URGENT! Your account has been compromised. Click this link immediately to secure your "
    "account and enter your username, password and OTP. http://paypa1-security.example/login",
    "Thanks so much, the replacement part arrived today and everything works perfectly now!",
    "My package was supposed to arrive 3 days ago and there's still no update on tracking.",
]


async def run_samples(texts: list[str]):
    total = len(texts)
    fallback_count = 0
    retry_count = 0

    for i, text in enumerate(texts, start=1):
        print(f"\n--- Sample {i}/{total} ---")
        print(f"Input: {text[:100]}{'...' if len(text) > 100 else ''}")
        result = await extract_customer_intelligence(text, conversation_id=f"smoke-{i}")
        if result.used_fallback:
            fallback_count += 1
            print(f"FALLBACK USED. Raw error: {result.raw_error}")
        elif result.attempts == 2:
            retry_count += 1
            print("Succeeded on corrective retry (first attempt was invalid).")
        print(f"Latency: {result.latency_ms:.0f}ms")
        print(result.data.model_dump_json(indent=2))

    print(f"\n=== Summary: {total} total, {retry_count} needed retry, {fallback_count} fell back ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", action="store_true", help="Run against data/sample_conversations.json instead of the 4 built-in samples")
    args = parser.parse_args()

    if args.dataset:
        with open("data/sample_conversations.json") as f:
            entries = json.load(f)
        texts = [e["raw_text"] for e in entries]
    else:
        texts = BUILT_IN_SAMPLES

    asyncio.run(run_samples(texts))
