import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.services.escalation_engine import decide, MIN_WORD_COUNT
from app.core.llm_provider import EvidenceCase


def _evidence(sim):
    return [EvidenceCase(example_id="X", customer_text="t", brand_text="r", similarity=sim)]


def test_always_escalate_intents_override_everything():
    for intent in ["fare_billing_dispute", "driver_behavior_safety", "account_access_security"]:
        result = decide(intent=intent, intent_confidence=0.99, evidence=_evidence(0.9),
                         message_word_count=20)
        assert result.decision == "ESCALATE"
        assert result.risk_level == "high"


def test_short_message_always_escalates():
    result = decide(intent="driver_cancellation_noshow", intent_confidence=0.99,
                     evidence=_evidence(0.9), message_word_count=MIN_WORD_COUNT - 1)
    assert result.decision == "ESCALATE"


def test_low_confidence_escalates():
    result = decide(intent="lost_item", intent_confidence=0.2, evidence=_evidence(0.9),
                     message_word_count=20)
    assert result.decision == "ESCALATE"


def test_weak_evidence_escalates():
    result = decide(intent="lost_item", intent_confidence=0.9, evidence=_evidence(0.01),
                     message_word_count=20)
    assert result.decision == "ESCALATE"


def test_no_evidence_escalates():
    result = decide(intent="lost_item", intent_confidence=0.9, evidence=[],
                     message_word_count=20)
    assert result.decision == "ESCALATE"


def test_auto_handle_when_all_conditions_met():
    result = decide(intent="lost_item", intent_confidence=0.9, evidence=_evidence(0.7),
                     message_word_count=20)
    assert result.decision == "AUTO_HANDLE"
    assert result.risk_level == "low"


def test_pipeline_smoke():
    from app.services.pipeline import analyze_message
    result = analyze_message("I was charged twice for my ride, please refund me")
    assert result.predicted_intent in {
        "fare_billing_dispute", "driver_cancellation_noshow", "driver_behavior_safety",
        "account_access_security", "lost_item", "general_unresolved",
    }
    assert result.decision in {"AUTO_HANDLE", "ESCALATE"}
    assert result.is_demo_mode is True
    assert "[DEMO MODE" in result.generated_reply
    # financial intent must always escalate, regardless of confidence
    if result.predicted_intent == "fare_billing_dispute":
        assert result.decision == "ESCALATE"
