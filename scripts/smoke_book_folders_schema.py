"""Phase 1 C5 smoke - book-folders schema + helper.

Tests:
  - book_folders table + columns + indexes
  - book_folder_groups table + UNIQUE constraint + indexes
  - books_v2.folder_id column + idx
  - _can_manage_books truth table
  - Existing books_v2_groups query unchanged
"""
import os, sys, io, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

cleanup_folder_ids = []
cleanup_publish_ids = []

# ── Test 1: book_folders table + columns ──
with A.app.app_context():
    db = A.get_db()
    cols = {dict(c)["name"]: dict(c)["type"]
            for c in db.execute("PRAGMA table_info(book_folders)").fetchall()}
expected = {"id":"INTEGER", "name_ar":"TEXT", "sort_order":"INTEGER",
            "created_by":"INTEGER", "created_by_username":"TEXT",
            "created_at":"TIMESTAMP", "is_active":"INTEGER",
            "notes":"TEXT"}
print(f"[1] book_folders columns: {sorted(cols.keys())}")
for k, t in expected.items():
    assert k in cols, f"missing column {k}"
    assert cols[k] == t, f"{k}: expected {t}, got {cols[k]}"
print("[1a] all 8 expected columns present with correct types ✓")

# ── Test 2: book_folders indexes ──
with A.app.app_context():
    db = A.get_db()
    idx = {dict(r)["name"] for r in db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE tbl_name='book_folders' AND type='index'").fetchall()}
print(f"[2] book_folders indexes: {sorted(idx)}")
assert "idx_book_folders_active" in idx
assert "idx_book_folders_name" in idx

# ── Test 3: book_folder_groups table + UNIQUE ──
with A.app.app_context():
    db = A.get_db()
    cols = {dict(c)["name"]: dict(c)["type"]
            for c in db.execute("PRAGMA table_info(book_folder_groups)").fetchall()}
print(f"[3] book_folder_groups columns: {sorted(cols.keys())}")
for k in ("id","folder_id","group_id","assigned_by",
          "assigned_by_username","assigned_at"):
    assert k in cols, f"missing column {k}"
# Verify UNIQUE constraint by trying a duplicate insert
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT INTO book_folder_groups(folder_id, group_id) VALUES(99999, 88888)")
    db.commit()
    dup_failed = False
    try:
        db.execute("INSERT INTO book_folder_groups(folder_id, group_id) VALUES(99999, 88888)")
        db.commit()
    except Exception:
        dup_failed = True
    db.execute("DELETE FROM book_folder_groups WHERE folder_id=99999")
    db.commit()
print(f"[3a] UNIQUE(folder_id, group_id) enforced? {dup_failed}")
assert dup_failed

# ── Test 4: book_folder_groups indexes ──
with A.app.app_context():
    db = A.get_db()
    idx = {dict(r)["name"] for r in db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE tbl_name='book_folder_groups' AND type='index'").fetchall()}
print(f"[4] book_folder_groups indexes: {sorted(idx)}")
assert "idx_book_folder_groups_folder" in idx
assert "idx_book_folder_groups_group" in idx

# ── Test 5: books_v2.folder_id column + idx + defaults to NULL ──
with A.app.app_context():
    db = A.get_db()
    cols = {dict(c)["name"]: dict(c)["type"]
            for c in db.execute("PRAGMA table_info(books_v2)").fetchall()}
print(f"[5] books_v2.folder_id present? {'folder_id' in cols} | type={cols.get('folder_id')!r}")
assert "folder_id" in cols
# Default check: existing books should all have folder_id IS NULL
with A.app.app_context():
    db = A.get_db()
    nulls = db.execute(
        "SELECT COUNT(*) FROM books_v2 WHERE folder_id IS NULL"
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM books_v2").fetchone()[0]
print(f"[5a] existing books with folder_id IS NULL: {nulls}/{total}")
assert nulls == total, "existing books got non-NULL folder_id — visibility regression!"
# Index
with A.app.app_context():
    db = A.get_db()
    idx_books = {dict(r)["name"] for r in db.execute(
        "SELECT name FROM sqlite_master "
        "WHERE tbl_name='books_v2' AND type='index'").fetchall()}
print(f"[5b] idx_books_v2_folder present? {'idx_books_v2_folder' in idx_books}")
assert "idx_books_v2_folder" in idx_books

# ── Test 6: INSERT a folder → succeeds ──
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO book_folders(name_ar, created_by_username) "
        "VALUES('C5 smoke folder A', 'smoke')")
    db.commit()
    r = db.execute(
        "SELECT id, is_active FROM book_folders "
        "WHERE name_ar='C5 smoke folder A' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    cleanup_folder_ids.append(int(dict(r)["id"]))
    print(f"[6] inserted folder id={cleanup_folder_ids[0]} "
          f"is_active={dict(r)['is_active']}")
    assert int(dict(r)["is_active"]) == 1  # default

# ── Test 7: INSERT same name (different ID) → succeeds (no DB UNIQUE) ──
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO book_folders(name_ar, created_by_username) "
        "VALUES('C5 smoke folder A', 'smoke')")
    db.commit()
    r = db.execute(
        "SELECT id FROM book_folders "
        "WHERE name_ar='C5 smoke folder A' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    cleanup_folder_ids.append(int(dict(r)["id"]))
print(f"[7] same-name folder created with id={cleanup_folder_ids[1]} "
      f"(API-level uniqueness, not DB-level) ✓")
assert cleanup_folder_ids[0] != cleanup_folder_ids[1]

# ── Test 8: Publish folder to group → succeeds ──
fid = cleanup_folder_ids[0]
gid = 5310  # the one existing group in local DB
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO book_folder_groups(folder_id, group_id, "
        "assigned_by_username) VALUES(?,?,'smoke')", (fid, gid))
    db.commit()
    r = db.execute(
        "SELECT id FROM book_folder_groups WHERE folder_id=? AND group_id=?",
        (fid, gid)).fetchone()
    cleanup_publish_ids.append(int(dict(r)["id"]))
print(f"[8] publish (folder={fid}, group={gid}) succeeded "
      f"id={cleanup_publish_ids[0]}")

# ── Test 9: Re-publish same (folder, group) → fails (UNIQUE) ──
with A.app.app_context():
    db = A.get_db()
    dup_failed = False
    try:
        db.execute(
            "INSERT INTO book_folder_groups(folder_id, group_id) "
            "VALUES(?,?)", (fid, gid))
        db.commit()
    except Exception:
        dup_failed = True
print(f"[9] duplicate publish blocked by UNIQUE? {dup_failed}")
assert dup_failed

# ── Test 10: existing books_v2_groups query unchanged ──
# Run the exact query the student-view endpoint uses; verify it
# still returns the same single row we had before this phase.
with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT DISTINCT b.id, b.uploaded_at FROM books_v2 b "
        "JOIN books_v2_groups bg ON bg.book_id=b.id "
        "WHERE bg.group_id IN (5310) "
        "AND COALESCE(b.is_deleted,0)=0").fetchall()
print(f"[10] existing student-view query still returns {len(rows)} rows "
      "(unchanged from pre-phase)")
assert len(rows) == 1

# ── Test 11: _can_manage_books truth table ──
cases = [
    ({'role':'admin','username':'admin'}, True),
    ({'role':'manager','username':'010307885'}, True),
    ({'role':'manager','username':'980909805'}, True),
    ({'role':'admin','username':'021005931'}, True),
    ({'role':'teacher','username':'040507718'}, False),
    ({'role':'teacher','username':'teacher1'}, False),
    ({'role':'reception','username':'reception'}, False),
    ({}, False),
    (None, False),
]
print(f"[11] _can_manage_books truth table:")
for u, exp in cases:
    got = A._can_manage_books(u)
    ok = "✓" if got == exp else "✗"
    print(f"     {ok} {u} -> {got} (expected {exp})")
    assert got == exp

# ── Test 12: 8-route admin regression ──
c = A.app.test_client()
c.post('/login', data={'username':'admin','password':'admin123'},
       follow_redirects=False)
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database',
          '/admin/books']:
    rv = c.get(p)
    print(f"[12] {p} -> {rv.status_code}")
    assert rv.status_code == 200, f"{p} regressed"

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    for pid in cleanup_publish_ids:
        db.execute("DELETE FROM book_folder_groups WHERE id=?", (pid,))
    for fid in cleanup_folder_ids:
        db.execute("DELETE FROM book_folders WHERE id=?", (fid,))
    db.commit()

print("\nPhase 1 schema smoke passed.")
