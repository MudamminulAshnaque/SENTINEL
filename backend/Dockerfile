# Build from the REPO ROOT, not this folder, since main.py imports the
# sibling customer_intelligence/ and security/ packages:
#   docker build -t omnishield-nlp -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY customer_intelligence/ customer_intelligence/
COPY security/ security/

WORKDIR /app/backend

# .env is NOT copied in (it's gitignored) — pass GROQ_API_KEY at runtime instead:
#   docker run -e GROQ_API_KEY=your_key -p 8000:8000 omnishield-nlp

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
