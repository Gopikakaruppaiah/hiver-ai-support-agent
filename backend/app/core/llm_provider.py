"""
Provider-agnostic LLM interface.

get_llm_provider() picks a provider based on environment variables ONLY --
nothing else in the application needs to know or care which provider is
active. Swapping in a real API later means setting LLM_MODEL_NAME +
OPENAI_API_KEY/ANTHROPIC_API_KEY in .env; no code changes elsewhere.

DemoLLMProvider is the default (no key configured). It is fully
deterministic and clearly labels every response as DEMO MODE -- it must
never be mistaken for live LLM output (assignment Section 33).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from configs.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_MODEL_NAME


@dataclass
class EvidenceCase:
    example_id: str
    customer_text: str
    brand_text: str
    similarity: float


@dataclass
class GeneratedReply:
    reply_text: str
    is_demo_mode: bool
    provider_name: str
    evidence_used: List[EvidenceCase]
    grounding_note: str  # explains, internally, what the reply is/isn't based on


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate_reply(self, customer_message: str, intent: str,
                        evidence: List[EvidenceCase]) -> GeneratedReply:
        ...


class DemoLLMProvider(LLMProvider):
    """Deterministic, template-based provider. No network calls. No
    fabricated policy/refund/timeline commitments -- ever. If evidence is
    weak or absent, it says so instead of inventing a resolution."""
    name = "demo"

    # Resolution-pattern phrases mined (by hand, from real Phase-1/4 samples)
    # from how Uber_Support's agents actually phrase next steps -- these are
    # historical PATTERNS, not current guaranteed policy (assignment Sec 44).
    ACK_PHRASES = {
        "fare_billing_dispute": "I understand you're disputing a charge on your account.",
        "driver_cancellation_noshow": "I'm sorry your ride didn't go as expected.",
        "driver_behavior_safety": "I'm very sorry to hear about this experience with your driver.",
        "account_access_security": "I understand you're having trouble accessing your account.",
        "lost_item": "I understand you left an item during a trip.",
        "general_unresolved": "I understand you're following up on an unresolved issue.",
    }

    def generate_reply(self, customer_message: str, intent: str,
                        evidence: List[EvidenceCase]) -> GeneratedReply:
        ack = self.ACK_PHRASES.get(intent, "I understand you're reaching out about an issue with your account.")

        if not evidence or evidence[0].similarity < 0.15:
            body = ("I don't have enough similar historical cases to confidently suggest next "
                    "steps here, so I'm not going to guess. This will be routed to a human agent.")
            grounding_note = "No sufficiently similar historical evidence found (below similarity threshold)."
        else:
            # Synthesize -- do NOT copy the historical reply verbatim.
            top = evidence[0]
            body = (f"Based on how similar cases were handled before, the next step is typically "
                    f"for our team to follow up directly for more details before we can resolve this. "
                    f"I've flagged your message with that same context.")
            grounding_note = (f"Synthesized from {len(evidence)} retrieved historical case(s); "
                               f"most similar case (similarity={top.similarity:.2f}) resolved via: "
                               f"\"{top.brand_text[:100]}\"")

        reply_text = (
            f"[DEMO MODE — template-based, not a live LLM response]\n"
            f"{ack} {body}"
        )
        return GeneratedReply(
            reply_text=reply_text,
            is_demo_mode=True,
            provider_name=self.name,
            evidence_used=evidence,
            grounding_note=grounding_note,
        )


class OpenAIProvider(LLMProvider):
    """Stub -- not implemented until a real key is supplied. Wiring is
    intentionally isolated here so no other module needs to change when
    this becomes real."""
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_reply(self, customer_message: str, intent: str,
                        evidence: List[EvidenceCase]) -> GeneratedReply:
        raise NotImplementedError(
            "OpenAIProvider is wired but not implemented in this build. "
            "Set OPENAI_API_KEY + LLM_MODEL_NAME and implement the API call here."
        )


class AnthropicProvider(LLMProvider):
    """Stub -- same status as OpenAIProvider."""
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_reply(self, customer_message: str, intent: str,
                        evidence: List[EvidenceCase]) -> GeneratedReply:
        raise NotImplementedError(
            "AnthropicProvider is wired but not implemented in this build. "
            "Set ANTHROPIC_API_KEY + LLM_MODEL_NAME and implement the API call here."
        )


def get_llm_provider() -> LLMProvider:
    if ANTHROPIC_API_KEY and LLM_MODEL_NAME:
        return AnthropicProvider(ANTHROPIC_API_KEY, LLM_MODEL_NAME)
    if OPENAI_API_KEY and LLM_MODEL_NAME:
        return OpenAIProvider(OPENAI_API_KEY, LLM_MODEL_NAME)
    return DemoLLMProvider()
