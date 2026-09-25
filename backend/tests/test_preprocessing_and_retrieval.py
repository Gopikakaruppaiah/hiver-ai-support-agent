import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "evaluation" / "baselines"))
sys.path.insert(0, str(_REPO_ROOT / "backend"))


def test_clean_text_strips_urls_and_whitespace():
    from scripts.prepare_data import clean_text
    assert clean_text("hello   world https://t.co/abc123  ") == "hello world"


def test_eats_keyword_heuristic_flags_food_terms():
    from scripts.prepare_data import is_probably_eats
    assert is_probably_eats("my food order never arrived") is True
    assert is_probably_eats("my driver cancelled the ride") is False


def test_pseudo_labeler_safety_priority_over_generic_words():
    from pseudo_labeler import classify
    # "unsafe" should win even if message also loosely mentions other terms
    assert classify("the driver was driving unsafely and scared me", n_words=8) == "driver_behavior_safety"


def test_pseudo_labeler_billing_keywords():
    from pseudo_labeler import classify
    assert classify("I was charged twice for my trip, need a refund", n_words=9) == "fare_billing_dispute"


def test_pseudo_labeler_account_security_keywords():
    from pseudo_labeler import classify
    assert classify("my account got hacked and I cannot log in", n_words=9) == "account_access_security"


def test_pseudo_labeler_falls_back_to_general_unresolved():
    from pseudo_labeler import classify
    assert classify("hi", n_words=1) == "general_unresolved"


def test_retrieval_service_returns_ranked_results():
    from app.services.retrieval_service import RetrievalService
    svc = RetrievalService()
    results = svc.retrieve("I was charged twice for my ride", k=3)
    assert len(results) == 3
    # results should be sorted by descending similarity
    sims = [r.similarity for r in results]
    assert sims == sorted(sims, reverse=True)


def test_intent_classifier_returns_valid_distribution():
    from app.services.intent_classifier import IntentClassifier
    clf = IntentClassifier()
    pred = clf.classify("my driver never showed up after 20 minutes")
    assert pred.intent in clf.classes
    assert 0.0 <= pred.confidence <= 1.0
    assert len(pred.alternatives) == 2
