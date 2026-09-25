import sys
from pathlib import Path
from dataclasses import asdict

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.services.pipeline import analyze_message

TEST_MESSAGES = [
    "I was charged twice for my ride yesterday, can you refund the extra charge?",
    "My driver cancelled on me after waiting 20 minutes, this happens every time",
    "the driver was driving so unsafely I was scared for my life, nearly hit another car",
    "my account got hacked, someone is using it and I can't log in",
    "I left my phone in the car after my last trip, how do I get it back",
    "worst app ever",
    "??",
    "hi",
]

for msg in TEST_MESSAGES:
    result = analyze_message(msg)
    print("=" * 90)
    print(f"CUSTOMER MESSAGE: {msg}")
    print(f"INTENT: {result.predicted_intent}  (confidence={result.intent_confidence:.0%})")
    print(f"  reason: {result.intent_reason}")
    print(f"  alternatives: {result.intent_alternatives}")
    print(f"EVIDENCE ({len(result.historical_evidence)} cases):")
    for e in result.historical_evidence:
        print(f"  - sim={e['similarity']:.2f} | {e['customer_text'][:80]}")
    print(f"REPLY: {result.generated_reply}")
    print(f"  grounding: {result.grounding_note}")
    print(f"DECISION: {result.decision}  (risk={result.risk_level})")
    print(f"  reason: {result.decision_reason}")
