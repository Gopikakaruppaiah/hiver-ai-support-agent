"""
Builds a single self-contained HTML annotation tool with the 300 golden-pool
candidates embedded directly as JSON. No server, no build step, no internet
connection needed -- open the output file directly in a browser.

Design choices (why not the CLI tool for this handoff):
  - Clean visual interface, easier for a long annotation session.
  - Progress is exported as an explicit JSON/CSV file the annotator downloads
    and can re-upload to resume -- no reliance on browser storage persisting
    across sessions/machines.
  - Human labels are NEVER pre-filled as if they were ground truth -- the
    model's suggestion is shown in a clearly separate, greyed-out panel.

Run:
    python evaluation/annotation/build_annotation_tool.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

GOLDEN_PATH = _REPO_ROOT / "data" / "golden" / "golden_eval_200.csv"
OUT_PATH = _REPO_ROOT / "evaluation" / "annotation" / "golden_annotation_tool.html"

TAXONOMY = [
    {"id": "fare_billing_dispute", "label": "Fare / Billing Dispute",
     "desc": "Charged incorrectly, double charge, disputed cancellation fee, refund request."},
    {"id": "driver_cancellation_noshow", "label": "Driver Cancellation / No-show",
     "desc": "Driver cancelled, never arrived, or app failed to complete a booking."},
    {"id": "driver_behavior_safety", "label": "Driver Behavior / Safety Complaint",
     "desc": "Unsafe driving, rude/abusive driver, harassment, accidents."},
    {"id": "account_access_security", "label": "Account Access / Security Issue",
     "desc": "Account hacked, disabled, locked; login/email problems; unauthorized use."},
    {"id": "lost_item", "label": "Lost Item",
     "desc": "Left a personal item in a vehicle, needs driver contacted."},
    {"id": "general_unresolved", "label": "General Inquiry / Unresolved Follow-up",
     "desc": "Generic dissatisfaction, 'already messaged, no response,' vague/ambiguous, very short."},
    {"id": "OTHER_MULTI_INTENT", "label": "Other / Multi-intent (explain in notes)",
     "desc": "Doesn't fit cleanly, or genuinely contains multiple distinct issues."},
]

ESCALATION_OPTIONS = ["AUTO_HANDLE", "ESCALATE"]


def main():
    if OUT_PATH.exists():
        import re as _re
        existing_html = OUT_PATH.read_text()
        m = _re.search(r'const EXAMPLES = (\[.*?\]);\s*\nconst TAXONOMY', existing_html, _re.S)
        if m:
            existing_data = json.loads(m.group(1))
            if any((e.get("human_label_intent") or "").strip() for e in existing_data):
                raise RuntimeError(
                    "REFUSING TO REGENERATE: the existing golden_annotation_tool.html "
                    "embeds examples with human labels already filled in (from a prior "
                    "build or a browser export round-trip). Regenerating now would risk "
                    "losing that work or shipping stale labels. Back up first if you "
                    "really intend to rebuild."
                )

    df = pd.read_csv(GOLDEN_PATH, dtype=str)
    for col in ["human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    records = df[[
        "example_id", "customer_text_clean", "brand_text_clean",
        "model_suggestion_intent", "n_words", "length_bucket", "has_risk_keyword",
        "human_label_intent", "human_escalation_label", "human_uncertain", "annotator_notes",
    ]].to_dict(orient="records")

    html = HTML_TEMPLATE.replace(
        "__EXAMPLES_JSON__", json.dumps(records).replace("</script", "<\\/script")
    ).replace(
        "__TAXONOMY_JSON__", json.dumps(TAXONOMY)
    ).replace(
        "__ESCALATION_JSON__", json.dumps(ESCALATION_OPTIONS)
    )

    OUT_PATH.write_text(html)
    print(f"Wrote {OUT_PATH} ({len(records)} examples embedded)")


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Golden Set Annotation — Uber_Support</title>
<style>
  :root { --border:#e2e8f0; --text:#0f172a; --muted:#64748b; --accent:#0f172a; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin:0; background:#f8fafc; color:var(--text); }
  header { background:#fff; border-bottom:1px solid var(--border); padding:16px 24px; }
  header h1 { margin:0; font-size:16px; }
  header p { margin:4px 0 0; font-size:13px; color:var(--muted); }
  main { max-width:860px; margin:24px auto; padding:0 16px 80px; }
  .progress { background:#fff; border:1px solid var(--border); border-radius:10px; padding:12px 16px; margin-bottom:16px; font-size:13px; }
  .bar { height:6px; background:#e2e8f0; border-radius:4px; overflow:hidden; margin-top:8px; }
  .bar-fill { height:100%; background:#16a34a; transition:width .2s; }
  .card { background:#fff; border:1px solid var(--border); border-radius:12px; padding:20px; }
  .msg { font-size:15px; line-height:1.5; padding:12px; background:#f1f5f9; border-radius:8px; margin-bottom:12px; }
  .meta { font-size:12px; color:var(--muted); margin-bottom:12px; }
  .suggestion { font-size:13px; color:#92400e; background:#fffbeb; border:1px solid #fde68a; border-radius:8px; padding:8px 12px; margin-bottom:16px; }
  fieldset { border:1px solid var(--border); border-radius:8px; padding:12px; margin-bottom:12px; }
  legend { font-size:12px; font-weight:600; color:var(--muted); padding:0 6px; }
  label.opt { display:block; padding:8px; border-radius:6px; cursor:pointer; font-size:14px; }
  label.opt:hover { background:#f1f5f9; }
  label.opt .d { font-size:12px; color:var(--muted); margin-left:24px; }
  textarea { width:100%; border:1px solid var(--border); border-radius:8px; padding:8px; font-size:13px; font-family:inherit; }
  .nav { display:flex; justify-content:space-between; align-items:center; margin-top:16px; }
  button { border:none; border-radius:8px; padding:10px 16px; font-size:14px; font-weight:500; cursor:pointer; }
  .btn-primary { background:#0f172a; color:#fff; }
  .btn-secondary { background:#fff; border:1px solid var(--border); color:var(--text); }
  .btn-primary:disabled { opacity:.4; cursor:not-allowed; }
  .toolbar { display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }
  .toolbar button { font-size:12px; padding:6px 10px; }
  .jump { font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>Golden Set Annotation — Uber_Support (ride-hailing)</h1>
  <p>The model's suggestion is NOT the answer. Read the message, pick what YOU think is correct.
     Progress auto-saves in this browser tab; export regularly and after you finish.</p>
</header>
<main>
  <div class="progress">
    <span id="progressText"></span>
    <div class="bar"><div class="bar-fill" id="progressBar"></div></div>
  </div>

  <div class="toolbar">
    <button class="btn-secondary" onclick="exportJSON()">⬇ Export progress (JSON)</button>
    <button class="btn-secondary" onclick="exportCSV()">⬇ Export progress (CSV)</button>
    <label class="btn-secondary" style="padding:6px 10px;">
      ⬆ Import previous progress
      <input type="file" accept=".json" style="display:none" onchange="importJSON(event)">
    </label>
    <span class="jump">Go to # <input type="number" id="jumpBox" style="width:60px" min="1"> <button class="btn-secondary" onclick="jumpTo()">Go</button></span>
  </div>

  <div class="card">
    <div class="meta" id="meta"></div>
    <div class="msg" id="customerMsg"></div>
    <div class="suggestion" id="suggestion"></div>

    <fieldset>
      <legend>Your intent label</legend>
      <div id="intentOptions"></div>
    </fieldset>

    <fieldset>
      <legend>Your escalation label (should this be auto-handled or escalated to a human?)</legend>
      <div id="escalationOptions"></div>
    </fieldset>

    <fieldset>
      <label class="opt" style="padding:4px 0;">
        <input type="checkbox" id="uncertainBox" onchange="setUncertain(this.checked)">
        Mark as <strong>ambiguous / uncertain</strong> — I'm not confident in this label
        <div class="d">Use this for genuinely hard cases: multi-intent messages, borderline
        calls, or anything where a different annotator might reasonably disagree. This does
        NOT block saving — it flags the example for extra attention in the failure analysis.</div>
      </label>
    </fieldset>

    <fieldset>
      <legend>Notes (optional — e.g. "ambiguous", "multi-intent", "hard case")</legend>
      <textarea id="notes" rows="2" onchange="saveNote()"></textarea>
    </fieldset>

    <div class="nav">
      <button class="btn-secondary" onclick="prevEx()">&larr; Previous</button>
      <span id="posText" style="font-size:13px;color:var(--muted);"></span>
      <button class="btn-primary" onclick="nextEx()">Next &rarr;</button>
    </div>
  </div>
</main>

<script>
const EXAMPLES = __EXAMPLES_JSON__;
const TAXONOMY = __TAXONOMY_JSON__;
const ESCALATION_OPTIONS = __ESCALATION_JSON__;

let idx = 0;
const STORAGE_KEY = "uber_golden_annotation_progress_v1";

function loadProgress() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    const parsed = JSON.parse(saved);
    parsed.forEach((row, i) => { if (EXAMPLES[i]) Object.assign(EXAMPLES[i], row); });
  }
}
function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(EXAMPLES));
}

function render() {
  const ex = EXAMPLES[idx];
  document.getElementById("meta").textContent =
    `${ex.example_id} · ${ex.n_words} words · ${ex.length_bucket} · risk-keyword: ${ex.has_risk_keyword}`;
  document.getElementById("customerMsg").textContent = ex.customer_text_clean;
  document.getElementById("suggestion").innerHTML =
    `<strong>Model suggestion (not ground truth):</strong> ${ex.model_suggestion_intent}`;

  const intentDiv = document.getElementById("intentOptions");
  intentDiv.innerHTML = TAXONOMY.map(t => `
    <label class="opt">
      <input type="radio" name="intent" value="${t.id}" ${ex.human_label_intent === t.id ? "checked" : ""} onchange="setIntent('${t.id}')">
      ${t.label}
      <div class="d">${t.desc}</div>
    </label>`).join("");

  const escDiv = document.getElementById("escalationOptions");
  escDiv.innerHTML = ESCALATION_OPTIONS.map(o => `
    <label class="opt">
      <input type="radio" name="escalation" value="${o}" ${ex.human_escalation_label === o ? "checked" : ""} onchange="setEscalation('${o}')">
      ${o}
    </label>`).join("");

  document.getElementById("notes").value = ex.annotator_notes || "";
  document.getElementById("uncertainBox").checked = ex.human_uncertain === "true" || ex.human_uncertain === true;
  document.getElementById("posText").textContent = `${idx + 1} / ${EXAMPLES.length}`;
  document.getElementById("jumpBox").value = idx + 1;

  const done = EXAMPLES.filter(e => e.human_label_intent).length;
  document.getElementById("progressText").textContent =
    `${done} / ${EXAMPLES.length} labeled (${Math.round(100 * done / EXAMPLES.length)}%)`;
  document.getElementById("progressBar").style.width = `${100 * done / EXAMPLES.length}%`;
}

function setIntent(v) { EXAMPLES[idx].human_label_intent = v; persist(); render(); }
function setEscalation(v) { EXAMPLES[idx].human_escalation_label = v; persist(); render(); }
function setUncertain(v) { EXAMPLES[idx].human_uncertain = v ? "true" : ""; persist(); }
function saveNote() { EXAMPLES[idx].annotator_notes = document.getElementById("notes").value; persist(); }

function nextEx() { if (idx < EXAMPLES.length - 1) idx++; render(); window.scrollTo(0,0); }
function prevEx() { if (idx > 0) idx--; render(); window.scrollTo(0,0); }
function jumpTo() {
  const n = parseInt(document.getElementById("jumpBox").value, 10);
  if (n >= 1 && n <= EXAMPLES.length) { idx = n - 1; render(); window.scrollTo(0,0); }
}

function exportJSON() {
  const blob = new Blob([JSON.stringify(EXAMPLES, null, 2)], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "golden_labels_export.json";
  a.click();
}
function exportCSV() {
  const cols = ["example_id","human_label_intent","human_escalation_label","human_uncertain","annotator_notes"];
  const rows = [cols.join(",")].concat(
    EXAMPLES.map(e => cols.map(c => `"${(e[c]||"").toString().replace(/"/g,'""')}"`).join(","))
  );
  const blob = new Blob([rows.join("\\n")], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "golden_labels_export.csv";
  a.click();
}
function importJSON(event) {
  const file = event.target.files[0];
  const reader = new FileReader();
  reader.onload = function(e) {
    const imported = JSON.parse(e.target.result);
    imported.forEach((row, i) => { if (EXAMPLES[i]) Object.assign(EXAMPLES[i], row); });
    persist();
    render();
    alert("Progress imported.");
  };
  reader.readAsText(file);
}

loadProgress();
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
