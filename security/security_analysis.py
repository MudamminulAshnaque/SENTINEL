"""
Real security_analysis service (replaces the former hardcoded stub).

This wraps `analyze_security()` from `security_analysis_engine.py` — the
standalone Phishing / Social-Engineering / Threat Detection engine — behind
the exact async signature `main.py` already expects:

    async def extract_security_analysis(raw_text: str) -> dict

The engine itself is pure stdlib (no network, no API key), so it's wrapped
with `asyncio.to_thread` purely so it plays nicely inside `asyncio.gather`
alongside the Groq-backed customer_intelligence call in main.py — it does
not actually block on I/O, but this keeps the event loop responsive if the
engine ever grows to do something heavier.
"""

from __future__ import annotations

import asyncio

from .security_analysis_engine import analyze_security


async def extract_security_analysis(raw_text: str) -> dict:
    """Runs the real phishing / social-engineering detector on raw_text."""
    return await asyncio.to_thread(analyze_security, raw_text)
