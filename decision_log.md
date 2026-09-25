# Decision Log

**D1 — Brand: Uber_Support.**
Why: measured 56,160 resolved customer↔brand pairs, 99.8% structurally
resolved (reply links to a real customer parent tweet), low template-dup
rate (0.1%). Alternatives considered: AmazonHelp/AppleSupport (more data
but too broad/multi-domain for a small mutually-exclusive taxonomy),
SpotifyCares (cleaner but smaller, less escalation-relevant financial/safety
texture). Trade-off: Uber's data mixes two products (rides + Eats, see D2).

**D2 — Scope to ride-hailing only; exclude Uber Eats via keyword heuristic.**
Why: sampling 40 real messages showed Uber_Support handles both rides and
food delivery, which have different resolution patterns and would blur the
taxonomy. Alternatives considered: build a unified agent covering both
(rejected — doubles taxonomy size and dilutes historical grounding).
Trade-off: the keyword heuristic is imperfect — spot-checked false positive
example: "could you give me a discount on my food, I'm broke!" was
excluded on the word "food" though it may not be an Eats order. Documented
as a known limitation, not silently fixed by over-tuning the keyword list.

**D3 — Golden pool (300) reserved before any modeling, via stratified sampling.**
Why: assignment requires leakage prevention between eval and training/retrieval
data. Stratified on message-length bucket (short/medium/long) and presence
of risk keywords (charge/refund/safety/lost), to avoid a golden set of only
easy/common cases (assignment Section 48). Verified 0 text overlap with the
retrieval corpus via an explicit assertion in the pipeline script, not just
an assumption.

**D4 — TF-IDF instead of Sentence-Transformers/FAISS for embeddings.**
Why: this sandbox's network allowlist blocks huggingface.co (confirmed via
direct request: `403 host_not_allowed`), so pretrained transformer embedding
weights cannot be downloaded. Alternatives considered: gensim pretrained
vectors via GitHub-hosted data (not attempted — added complexity for
marginal gain given time budget). Trade-off: TF-IDF captures lexical overlap,
not deep semantic similarity — paraphrased issues ("driver never came" vs.
"waited forever, no car") will retrieve worse than with real embeddings.
This is a real capability gap, documented rather than hidden.

**D5 — Intent taxonomy: 6 classes, including one explicit catch-all.**
Why: two independent TF-IDF+KMeans clustering passes (8 clusters each) both
produced a handful of sharp topical clusters (billing, account security) plus
one large (~45-50%) cluster of generic frustration/follow-up messages that
did not separate further under TF-IDF. Rather than force an artificially
clean taxonomy, `general_unresolved` was kept as an explicit 6th class,
matching the real shape of the data. This directly affects baseline
interpretation (see D6 caveat below) and will be a headline-number caveat.

**D6 — Baselines evaluated against rule-based pseudo-labels, marked non-final.**
Why: no human-labeled golden set exists yet (annotation is a pending human
task). Building the majority-class and TF-IDF+LogReg baselines against
pseudo-labels lets development proceed without fabricating human evaluation.
Known issue surfaced immediately: the pseudo-labeler and the TF-IDF
classifier both key off the same lexical cues (e.g. "charged"), so the 95.1%
TF-IDF+LogReg accuracy is partly circular and should not be read as a
real-world performance estimate. Final, trustworthy baseline numbers require
re-running `evaluation/baselines/run_baselines.py` against
`human_label_intent` once golden-set annotation is complete.

**D7 — Embedding model: spaCy `en_core_web_md` (GloVe word vectors), obtained via GitHub release asset.**
Why: user asked for a small, reliable, locally-runnable sentence-embedding
model without a paid API, reachable despite the huggingface.co block (D4).
spaCy model wheels are hosted on GitHub release assets, which this
sandbox's network allowlist permits. 300-dim, ~40MB, embeds ~1,280
msgs/sec on CPU -- embeds the full 46,740-message corpus in 36.6s, well
inside the 15-minute reproducibility budget. See
reports/embedding_model_card.md for full detail.

**D8 — Primary retrieval method: TF-IDF cosine, not spaCy+FAISS embeddings.**
Why: direct side-by-side spot-checks on identical queries showed TF-IDF
retrieval was qualitatively more precise than spaCy word-vector averaging
on this dataset -- e.g. a "discounted rides for a charity event" query
returned genuinely on-topic TF-IDF matches at a realistic similarity score
(0.40), while spaCy+FAISS returned unrelated boilerplate complaints at a
falsely confident 0.94+. Root cause: short, template-heavy support tweets
share so much common vocabulary ("help", "DM", "Uber_Support") that
word-vector averaging collapses distinct messages into a falsely tight
cluster; TF-IDF's IDF weighting suppresses that boilerplate instead.
Alternatives considered: hybrid re-ranking (score with both, blend) --
deferred as a one-week-next-step, not built now, to avoid tuning a blend
without human relevance labels to validate it against. The spaCy/FAISS
index is kept and available, not deleted, for future comparison once a
true sentence-transformer becomes reachable.

**D9 — Provider-agnostic LLM interface with a deterministic DemoLLMProvider as default.**
Why: no API key was provided, and the assignment explicitly forbids
pretending demo output is live LLM output. Built `LLMProvider` as an
abstract base with `DemoLLMProvider` (fully deterministic, template-based,
grounded only in retrieved evidence, never invents refunds/policy/timelines)
plus `OpenAIProvider`/`AnthropicProvider` stubs wired to environment
variables. Swapping providers requires zero changes outside
`backend/app/core/llm_provider.py` and `.env`.

**D10 — Escalation-always intents chosen by risk category, not tuned thresholds.**
Why: fare/billing, safety, and security intents escalate unconditionally
regardless of confidence or evidence strength, because the assignment
prioritizes safe escalation over hallucinated support (Section 16) more
than it prioritizes automation rate. The confidence (0.55) and similarity
(0.15) thresholds used for the remaining intents are explicitly labeled
"heuristic starting point, NOT YET TUNED" in code comments -- tuning them
against real precision/recall requires the human-labeled golden set.

**D11 — LLM-as-judge scaffold returns explicit nulls in DEMO MODE, not fabricated scores.**
Why: assignment Section 22-24 forbids inventing judge scores or human-vs-LLM
agreement. `evaluation/judges/llm_judge.py` is fully wired (prompt template,
rubric, JSON schema) but returns `status: NOT_YET_MEASURED` with every score
field `null` when DemoLLMProvider is active. Verified this is what actually
happens by running the script, not just asserted.

**D12 — Frontend: single Support Console page built and verified; Evaluation Dashboard / Golden Set / Failure Analysis pages NOT yet built.**
Why: given the scope of remaining work (Phase 9 broader tests, README,
report, and the still-pending human annotation this all depends on),
prioritized building the Support Console -- the assignment's primary
evidence-first UX requirement (Section 20) -- completely and verifying it
end-to-end (npm build succeeds with 0 TypeScript errors; live uvicorn
server hit via curl, not just TestClient) over partially stubbing 4 more
pages. This is an honest scope trade-off, not a hidden gap -- the other
4 pages (Evaluation Dashboard, Golden Set/Annotation, Failure Analysis,
System/About) are explicitly listed as NOT YET BUILT in the compliance
matrix, not silently skipped.

**D13 — Golden-set annotation via a standalone HTML tool, not the earlier CLI, for the actual handoff.**
Why: a 150-250-example annotation session benefits from a visual interface
over a terminal loop. Built `evaluation/annotation/golden_annotation_tool.html`
as a single self-contained file (data embedded as JSON, no server, no
internet) rather than relying on browser storage alone — progress exports
to JSON/CSV explicitly, importable to resume, and merges back into the
canonical CSV via `merge_labels.py`. The original CLI tool
(`annotate_golden.py`) is kept as an alternative, not removed.

**D14 — Human evaluation harness kept in a separate script/file from pseudo-label baselines, never merged.**
Why: user explicitly required headline metrics to be computed against
human labels once available, with pseudo-label results kept clearly
separate. `run_baselines_human.py` writes to
`reports/human_evaluation_results.json`; `run_baselines.py` continues
writing to `reports/baseline_results.json`. The human-eval script refuses
to compute or print any metric when zero human labels exist (verified by
running it against the real, currently-unlabeled golden set) rather than
falling back to pseudo-labels silently.

**D15 — Added a hard safety guard against `prepare_data.py` overwriting real annotation work.**
Why: a real bug was found during this session — an earlier re-run of
`prepare_data.py` (for a timing measurement) silently wiped the
`model_suggestion_intent` column from the golden pool file, because the
script always regenerates that file from scratch. Fixed by adding an
explicit check that raises and refuses to proceed if the existing golden
file already contains any non-empty `human_label_intent` values. This
protects real future annotation work from an equivalent accidental re-run.

**D16 — Fixed 200-example golden evaluation set, derived from the 300-candidate pool, frozen once annotation begins.**
Why: user wanted to resolve the "300 pool vs. 150-250 required" ambiguity
with one fixed, final evaluation set rather than an open-ended range.
Chose 200 (middle of the 150-250 range) via the same stratification
methodology as the original pool (length bucket x risk-keyword presence),
proportionally scaled (`scripts/select_golden_eval_200.py`), rather than
re-deriving strata from scratch -- keeps the sampling methodology
consistent and auditable. The 300-candidate pool is preserved unchanged
at `data/golden/golden_pool_candidates.csv`, not deleted, in case it's
useful later (e.g. expanding the eval set). Added a hard guard: the
selection script refuses to regenerate `golden_eval_200.csv` if it already
contains any annotation, and the annotation-tool builder likewise refuses
to rebuild `golden_annotation_tool.html` if the currently-embedded data
already has human labels -- both verified by inspecting the guard logic,
consistent with the D15 safety-guard precedent.

**D17 — Added an explicit "ambiguous/uncertain" flag, separate from the intent taxonomy's `OTHER_MULTI_INTENT` option.**
Why: user asked whether ambiguous/uncertain cases could be supported.
`OTHER_MULTI_INTENT` addresses one specific ambiguity (the message doesn't
fit any single taxonomy category); the new `human_uncertain` checkbox
addresses a different, broader case -- the annotator has low confidence in
whatever label they did pick, including on an otherwise-clean intent.
Kept as a non-blocking flag (doesn't prevent saving a best-guess label) so
it adds signal for failure analysis without forcing annotation to stall
on hard cases.

**D18 — Root-level `package.json` with `concurrently` for a genuine one-command dev startup.**
Why: user explicitly wanted a single command to start both services where
technically possible. `npm run dev` runs backend (`python -m uvicorn...`)
and frontend (`npm --prefix frontend run dev`) together via `concurrently`,
labeled `[backend]`/`[frontend]`. Verified live: both processes started,
backend health check passed, frontend served HTTP 200, all while running
under the single command. Two-terminal instructions are kept in the
README as Option B for anyone who prefers separate windows, or whose
system doesn't have a `python` alias (only `python3`).

**D19 — Added `__init__.py` to every backend package and friendly RuntimeErrors for missing model artifacts.**
Why: the existing sys.path-manipulation approach worked but relied on
implicit namespace packages, which is more fragile across environments/
IDEs than explicit packages. Added `__init__.py` throughout for
robustness. Separately, `IntentClassifier` and `RetrievalService` now
catch `FileNotFoundError` on startup and re-raise a `RuntimeError` with
the exact fix command (`python scripts/setup_check.py`), verified by
deliberately removing a model file and confirming the message -- per the
explicit requirement that the project "must never silently continue with
a missing model" and must give a useful error instead of a raw traceback.

**D20 — Frontend API base URL made configurable (`VITE_API_BASE_URL`), not hardcoded.**
Why: the app previously worked correctly via the Vite dev-server proxy
(itself pointing at a `BACKEND_URL` env var, defaulting to
`localhost:8000`), but relative fetch paths would silently 404 if the
frontend were ever served without that proxy (e.g. `npm run preview`).
Added an explicit, typed (`vite-env.d.ts`) `VITE_API_BASE_URL` override,
defaulting to empty string (relative path, current behavior unchanged) so
existing dev workflow needs zero changes, but a non-proxied deployment is
now possible via one env var instead of a code change.

**D21 — `scripts/setup_check.py` as the one-command "build everything" entry point.**
Why: model/index artifacts are gitignored (regenerable, large) and a
fresh clone has none of them -- attempting to start the backend without
running the pipeline scripts first would hit the D19 friendly errors.
Built one idempotent script that checks prerequisites (raw dataset,
Python deps, spaCy model), then runs only the pipeline stages whose
output doesn't already exist, in the correct order, never touching the
golden evaluation set if it already contains annotation. Verified this
session by wiping every regenerable artifact (`node_modules`, `models/*`,
`data/processed/*`) and confirming a full rebuild in ~88 seconds with the
golden data coming out byte-identical to a pre-wipe backup.
