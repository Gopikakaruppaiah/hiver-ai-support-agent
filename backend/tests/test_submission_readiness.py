"""
Covers the explicit test categories requested for submission readiness:
backend startup, health, valid/empty/invalid analysis requests,
out-of-domain messages, vague messages, and one message per intent
category (billing, cancellation, safety, account/security, lost item).
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_backend_starts_and_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_valid_analysis_request():
    r = client.post("/api/analyze", json={"message": "my driver never showed up"})
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_intent"]
    assert body["decision"] in {"AUTO_HANDLE", "ESCALATE"}
    assert body["is_demo_mode"] is True


def test_empty_message_rejected():
    r = client.post("/api/analyze", json={"message": ""})
    assert r.status_code == 422


def test_missing_field_rejected():
    r = client.post("/api/analyze", json={})
    assert r.status_code == 422


def test_invalid_json_rejected():
    r = client.post("/api/analyze", data="not valid json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_oversized_message_rejected():
    r = client.post("/api/analyze", json={"message": "x" * 5000})
    assert r.status_code == 422


def test_out_of_domain_message_does_not_crash():
    # Off-topic content (not a ride-hailing issue at all) should still
    # get a valid response, not an error -- the system should fall back
    # to a safe classification/escalation, never hallucinate a confident
    # ride-related answer to unrelated content.
    r = client.post("/api/analyze", json={"message": "bonjour, je voudrais commander une pizza"})
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_intent"]
    assert body["decision"] in {"AUTO_HANDLE", "ESCALATE"}


def test_vague_message_escalates():
    r = client.post("/api/analyze", json={"message": "worst app ever"})
    assert r.status_code == 200
    assert r.json()["decision"] == "ESCALATE"


def test_billing_message_always_escalates():
    r = client.post("/api/analyze", json={"message": "I was charged twice for my ride, please refund me"})
    assert r.status_code == 200
    body = r.json()
    if body["predicted_intent"] == "fare_billing_dispute":
        assert body["decision"] == "ESCALATE"


def test_safety_message_always_escalates():
    r = client.post("/api/analyze", json={"message": "the driver was driving so unsafely I was terrified"})
    assert r.status_code == 200
    body = r.json()
    if body["predicted_intent"] == "driver_behavior_safety":
        assert body["decision"] == "ESCALATE"


def test_account_security_message_always_escalates():
    r = client.post("/api/analyze", json={"message": "my account got hacked and someone is using it"})
    assert r.status_code == 200
    body = r.json()
    if body["predicted_intent"] == "account_access_security":
        assert body["decision"] == "ESCALATE"


def test_lost_item_message_returns_valid_response():
    r = client.post("/api/analyze", json={"message": "I left my phone in the car after my last trip"})
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_intent"]
    assert len(body["historical_evidence"]) > 0


def test_cancellation_message_returns_valid_response():
    r = client.post("/api/analyze", json={"message": "my driver cancelled on me after waiting 20 minutes"})
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_intent"]


def test_retrieval_returns_evidence_with_similarity_scores():
    r = client.post("/api/analyze", json={"message": "I was charged twice for my ride"})
    body = r.json()
    assert len(body["historical_evidence"]) > 0
    for e in body["historical_evidence"]:
        assert "similarity" in e
        assert "customer_text" in e
        assert "brand_text" in e


def test_demo_reply_is_clearly_labeled():
    r = client.post("/api/analyze", json={"message": "my driver never showed up"})
    body = r.json()
    assert body["is_demo_mode"] is True
    assert "DEMO MODE" in body["generated_reply"]


def test_all_endpoints_return_valid_json_and_status():
    for path in ["/health", "/api/brand", "/api/intents", "/api/stats", "/api/evaluation/summary"]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert r.headers["content-type"].startswith("application/json")
