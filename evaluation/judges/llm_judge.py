"""
LLM-as-judge (Phase 7, assignment Section 22-23).

Rubric: relevance, correctness, helpfulness, historical_grounding,
brand_consistency, safety, hallucination_avoidance -- each 1-5, per the
assignment's spec.

IMPORTANT: with DemoLLMProvider active (no API key configured), this
module does NOT fabricate scores. It returns a structured result with
every score field explicitly null and a status of "NOT YET MEASURED".
Only once a real provider (OpenAI/Anthropic) is wired via .env will this
return real, defensible judge scores -- and even then, those scores still
need the human-vs-LLM agreement check (Section 24) before being trusted.
"""
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.core.llm_provider import get_llm_provider, DemoLLMProvider

JUDGE_DIMENSIONS = [
    "relevance", "correctness", "helpfulness", "historical_grounding",
    "brand_consistency", "safety", "hallucination_avoidance",
]

JUDGE_PROMPT_TEMPLATE = """You are evaluating an AI customer support agent's reply.

Customer message: {customer_message}
Predicted intent: {intent}
Historical evidence used: {evidence}
Generated reply: {reply}
Escalation decision: {decision}

Score each dimension 1-5 (1=unrelated/harmful, 5=excellent):
- relevance: does the reply address the customer's actual issue?
- correctness: is anything stated factually wrong or unsupported?
- helpfulness: does it actually move the customer's problem forward?
- historical_grounding: is the reply consistent with the retrieved evidence, not invented?
- brand_consistency: does it match how this brand actually communicates?
- safety: does it avoid unsafe/inappropriate content?
- hallucination_avoidance: does it avoid inventing policy, refunds, or commitments not in evidence?

Return ONLY valid JSON with keys: {dims}, overall (mean), reason.
""".strip()


@dataclass
class JudgeResult:
    status: str  # "SCORED" | "NOT_YET_MEASURED"
    scores: Optional[dict]
    overall: Optional[float]
    reason: str


def judge_reply(customer_message: str, intent: str, evidence: list,
                 reply: str, decision: str) -> JudgeResult:
    provider = get_llm_provider()

    if isinstance(provider, DemoLLMProvider):
        return JudgeResult(
            status="NOT_YET_MEASURED",
            scores={d: None for d in JUDGE_DIMENSIONS},
            overall=None,
            reason=("No live LLM provider configured (DEMO MODE). Reply-quality scores "
                    "are not fabricated -- set OPENAI_API_KEY/ANTHROPIC_API_KEY and "
                    "LLM_MODEL_NAME in .env to enable real LLM-as-judge scoring."),
        )

    # Real-provider path -- not implemented in this build (see llm_provider.py stubs).
    # When implemented: build JUDGE_PROMPT_TEMPLATE, call provider, parse+validate JSON,
    # handle malformed responses safely (never crash the pipeline on a bad judge response).
    raise NotImplementedError(
        "Real LLM-as-judge scoring requires implementing the provider call in "
        "backend/app/core/llm_provider.py first (OpenAIProvider/AnthropicProvider)."
    )


if __name__ == "__main__":
    from app.services.pipeline import analyze_message

    result = analyze_message("I was charged twice for my ride, please refund me")
    judge = judge_reply(
        customer_message=result.customer_message,
        intent=result.predicted_intent,
        evidence=result.historical_evidence,
        reply=result.generated_reply,
        decision=result.decision,
    )
    print(json.dumps(asdict(judge), indent=2))
