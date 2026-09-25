# Embedding Model Card — Retrieval Index

## Model
- **spaCy `en_core_web_md`**, version 3.7.1.
- Architecture: static GloVe-style word vectors (not a transformer, not
  contextual). Sentence/message vector = mean of in-vocabulary token vectors.
- **Dimensions**: 300.
- **Vocabulary with vectors**: 20,000 lexemes.
- **Source**: GitHub release asset (`explosion/spacy-models`), not
  huggingface.co — see decision_log.md D4 for why.
- **Size on disk**: ~40MB.

## Measured runtime (this machine, CPU only)
- Embedding 46,740 messages: **36.6s** (~1,279 msgs/sec).
- Index build (FAISS `IndexFlatIP` on normalized vectors): negligible (<1s for this corpus size).
- TF-IDF index (comparison baseline): 1.1s to build.
- Both comfortably fit inside the assignment's <15-minute reproducibility target.

## Coverage
- 133 / 46,740 messages (0.28%) produced an all-zero vector (fully out-of-vocabulary — e.g. messages that are pure emoji/URLs/IDs after cleaning).

## Measured limitation (real finding, not assumed)
Direct side-by-side spot-checks (`scripts/compare_retrieval.py`) against
identical queries showed **TF-IDF cosine similarity retrieval frequently
outperforms the spaCy word-vector embeddings** on this dataset:

- Query: *"We want to ask you about discounted rides for a charity event..."*
  - spaCy+FAISS top match (sim=0.947): unrelated DM/complaint boilerplate.
  - TF-IDF top match (sim=0.404): "*can i get more discounted rides or nah?*" — actually on-topic.
- Query: *"you owe me three refunds..."*
  - spaCy+FAISS: unrelated generic complaints, all scored 0.91+.
  - TF-IDF: found an actual refund-related message, correctly scored lower (0.42) reflecting genuine partial relevance rather than false confidence.

**Why this happens**: these are short tweets replying to the same support
account, sharing heavy boilerplate vocabulary ("Uber_Support", "help", "DM",
"sorry"). Averaging word vectors over a short message lets that shared
boilerplate dominate the resulting vector, collapsing semantically distinct
messages into a tight, falsely-similar cluster (scores bunched at 0.9+ with
little discrimination). TF-IDF's inverse-document-frequency weighting
naturally suppresses that same boilerplate, so its retrieval is more
lexically precise here — an advantage of a "dumber" method on this
particular kind of short, template-heavy text.

## Implication for the system
Given this finding, **TF-IDF cosine similarity is used as the primary
retrieval method** for grounding replies, not the spaCy embeddings. The
spaCy/FAISS index is kept and exposed for comparison and for future
upgrade path (e.g. if a real sentence-transformer becomes reachable), but
is not the default per decision_log.md D8.

## What is NOT yet measured
Recall@K, Precision@K, and MRR against real relevance judgments — these
require the golden set's human labels, which do not exist yet. The spot
checks above are qualitative illustrations, not a quantitative evaluation.

## Additional limitation found on re-verification (Phase-10 checkpoint)
Re-running `scripts/compare_retrieval.py` after later pipeline changes
reproduced the same TF-IDF-beats-embeddings pattern, and surfaced one more
honest wrinkle: **TF-IDF gives literal 1.000 cosine similarity to
non-identical short messages** (e.g. query "this isn't working" matched
"This isn't working either!!" at sim=1.000). For very short texts with
stopwords/mentions stripped, few remaining terms can make two distinct
messages vectorize identically. This means TF-IDF's similarity scores are
not well-calibrated at the top end for short text either — a real
limitation of the current primary retrieval method, not just the spaCy
fallback. Worth revisiting if/when human relevance labels make proper
Recall@K measurement possible.
