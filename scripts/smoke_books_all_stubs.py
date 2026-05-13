"""C3 smoke — all ADMIN_BOOKS_HTML Phase-3 stubs are gone.

Builds on smoke_books_add_folder_button.py (which covered only
the C2 stub). After v2.9.2, every "سيتم تفعيل هذا الزر …"
placeholder in /admin/books has been replaced by the real
handler that lives earlier in the same script. This test
enforces that invariant going forward.

Strategy:
  1. Pull /admin/books rendered HTML
  2. Assert zero "سيتم تفعيل" stub strings
  3. Assert each window.bk* function has exactly one assignment
     (no late-binding duplicates → no future C-phase stubs can
     shadow real handlers)
  4. Spot-check the two specific buttons + their handlers +
     the modals/endpoints they reach
"""
import os
import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A  # noqa: E402

c = A.app.test_client()
r = c.post("/login", data={"username": "admin", "password": "admin123"},
           follow_redirects=False)
assert r.status_code in (200, 302), f"login failed: {r.status_code}"

r = c.get("/admin/books")
assert r.status_code == 200, f"/admin/books status {r.status_code}"
html = r.get_data(as_text=True)


# ── Invariant 1: zero stub strings remain ────────────────────
STUB_PHRASE = "سيتم تفعيل هذا الزر"
stub_count = html.count(STUB_PHRASE)
assert stub_count == 0, (
    f'found {stub_count} occurrence(s) of "{STUB_PHRASE}" in served '
    f'HTML — every Phase-N placeholder must be removed')
print(f"[1] zero 'سيتم تفعيل هذا الزر' stub strings in served HTML")


# ── Invariant 2: no duplicate window.bk* assignments ─────────
# Late-binding (same global key reassigned later in the same
# <script>) is how the C2 + C4 stubs hid the real handlers. If
# any future stub repeats the pattern, this assert catches it.
assigns = re.findall(r"window\.(bk[A-Za-z]+)\s*=\s*function", html)
from collections import Counter
counts = Counter(assigns)
dupes = {name: n for name, n in counts.items() if n > 1}
assert not dupes, (
    f"window.bk* late-binding duplicates found: {dupes} — every "
    f"name must be assigned exactly once in ADMIN_BOOKS_HTML")
print(f"[2] no duplicate window.bk* assignments "
      f"({len(counts)} unique handlers, all single-assignment)")


# ── Invariant 3: specific buttons + handlers + reachable APIs

# 3a. C2 stub fix — "+ مجلد جديد" + bkCreateFolder + POST /api/book-folders
assert "+ مجلد جديد" in html
assert 'onclick="bkCreateFolder()"' in html
assert "/api/book-folders" in html
assert "name_ar: name" in html      # real impl POST body shape
print("[3a] C2 fix intact — '+ مجلد جديد' wired to bkCreateFolder")

# 3b. C4 stub fix — bkOpenMultiUpload wired, bk-up-modal present
assert "📤 رفع كتب" in html
assert "+ ارفع أول كتاب" in html
assert 'onclick="bkOpenMultiUpload()"' in html
assert 'id="bk-up-modal"' in html
assert "/api/books/upload-multi" in html
print("[3b] C4 fix intact — '📤 رفع كتب' + '+ ارفع أول كتاب' "
      "wired to bkOpenMultiUpload (opens bk-up-modal, posts to "
      "/api/books/upload-multi)")


# ── Invariant 4: every onclick attribute points to a real handler

# Pull every onclick="bkXxx(...)" reference and verify the
# function name appears in the served JS as a window assignment.
button_handlers = set(re.findall(
    r'onclick="(bk[A-Za-z]+)\s*\(', html))
defined = set(assigns)
# A small allowlist of inline-only handlers that are defined as
# local consts inside the IIFE (not window-scoped) — these are
# allowed to not appear in `defined`.
INLINE_OK = {"bkUpAddFiles"}  # populated by drag-drop handlers
missing = button_handlers - defined - INLINE_OK
if missing:
    # Tolerate any that are at least mentioned somewhere in the
    # served JS (might be defined as `function bkXxx()` rather
    # than `window.bkXxx = function`).
    really_missing = {
        h for h in missing
        if not re.search(r"function\s+" + re.escape(h) + r"\s*\(", html)
    }
    assert not really_missing, (
        f"onclick handlers with no definition in served JS: "
        f"{really_missing}")
print(f"[4] all {len(button_handlers)} onclick='bkXxx()' attributes "
      f"resolve to defined handlers")


print()
print("PASS — all ADMIN_BOOKS_HTML stubs are gone and no late-binding "
      "duplicates remain.")
