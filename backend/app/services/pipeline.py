"""
Main end-to-end pipeline: customer message -> intent -> evidence -> reply
-> escalation decision -> final structured result.

This is the single function the API layer (Phase 8) and any test/demo
script call. Keeping orchestration in one place makes the flow easy to
explain in an interview (assignment Section 53).
"""
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_BACKEND_DIR = _REPO_ROOT / "backend"
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_BACKEND_DIR))
from app.services.intent_classifier import IntentClassifier, IntentPrediction
from app.services.retrieval_service import RetrievalService
from app.services.escalation_engine import decide, EscalationDecision
from app.core.llm_provider import get_llm_provider, EvidenceCase

_intent_classifier = None
_retrieval_service = None
_llm_provider = None


def _lazy_init():
    global _intent_classifier, _retrieval_service, _llm_provider
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    if _llm_provider is None:
        _llm_provider = get_llm_provider()


@dataclass
class PipelineResult:
    customer_message: str
    predicted_intent: str
    intent_confidence: float
    intent_alternatives: list
    intent_reason: str
    historical_evidence: list
    generated_reply: str
    is_demo_mode: bool
    llm_provider: str
    grounding_note: str
    decision: str
    risk_level: str
    decision_reason: str


def analyze_message(customer_message: str) -> PipelineResult:
    _lazy_init()

    word_count = len(customer_message.split())

    intent_pred: IntentPrediction = _intent_classifier.classify(customer_message)
    evidence: List[EvidenceCase] = _retrieval_service.retrieve(customer_message, k=3)

    escalation: EscalationDecision = decide(
        intent=intent_pred.intent,
        intent_confidence=intent_pred.confidence,
        evidence=evidence,
        message_word_count=word_count,
    )

    generated = _llm_provider.generate_reply(
        customer_message=customer_message,
        intent=intent_pred.intent,
        evidence=evidence,
    )

    return PipelineResult(
        customer_message=customer_message,
        predicted_intent=intent_pred.intent,
        intent_confidence=intent_pred.confidence,
        intent_alternatives=intent_pred.alternatives,
        intent_reason=intent_pred.reason,
        historical_evidence=[asdict(e) for e in evidence],
        generated_reply=generated.reply_text,
        is_demo_mode=generated.is_demo_mode,
        llm_provider=generated.provider_name,
        grounding_note=generated.grounding_note,
        decision=escalation.decision,
        risk_level=escalation.risk_level,
        decision_reason=escalation.reason,
    )
