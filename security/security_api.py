"""
security_api.py
Standalone FastAPI wrapper around security_analysis.py.

Lets YOU test and demo your module independently, before Person 1's
customer-intelligence module or Person 3's dashboard exist. Person 3
can later either call this API directly, or just import your Python
function — this file is for your own convenience and demo-ability.

Run with (from inside the security/ folder):
    pip install fastapi uvicorn
    uvicorn security_api:app --reload

Then open http://127.0.0.1:8000/docs for an interactive test page
(FastAPI auto-generates this — great for a live demo, you can paste
text in a browser and show judges the JSON come back in real time).
"""

from fastapi import FastAPI
from pydantic import BaseModel

from security_analysis_engine import analyze_security

app = FastAPI(
    title="Security & Threat Detection Engine",
    description="Standalone phishing / social-engineering / risk analysis API "
                "for the AI-Powered Customer Support Intelligence hackathon project.",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    conversation_id: str = "CS-00000"
    text: str


class BatchAnalyzeRequest(BaseModel):
    conversations: list[AnalyzeRequest]


@app.get("/")
def health_check():
    return {"status": "ok", "service": "security-analysis-engine"}


@app.post("/analyze")
def analyze_single(request: AnalyzeRequest):
    """Analyze one message/conversation. Returns the security_analysis block."""
    result = analyze_security(request.text)
    return {
        "conversation_id": request.conversation_id,
        "security_analysis": result,
    }


@app.post("/analyze/batch")
def analyze_batch(request: BatchAnalyzeRequest):
    """
    Analyze many conversations in one call — this is what Person 3's
    dashboard should hit to populate the security KPIs (total threats
    detected, risk distribution, etc.) instead of calling /analyze in
    a loop.
    """
    results = []
    for convo in request.conversations:
        analysis = analyze_security(convo.text)
        results.append({
            "conversation_id": convo.conversation_id,
            "security_analysis": analysis,
        })

    # Quick aggregate stats — handy to hand straight to a dashboard chart
    risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    threats_detected = 0
    for r in results:
        risk_counts[r["security_analysis"]["risk_level"]] += 1
        if r["security_analysis"]["threat_detected"]:
            threats_detected += 1

    return {
        "total_conversations": len(results),
        "threats_detected": threats_detected,
        "risk_distribution": risk_counts,
        "results": results,
    }
