"""C3 smoke — verify the "+ مجلد جديد" stub on /admin/books is
gone and the real bkCreateFolder implementation is intact.

The bug (commit 6e4a4cd): a duplicate `window.bkCreateFolder`
assignment lived ~470 lines below the real implementation in
the same <script>. JS late-binding made the stub win at
runtime, so the button showed an alert "سيتم تفعيل هذا الزر
في C2" instead of opening the create flow.

This test enforces four invariants on the rendered HTML.
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

# ── Invariant 1: the C2 stub message is GONE ──────────────────
STUB = "سيتم تفعيل هذا الزر في C2"
assert STUB not in html, "C2 stub message still present in served HTML"
print("[1] C2 stub Arabic text is gone from served HTML")

# ── Invariant 2: only ONE window.bkCreateFolder assignment ────
# Count actual function-binding occurrences. The explanatory
# comment near where the stub used to live is allowed (it
# mentions the function name in prose, not as an assignment).
assignments = len(re.findall(
    r"window\.bkCreateFolder\s*=\s*function", html))
assert assignments == 1, (
    f"expected exactly 1 window.bkCreateFolder assignment, "
    f"found {assignments}")
print(f"[2] exactly 1 window.bkCreateFolder = function assignment "
      f"(was 2 before fix)")

# ── Invariant 3: the real implementation is intact ────────────
# The real bkCreateFolder POSTs to /api/book-folders with the
# name_ar field. Both must appear in served HTML.
assert "/api/book-folders" in html, "/api/book-folders not in served HTML"
# Look for the POST body shape near the bkCreateFolder definition
real_impl_marker = "name_ar: name"
assert real_impl_marker in html, (
    "real bkCreateFolder impl ({name_ar: name} body) missing")
print("[3] real bkCreateFolder implementation is intact "
      "(POST /api/book-folders with name_ar)")

# ── Invariant 4: the button itself is still present ──────────
assert "+ مجلد جديد" in html, '"+ مجلد جديد" button text missing'
assert 'onclick="bkCreateFolder()"' in html, (
    'button onclick="bkCreateFolder()" missing')
print('[4] button "+ مجلد جديد" + onclick="bkCreateFolder()" present')

# ── Invariant 5 (negative): sibling C4 stub for bkOpenMultiUpload
#    is explicitly out of scope and should still be there ──
C4_STUB = "سيتم تفعيل هذا الزر في C4"
assert C4_STUB in html, (
    "C4 stub message went missing — out-of-scope sibling should "
    "still be present (bkOpenMultiUpload)")
print("[5] C4 sibling stub still present (out-of-scope, untouched)")

print()
print("PASS — add-folder button is wired to the real implementation.")
