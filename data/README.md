# Data

- `raw/` — place `twcs.csv` here (download from
  [Kaggle: Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)).
  Not committed to git (516MB, Kaggle's terms require you to download it
  yourself).
- `processed/` — output of `scripts/prepare_data.py`: `retrieval_corpus.csv`
  (46,740 rows, the historical evidence store).
- `golden/` — `golden_pool_candidates.csv`, 300 rows reserved for human
  annotation. This one **is** committed (small, no raw dataset content
  concerns beyond what's already public on Kaggle) since it's the
  artifact you'll actually annotate.
