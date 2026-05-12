"""C2 smoke - UI link visibility for points-manage."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Provision allowlist users locally (mirror C1 setup)
SMOKE_USERS = [("raed", "raed_smoke_pw"),
               ("ahmed_ibrahim", "ahmed_smoke_pw")]
with A.app.app_context():
    db = A.get_db()
    for u, p in SMOKE_USERS:
        existing = db.execute("SELECT id FROM users WHERE username=?",
                              (u,)).fetchone()
        if existing:
            db.execute(
                "UPDATE users SET password=?, role='reception', "
                "is_active=1, can_be_assigned_tasks=1 WHERE username=?",
                (A.hp(p), u))
        else:
            db.execute(
                "INSERT INTO users(username, password, role, name, "
                "is_active, can_be_assigned_tasks) "
                "VALUES(?,?,?,?,1,1)",
                (u, A.hp(p), "reception", u))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: admin /dashboard → data-role="admin" + data-can-manage-points="1" ──
login("admin", "admin123")
rv = c.get("/dashboard")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
# data-role injected via JS — we look for the placeholder substitution
assert 'dataset.role = (window._mxUserRole = "admin")' in html, \
    "admin role not in body dataset script"
assert 'dataset.canManagePoints = "1"' in html, \
    "admin missing data-can-manage-points=1"
# Sidebar link present with new class
assert 'mx-points-manage-link" href="/points/manage"' in html, \
    "sidebar link missing mx-points-manage-link class"
# Dashboard card has the class
assert 'dh-action-card mx-points-manage-link" data-button-key="dashboard.points_manage"' in html, \
    "dashboard card missing mx-points-manage-link class"
print("[1] admin /dashboard: data-can-manage-points=1 + sidebar/card classes")

# ── Test 2: raed /dashboard → data-can-manage-points="1" + role NOT admin ──
login("raed", "raed_smoke_pw")
rv = c.get("/dashboard")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert 'dataset.role = (window._mxUserRole = "reception")' in html, \
    "raed role should be 'reception' (not 'admin')"
assert 'dataset.canManagePoints = "1"' in html, \
    "raed missing data-can-manage-points=1"
# Same link markup (it's in the static HTML — gated by CSS)
assert 'mx-points-manage-link" href="/points/manage"' in html
print("[2] raed /dashboard: data-can-manage-points=1, role=reception (not admin)")

# ── Test 3: ahmed_ibrahim /dashboard → same ──
login("ahmed_ibrahim", "ahmed_smoke_pw")
rv = c.get("/dashboard")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert 'dataset.canManagePoints = "1"' in html, \
    "ahmed_ibrahim missing data-can-manage-points=1"
print("[3] ahmed_ibrahim /dashboard: data-can-manage-points=1")

# ── Test 4: reception (other) /dashboard → data-can-manage-points="0" ──
login("reception", "rec123")
rv = c.get("/dashboard")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert 'dataset.canManagePoints = "0"' in html, \
    "reception (non-allowlist) should have data-can-manage-points=0"
# CSS gate hides the link for them
print("[4] reception /dashboard: data-can-manage-points=0 (gated)")

# ── Test 5: CSS rule emits the gating selector ──
# Verify the CSS rule we added is in the served HTML
needle = ('body:not([data-role="admin"]):not([data-can-manage-points="1"]) '
         '.mx-points-manage-link')
assert needle in html, "CSS gating rule for mx-points-manage-link missing"
print("[5] CSS gating rule present in /dashboard body")

# ── Test 6: JS reveal block extended for canManagePoints ──
assert "dataset.canManagePoints" in html, "JS reveal block not updated"
assert "canPts === '1'" in html, "JS conditional reveal not present"
print("[6] JS reveal block extended for non-admin allowlist users")

# ── Test 7: teacher → redirected away from /dashboard (no card seen) ──
login("teacher1", "tea123")
rv = c.get("/dashboard", follow_redirects=False)
print("[7] teacher1 /dashboard ->", rv.status_code, "(302 to teacher hub)")
assert rv.status_code == 302

# ── Test 8: 8-route regression (admin) ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[8] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 9: raed /points/manage still 200 (C1 preserved) ──
login("raed", "raed_smoke_pw")
rv = c.get("/points/manage")
print(f"[9] raed /points/manage -> {rv.status_code}")
assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    for u, _ in SMOKE_USERS:
        db.execute("DELETE FROM users WHERE username=?", (u,))
    db.commit()

print("\nC2 smoke passed.")
