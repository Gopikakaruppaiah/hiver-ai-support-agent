from typing import List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AlternativeIntent(BaseModel):
    intent: str
    confidence: float


class EvidenceCaseOut(BaseModel):
    example_id: str
    customer_text: str
    brand_text: str
    similarity: float


class AnalyzeResponse(BaseModel):
    customer_message: str
    predicted_intent: str
    intent_confidence: float
    intent_alternatives: List[AlternativeIntent]
    intent_reason: str
    intent_caveat: str = ""
    historical_evidence: List[EvidenceCaseOut]
    generated_reply: str
    is_demo_mode: bool
    llm_provider: str
    grounding_note: str
    decision: str
    risk_level: str
    decision_reason: str


class BrandInfo(BaseModel):
    brand_name: str
    scope: str
    resolved_pairs_total: int
    retrieval_corpus_size: int
    golden_pool_size: int
    selection_rationale: str


class IntentInfo(BaseModel):
    name: str
    risk_level: str
    escalation_default: str


class IntentsResponse(BaseModel):
    intents: List[IntentInfo]
    taxonomy_note: str


class StatsResponse(BaseModel):
    raw_rows_total: int
    resolved_customer_brand_pairs: int
    excluded_as_probable_eats: int
    rides_scope_final_count: int
    golden_pool_size: int
    retrieval_corpus_size: int


class EvaluationSummaryResponse(BaseModel):
    status: str
    baseline_results: Optional[dict] = None
    caveat: str
