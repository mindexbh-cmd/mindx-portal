"""v2.8.5 smoke — /parent/evaluations/view back button preserves PID.

Owner reported the رجوع button on the evaluations page sent
them back to the empty PID lookup form. The fix gives the back
anchor id='pe-back-link' and rewrites its href to /parent?pid=
inside the existing IIFE (server injects PID as __PID_JSON__).

Tests:
  [1] GET /parent/evaluations/view?pid=<valid> -> 200.
  [2] Rendered HTML carries the id='pe-back-link' anchor.
  [3] Rendered HTML carries the JS that sets _peBack.href to
      '/parent?pid=' + encodeURIComponent(PID).
  [4] The original href fallback (/parent) is still there for
      the no-JS path.
  [5] Invalid PID still 403s (route validation unchanged).
  [6] The route still serves the same template shell (status
      spinner + content slot present).
"""
import os, sys, io, re, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Find a real PID locally so the validator passes.
_con = sqlite3.connect("mindx.db")
_con.row_factory = sqlite3.Row
_row = _con.execute(
    "SELECT personal_id FROM students "
    "WHERE TRIM(COALESCE(personal_id,''))<>'' LIMIT 1").fetchone()
_con.close()
assert _row, "no student with a personal_id seeded; cannot smoke-test"
VALID_PID = _row["personal_id"].strip()

c = A.app.test_client()

# Test 1: page renders 200 for a valid PID.
rv = c.get(f"/parent/evaluations/view?pid={VALID_PID}")
print(f"[1] GET /parent/evaluations/view?pid={VALID_PID} -> {rv.status_code}")
assert rv.status_code == 200, \
    f"expected 200, got {rv.status_code}"
html = rv.get_data(as_text=True)

# Test 2: back anchor has the id we added.
assert 'id="pe-back-link"' in html, \
    "back anchor missing id='pe-back-link'"
print("[2] back anchor carries id='pe-back-link'")

# Test 3: JS sets the back link's href to /parent?pid=<encoded PID>.
for snip in [
    "getElementById('pe-back-link')",
    "'/parent?pid=' + encodeURIComponent(PID)",
]:
    assert snip in html, f"PID-threading JS missing: {snip!r}"
print("[3] back-link href is rewritten to /parent?pid=<encoded PID>")

# Test 4: static fallback href still points at /parent (so no-JS
#         clients still land on the hub, just without the PID).
m = re.search(
    r'<a\s+class="pe-back"\s+id="pe-back-link"\s+href="([^"]+)">',
    html)
assert m, "back anchor tag not found in expected shape"
assert m.group(1) == "/parent", \
    f"static href should still be /parent, got {m.group(1)!r}"
print("[4] static href fallback (/parent) preserved for no-JS path")

# Test 5: invalid PID still 403s — route auth untouched.
rv2 = c.get("/parent/evaluations/view?pid=ZZZ_NOT_A_PID_99999")
print(f"[5] GET /parent/evaluations/view?pid=<bogus> -> {rv2.status_code}")
assert rv2.status_code == 403, \
    f"bogus PID should still 403, got {rv2.status_code}"

# Test 6: template shell intact (sanity — empty-state + loader).
for snip in ["pe-status", "pe-content", "جاري التحميل", "PID = "]:
    assert snip in html, f"template shell regression: {snip!r}"
print("[6] template shell (loader + content slot + PID var) intact")

print("\nv2.8.5 evaluations back-button smoke passed.")
