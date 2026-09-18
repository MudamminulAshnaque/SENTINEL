"""
run_batch.py
Command-line batch runner for security_analysis.py.

Point it at a CSV with columns: conversation_id, raw_text
(this matches the "minimum dataset needs" your team agreed on).

Usage:
    python run_batch.py sample_conversations.csv
    python run_batch.py sample_conversations.csv --out results.json

Outputs:
    - Prints a risk-level summary to the terminal (quick sanity check)
    - Writes full per-conversation results to a JSON file
"""

import argparse
import csv
import json
import sys

from security_analysis_engine import analyze_security


def load_conversations(csv_path: str):
    conversations = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"conversation_id", "raw_text"}
        if not required.issubset(reader.fieldnames or []):
            sys.exit(
                f"CSV must have columns {required}. "
                f"Found: {reader.fieldnames}"
            )
        for row in reader:
            conversations.append({
                "conversation_id": row["conversation_id"],
                "raw_text": row["raw_text"],
            })
    return conversations


def run(csv_path: str, out_path: str):
    conversations = load_conversations(csv_path)
    results = []
    risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    threats_detected = 0

    for convo in conversations:
        analysis = analyze_security(convo["raw_text"])
        risk_counts[analysis["risk_level"]] += 1
        if analysis["threat_detected"]:
            threats_detected += 1
        results.append({
            "conversation_id": convo["conversation_id"],
            "raw_text": convo["raw_text"],
            "security_analysis": analysis,
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nProcessed {len(conversations)} conversations.")
    print(f"Threats detected: {threats_detected}")
    print("Risk distribution:")
    for level, count in risk_counts.items():
        print(f"  {level:9s}: {count}")
    print(f"\nFull results written to: {out_path}")

    # Show the top 3 highest-risk conversations — useful to eyeball whether
    # your detection logic is catching the right things before demo day
    ranked = sorted(results, key=lambda r: r["security_analysis"]["risk_score"], reverse=True)
    print("\nTop 3 highest-risk conversations:")
    for r in ranked[:3]:
        print(f"  [{r['security_analysis']['risk_level']}] "
              f"{r['conversation_id']}: {r['raw_text'][:80]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch-run security analysis over a CSV.")
    parser.add_argument("csv_path", help="Path to input CSV (columns: conversation_id, raw_text)")
    parser.add_argument("--out", default="security_results.json", help="Output JSON path")
    args = parser.parse_args()
    run(args.csv_path, args.out)
