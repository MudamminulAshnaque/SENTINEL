# SENTINEL — merged backend (customer_intelligence + security_analysis)

Production-ready backend for the full team `/analyze` contract. Built in
phases; all phases are done and tested. **Update:** the security stub has
been replaced with the real engine — see below.

## What's actually here

| Piece | Status |
|---|---|
| `customer_intelligence` extraction | **Real** — Groq-backed, validated, retried, logged |
| `security_analysis` | **Real** — `services/security_analysis_engine.py`, a rule-based phishing / social-engineering / threat-detection engine (URL + email analysis, lookalike-domain detection, credential/OTP-harvesting keyword buckets, risk scoring), wrapped by `services/security_analysis.py` for the async `/analyze` flow. No longer a stub. |
| `recommended_action` (unowned top-level field) | **Placeholder derivation** — combines priority + risk_level. Confirm ownership/logic with your team — this was never assigned to either of you in the contract doc. |

See `../README.md` (one level up) for the full merged-project overview,
dataset changes, and how to run this alongside the frontend.

## Setup in VS Code

1. Open this folder in VS Code.
2. Terminal: `python -m venv venv`
3. Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (macOS/Linux)
4. `Ctrl+Shift+P` → "Python: Select Interpreter" → pick the `./venv` one.
5. `pip install -r requirements.txt`
6. `cp .env.example .env` and put your real Groq key in `.env`. It's gitignored — never commit it.

## Running things

**Start the API server:**
```
uvicorn main:app --reload
```
Then POST to `http://127.0.0.1:8000/analyze`:
```
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "CS-10245", "raw_text": "URGENT! Your account has been compromised..."}'
```
Check health: `curl http://127.0.0.1:8000/health`

Interactive API docs (FastAPI auto-generates this): `http://127.0.0.1:8000/docs`

**Run the mocked test suite (no API key needed, no network, fast):**
```
pytest tests/ -v
```
16 tests, all passing as of this build — covers schema validation, retry
logic, fallback logic, and health checks, all without touching the real
Groq API.

**Run a REAL smoke test against Groq (uses your API key, costs real usage):**
```
python run_live_smoke_test.py                # 4 built-in samples
python run_live_smoke_test.py --dataset       # all 30 samples in data/sample_conversations.json
```
This is the one that actually proves the prompt + retry logic works
against a live model — the pytest suite mocks Groq entirely.

**Run with Docker:**
```
docker build -t omnishield-nlp .
docker run -e GROQ_API_KEY=your_key -p 8000:8000 omnishield-nlp
```

## Project structure

```
backend/
├── main.py                          # FastAPI app, /analyze + /health
├── logging_config.py                # structured JSON logging setup
├── schemas/
│   └── customer_intelligence.py     # Pydantic contract model
├── services/
│   ├── groq_extraction.py           # prompt, call, retry, fallback, backoff
│   ├── security_analysis_engine.py  # REAL phishing/social-engineering engine (no deps, no API key)
│   └── security_analysis.py         # async wrapper main.py calls, delegates to the engine above
├── data/
│   └── sample_conversations.json    # 135-entry dataset (30 original + 105 merged in)
├── tests/
│   ├── test_schema.py               # schema validation tests (mocked, no network)
│   └── test_extraction.py           # retry/fallback/health tests (mocked, no network)
├── tools/                           # offline dev/demo tools for the security engine
│   ├── dataset.csv                  # labeled dataset the 105 extra sample conversations came from
│   ├── generate_dataset.py          # regenerate/extend that dataset
│   ├── run_batch.py                 # batch-run the engine over any CSV, prints risk distribution
│   └── security_api.py              # standalone FastAPI wrapper around the engine alone
├── run_live_smoke_test.py           # Manual script for REAL Groq calls
├── requirements.txt
├── Dockerfile / .dockerignore
├── .env.example
└── .gitignore
```

## How the reliability layers fit together

There are two independent kinds of "retry" in `groq_extraction.py` — don't
conflate them when debugging:

1. **Network-layer retry** (`_call_groq_with_backoff`): handles a single
   message exchange failing due to timeout, rate limit, connection drop,
   or a Groq 5xx. Retries with exponential backoff (1s, 2s...), invisible
   to the rest of the pipeline. Auth/permission/bad-request errors are
   NOT retried here — they're config problems, not transient blips.
2. **Semantic retry** (`extract_customer_intelligence`): handles the call
   *succeeding* but the model's JSON failing schema validation. Sends the
   model its own bad output plus the exact Pydantic error, asks for a fix.

If both a network retry AND a semantic retry exhaust, the function returns
a safe fallback object (`category: Other`, `priority: Medium`,
`resolution_status: Unresolved`) rather than raising — so one bad message
never takes down the whole `/analyze` call. It only ever raises
`ExtractionError` for a genuinely broken deployment (missing/invalid API
key), because silently falling back there would mask the whole service
being unconfigured.

Every extraction call — success, retry-recovery, or fallback — is logged
as a single structured JSON line via `logging_config.py`, including
`conversation_id`, `latency_ms`, and which path was taken. No external
logging service required; pipe stdout into whatever aggregator you use.

## What I could NOT verify from this environment

Being upfront about this since it matters for a "production ready" claim:

- **No real Groq API call has been made.** This build environment can't
  reach `api.groq.com` and has no API key. Everything Groq-related was
  verified by mocking `_call_groq_with_backoff` and asserting on the
  resulting code paths (16 passing pytest tests) — the actual prompt
  quality, enum-accuracy, and whether `llama-3.1-70b-versatile` is still
  a live model name on your account are **untested**. Run
  `run_live_smoke_test.py` yourself before trusting this in a demo.
- **Model name may be stale.** Groq rotates available models. Verify
  `MODEL` in `services/groq_extraction.py` against your Groq console.
- **`recommended_action` logic is a guess**, not a team-confirmed spec —
  flag this with Person 2/3 before the demo.

## Still genuinely open (not bugs, just unbuilt scope)

- Rate limiting / auth on the `/analyze` endpoint itself (currently open —
  fine for a hackathon demo, not fine for a real production deploy).
- No persistence layer — nothing is stored; every call is stateless.
- No CI config (GitHub Actions etc.) wired up to auto-run `pytest` on push.
