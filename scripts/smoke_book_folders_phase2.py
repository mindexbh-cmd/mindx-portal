"""Phase 2 C10 smoke - book-folders API endpoint coverage.

Exercises all 9 new endpoints + 4-role permission matrix +
E2E scenarios from the spec.
"""
import os, sys, io, json, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# ── Provision test users with known passwords ──
USERS = [
    ("admin",      "admin123",  "admin",     None),
    ("980909805",  "raed_pw",   "manager",   "رائد"),
    ("010307885",  "ahib_pw",   "manager",   "أحمد إبراهيم"),
    ("021005931",  "younis_pw", "admin",     "أحمد يونس"),  # admin role
    ("teacher1",   "tea123",    "teacher",   None),         # blocked
]
with A.app.app_context():
    db = A.get_db()
    for uname, pw, role, name in USERS:
        ex = db.execute("SELECT id FROM users WHERE username=?",
                        (uname,)).fetchone()
        if ex:
            db.execute(
                "UPDATE users SET password=?, role=?, is_active=1, "
                "can_be_assigned_tasks=1 WHERE username=?",
                (A.hp(pw), role, uname))
        else:
            db.execute(
                "INSERT INTO users(username, password, role, name, "
                "is_active, can_be_assigned_tasks) VALUES(?,?,?,?,1,1)",
                (uname, A.hp(pw), role, name))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

def J(rv):
    try: return rv.get_json()
    except Exception: return None

cleanup_folder_ids = []
cleanup_book_ids = []

# ============================================================
# Scenario A — Folder lifecycle (create/list/rename/delete)
# ============================================================
print("\n=== Scenario A — folder lifecycle ===")
login("admin", "admin123")

rv = c.post("/api/book-folders",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"name_ar": "smoke ترم 1", "sort_order": 10}))
j = J(rv); assert rv.status_code == 200, j
folder_a = j["folder"]["id"]; cleanup_folder_ids.append(folder_a)
print(f"[A.1] admin creates folder → 200, id={folder_a}")

login("980909805", "raed_pw")
rv = c.post("/api/book-folders",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"name_ar": "smoke اختبارات"}))
j = J(rv); assert rv.status_code == 200
folder_b = j["folder"]["id"]; cleanup_folder_ids.append(folder_b)
print(f"[A.2] raed creates folder → 200, id={folder_b}")

login("admin", "admin123")
rv = c.get("/api/book-folders?active_only=1")
j = J(rv)
my = [f for f in j["folders"] if f["id"] in (folder_a, folder_b)]
assert len(my) == 2
assert all(f["book_count"] == 0 for f in my)
print(f"[A.3] list returns both new folders (book_count=0 each)")

rv = c.patch(f"/api/book-folders/{folder_a}",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"name_ar": "smoke الفصل الأول"}))
j = J(rv); assert rv.status_code == 200
print(f"[A.4] rename → 200")

# Duplicate name → 400
rv = c.patch(f"/api/book-folders/{folder_b}",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"name_ar": "smoke الفصل الأول"}))
j = J(rv)
print(f"[A.5] duplicate name → {rv.status_code} err={j.get('error')!r}")
assert rv.status_code == 400

# Empty folder delete → 200 soft delete
rv = c.delete(f"/api/book-folders/{folder_b}")
j = J(rv)
print(f"[A.6] delete empty folder → {rv.status_code} {j}")
assert rv.status_code == 200 and j["soft_deleted"] is True

# Verify deleted folder hidden when active_only=1
rv = c.get("/api/book-folders?active_only=1")
j = J(rv)
ids_visible = {f["id"] for f in j["folders"]}
assert folder_b not in ids_visible
print(f"[A.7] active_only=1 hides soft-deleted folder ✓")

# active_only=0 includes it
rv = c.get("/api/book-folders?active_only=0")
j = J(rv)
assert folder_b in {f["id"] for f in j["folders"]}
print(f"[A.7b] active_only=0 shows soft-deleted folder ✓")

# Patching a soft-deleted folder → 404
rv = c.patch(f"/api/book-folders/{folder_b}",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"name_ar": "x"}))
print(f"[A.8] patch soft-deleted → {rv.status_code}")
assert rv.status_code == 404

# ============================================================
# Scenario B — Publishing + propagation
# ============================================================
print("\n=== Scenario B — publishing propagation ===")

# Create a fresh folder for B + seed 2 books inside it
rv = c.post("/api/book-folders",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"name_ar": "smoke Pub Folder"}))
folder_c = J(rv)["folder"]["id"]; cleanup_folder_ids.append(folder_c)

with A.app.app_context():
    db = A.get_db()
    for title in ("Pub Book 1", "Pub Book 2"):
        cur = db.execute(
            "INSERT INTO books_v2(title, description, file_path, "
            "file_size_bytes, can_download, uploaded_by_username, "
            "uploaded_at, is_deleted, folder_id) "
            "VALUES(?,?,?,100,1,'smoke',CURRENT_TIMESTAMP,0,?)",
            (title, "", "", folder_c))
        try: bid = int(cur.lastrowid)
        except Exception: bid = 0
        if not bid:
            r = db.execute(
                "SELECT id FROM books_v2 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            bid = int(dict(r)["id"]) if r else 0
        if bid: cleanup_book_ids.append(bid)
    db.commit()
print(f"[B.1] created 2 books in folder {folder_c}: {cleanup_book_ids[-2:]}")

GID = 5310   # the one group existing on local DB

# Need 2 more groups to do the diff test. Create them.
extra_group_ids = []
with A.app.app_context():
    db = A.get_db()
    for gname in ("smoke pub group A", "smoke pub group B"):
        db.execute(
            "INSERT INTO student_groups(group_name) VALUES(?)", (gname,))
        r = db.execute(
            "SELECT id FROM student_groups WHERE group_name=? "
            "ORDER BY id DESC LIMIT 1", (gname,)).fetchone()
        extra_group_ids.append(int(dict(r)["id"]))
    db.commit()
G_A, G_B = extra_group_ids
print(f"[B.1b] created groups G_A={G_A}, G_B={G_B}")

# PUT folder's groups to [G_A, G_B]
rv = c.put(f"/api/book-folders/{folder_c}/groups",
           headers={"Content-Type": "application/json"},
           data=json.dumps({"group_ids": [G_A, G_B]}))
j = J(rv)
print(f"[B.2] PUT publish [{G_A},{G_B}] → {rv.status_code} {j}")
assert rv.status_code == 200
assert set(j["added"]) == {G_A, G_B}
assert j["books_affected"] == 2

# Verify books_v2_groups has 4 entries (2 books × 2 groups)
with A.app.app_context():
    db = A.get_db()
    cnt = int(db.execute(
        "SELECT COUNT(*) FROM books_v2_groups "
        "WHERE book_id IN (?,?) AND group_id IN (?,?)",
        (cleanup_book_ids[-2], cleanup_book_ids[-1], G_A, G_B)).fetchone()[0])
print(f"[B.3] books_v2_groups propagation count: {cnt} (expected 4)")
assert cnt == 4

# Re-publish to [G_A, GID] — G_B removed, GID added
rv = c.put(f"/api/book-folders/{folder_c}/groups",
           headers={"Content-Type": "application/json"},
           data=json.dumps({"group_ids": [G_A, GID]}))
j = J(rv)
print(f"[B.4] re-publish [{G_A},{GID}] → {rv.status_code}")
assert rv.status_code == 200
assert set(j["added"]) == {GID}
assert set(j["removed"]) == {G_B}

# Verify propagation: books_v2_groups has G_A + GID for each book, no G_B
with A.app.app_context():
    db = A.get_db()
    for bid in cleanup_book_ids[-2:]:
        rows = db.execute(
            "SELECT group_id FROM books_v2_groups WHERE book_id=?",
            (bid,)).fetchall()
        gids = sorted({int(dict(r)["group_id"]) for r in rows})
        print(f"     book {bid}: {gids}")
        assert G_A in gids
        assert GID in gids
        assert G_B not in gids
print(f"[B.5] book→group propagation: G_B removed, GID added ✓")

# Empty publish set
rv = c.put(f"/api/book-folders/{folder_c}/groups",
           headers={"Content-Type": "application/json"},
           data=json.dumps({"group_ids": []}))
j = J(rv)
print(f"[B.6] PUT [] → {rv.status_code} removed={j['removed']}")
assert rv.status_code == 200
with A.app.app_context():
    db = A.get_db()
    cnt = int(db.execute(
        "SELECT COUNT(*) FROM books_v2_groups "
        "WHERE book_id IN (?,?)",
        (cleanup_book_ids[-2], cleanup_book_ids[-1])).fetchone()[0])
print(f"[B.7] books_v2_groups after empty publish: {cnt}")
assert cnt == 0

# GET folder groups
rv = c.put(f"/api/book-folders/{folder_c}/groups",
           headers={"Content-Type": "application/json"},
           data=json.dumps({"group_ids": [GID]}))
assert J(rv)["ok"] is True
rv = c.get(f"/api/book-folders/{folder_c}/groups")
j = J(rv)
print(f"[B.8] GET folder groups → {rv.status_code}, {len(j['groups'])} groups")
assert rv.status_code == 200
assert any(g["group_id"] == GID for g in j["groups"])

# ============================================================
# Scenario C — Multi-upload with folder inheritance
# ============================================================
print("\n=== Scenario C — multi-upload with folder inheritance ===")

# Tiny valid PDF body (magic bytes + minimal trailer)
pdf_bytes = b"%PDF-1.4\n%fake test content\n"

# Folder is already published to [GID] from B.8
# Upload 3 PDFs with inherit=true → each gets GID
import io as _io
data = {
    "titles": json.dumps(["Smoke C 1", "Smoke C 2", "Smoke C 3"]),
    "folder_id": str(folder_c),
    "inherit_folder_groups": "1",
}
data["files"] = [
    (_io.BytesIO(pdf_bytes), "smoke1.pdf"),
    (_io.BytesIO(pdf_bytes), "smoke2.pdf"),
    (_io.BytesIO(pdf_bytes), "smoke3.pdf"),
]
rv = c.post("/api/books/upload-multi", data=data,
            content_type="multipart/form-data")
j = J(rv)
print(f"[C.1] upload 3 PDFs → {rv.status_code} success={j['success_count']} "
      f"fail={j['fail_count']}")
assert rv.status_code == 200 and j["success_count"] == 3
new_ids = [r["book_id"] for r in j["results"] if r["ok"]]
cleanup_book_ids.extend(new_ids)

# Verify each new book has GID in books_v2_groups
with A.app.app_context():
    db = A.get_db()
    for bid in new_ids:
        rows = db.execute(
            "SELECT group_id FROM books_v2_groups WHERE book_id=?",
            (bid,)).fetchall()
        gids = {int(dict(r)["group_id"]) for r in rows}
        assert GID in gids, f"book {bid} missing inherited group"
print(f"[C.2] all 3 new books inherited group {GID} ✓")

# Upload at root → folder_id null, no inheritance
data2 = {
    "titles": json.dumps(["Root Book"]),
    "files": [(_io.BytesIO(pdf_bytes), "root.pdf")],
}
rv = c.post("/api/books/upload-multi", data=data2,
            content_type="multipart/form-data")
j = J(rv)
print(f"[C.3] upload 1 PDF at root → {rv.status_code} ok={j['success_count']}")
assert rv.status_code == 200 and j["success_count"] == 1
root_bid = j["results"][0]["book_id"]; cleanup_book_ids.append(root_bid)

with A.app.app_context():
    db = A.get_db()
    r = dict(db.execute(
        "SELECT folder_id FROM books_v2 WHERE id=?", (root_bid,)).fetchone())
print(f"[C.4] root book folder_id = {r['folder_id']!r}")
assert r["folder_id"] is None

# 11 files → 400 (max 10)
data11 = {
    "titles": json.dumps(["t"] * 11),
    "files": [(_io.BytesIO(pdf_bytes), f"x{i}.pdf") for i in range(11)],
}
rv = c.post("/api/books/upload-multi", data=data11,
            content_type="multipart/form-data")
print(f"[C.5] 11 files → {rv.status_code}")
assert rv.status_code == 400

# Invalid mime → that one fails, others succeed
bad_bytes = b"this is not a valid file"
data_mix = {
    "titles": json.dumps(["good1", "bad1", "good2"]),
    "files": [
        (_io.BytesIO(pdf_bytes), "good1.pdf"),
        (_io.BytesIO(bad_bytes), "bad.xyz"),
        (_io.BytesIO(pdf_bytes), "good2.pdf"),
    ],
}
rv = c.post("/api/books/upload-multi", data=data_mix,
            content_type="multipart/form-data")
j = J(rv)
print(f"[C.6] mixed (good/bad/good) → success={j['success_count']} "
      f"fail={j['fail_count']}")
assert j["success_count"] == 2 and j["fail_count"] == 1
for r in j["results"]:
    if r["ok"]: cleanup_book_ids.append(r["book_id"])

# Title count mismatch → 400
data_tc = {
    "titles": json.dumps(["only_one_title"]),
    "files": [
        (_io.BytesIO(pdf_bytes), "a.pdf"),
        (_io.BytesIO(pdf_bytes), "b.pdf"),
    ],
}
rv = c.post("/api/books/upload-multi", data=data_tc,
            content_type="multipart/form-data")
print(f"[C.7] title count mismatch → {rv.status_code}")
assert rv.status_code == 400

# ============================================================
# Scenario D — Permissions matrix
# ============================================================
print("\n=== Scenario D — permission matrix ===")

# zahraa / teacher1 → 403 on every endpoint
login("teacher1", "tea123")
endpoint_checks = [
    ("GET",   "/api/book-folders", None),
    ("POST",  "/api/book-folders", '{"name_ar":"x"}'),
    ("PATCH", f"/api/book-folders/{folder_a}", '{"name_ar":"x"}'),
    ("DELETE", f"/api/book-folders/{folder_a}", None),
    ("GET",   f"/api/book-folders/{folder_a}/groups", None),
    ("PUT",   f"/api/book-folders/{folder_a}/groups", '{"group_ids":[]}'),
    ("GET",   f"/api/book-folders/{folder_a}/books", None),
    ("PATCH", f"/api/books/{cleanup_book_ids[0]}/move",
              '{"folder_id":null}'),
]
for method, path, body in endpoint_checks:
    if method == "GET":
        rv = c.get(path)
    elif method == "POST":
        rv = c.post(path, headers={"Content-Type": "application/json"},
                    data=body)
    elif method == "PATCH":
        rv = c.patch(path, headers={"Content-Type": "application/json"},
                     data=body or "{}")
    elif method == "DELETE":
        rv = c.delete(path)
    elif method == "PUT":
        rv = c.put(path, headers={"Content-Type": "application/json"},
                   data=body or "{}")
    print(f"     teacher1 {method:6s} {path:50s} -> {rv.status_code}")
    assert rv.status_code == 403, f"{method} {path} expected 403, got {rv.status_code}"

# Multi-upload too
rv = c.post("/api/books/upload-multi", data={
    "titles": json.dumps(["x"]),
    "files": [(_io.BytesIO(pdf_bytes), "x.pdf")],
}, content_type="multipart/form-data")
assert rv.status_code == 403
print(f"     teacher1 POST /api/books/upload-multi -> 403")

# Each of the 4 allowed users can hit GET /api/book-folders
for uname, pw, _, _ in USERS[:4]:
    sc = login(uname, pw)
    rv = c.get("/api/book-folders")
    print(f"     {uname:11s} GET /api/book-folders -> {rv.status_code}")
    assert rv.status_code == 200

# ============================================================
# Move book between folders (Scenario A finishing test)
# ============================================================
print("\n=== Scenario E — move book ===")
login("admin", "admin123")

# Move root_bid into folder_c
rv = c.patch(f"/api/books/{root_bid}/move",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"folder_id": folder_c}))
j = J(rv)
print(f"[E.1] move to folder → {rv.status_code} {j}")
assert rv.status_code == 200 and j["new_folder_id"] == folder_c

# Move back to root
rv = c.patch(f"/api/books/{root_bid}/move",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"folder_id": None}))
j = J(rv)
print(f"[E.2] move to root (null) → {rv.status_code} new={j['new_folder_id']}")
assert rv.status_code == 200 and j["new_folder_id"] is None

# Move with inherit=true into a published folder
rv = c.patch(f"/api/books/{root_bid}/move",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"folder_id": folder_c,
                              "inherit_new_folder_groups": True}))
j = J(rv)
print(f"[E.3] move with inherit=true → groups inherited={j['inherited_groups']}")
assert GID in j["inherited_groups"]

# Invalid folder_id
rv = c.patch(f"/api/books/{root_bid}/move",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"folder_id": 99999999}))
print(f"[E.4] invalid folder_id → {rv.status_code}")
assert rv.status_code == 404

# Non-existent book
rv = c.patch("/api/books/99999999/move",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"folder_id": None}))
print(f"[E.5] non-existent book → {rv.status_code}")
assert rv.status_code == 404

# ============================================================
# Tear down
# ============================================================
print("\n=== Cleanup ===")
login("admin", "admin123")
with A.app.app_context():
    db = A.get_db()
    # Books
    for bid in cleanup_book_ids:
        db.execute("DELETE FROM books_v2_groups WHERE book_id=?", (bid,))
        db.execute("DELETE FROM books_v2 WHERE id=?", (bid,))
    # Folders + publishing rows
    for fid in cleanup_folder_ids:
        db.execute("DELETE FROM book_folder_groups WHERE folder_id=?", (fid,))
        db.execute("DELETE FROM book_folders WHERE id=?", (fid,))
    # Test groups
    for gid in extra_group_ids:
        db.execute("DELETE FROM student_groups WHERE id=?", (gid,))
    db.commit()
print(f"[cleanup] removed {len(cleanup_book_ids)} books, "
      f"{len(cleanup_folder_ids)} folders, {len(extra_group_ids)} groups")

# ── Regression: 8-route admin ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database',
          '/admin/books']:
    rv = c.get(p)
    print(f"[regression] {p} -> {rv.status_code}")
    assert rv.status_code == 200

print("\nPhase 2 endpoint smoke passed.")
