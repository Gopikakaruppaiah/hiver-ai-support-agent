# Hiver AI Support Agent — Uber_Support (Ride-Hailing)

An AI support agent for **Uber_Support** that classifies incoming customer
messages, drafts a reply grounded in how Uber has historically resolved
similar issues, and decides whether to auto-handle or escalate to a human
— with a stated reason.

**DEMO MODE works out of the box — no API key, no paid service, no
external LLM required.** REAL LLM MODE is optional (see §10 below).

---

## QUICK START

Works on **Windows, macOS, and Linux**. Tested from a clean state.

### 0. Requirements

- Python 3.10+ (`python --version` — on Windows this is usually `python`;
  on macOS/Linux it may be `python3`)
- Node.js 18+ and npm (`node --version`)
- ~1GB free disk space (mostly the raw dataset)

### 1. Open the project in VS Code

Open the repo's root folder (the one containing this README) in VS Code.
Open a terminal (`` Ctrl+` `` / `` Cmd+` ``) — all commands below run from
the repo root.

### 2. Get the dataset (one-time, manual — required)

Download **twcs.csv** from Kaggle:
[Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)

Place it at `data/raw/twcs.csv`. This file isn't included in the repo
(516MB, and Kaggle's terms require downloading it yourself).

### 3. Install dependencies

**Backend (Python):**
```bash
pip install -r backend/requirements.txt
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.7.1/en_core_web_md-3.7.1-py3-none-any.whl
```
*(Windows: same commands, in the same terminal — `pip` works identically.)*

**Frontend (Node):**
```bash
cd frontend && npm install && cd ..
```

**Root (for the one-command dev launcher):**
```bash
npm install
```

### 4. Build the models/indexes (one-time, ~90 seconds)

```bash
python scripts/setup_check.py
```
*(macOS/Linux: use `python3` instead of `python` if `python` isn't found.)*

This checks everything is in place and builds the TF-IDF/Logistic
Regression classifier, retrieval indexes, and the golden evaluation set —
skipping any step whose output already exists. Re-run it any time; it's
safe and idempotent, and will never overwrite real annotation work.

### 5. Start the application

**Option A — one command (recommended):**
```bash
npm run dev
```
Starts backend (port 8000) and frontend (port 5173) together in one
terminal, clearly labeled `[backend]` / `[frontend]`.

**Option B — two terminals** (if you prefer separate windows/tabs):
```bash
# Terminal 1
python -m uvicorn backend.app.main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev
```

### 6. Open the browser

Go to **http://localhost:5173**. You'll see the Support Console with a
`DEMO MODE` badge in the header.

### 7. Try it

Type a message, or click one of the sample-message chips (Fare/billing,
Cancellation, Lost item, Driver safety, Account issue) above the input
box, then click **Analyze Message**. You'll see the detected intent,
confidence, retrieved historical evidence, a generated reply, and the
auto-handle/escalate decision with its reason.

### 8. Run tests

```bash
npm run test
```
(or directly: `python -m pytest backend/tests/ -v`) — 33 tests, covering
preprocessing, retrieval, classification, escalation, the full API, error
handling, and golden-set protection.

### 9. Run evaluation

```bash
python evaluation/baselines/run_baselines.py        # pseudo-label baselines (majority-class, TF-IDF+LogReg)
python evaluation/baselines/run_baselines_human.py  # real metrics -- reports PENDING_HUMAN_ANNOTATION until you annotate
```

To do the real human annotation: open
`evaluation/annotation/golden_annotation_tool.html` directly in a browser
and follow `evaluation/annotation/ANNOTATION_GUIDELINES.md`.

### 10. Optional: real LLM instead of DEMO MODE

Not required. If you want live generative replies instead of the
DEMO MODE template:

1. Copy `.env.example` to `.env`.
2. Fill in `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, and `LLM_MODEL_NAME`.
3. Implement the provider call body in `backend/app/core/llm_provider.py`
   (`OpenAIProvider`/`AnthropicProvider` — currently stubs that raise
   `NotImplementedError`, by design, so nothing pretends to be live when
   it isn't).

Without this, the app runs entirely in DEMO MODE — this is expected and
correct, not a broken state.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` on backend start | Run `pip install -r backend/requirements.txt` (and the spaCy model line above) |
| `RuntimeError: Intent classifier model files not found` | Run `python scripts/setup_check.py` |
| `RuntimeError: Retrieval index files not found` | Same — `python scripts/setup_check.py` |
| `FileNotFoundError` mentioning `twcs.csv` | You skipped step 2 — download the dataset from Kaggle first |
| Frontend loads but "Analyze" does nothing / network error | Backend isn't running, or isn't on port 8000 — check Terminal 1 / the `[backend]` log lines |
| `npm run dev` fails with "python: command not found" | Your system uses `python3` instead — edit `package.json`'s `"backend"` script to use `python3`, or use Option B (two terminals) with `python3` directly |
| Port 8000 or 5173 already in use | Stop whatever's using it, or run backend with `--port 8001` and set `frontend/.env`'s `VITE_API_BASE_URL` accordingly |
| CORS error in browser console | Confirm you're opening `http://localhost:5173` (not a different port) — the backend allows `localhost`/`127.0.0.1` on ports 5173/3000/4173 by default |

---

## What "DEMO MODE" means (and doesn't)

- No LLM API is called. Replies are deterministic templates, built from
  the actual retrieved historical evidence for that message — never
  invented refunds, policies, or timelines.
- Every demo reply is prefixed `[DEMO MODE — template-based, not a live
  LLM response]` in the text itself, and `is_demo_mode: true` in the API
  response, so it's never confused with real generative output or
  presented as measured LLM performance.
- Intent classification, retrieval, and the escalation decision are
  **not** part of DEMO MODE — they're real, trained/rule-based components
  that run the same way regardless of whether an LLM is configured.

## Evaluation honesty — current status

- **Golden evaluation set**: a **fixed 200 examples**
  (`data/golden/golden_eval_200.csv`), stratified-sampled from a
  300-candidate pool. **Currently 0/200 are human-labeled.** Every
  classification/escalation number you can compute right now is either a
  pseudo-label proxy (clearly marked) or `PENDING_HUMAN_ANNOTATION`
  (never silently replaced with a pseudo-label).
- Full details, the mandatory "what's misleading about my headline
  number" discussion, and the compliance matrix: see
  [`reports/final_report.md`](reports/final_report.md) and
  [`reports/compliance_matrix.md`](reports/compliance_matrix.md).

## Architecture

```
                 ┌─────────────────────┐
                 │   React Frontend     │
                 │  Support Console     │
                 └──────────┬───────────┘
                            │ REST (JSON), via Vite dev proxy or VITE_API_BASE_URL
                            ▼
                 ┌─────────────────────┐
                 │     FastAPI          │
                 │  /api/analyze etc.   │
                 └──────────┬───────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
 ┌─────────────┐    ┌──────────────┐    ┌────────────────┐
 │   Intent     │    │  Retrieval    │    │   Escalation    │
 │ Classifier   │    │  (TF-IDF      │    │     Engine      │
 │ (TF-IDF +    │    │  cosine, +    │    │  (rule-based,   │
 │  LogReg)     │    │  spaCy/FAISS  │    │  fully          │
 │              │    │  available)   │    │  explainable)   │
 └──────────────┘    └──────┬────────┘    └────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Historical    │
                    │  Support Data  │
                    │  (46,740 pairs)│
                    └──────┬────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Reply / LLM   │
                    │  Generation    │
                    │  (DEMO MODE,   │
                    │  provider-     │
                    │  agnostic)     │
                    └───────────────┘
```

## Tech stack

- **ML/Data**: pandas, scikit-learn (TF-IDF, Logistic Regression, KMeans),
  spaCy `en_core_web_md` (word-vector embeddings), FAISS (vector index).
- **Backend**: FastAPI, Pydantic, pytest.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS.
- **LLM**: provider-agnostic interface; DEMO MODE (no key) by default,
  OpenAI/Anthropic pluggable via `.env` (call bodies not implemented in
  this build — see §10/Optional above).

## Project structure

```
hiver-ai-support-agent/
├── package.json           Root one-command dev launcher (npm run dev/test/build/setup)
├── backend/                FastAPI app + pytest tests (33 passing)
│   ├── app/{api,core,schemas,services}/
│   └── tests/
├── frontend/                React+TS+Vite+Tailwind Support Console
├── data/
│   ├── raw/                  twcs.csv goes here (gitignored, download yourself)
│   ├── processed/             regenerable via scripts/prepare_data.py
│   └── golden/                 golden_eval_200.csv (fixed eval set) + golden_pool_candidates.csv (300-candidate reserve)
├── models/                      persisted TF-IDF/LogReg/spaCy/FAISS artifacts (regenerable, gitignored)
├── evaluation/
│   ├── baselines/                 pseudo-label + human-label evaluation harnesses
│   ├── annotation/                  HTML annotation tool + guidelines + merge script
│   └── judges/                       LLM-as-judge (wired, returns NOT_YET_MEASURED without a key)
├── scripts/
│   ├── setup_check.py                One-command setup: checks + builds everything
│   ├── prepare_data.py, build_index.py, discover_intents.py, select_golden_eval_200.py
├── configs/                            central config (brand, paths, seeds)
├── docs/                                 intent taxonomy definitions
├── reports/                               final_report.md, compliance_matrix.md, real stats, model cards
├── decision_log.md                        17+ documented non-obvious decisions
└── .env.example
```

## Data source

[Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
(Kaggle). Not committed to this repo — see §2 above.
