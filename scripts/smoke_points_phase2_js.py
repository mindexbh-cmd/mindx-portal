"""Phase 2 + 3 JS validation smoke for the points board UI.

Mirrors scripts/smoke_parent_html_js_valid.py but targets the
points-board template constants. Catches the class of bug where
a Python triple-quoted-with-backslashes string ends up with an
inner quote that crashes the browser's JS parser and silently
takes down every function in the <script> block.

Three things are checked:

  [1] Every <script>…</script> block in POINTS_BOARD_HTML
      parses cleanly as JavaScript (via node's Function ctor).
  [2] The Phase 2 wiring is actually present in the rendered
      HTML for a real /points/board request — function names,
      DOM ids, and CSS classes that the owner browser-test
      will rely on.
  [3] Existing functions that pre-date Phase 2 are still
      defined (regression guard).

No DB writes. No test fixtures created.
"""
import os
import sys
import io
import re
import subprocess
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A  # noqa: E402

# Ensure node is available.
try:
    rv = subprocess.run(["node", "--version"], capture_output=True,
                        text=True, timeout=15)
    if rv.returncode != 0:
        print("FATAL: node returned non-zero:", rv.returncode)
        sys.exit(2)
    print(f"[env] node {rv.stdout.strip()}")
except FileNotFoundError:
    print("FATAL: node not on PATH — install Node.js and re-run.")
    sys.exit(2)


def run_node(js_body):
    """Feed a script body into node's Function constructor. Returns
    (ok, message)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False,
                                     encoding="utf-8") as fp:
        fp.write(js_body)
        fp.flush()
        path = fp.name
    try:
        rv = subprocess.run(
            ["node", "-e",
             "try{ new Function(require('fs').readFileSync("
             f"'{path.replace(chr(92), '/')}','utf8')); "
             "console.log('OK'); }catch(e){"
             "console.log('ERR:'+e.message); process.exit(1);}"],
            capture_output=True, text=True, timeout=30)
        out = (rv.stdout or "").strip() + (rv.stderr or "").strip()
        return rv.returncode == 0 and "OK" in out, out
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ── Test 1 — module-level constant ──────────────────────────────
print("[1] Validating POINTS_BOARD_HTML <script> blocks…")
const_body = getattr(A, "POINTS_BOARD_HTML", "")
assert const_body, "POINTS_BOARD_HTML missing on app module"
scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",
                     const_body, re.IGNORECASE)
assert scripts, "no <script> block found in POINTS_BOARD_HTML"
for i, body in enumerate(scripts):
    # The constant has __GROUP_ARG__ / __SOUND_ON__ placeholders.
    # Replace them with valid JS literals so node can parse the
    # template body. Production swaps these via Python .replace()
    # before sending, so this mirrors the served form.
    js = (body
          .replace("__GROUP_ARG__", '""')
          .replace("__SOUND_ON__",  "false")
          .replace("__BACK_HREF__", '"/"')
          .replace("__QA_DISP__",   "none"))
    ok, msg = run_node(js)
    assert ok, f"POINTS_BOARD_HTML <script> #{i} failed: {msg}"
    print(f"  block {i}: OK ({len(body)} chars)")

# ── Test 2 — Phase 2 wiring present in served HTML ──────────────
print("[2] Verifying Phase 2 markers in the served /points/board HTML…")
import sqlite3 as _sql
db = _sql.connect("mindx.db"); db.row_factory = _sql.Row
admin = dict(db.execute(
    "SELECT id, username, role, name FROM users "
    "WHERE role='admin' LIMIT 1").fetchone())
db.close()
c = A.app.test_client()
with c.session_transaction() as s:
    s["user"] = admin
rv = c.get("/points/board")
assert rv.status_code == 200, f"/points/board HTTP {rv.status_code}"
html = rv.get_data(as_text=True)

PHASE2_MARKERS = {
    # Phase 2 — C1 budget bar
    "id=\"pb-budget\"":            "C1 budget card DOM",
    "function loadBudget":         "C1 budget loader",
    "function renderBudget":       "C1 budget renderer",
    # Phase 2 — C2 per-student session chip
    "function loadSessionEvents":  "C2 session-events loader",
    "function paintSessionBadge":  "C2 chip painter",
    # Phase 2 — C3 quick-action buttons
    "function quickGrant":         "C3 quick-grant fn",
    "function pickBehaviorForAmount": "C3 behavior picker",
    "pq-row":                      "C3 quick-action row CSS",
    # Phase 2 — C4 warnings + disable
    "function refreshQuickButtonStates": "C4 button-state refresher",
    "function toastVariant":       "C4 colour toast helper",
    "_lastPctSeen":                "C4 threshold-crossing guard",
    # Phase 2 — C5 undo
    "function undoLastGrant":      "C5 undo fn",
    "function rememberLastGrant":  "C5 undo state",
    "id=\"pbUndo\"":               "C5 undo pill DOM",
    # Phase 2 — C6 absent
    "function paintAbsentCards":   "C6 absent painter",
    "pb-abs-badge":                "C6 absent badge CSS",
    "pb-absent":                   "C6 absent grayout CSS",
    # Phase 2 — C7 note modal
    "id=\"noteBack\"":             "C7 note modal DOM",
    "function openNoteModal":      "C7 note open fn",
    "function saveNoteGrant":      "C7 note save fn",
    "function selectNoteAmt":      "C7 amount picker fn",
    # Phase 2 — C8 orchestrator
    "function refreshBoardState":  "C8 refresh orchestrator",
    # Phase 3 — C2 stats modal
    "id=\"statsBack\"":            "P3-C2 stats modal DOM",
    "function openStatsModal":     "P3-C2 stats open fn",
    "function closeStatsModal":    "P3-C2 stats close fn",
    "function renderStatsModal":   "P3-C2 stats renderer",
    # Phase 3 — C4 distribute modal
    "id=\"distBack\"":             "P3-C4 distribute modal DOM",
    "function openDistModal":      "P3-C4 distribute open fn",
    "function executeDist":        "P3-C4 distribute execute fn",
    "function selectDistAmt":      "P3-C4 amount picker fn",
    "function refreshDistPreview": "P3-C4 preview refresher",
    "function countPresent":       "P3-C4 present-counter helper",
    # Phase 3 — C5 polish
    "pb-sess-badge--bumped":       "P3-C5 chip bump anim CSS",
    "(hover: hover) and (pointer: fine)": "P3-C5 desktop-only hover",
}
for needle, label in PHASE2_MARKERS.items():
    assert needle in html, f"missing — {label} ({needle!r})"
print(f"  {len(PHASE2_MARKERS)} Phase 2 markers all present")

# ── Test 3 — regression guard for pre-Phase-2 wiring ────────────
print("[3] Regression guard — original board functions still defined…")
REGRESSION_MARKERS = [
    "function init",
    "function loadGroup",
    "function render",
    "function grant",
    "function setMenuTab",
    "function openGrant",
    "openQuickAttendance",
    "STATE.behaviors",
]
for m in REGRESSION_MARKERS:
    assert m in html, f"regression — pre-Phase-2 piece missing: {m!r}"
print(f"  {len(REGRESSION_MARKERS)} pre-Phase-2 markers preserved")

print("\nPhase 2 + 3 JS validation smoke passed.")
