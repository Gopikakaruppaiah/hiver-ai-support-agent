"""
Escalation / auto-handle decision engine.

Deliberately simple and fully explainable -- every decision traces to one
or more named rules, no black-box scoring. Thresholds below are reasonable
STARTING POINTS based on the taxonomy's risk levels (docs/intent_taxonomy.md),
NOT tuned against human-labeled data yet (that requires the golden set --
see decision_log.md D3/D6). This is stated explicitly rather than claiming
false precision (assignment Section 47).
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BACKEND_DIR))
from app.core.llm_provider import EvidenceCase

# Intents that are ALWAYS escalated regardless of confidence/evidence,
# because the downside of a wrong auto-handle is severe (financial/safety/
# security) -- matches docs/intent_taxonomy.md risk levels.
ALWAYS_ESCALATE_INTENTS = {
    "fare_billing_dispute": "financial commitments should not be auto-promised without human review",
    "driver_behavior_safety": "safety/legal issues are never auto-handled in this system",
    "account_access_security": "account security should not be auto-resolved",
    "general_unresolved": "insufficient information to safely auto-handle",
}

MIN_INTENT_CONFIDENCE = 0.55  # heuristic starting point, NOT YET TUNED
MIN_RETRIEVAL_SIMILARITY = 0.15  # heuristic starting point, NOT YET TUNED
MIN_WORD_COUNT = 5  # messages shorter than this are treated as ambiguous


@dataclass
class EscalationDecision:
    decision: str  # "AUTO_HANDLE" | "ESCALATE"
    risk_level: str  # "low" | "medium" | "high"
    reason: str


def decide(intent: str, intent_confidence: float, evidence: List[EvidenceCase],
           message_word_count: int) -> EscalationDecision:

    if message_word_count < MIN_WORD_COUNT:
        return EscalationDecision(
            decision="ESCALATE", risk_level="unknown",
            reason=f"Message is very short ({message_word_count} words) -- too little "
                   f"information to classify or resolve safely.",
        )

    if intent in ALWAYS_ESCALATE_INTENTS:
        return EscalationDecision(
            decision="ESCALATE", risk_level="high",
            reason=f"Intent '{intent}' is always escalated: {ALWAYS_ESCALATE_INTENTS[intent]}.",
        )

    if intent_confidence < MIN_INTENT_CONFIDENCE:
        return EscalationDecision(
            decision="ESCALATE", risk_level="medium",
            reason=f"Intent confidence ({intent_confidence:.0%}) is below the "
                   f"{MIN_INTENT_CONFIDENCE:.0%} threshold.",
        )

    if not evidence or evidence[0].similarity < MIN_RETRIEVAL_SIMILARITY:
        top_sim = evidence[0].similarity if evidence else 0.0
        return EscalationDecision(
            decision="ESCALATE", risk_level="medium",
            reason=f"No sufficiently similar historical evidence (top similarity="
                   f"{top_sim:.2f}, threshold={MIN_RETRIEVAL_SIMILARITY}) to safely ground a reply.",
        )

    return EscalationDecision(
        decision="AUTO_HANDLE", risk_level="low",
        reason=(f"Intent '{intent}' is a low/medium-risk category, confidence "
                f"({intent_confidence:.0%}) meets threshold, and historical evidence "
                f"(top similarity={evidence[0].similarity:.2f}) is strong enough to ground a reply."),
    )
