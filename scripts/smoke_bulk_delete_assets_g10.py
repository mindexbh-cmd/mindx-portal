"""G10.3 — verify POST /api/assets/bulk-delete behaves correctly
across the 5 operator-specified scenarios.

Flask test client against a tmp SQLite. Two roles seeded:
  admin_g10  — role=admin (passes _can_access_expenses)
  parent_g10 — role=parent (must fail with 403)

Scenarios:
  S1 — happy path: seed 5 assets, delete 3 → response says
       deleted=3 and only 2 remain in the DB.
  S2 — empty ids array → HTTP 400 "قائمة المعرفات مطلوبة".
  S3 — mix of existing + non-existent IDs → only existing rows
       get deleted, response.deleted reflects actual count.
  S4 — non-admin role (parent) → HTTP 403 "غير مصرح".
  S5 — backup artefact: after a successful delete, a JSON file
       lands in scripts/backups/ and contains the affected
       rows' metadata (sans image_bytes).
"""
import os
import sys
import sqlite3
import tempfile
import glob
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_g10_smoke.db")
BACKUP_DIR = os.path.join(REPO, "scripts", "backups")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-g10")
sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    db.executemany(
        "INSERT INTO users(username, password, role) VALUES(?,?,?)",
        [
            ("admin_g10",  appmod.hp("G10pwd!"), "admin"),
            ("parent_g10", appmod.hp("G10pwd!"), "parent"),
        ],
    )
    # 5 test assets — explicit ids so we know which to target.
    rows = []
    for i in range(1, 6):
        rows.append((1000 + i, "Asset " + str(i), "electronics",
                     "good", "admin_g10"))
    db.executemany(
        "INSERT INTO assets(id, name_ar, category, condition, "
        "                   created_by_username) VALUES(?,?,?,?,?)",
        rows,
    )
    db.commit()
    db.close()


def _login(c, username, password):
    r = c.post("/login", data={"username": username, "password": password})
    assert r.status_code in (200, 302), "login " + username + " failed: " + str(r.status_code)


def _ids_in_db():
    db = sqlite3.connect(TMP_DB)
    out = [int(r[0]) for r in db.execute("SELECT id FROM assets ORDER BY id").fetchall()]
    db.close()
    return out


def main() -> int:
    pre_backups = set(glob.glob(os.path.join(BACKUP_DIR, "assets_bulk_delete_*.json"))) \
                  if os.path.exists(BACKUP_DIR) else set()
    _seed()
    failures: list[str] = []

    # ── S1 — admin deletes 3 of 5
    c_admin = appmod.app.test_client()
    _login(c_admin, "admin_g10", "G10pwd!")
    r = c_admin.post("/api/assets/bulk-delete",
                     json={"ids": [1001, 1002, 1003]})
    d = r.get_json() or {}
    if r.status_code != 200 or not d.get("ok"):
        failures.append("S1: HTTP " + str(r.status_code) + " body " + str(d))
    if d.get("deleted") != 3:
        failures.append("S1: deleted expected 3, got " + str(d.get("deleted")))
    remaining = _ids_in_db()
    if remaining != [1004, 1005]:
        failures.append("S1: remaining ids expected [1004,1005], got " + str(remaining))

    # ── S2 — empty ids array → 400
    r = c_admin.post("/api/assets/bulk-delete", json={"ids": []})
    if r.status_code != 400:
        failures.append("S2: empty ids expected 400, got " + str(r.status_code))

    # ── S3 — mix of existing + non-existent (1004 exists, 9999 doesn't)
    r = c_admin.post("/api/assets/bulk-delete",
                     json={"ids": [1004, 9999, 12345]})
    d = r.get_json() or {}
    if r.status_code != 200 or not d.get("ok"):
        failures.append("S3: HTTP " + str(r.status_code) + " body " + str(d))
    # Only 1004 existed
    if d.get("deleted") != 1:
        failures.append("S3: deleted expected 1, got " + str(d.get("deleted")))
    if d.get("ids") != [1004]:
        failures.append("S3: ids expected [1004], got " + str(d.get("ids")))
    remaining = _ids_in_db()
    if remaining != [1005]:
        failures.append("S3: remaining ids expected [1005], got " + str(remaining))

    # ── S4 — non-admin role → 403
    c_parent = appmod.app.test_client()
    _login(c_parent, "parent_g10", "G10pwd!")
    r = c_parent.post("/api/assets/bulk-delete",
                      json={"ids": [1005]})
    if r.status_code != 403:
        failures.append("S4: parent expected 403, got " + str(r.status_code))

    # ── S5 — backup file written
    post_backups = set(glob.glob(os.path.join(BACKUP_DIR, "assets_bulk_delete_*.json")))
    new_files = post_backups - pre_backups
    if not new_files:
        failures.append("S5: no backup file created in " + BACKUP_DIR)
    else:
        latest = max(new_files)
        try:
            with open(latest, encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as ex:
            failures.append("S5: backup unreadable: " + str(ex))
            payload = {}
        if payload.get("operation") != "assets_bulk_delete":
            failures.append("S5: backup operation field wrong")
        if payload.get("actor") != "admin_g10":
            failures.append("S5: backup actor expected admin_g10, got "
                            + str(payload.get("actor")))
        # The latest backup corresponds to S3 (single 1004 deletion).
        if payload.get("row_count") != 1:
            failures.append("S5: latest backup row_count expected 1, got "
                            + str(payload.get("row_count")))
        rows_blob = payload.get("rows") or []
        if not rows_blob or rows_blob[0].get("id") != 1004:
            failures.append("S5: latest backup doesn't contain row 1004")
        # Image bytes must NOT be in the backup
        if rows_blob and "image_bytes" in rows_blob[0]:
            failures.append("S5: image_bytes leaked into backup")
        # Clean up our test backups so we don't pollute the dir
        for f in new_files:
            try: os.remove(f)
            except Exception: pass

    if failures:
        print("[G10] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G10] PASS — happy-path delete, empty-ids rejected, missing "
          "ids skipped gracefully, non-admin blocked, backup JSON "
          "written with correct shape (no image_bytes leak).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
