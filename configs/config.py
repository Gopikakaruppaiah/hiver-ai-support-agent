"""
Central configuration for the Hiver AI Support Agent project.

All values are overridable via environment variables so nothing is
hardcoded for one machine. See .env.example at the repo root.
"""
import os
from pathlib import Path

# ---- Paths -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = Path(os.getenv("DATA_RAW_PATH", REPO_ROOT / "data" / "raw" / "twcs.csv"))
DATA_PROCESSED_DIR = Path(os.getenv("DATA_PROCESSED_DIR", REPO_ROOT / "data" / "processed"))
DATA_GOLDEN_DIR = Path(os.getenv("DATA_GOLDEN_DIR", REPO_ROOT / "data" / "golden"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", REPO_ROOT / "models"))

# ---- Brand selection ---------------------------------------------------------
# Chosen in Phase 1 based on measured evidence (see reports/brand_selection.md):
# largest *single-domain* brand among top candidates, 55K+ resolved historical
# pairs, 99.8% structurally resolved, low template-dup rate.
BRAND_NAME = os.getenv("BRAND_NAME", "Uber_Support")

# Uber_Support's account handles both ride-hailing AND Uber Eats. We scope
# this project to ride-hailing only (see decision_log.md, decision D2).
# Simple keyword heuristic to flag likely Eats/food-delivery messages for
# exclusion. This is a heuristic, not a perfect classifier -- documented as
# a limitation in the report's "misleading headline number" section.
EATS_EXCLUSION_KEYWORDS = [
    "uber eats", "ubereats", " eats ", "food", "order", "restaurant",
    "delivery", "delivered", "mcdonald", "meal", "menu", "cold food",
    "missing item", "wrong order",
]

# ---- Reproducibility ---------------------------------------------------------
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

# ---- Split sizes --------------------------------------------------------------
GOLDEN_POOL_SIZE = int(os.getenv("GOLDEN_POOL_SIZE", "300"))  # candidates for hand-labeling; final golden = 150-250 after review
GOLDEN_EVAL_SIZE = int(os.getenv("GOLDEN_EVAL_SIZE", "200"))  # FIXED final evaluation set, frozen once annotation begins
MIN_CUSTOMER_MSG_CHARS = int(os.getenv("MIN_CUSTOMER_MSG_CHARS", "3"))

# ---- LLM / API config (never hardcode keys) -----------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")  # empty => DEMO MODE fallback
