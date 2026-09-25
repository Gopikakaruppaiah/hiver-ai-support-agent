# Would a real LLM provider materially improve this system?

**Status: PRELIMINARY reasoning based on what's observable now — NOT a
final verdict.** The definitive answer requires the pending evaluation
(human-labeled golden set + real LLM-as-judge scores + human-vs-LLM
agreement), none of which exist yet. This document reasons from what the
current DEMO MODE output and pipeline structure already show.

## Where a real LLM would likely help

1. **Reply specificity.** `DemoLLMProvider`'s output is a fixed template
   per intent plus one boilerplate sentence referencing the top evidence
   case. Real examples of its output are genuinely generic — "the next
   step is typically for our team to follow up directly for more
   details." A real LLM could synthesize something that actually
   references the *specific* content of the customer's message (e.g.
   which fare, which trip) instead of a category-level template.
2. **The `general_unresolved` catch-all (~68-78% of examples by different
   labeling passes).** This is where a real LLM's language understanding
   would matter most — distinguishing a vague complaint that's actually a
   billing issue in disguise from genuine noise ("hi", "??"). A rule/regex
   approach or TF-IDF classifier structurally cannot do this well; an LLM
   reading the message in context plausibly could.
3. **Multi-intent messages** (Section 46 of the assignment) — the current
   system has no real handling for these beyond an `OTHER_MULTI_INTENT`
   annotation-tool option; a real LLM could plausibly decompose and
   address (or correctly flag) compound issues.

## Where a real LLM probably would NOT help much

1. **Escalation safety for the always-escalate intents** (fare/billing,
   safety, account security). These escalate unconditionally by design
   (D10) regardless of model confidence — an LLM's fluency doesn't change
   a rule that intentionally ignores confidence for these categories.
2. **Retrieval quality.** The bottleneck found in Phase 5 (D8) is in how
   *messages are matched to historical evidence*, not in how the reply is
   phrased once evidence is retrieved. A better LLM writing from
   already-irrelevant evidence would still produce an ungrounded reply —
   it would need to be paired with better retrieval (a real
   sentence-transformer, not reachable here) to compound in value.
3. **The core taxonomy/labeling problem.** No LLM changes the fact that
   56% (78% in the pseudo-labeled corpus) of this brand's traffic seems to
   be low-information, ambiguous, or off-topic. That's a property of the
   data and the current taxonomy's catch-all design, not something
   reply-generation quality fixes.

## What would actually settle this

- Real LLM-as-judge scores (`evaluation/judges/llm_judge.py` is wired,
  waiting on a provider implementation) on the same messages currently
  served by `DemoLLMProvider`, compared head-to-head.
- Human-vs-LLM judge agreement (Section 24) on 30-50 examples, to confirm
  the judge itself is trustworthy before trusting its verdict on reply
  quality.
- The human-labeled golden set, to know whether the classification/
  retrieval bottleneck (which an LLM can't fix on its own) or the reply-
  generation bottleneck (which it can) is the bigger factor in overall
  system quality.

**Preliminary conclusion**: a real LLM would very likely improve reply
*fluency and specificity*, but is unlikely by itself to fix the bigger
structural gaps this project has already found (retrieval imprecision on
paraphrased issues, the oversized ambiguous-intent bucket). It should be
treated as a complement to fixing retrieval and getting real labels, not
a substitute for either.
