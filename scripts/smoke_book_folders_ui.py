"""Phase 3 C8 smoke - book-folders UI integration.

Server-rendered HTML inspection: all 4 allowed roles get the
explorer markup; teacher1 is bounced. Verifies that every
JS function the modals depend on is present in the served
HTML.
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Ensure all 4 allowed users + teacher1 have known passwords
USERS = [
    ("admin",      "admin123",  "admin",     None),
    ("980909805",  "raed_pw",   "manager",   "رائد"),
    ("010307885",  "ahib_pw",   "manager",   "أحمد إبراهيم"),
    ("021005931",  "younis_pw", "admin",     "أحمد يونس"),
    ("teacher1",   "tea123",    "teacher",   None),
]
with A.app.app_context():
    db = A.get_db()
    for uname, pw, role, name in USERS:
        ex = db.execute("SELECT id FROM users WHERE username=?",
                        (uname,)).fetchone()
        if ex:
            db.execute(
                "UPDATE users SET password=?, role=?, is_active=1 "
                "WHERE username=?", (A.hp(pw), role, uname))
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

# ── Test 1: admin /admin/books renders + has explorer scaffold ──
login("admin", "admin123")
rv = c.get("/admin/books")
assert rv.status_code == 200
html = rv.get_data(as_text=True)

# Layout scaffold (C1)
for marker in ['class="bk-explorer"', 'class="bk-sidebar"',
               'class="bk-main"', 'id="bk-folders-list"',
               'id="bk-books-list"', 'id="bk-main-header"',
               'class="bk-add-folder"']:
    assert marker in html, f"missing layout marker: {marker}"
print("[1] admin /admin/books: layout scaffold (7 markers) present")

# ── Test 2: all 4 allowed users see the same scaffold ──
for uname, pw, _, _ in USERS[:4]:
    login(uname, pw)
    rv = c.get("/admin/books")
    assert rv.status_code == 200, f"{uname} got {rv.status_code}"
    assert 'class="bk-explorer"' in rv.get_data(as_text=True)
    print(f"[2] {uname:11s} /admin/books -> 200 + explorer markup ✓")

# ── Test 3: teacher1 blocked ──
login("teacher1", "tea123")
rv = c.get("/admin/books", follow_redirects=False)
print(f"[3] teacher1 /admin/books -> {rv.status_code}")
assert rv.status_code in (302, 403)

# ── Test 4: All 3 modals + JS scaffold present ──
login("admin", "admin123")
html = c.get("/admin/books").get_data(as_text=True)
modals = ['id="bk-up-modal"',  # C4 multi-upload
          'id="bk-pub-modal"', # C5 publish
          'id="bk-mv-modal"']  # C6 move
for m in modals:
    assert m in html, f"missing modal: {m}"
print("[4] 3 modals scaffolded (upload + publish + move) ✓")

# ── Test 5: All JS functions named ──
js_fns = [
    'function bkLoadFolders',
    'function bkRenderSidebar',
    # All these are window.bk* (closure-exposed via window)
    'window.bkSelectFolder',
    'window.bkLoadBooks',
    'window.bkCreateFolder',
    'window.bkRenameFolder',
    'window.bkDeleteFolder',
    'window.bkOpenPublish',
    'window.bkClosePublish',
    'window.bkPubSubmit',
    'window.bkPubToggle',
    'window.bkPubSearch',
    'window.bkOpenMove',
    'window.bkCloseMove',
    'window.bkMoveSubmit',
    'window.bkOpenMultiUpload',
    'window.bkCloseMultiUpload',
    'window.bkUpAddFiles',
    'window.bkUpRemove',
    'window.bkUpSetTitle',
    'window.bkUpSubmit',
    'window.bkDeleteBook',
]
missing = [fn for fn in js_fns if fn not in html]
print(f"[5] JS functions present: {len(js_fns) - len(missing)}/{len(js_fns)}")
assert not missing, f"missing JS: {missing}"

# ── Test 6: CSS classes present ──
css_classes = ['.bk-explorer', '.bk-sidebar', '.bk-main',
               '.bk-folder-item', '.bk-book-card', '.bk-empty',
               '.bk-dropzone', '.bk-file-row', '.bk-add-folder',
               '.bk-main-header']
for cl in css_classes:
    assert cl in html, f"missing CSS class: {cl}"
print(f"[6] CSS classes present: {len(css_classes)}/{len(css_classes)}")

# ── Test 7: Legacy upload form still present (no regression) ──
assert 'id="bk-file"' in html, "legacy single-file form removed!"
assert 'id="bk-title"' in html
assert 'id="bk-save-btn"' in html
print("[7] legacy single-file upload form still in markup ✓")

# ── Test 8: Mobile breakpoint markers ──
assert "@media (max-width:768px)" in html
assert "flex-direction:column" in html
print("[8] responsive @ 768px breakpoint present ✓")

# ── Test 9: Existing API endpoints still respond ──
for ep in ('/api/books', '/api/books/groups-list',
           '/api/books/teachers-list'):
    rv = c.get(ep)
    print(f"[9] {ep:35s} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 10: 9-route admin regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database',
          '/admin/books']:
    rv = c.get(p)
    print(f"[10] {p} -> {rv.status_code}")
    assert rv.status_code == 200

print("\nPhase 3 UI smoke passed.")
