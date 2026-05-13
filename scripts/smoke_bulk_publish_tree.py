"""Smoke test — admin/books bulk-publish tree feature (v2.9.7).

Invariants enforced:
  [1] POST /api/books/bulk-publish is registered.
  [2] GET  /api/books/all-with-folders is registered.
  [3] ADMIN_BOOKS_HTML contains the modal IDs the JS expects
      (bkBpBack, bkBpTree, bkBpGroups, bkBpExecute, bkBpPreview,
       bkBpBookCount, bkBpGroupCount, bkBpAllBooks, bkBpAllGroups).
  [4] All required window-level handlers are defined exactly once
      in ADMIN_BOOKS_HTML (anti late-binding): openBulkPublish,
      closeBulkPublish, executeBulkPublish, bkBpToggleAllBooks,
      bkBpToggleAllGroups, bkBpToggleFolder, bkBpToggleFolderBooks.
  [5] Top-level button calls openBulkPublish() in the rendered HTML.
  [6] Existing 'نشر للمجموعات' folder-level button still emitted by
      the renderer (regression guard — the old feature must not have
      been collateral-damaged).
  [7] The new endpoints route to handlers that read book_ids /
      group_ids from the JSON body (handler bodies sanity-check).
  [8] app.py parses + imports cleanly with the new code in place.

Run from repo root:  python scripts/smoke_bulk_publish_tree.py
Exits 0 on pass; raises on any invariant violation.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

# ── Invariant 8: app imports cleanly ─────────────────────────────
import app  # noqa: E402,F401
print("[8] app.py imports without raising")

# ── Invariant 1 + 2: routes registered ───────────────────────────
rules = {(r.rule, tuple(sorted(r.methods - {"OPTIONS", "HEAD"})))
         for r in app.app.url_map.iter_rules()}
bp_rule = ("/api/books/bulk-publish", ("POST",))
awf_rule = ("/api/books/all-with-folders", ("GET",))
assert bp_rule in rules, ("POST /api/books/bulk-publish missing from "
                          "Flask url_map")
print("[1] POST /api/books/bulk-publish registered")
assert awf_rule in rules, ("GET /api/books/all-with-folders missing "
                            "from Flask url_map")
print("[2] GET /api/books/all-with-folders registered")

# ── Invariant 3: modal element IDs present in the HTML blob ──────
required_ids = [
    "bkBpBack", "bkBpTree", "bkBpGroups", "bkBpExecute",
    "bkBpPreview", "bkBpBookCount", "bkBpGroupCount",
    "bkBpAllBooks", "bkBpAllGroups",
]
missing_ids = [i for i in required_ids if 'id="' + i + '"' not in SRC]
assert not missing_ids, ("modal HTML missing element ids: " +
                          str(missing_ids))
print("[3] Modal element IDs present: " + ", ".join(required_ids))

# ── Invariant 4: window handlers defined exactly once ────────────
required_handlers = [
    "openBulkPublish", "closeBulkPublish", "executeBulkPublish",
    "bkBpToggleAllBooks", "bkBpToggleAllGroups",
    "bkBpToggleFolder", "bkBpToggleFolderBooks",
]
for h in required_handlers:
    pat = re.compile(r"window\." + re.escape(h) + r"\s*=\s*function")
    matches = pat.findall(SRC)
    assert len(matches) == 1, (
        "handler window." + h + " defined " + str(len(matches))
        + " times in app.py (expected exactly 1)")
print("[4] All handlers defined exactly once: "
      + ", ".join(required_handlers))

# ── Invariant 5: top-level button calls openBulkPublish ─────────
# Render admin/books HTML through Flask test client to confirm
# the button reaches the user (not just present in source).
with app.app.test_client() as c:
    # Bypass auth by mutating the session to look like an admin.
    with c.session_transaction() as sess:
        sess["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.get("/admin/books")
assert rv.status_code == 200, ("/admin/books returned "
                                + str(rv.status_code))
html = rv.get_data(as_text=True)
assert 'onclick="openBulkPublish()"' in html, (
    "top-level bulk-publish button missing from rendered "
    "/admin/books HTML")
print("[5] Top-level openBulkPublish() button present in "
      "/admin/books rendered HTML")

# ── Invariant 6: legacy folder-publish renderer intact ──────────
assert "bkOpenPublish(' + folder.id + ')" in SRC, (
    "existing folder-level 'نشر للمجموعات' button removed — that "
    "feature must remain alongside the new top-level button")
print("[6] Existing folder-level publish button still emitted")

# ── Invariant 7: handler reads book_ids / group_ids ────────────
bp_idx = SRC.index("def api_books_v2_bulk_publish")
bp_body = SRC[bp_idx:bp_idx + 4000]
assert "book_ids" in bp_body and "group_ids" in bp_body, (
    "api_books_v2_bulk_publish handler doesn't reference "
    "book_ids / group_ids — implementation drift")
assert "INSERT OR IGNORE INTO books_v2_groups" in bp_body, (
    "api_books_v2_bulk_publish must use INSERT OR IGNORE INTO "
    "books_v2_groups (additive). Pattern not found.")
print("[7] api_books_v2_bulk_publish reads book_ids+group_ids, "
      "uses INSERT OR IGNORE INTO books_v2_groups")

print("")
print("All 8 invariants passed.")
