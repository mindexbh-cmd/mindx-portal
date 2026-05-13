"""Smoke for the chunked-upload feature (v2.9.5).

Eight invariants on the running app:

  [1] All four endpoints exist:
        POST /api/books/upload/init
        POST /api/books/upload/chunk
        POST /api/books/upload/finalize
        GET  /api/books/upload/status
  [2] Server constants are at expected values:
        _CHUNKED_CHUNK_SIZE       == 5 MB
        _CHUNKED_CHUNK_HARD_CAP   == 6 MB
        _CHUNKED_MAX_TOTAL_BYTES  == 150 MB
        _CHUNKED_MAX_CHUNKS       == 30
        _CHUNKED_SESSION_TTL_SEC  == 3600
  [3] upload_sessions table exists in the live SQLite DB
  [4] upload_sessions registered in _TBL_AUDIT_FEATURE
        (so it doesn't surface as a Category-D orphan)
  [5] ChunkedUploader JS class is in served HTML, with all five
      protocol methods on the prototype (start, _init, _tryResume,
      _sendChunk, _finalize)
  [6] Per-file progress UI elements exist in the multi-upload modal:
        bk-up-prog-{idx}, bk-up-bar-{idx}, bk-up-status-{idx},
        bkUpFileSetProgress(), bkUpFileSetStatus()
  [7] Resume detection (C6): banner element + render function +
      Arabic banner text + localStorage key prefix all present
  [8] bkUpSubmit drives ChunkedUploader (C7): no leftover
      fetch('/api/books/upload-multi') in bkUpSubmit; new
      sequential uploadOne() helper present
"""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A  # noqa: E402


# ── Invariant 1: endpoints registered ──────────────────────────────
seen = {str(r.rule) for r in A.app.url_map.iter_rules()}
must_have = [
    "/api/books/upload/init",
    "/api/books/upload/chunk",
    "/api/books/upload/finalize",
    "/api/books/upload/status",
]
missing = [e for e in must_have if e not in seen]
assert not missing, f"missing endpoints: {missing}"
print(f"[1] all 4 chunked-upload endpoints wired: {must_have}")


# ── Invariant 2: constants ─────────────────────────────────────────
const_checks = [
    ("_CHUNKED_CHUNK_SIZE",       5 * 1024 * 1024),
    ("_CHUNKED_CHUNK_HARD_CAP",   6 * 1024 * 1024),
    ("_CHUNKED_MAX_TOTAL_BYTES",  150 * 1024 * 1024),
    ("_CHUNKED_MAX_CHUNKS",       30),
    ("_CHUNKED_SESSION_TTL_SEC",  3600),
]
for name, expected in const_checks:
    actual = getattr(A, name, None)
    assert actual == expected, f"{name} = {actual!r}, expected {expected!r}"
print(f"[2] all {len(const_checks)} chunked-upload constants at expected values")


# ── Invariant 3: upload_sessions table exists ──────────────────────
with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='upload_sessions'").fetchall()
    assert rows, "upload_sessions table missing from live DB"
    cols = {dict(r).get("name"): dict(r).get("type")
            for r in db.execute("PRAGMA table_info(upload_sessions)").fetchall()}
    expected_cols = {"id", "user_id", "filename", "total_size",
                     "total_chunks", "received_chunks", "title",
                     "folder_id", "created_at", "expires_at"}
    missing_cols = expected_cols - set(cols)
    assert not missing_cols, f"upload_sessions missing columns: {missing_cols}"
print(f"[3] upload_sessions table present with all 10 expected columns")


# ── Invariant 4: registered in _TBL_AUDIT_FEATURE ──────────────────
audit_feature = getattr(A, "_TBL_AUDIT_FEATURE", {})
assert "upload_sessions" in audit_feature, (
    "upload_sessions not in _TBL_AUDIT_FEATURE — will fire orphan-table "
    "warning on every boot")
print(f"[4] upload_sessions registered in _TBL_AUDIT_FEATURE: "
      f"{audit_feature['upload_sessions']!r}")


# ── Invariant 5–8: served HTML markers ─────────────────────────────
c = A.app.test_client()
r = c.post("/login", data={"username": "admin", "password": "admin123"},
           follow_redirects=False)
assert r.status_code in (200, 302), f"login failed: {r.status_code}"
r = c.get("/admin/books")
assert r.status_code == 200, f"/admin/books status {r.status_code}"
html = r.get_data(as_text=True)


# ── Invariant 5: ChunkedUploader class + all 5 prototype methods ──
proto_markers = [
    "function ChunkedUploader(file, options)",
    "ChunkedUploader.prototype.start",
    "ChunkedUploader.prototype._init",
    "ChunkedUploader.prototype._tryResume",
    "ChunkedUploader.prototype._sendChunk",
    "ChunkedUploader.prototype._finalize",
    "window.ChunkedUploader = ChunkedUploader",
]
for m in proto_markers:
    assert m in html, f"missing JS marker: {m!r}"
print(f"[5] ChunkedUploader class + all 5 prototype methods in served HTML")


# ── Invariant 6: per-file progress UI ──────────────────────────────
ui_markers = [
    "bk-up-prog-",
    "bk-up-bar-",
    "bk-up-status-",
    "bk-up-pct-",
    "window.bkUpFileSetProgress",
    "window.bkUpFileSetStatus",
    "bk-up-file-progress",
    "bk-up-prog-bar",
]
for m in ui_markers:
    assert m in html, f"missing per-file progress marker: {m!r}"
print(f"[6] per-file progress UI elements + mutators present "
      f"({len(ui_markers)} markers)")


# ── Invariant 7: resume detection (C6) ─────────────────────────────
resume_markers = [
    'id="bk-up-resume-banner"',
    "window.bkUpRenderResumeBanner",
    "window.bkUpResumeAccept",
    "window.bkUpResumeDismiss",
    "_bkResumeListEntries",
    "bk_upload_resume_",
    # Arabic banner copy lives inside a JS template; the Unicode
    # codepoints survive the round-trip through the served HTML.
    "يوجد رفع غير "
    "مكتمل",   # "يوجد رفع غير مكتمل"
]
for m in resume_markers:
    assert m in html, f"missing resume-detection marker: {m!r}"
print(f"[7] resume-detection elements + Arabic banner copy present "
      f"({len(resume_markers)} markers)")


# ── Invariant 8: bkUpSubmit drives ChunkedUploader (C7) ───────────
c7_markers = [
    "function uploadOne(idx)",
    "new window.ChunkedUploader(f",
    "inheritFolderGroups: inherit",
    "statusText(s)",
]
for m in c7_markers:
    assert m in html, f"missing bkUpSubmit C7 marker: {m!r}"
# The legacy single-shot fetch must NOT be wired into bkUpSubmit
# anymore. The route itself stays as a fallback — this only checks
# the modal handler path.
assert "fetch('/api/books/upload-multi'" not in html, (
    "bkUpSubmit still posts to /api/books/upload-multi — "
    "the chunked-upload migration is incomplete")
# But the legacy ROUTE should still exist as a fallback
assert "/api/books/upload-multi" in seen, (
    "/api/books/upload-multi route was deleted; brief said keep it")
print(f"[8] bkUpSubmit drives ChunkedUploader sequentially "
      f"({len(c7_markers)} markers); legacy /upload-multi route "
      f"intact as fallback")


print()
print("PASS — chunked upload (v2.9.5) is wired end-to-end: server "
      "endpoints + table + audit registration + JS class + progress UI + "
      "resume banner + bkUpSubmit driver.")
