"""
Verifies run_baselines_human.py's SCORING LOGIC is correct, using a
temp-directory copy of the golden pool with synthetic TEST-FIXTURE labels.
This never writes to or reads from the real data/golden/golden_pool_candidates.csv
with fake labels -- it operates on an isolated tmp_path copy only, and
asserts the real file is untouched afterward.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_human_eval_harness_scores_correctly_on_isolated_copy(tmp_path, monkeypatch):
    real_golden = _REPO_ROOT / "data" / "golden" / "golden_eval_200.csv"
    real_hash_before = real_golden.read_bytes()

    temp_dir = tmp_path / "golden"
    temp_dir.mkdir()
    temp_golden = temp_dir / "golden_eval_200.csv"
    shutil.copy(real_golden, temp_golden)

    df = pd.read_csv(temp_golden, dtype=str, keep_default_na=False, na_filter=False)

    # Assign synthetic TEST-FIXTURE labels to first 20 rows only, using the
    # model's own suggestion as the "human" label so we get a KNOWN,
    # predictable accuracy (should score very well vs. itself) -- this is
    # purely to test the harness's arithmetic, not a claim about real accuracy.
    for i in range(20):
        df.at[i, "human_label_intent"] = df.at[i, "model_suggestion_intent"]
        df.at[i, "human_escalation_label"] = "ESCALATE" if i % 2 == 0 else "AUTO_HANDLE"
    df.to_csv(temp_golden, index=False)

    # run the harness against the temp copy via env var override
    env = {**__import__("os").environ, "DATA_GOLDEN_DIR": str(temp_dir)}
    result = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "evaluation" / "baselines" / "run_baselines_human.py")],
        cwd=str(_REPO_ROOT), env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr

    out_json = _REPO_ROOT / "reports" / "human_evaluation_results.json"
    payload = json.loads(out_json.read_text())

    # cleanup: this test run WILL have written a real reports/human_evaluation_results.json
    # with SCORED status from synthetic data -- restore it to PENDING state after, since
    # that file should only ever reflect the real golden pool's real status.
    payload_is_from_this_test = payload.get("n_labeled") == 20
    assert payload_is_from_this_test, "harness did not pick up the temp golden dir override"
    assert payload["status"] == "SCORED"
    assert payload["n_golden_pool_total"] == 200

    # since model_suggestion == human_label for these rows, TF-IDF+LogReg
    # should score very high (it's the training signal) -- sanity check
    assert payload["intent_classification"]["tfidf_logreg"]["accuracy"] > 0.5

    # restore reports/human_evaluation_results.json to the honest PENDING
    # state, since the real golden pool has 0 human labels right now
    pending_result = {
        "status": "PENDING_HUMAN_ANNOTATION",
        "n_labeled": 0,
        "message": (
            "No human_label_intent values found in data/golden/golden_pool_candidates.csv. "
            "Run evaluation/annotation/golden_annotation_tool.html, then "
            "evaluation/annotation/merge_labels.py, then re-run this script."
        ),
    }
    out_json.write_text(json.dumps(pending_result, indent=2))

    # confirm the REAL golden file was never touched by any of this
    assert real_golden.read_bytes() == real_hash_before
