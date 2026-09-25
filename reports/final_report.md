# Report — Uber_Support AI Support Agent

## 1. Problem framing

**What "good" means for this brand**: an agent that correctly identifies
the customer's issue, grounds any reply in how Uber has actually resolved
similar cases before (not invented policy), and — critically for a brand
with real financial and safety exposure — escalates anything involving
money, safety, or account security rather than confidently auto-handling
it. Given ride-hailing's failure modes (wrong fare, unsafe driving, lost
items, hacked accounts), the cost of a wrong auto-handled reply is much
higher than the cost of an unnecessary escalation. The system is
deliberately biased toward escalation.

**What this system does**: classifies a message into one of 6 intents,
retrieves the most similar historical customer/agent exchanges via TF-IDF
cosine similarity, drafts a grounded (currently template-based/DEMO MODE)
reply, and applies a transparent, rule-based escalate/auto-handle
decision.

**What it deliberately does NOT build**: a live LLM integration (no API
key available in this environment — DEMO MODE only, clearly labeled), a
fine-tuned semantic embedding model (huggingface.co unreachable in the
dev sandbox — TF-IDF used instead, and empirically preferred after
spot-checks), and a validated accuracy number (no human labels exist yet
— every classification metric below is explicitly a proxy).

## 2. Data and methodology

- **Dataset**: Customer Support on Twitter (Kaggle), 2,811,774 raw rows.
- **Brand selection**: Uber_Support, chosen from measured evidence across
  6 candidate brands (pair-resolution rate, dup rate, sample quality) —
  see `decision_log.md` D1.
- **Scope**: ride-hailing only. Discovered mid-exploration that
  Uber_Support also handles Uber Eats; excluded via keyword heuristic
  (7,206 messages excluded, ~15% of the resolved-pair pool) — D2.
- **Cleaning**: URL stripping, whitespace normalization, exact-duplicate
  removal (1,913 dropped), minimum-length filter (1 dropped).
- **Intent discovery**: 2 rounds of TF-IDF + KMeans clustering (8
  clusters each), refined by stripping @mention noise between rounds,
  cross-checked against 40 manually-read real samples. Landed on 6
  intents including one explicit, large catch-all (`general_unresolved`)
  rather than forcing an artificially clean taxonomy — see
  `docs/intent_taxonomy.md`.
- **Train/test methodology**: golden pool of 300 examples reserved via
  stratified sampling (length bucket × risk-keyword presence) **before**
  any clustering, training, or indexing touched the data. Verified zero
  text overlap between golden pool and retrieval corpus via an explicit
  assertion in the pipeline script (not just a claim) — D3. A **fixed
  200-example golden evaluation set** was then derived from this 300-pool
  using the identical stratification methodology, proportionally scaled
  — D16. This is the set that gets annotated and used for all final
  metrics; the 300-pool is preserved separately, untouched.
- **Golden set**: 200 examples (`data/golden/golden_eval_200.csv`)
  prepared with `model_suggestion_intent`
  pre-filled by a rule-based labeler; `human_label_intent` column exists
  and is empty. **Human annotation has not been completed** — this is the
  single largest open item in the project.

## 3. System architecture

See `README.md` for the full diagram. Summary: FastAPI backend wraps a
4-stage pipeline (intent classify → TF-IDF retrieve → generate reply →
escalation decision); React/TS/Vite/Tailwind frontend (Support Console
page only) calls it via REST.

## 4. Results

### 4.1 Intent classification (⚠️ vs. pseudo-labels, not human ground truth)

| System | Accuracy | Macro P | Macro R | Macro F1 |
|---|---:|---:|---:|---:|
| Majority-class baseline | 78.0% | 0.13 | 0.17 | 0.15 |
| TF-IDF + Logistic Regression | 95.1% | 0.78 | 0.94 | 0.84 |

Full per-class report and confusion matrix:
`reports/baseline_results.json`, `reports/baseline2_confusion_matrix.csv`.

A "main semantic classifier" separate from the TF-IDF+LogReg baseline was
not built — see README §Baseline comparison for why.

### 4.2 Retrieval

No quantitative retrieval metrics (Recall@K, Precision@K, MRR) — these
require human relevance judgments that don't exist yet. **Qualitative**
finding, from direct side-by-side spot-checks
(`scripts/compare_retrieval.py`, `reports/embedding_model_card.md`):
TF-IDF cosine retrieval was **more precise** than spaCy word-vector
embeddings on this dataset, because short boilerplate-heavy tweets cause
word-averaging to collapse distinct issues into false similarity. TF-IDF
is the production retrieval method as a result (D8).

### 4.3 Reply quality

`NOT YET MEASURED`. The LLM-as-judge (`evaluation/judges/llm_judge.py`)
is fully implemented (prompt, rubric, JSON schema) but returns explicit
nulls when no live LLM provider is configured — verified by running it,
not just asserted (D11).

### 4.4 Escalation

Not formally evaluated against human labels (needs the golden set's
`human_escalation_label` field, currently empty). Qualitatively verified
via 8 hand-picked test messages spanning all 6 intents plus edge cases
(very short messages, ambiguous input) — all matched expected behavior
(financial/safety/security → escalate; strong-evidence routine issues →
auto-handle; short/ambiguous → escalate). See
`scripts/test_pipeline_demo.py` output.

## 5. Failure analysis (partial)

A full top-5 failure-mode analysis against real labeled failures isn't
possible yet — there's no ground truth to compare against. What can
honestly be reported from what's been observed so far:

1. **Circular pseudo-labels inflate the TF-IDF+LogReg number.** The
   labeler and the classifier key off the same words (e.g. "charged").
   Real example: any message containing "refund" is guaranteed to be
   pseudo-labeled `fare_billing_dispute`, which the TF-IDF classifier
   then trivially learns. Expected fix: re-evaluate against human labels,
   where lexical shortcuts won't automatically be correct.
2. **`general_unresolved` is a large, heterogeneous catch-all (~78% of
   pseudo-labels)** that likely bundles several real sub-intents (vague
   complaints, unanswered follow-ups, off-topic mentions). Real example:
   "worst app ever" and "??" and "hi" all land here despite being
   different situations. Hypothesis: the taxonomy needs either a 7th
   intent or better short-message handling; can't confirm without human
   review of a sample.
3. **Retrieval collapses on boilerplate for word-vector embeddings.**
   Real example: a "discounted rides for a charity event" query matched
   unrelated complaint boilerplate at 0.94+ similarity under spaCy
   embeddings. Root-caused and mitigated by switching primary retrieval
   to TF-IDF (D8), but TF-IDF itself will still struggle with true
   paraphrases that share no vocabulary.
4. **Eats-filtering heuristic has real false positives.** Example: "could
   you give me a discount on my food, I'm broke!" was excluded from the
   ride-hailing scope purely on the word "food" — may not actually be an
   Eats message. Unknown false-negative rate (Eats messages not caught by
   the keyword list) — not measured.
5. **Historical agent replies are themselves boilerplate**, e.g. "Send us
   a note here so our team can assist." This makes grounded generation
   harder to meaningfully differentiate from a template — the demo
   replies inherit this genericness honestly, but a real LLM would need
   explicit instruction to synthesize something more specific from the
   *pattern* of resolutions, not just echo the boilerplate phrasing.

## 6. What is misleading about my headline number?

If someone only reads "TF-IDF + Logistic Regression: 95.1% accuracy,"
here is what that number hides:

- **It is not evaluated against real ground truth.** It measures how well
  a TF-IDF classifier reproduces a keyword-regex labeler — not how well
  it identifies real customer intent. The regex rules and the classifier
  share almost the same feature space (both key on words like "charged,"
  "hacked," "unsafe"), so a large share of that 95.1% is the model
  learning to detect exact keywords it was implicitly told the answer
  from. This is closer to measuring "can a classifier reproduce a regex"
  than "can a classifier understand intent."
- **The label distribution is extremely imbalanced** (78% in one class),
  so a trivial majority-class baseline already gets 78% accuracy "for
  free." The 95.1% vs. 78.0% gap looks like a 17-point win, but macro-F1
  (0.84 vs. 0.15) is the more honest comparison, and even that is
  measured on the same circular labels.
- **The taxonomy itself has a large, admittedly fuzzy catch-all class**
  (`general_unresolved`), discovered from real clustering, not designed
  for classifier convenience — but its size means a model that's
  "good at spotting the 5 sharp categories and defaulting to catch-all
  otherwise" will score deceptively well without doing much intent
  discrimination on the hard, ambiguous cases that actually matter for
  escalation safety.
- **Retrieval "similarity" scores are not calibrated probabilities of
  relevance.** A 0.75 TF-IDF cosine similarity means two messages share a
  lot of vocabulary — it does not mean the retrieved historical
  resolution is actually the correct precedent for the current case.
- **Sample size and selection**: the golden evaluation set (fixed at 200)
  hasn't been
  human-labeled, so *no* number in this report has been checked against
  an actual human judgment yet. Every accuracy/F1/similarity figure here
  should be read as "what the code currently computes," not "how good
  this agent actually is."
- **Offline vs. production**: even once human-labeled, offline evaluation
  on historical Twitter data doesn't capture how customers phrase issues
  today, whether Uber's actual current policies match 2014-2017 agent
  behavior, or how the interface (not just the model) affects real
  outcomes.

## 7. What I would do with one more week

1. **Complete golden-set annotation** (the fixed 200-example set,
   `data/golden/golden_eval_200.csv`) —
   the single highest-leverage next step; unblocks every other honest
   metric in this report.
2. **Re-run all baselines against human labels**, and report the honest
   gap versus the pseudo-label numbers above.
3. **Wire a real LLM provider** (Anthropic or OpenAI) behind the existing
   `LLMProvider` interface — no other code changes needed — and get real
   LLM-as-judge scores plus a human-vs-LLM agreement analysis on 30-50
   examples.
4. **Tune escalation thresholds** (confidence=0.55, similarity=0.15,
   currently explicit "not yet tuned" placeholders) against real
   precision/recall on the human-labeled escalation field, prioritizing
   minimizing the missed-escalation rate.
5. **Investigate the `general_unresolved` catch-all** with a targeted
   re-clustering pass restricted to that subset, to see if a 7th/8th
   intent should be split out.
6. **Build the remaining 4 frontend pages** (Evaluation Dashboard, Golden
   Set/Annotation UI, Failure Analysis, System/About) — currently only
   Support Console exists.
7. **Measure the Eats-filter's false-negative rate** with a small manual
   sample, since only false positives were spot-checked so far.
8. **Add a hybrid TF-IDF + embedding re-ranking** for retrieval once
   human relevance labels make it possible to validate the blend
   actually helps (deferred in D8 rather than tuned blindly).
