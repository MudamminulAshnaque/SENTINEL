# security/ — Phishing / Social-Engineering Detection Engine

Rule-based threat detection module (Person 2's part of the contract). No
network calls, no API key — pure Python stdlib for the detection logic
itself.

## What's here

| File | What it does |
|---|---|
| `security_analysis_engine.py` | The actual engine. `analyze_security(text)` returns the full detection block: lookalike-domain/email detection (Levenshtein distance), URL shorteners, IP-based URLs, suspicious paths, and six weighted keyword buckets (urgency, fear/threat, credential harvesting, OTP harvesting, authority impersonation, reward/threat bait). Also exposes `analyze_conversation()` for multi-turn message threads and `decide_action()` for the combined recommended-action logic. |
| `security_analysis.py` | Thin async wrapper (`extract_security_analysis`) so the engine plugs into the backend's `asyncio.gather` alongside the Groq-backed customer_intelligence call. |
| `security_api.py` | Standalone FastAPI wrapper so you can demo/test this module entirely on its own, before the rest of the team's pieces exist. |
| `run_batch.py` | CLI batch runner — point it at a CSV (`conversation_id, raw_text` columns) and get a risk-level summary plus full JSON results. |
| `generate_dataset.py` | Generates the synthetic demo dataset (normal support complaints across 10 categories + phishing/social-engineering examples + legit "urgent-sounding but not phishing" negative controls). |

## Running it

```bash
cd security
pip install -r requirements.txt        # only needed for security_api.py

# As a standalone API:
uvicorn security_api:app --reload      # see http://127.0.0.1:8000/docs

# As a batch job over the shared dataset:
python run_batch.py ../data/dataset.csv --out results.json

# Regenerate the demo dataset:
python generate_dataset.py --out ../data/dataset.csv

# Quick self-test (no server needed):
python security_analysis_engine.py
```

## Using it from the backend

`security_analysis.py` is imported by the integration layer in `../backend/`
as `security.security_analysis` — the repo root is on `sys.path` there, so
this module works as an ordinary sibling package. No changes needed here if
the backend structure changes; this folder is self-contained.

See `../docs/json_schema_contract.md` for the exact JSON shape this module
contributes to the merged `/analyze` response.
