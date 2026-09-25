"""
Rule-based pseudo-labeler for the 6-intent taxonomy (docs/intent_taxonomy.md).

IMPORTANT: outputs of this module are `model_suggestion` labels only.
They are NOT human labels. They exist so we can (a) bootstrap baseline
training/evaluation before human annotation is done, and (b) pre-fill
suggestions in the annotation tool to speed up human labeling.
Never treat this as ground truth in the final report.
"""
import re

INTENTS = [
    "fare_billing_dispute",
    "driver_cancellation_noshow",
    "driver_behavior_safety",
    "account_access_security",
    "lost_item",
    "general_unresolved",
]

RULES = [
    # (intent, ordered by priority -- first match wins, since safety/security
    # should never be masked by a weaker generic keyword match)
    ("driver_behavior_safety", re.compile(
        r"\b(unsafe|accident|crash|assault|harass|rude|abusive|threat|danger|"
        r"scary|scared|drunk driver|hit me|hit my|police)\b", re.I)),
    ("account_access_security", re.compile(
        r"\b(hack(ed)?|disabled|locked|log ?in|password|can'?t access|"
        r"unauthori[sz]ed|someone (else )?us(ed|ing) my account)\b", re.I)),
    ("lost_item", re.compile(
        r"\b(left (my|a)|lost (my|a)|forgot (my|a)).{0,20}\b(phone|bag|wallet|"
        r"item|jacket|keys|luggage)\b|driver has my", re.I)),
    ("fare_billing_dispute", re.compile(
        r"\b(charged?|overcharg|refund|double charge|cancellation fee|"
        r"fare (was|is) (higher|wrong)|billing|bank statement)\b", re.I)),
    ("driver_cancellation_noshow", re.compile(
        r"driver.{0,15}cancel|cancel.{0,15}driver|no show|never (showed|arrived)|"
        r"waited \d+ ?min|driver (didn'?t|never) (show|arrive)|"
        r"driver.{0,20}(late|didn'?t (show|come)|stood me up)|"
        r"stuck (waiting|outside)|cab (never came|didn'?t come)", re.I)),
]

GENERIC_LOW_INFO_WORD_THRESHOLD = 4


def classify(text: str, n_words: int) -> str:
    for intent, pattern in RULES:
        if pattern.search(text):
            return intent
    if n_words <= GENERIC_LOW_INFO_WORD_THRESHOLD:
        return "general_unresolved"
    return "general_unresolved"


if __name__ == "__main__":
    import sys
    from pathlib import Path
    import pandas as pd

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from configs.config import DATA_PROCESSED_DIR, DATA_GOLDEN_DIR

    for name, path in [
        ("retrieval_corpus", DATA_PROCESSED_DIR / "retrieval_corpus.csv"),
        ("golden_pool_candidates", DATA_GOLDEN_DIR / "golden_pool_candidates.csv"),
    ]:
        df = pd.read_csv(path)
        df["model_suggestion_intent"] = [
            classify(t, n) for t, n in zip(df["customer_text_clean"].astype(str), df["n_words"])
        ]
        if "golden" in name:
            df["human_label_intent"] = ""  # explicitly empty -- PENDING HUMAN ANNOTATION
        df.to_csv(path, index=False)
        print(f"\n{name} ({len(df)} rows) -- model_suggestion_intent distribution:")
        print(df["model_suggestion_intent"].value_counts())
        print((100 * df["model_suggestion_intent"].value_counts(normalize=True)).round(1))
