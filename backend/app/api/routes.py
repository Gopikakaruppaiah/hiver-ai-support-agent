import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from configs.config import BRAND_NAME
from app.services.pipeline import analyze_message
from app.schemas.schemas import (
    AnalyzeRequest, AnalyzeResponse, BrandInfo, IntentsResponse, IntentInfo,
    StatsResponse, EvaluationSummaryResponse, AlternativeIntent, EvidenceCaseOut,
)

router = APIRouter()

ALWAYS_ESCALATE = {"fare_billing_dispute", "driver_behavior_safety", "account_access_security", "general_unresolved"}
RISK_MAP = {
    "fare_billing_dispute": "high", "driver_cancellation_noshow": "low",
    "driver_behavior_safety": "high", "account_access_security": "high",
    "lost_item": "medium", "general_unresolved": "unknown",
}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        result = analyze_message(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    return AnalyzeResponse(
        customer_message=result.customer_message,
        predicted_intent=result.predicted_intent,
        intent_confidence=result.intent_confidence,
        intent_alternatives=[AlternativeIntent(**a) for a in result.intent_alternatives],
        intent_reason=result.intent_reason,
        historical_evidence=[EvidenceCaseOut(**e) for e in result.historical_evidence],
        generated_reply=result.generated_reply,
        is_demo_mode=result.is_demo_mode,
        llm_provider=result.llm_provider,
        grounding_note=result.grounding_note,
        decision=result.decision,
        risk_level=result.risk_level,
        decision_reason=result.decision_reason,
    )


@router.get("/api/brand", response_model=BrandInfo)
def brand():
    stats_path = _REPO_ROOT / "reports" / "data_pipeline_stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    return BrandInfo(
        brand_name=BRAND_NAME,
        scope="Ride-hailing only (Uber Eats messages excluded, see decision_log.md D2)",
        resolved_pairs_total=stats.get("resolved_customer_brand_pairs", 0),
        retrieval_corpus_size=stats.get("retrieval_corpus_size", 0),
        golden_pool_size=stats.get("golden_pool_size", 0),
        selection_rationale=(
            "Selected for single-domain size/cleanliness trade-off: 56K resolved pairs, "
            "99.8% structurally resolved, low template-dup rate. See docs/ and decision_log.md D1."
        ),
    )


@router.get("/api/intents", response_model=IntentsResponse)
def intents():
    return IntentsResponse(
        intents=[
            IntentInfo(name=name, risk_level=RISK_MAP[name],
                       escalation_default="ESCALATE" if name in ALWAYS_ESCALATE else "context-dependent")
            for name in RISK_MAP
        ],
        taxonomy_note="Full definitions with examples in docs/intent_taxonomy.md",
    )


@router.get("/api/stats", response_model=StatsResponse)
def stats():
    stats_path = _REPO_ROOT / "reports" / "data_pipeline_stats.json"
    if not stats_path.exists():
        raise HTTPException(status_code=404, detail="Pipeline stats not found -- run scripts/prepare_data.py first")
    s = json.loads(stats_path.read_text())
    return StatsResponse(
        raw_rows_total=s["raw_rows_total"],
        resolved_customer_brand_pairs=s["resolved_customer_brand_pairs"],
        excluded_as_probable_eats=s["excluded_as_probable_eats"],
        rides_scope_final_count=s["rides_scope_final_count"],
        golden_pool_size=s["golden_pool_size"],
        retrieval_corpus_size=s["retrieval_corpus_size"],
    )


@router.get("/api/evaluation/summary", response_model=EvaluationSummaryResponse)
def evaluation_summary():
    path = _REPO_ROOT / "reports" / "baseline_results.json"
    baseline_results = json.loads(path.read_text()) if path.exists() else None
    return EvaluationSummaryResponse(
        status="PARTIAL -- baselines computed vs pseudo-labels only; human golden-set evaluation PENDING",
        baseline_results=baseline_results,
        caveat=(
            "These metrics are evaluated against rule-based pseudo-labels, not human-verified "
            "ground truth. Run evaluation/annotation/annotate_golden.py to produce real labels, "
            "then re-run evaluation/baselines/run_baselines.py against them."
        ),
    )
