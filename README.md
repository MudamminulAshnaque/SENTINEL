# sentinel

AI-powered customer support intelligence: classifies and prioritizes support
conversations (Person 1), detects phishing / social-engineering attempts in
the same messages (Person 2), and surfaces both in a live dashboard
(Person 3).

## Layout

```
sentinel/
├── security/              Person 2 — phishing / social-engineering detection engine
├── customer_intelligence/ Person 1 — Groq-backed classification + schema
├── dashboard/              Person 3 — React/Vite/TypeScript frontend
├── backend/                Integration layer: FastAPI app that ties the above
│                           together into the shared /analyze contract + the
│                           dashboard's own API
├── data/                   Shared datasets (dataset.csv, sample_conversations.json)
├── docs/
│   └── json_schema_contract.md   The full contract every module builds against
└── README.md
```

`security/` and `customer_intelligence/` are self-contained Python packages
with no dependency on `backend/`. `backend/` imports both as sibling
packages to build the merged `/analyze` endpoint the `dashboard/` calls.

## Running the whole thing

**1. Backend** (needs a [Groq API key](https://console.groq.com)):
```bash
cd backend
python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env          # paste your GROQ_API_KEY in here
uvicorn main:app --reload     # http://127.0.0.1:8000 — /docs for interactive API
```

**2. Dashboard** (separate terminal):
```bash
cd dashboard
npm install
npm run dev                   # http://localhost:5173
```

**3. Run tests:**
```bash
cd backend && pytest tests/ -v          # 30 tests, fully mocked, no API key needed
```

**4. Just the security engine, standalone** (no API key, no other module needed):
```bash
cd security
pip install -r requirements.txt
uvicorn security_api:app --reload       # http://127.0.0.1:8000/docs
# or:
python run_batch.py ../data/dataset.csv
```

See each folder's own README for more detail, and `docs/json_schema_contract.md`
for the exact response shape the whole team builds against.

## Docker

Build from the repo root (not from inside `backend/`), since the backend
image needs the sibling `customer_intelligence/` and `security/` packages:
```bash
docker build -t omnishield-nlp -f backend/Dockerfile .
docker run -e GROQ_API_KEY=your_key -p 8000:8000 omnishield-nlp
```
