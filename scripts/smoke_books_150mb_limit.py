"""Smoke for the 150 MB book-upload limit change.

Six invariants on the running app + the deploy config:

  [1] _BOOKS_V2_MAX_BYTES == 150 * 1024 * 1024 (157286400)
  [2] _BOOKS_V2_MULTI_MAX_BYTES == 150 * 1024 * 1024
  [3] Rendered /admin/books HTML carries the new 150 MB JS check
      AND the new Arabic strings
  [4] No leftover "20 ميجا" / "50 ميجا" strings in served HTML
  [5] gunicorn config (Procfile + render.yaml) uses --timeout 300
  [6] Upload endpoints still wired (no regression — routes resolve)
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A  # noqa: E402

EXPECTED = 150 * 1024 * 1024   # 157,286,400 bytes


# ── Invariant 1: single-upload constant ─────────────────────────
assert A._BOOKS_V2_MAX_BYTES == EXPECTED, (
    f"_BOOKS_V2_MAX_BYTES = {A._BOOKS_V2_MAX_BYTES}, expected {EXPECTED}")
print(f"[1] _BOOKS_V2_MAX_BYTES == {EXPECTED:,} bytes (= 150 MB)")


# ── Invariant 2: multi-upload constant ──────────────────────────
assert A._BOOKS_V2_MULTI_MAX_BYTES == EXPECTED, (
    f"_BOOKS_V2_MULTI_MAX_BYTES = {A._BOOKS_V2_MULTI_MAX_BYTES}, "
    f"expected {EXPECTED}")
print(f"[2] _BOOKS_V2_MULTI_MAX_BYTES == {EXPECTED:,} bytes (= 150 MB)")


# ── Invariant 3: rendered /admin/books carries new markers ─────
c = A.app.test_client()
r = c.post("/login", data={"username": "admin", "password": "admin123"},
           follow_redirects=False)
assert r.status_code in (200, 302), f"login failed: {r.status_code}"
r = c.get("/admin/books")
assert r.status_code == 200, f"/admin/books status {r.status_code}"
html = r.get_data(as_text=True)

expected_markers = [
    "150 * 1024 * 1024",                        # JS literal somewhere
    "150*1024*1024",                            # JS literal alt spacing
    "150 ميغا",                                  # Arabic hint at least once
    "حد أقصى 150 ميغا",                          # single-upload label
    "الحد الأقصى 150 ميغا",                       # multi-upload drop-zone hint
    'onclick="bkOpenMultiUpload()"',            # regression-guard from v2.9.2
]
for m in expected_markers:
    assert m in html, f"missing marker in served HTML: {m!r}"
print(f"[3] all {len(expected_markers)} expected 150 MB markers in served HTML")


# ── Invariant 4: zero leftover old-limit strings ────────────────
# Use word boundaries on the JS literals — "50 * 1024 * 1024" is a
# substring of "150 * 1024 * 1024", so a naive `in` check would
# spuriously flag the new value. Arabic strings don't need that
# care (no Arabic letter wraps the digit "50"/"20" by accident in
# the books area).
leftover_re_patterns = [
    r"(?<!\d)20\s*\*\s*1024\s*\*\s*1024",
    r"(?<!\d)50\s*\*\s*1024\s*\*\s*1024",
]
leftover_str_patterns = ["20 ميجا", "50 ميجا"]
leftovers = []
for pat in leftover_re_patterns:
    if re.search(pat, html):
        leftovers.append(pat)
for s in leftover_str_patterns:
    if s in html:
        leftovers.append(s)
assert not leftovers, f"leftover old-limit strings in served HTML: {leftovers}"
print(f"[4] no leftover '20 ميجا' / '50 ميجا' / 20|50 MB JS literals "
      "(word-boundary checked so '150 * 1024 * 1024' doesn't trip)")


# ── Invariant 5: gunicorn --timeout 300 in both deploy files ────
repo_root = os.path.dirname(os.path.abspath(__file__)) + "/.."
procfile = open(os.path.join(repo_root, "Procfile"), encoding="utf-8").read()
render_yml = open(os.path.join(repo_root, "render.yaml"), encoding="utf-8").read()
# Match the gunicorn line specifically — not the inline comment in
# render.yaml which has now been rewritten to also reference 300.
m_proc = re.search(r"gunicorn[^\n]*--timeout\s+(\d+)", procfile)
m_rend = re.search(r"startCommand:\s+gunicorn[^\n]*--timeout\s+(\d+)", render_yml)
assert m_proc and m_proc.group(1) == "300", (
    f"Procfile gunicorn --timeout = {m_proc and m_proc.group(1)} "
    "(expected 300)")
assert m_rend and m_rend.group(1) == "300", (
    f"render.yaml gunicorn --timeout = {m_rend and m_rend.group(1)} "
    "(expected 300)")
# Belt-and-suspenders: no stale "--timeout 120" anywhere
assert "--timeout 120" not in procfile, "Procfile still references --timeout 120"
assert "--timeout 120" not in render_yml, "render.yaml still references --timeout 120"
print("[5] gunicorn --timeout = 300 in BOTH Procfile and render.yaml, "
      "no stale --timeout 120")


# ── Invariant 6: upload endpoints still resolve (no regression) ─
endpoints_seen = {str(rule.rule) for rule in A.app.url_map.iter_rules()}
must_have = ["/api/books/upload", "/api/books/upload-multi",
             "/api/books/<int:bid>/reupload"]
missing = [e for e in must_have if e not in endpoints_seen]
assert not missing, f"upload endpoints missing from url_map: {missing}"
print(f"[6] all 3 upload endpoints still wired "
      "(/upload, /upload-multi, /<bid>/reupload)")


print()
print("PASS — 150 MB limit landed cleanly across server + client + UI + "
      "deploy config.")
