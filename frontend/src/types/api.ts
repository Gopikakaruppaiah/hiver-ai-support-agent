export interface AlternativeIntent {
  intent: string
  confidence: number
}

export interface EvidenceCase {
  example_id: string
  customer_text: string
  brand_text: string
  similarity: number
}

export interface AnalyzeResponse {
  customer_message: string
  predicted_intent: string
  intent_confidence: number
  intent_alternatives: AlternativeIntent[]
  intent_reason: string
  intent_caveat: string
  historical_evidence: EvidenceCase[]
  generated_reply: string
  is_demo_mode: boolean
  llm_provider: string
  grounding_note: string
  decision: 'AUTO_HANDLE' | 'ESCALATE'
  risk_level: 'low' | 'medium' | 'high' | 'unknown'
  decision_reason: string
}

export interface BrandInfo {
  brand_name: string
  scope: string
  resolved_pairs_total: number
  retrieval_corpus_size: number
  golden_pool_size: number
  selection_rationale: string
}
