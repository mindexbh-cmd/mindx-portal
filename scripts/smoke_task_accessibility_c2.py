"""C2 smoke - teacher hub task card."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: teacher1 → /teacher/hub shows the new 6th card ──
login("teacher1", "tea123")
rv = c.get("/teacher/hub")
assert rv.status_code == 200, f"/teacher/hub expected 200, got {rv.status_code}"
html = rv.get_data(as_text=True)

# 6th card: class="card tasks", href="/tasks", heading "مهامي"
assert 'class="card tasks"' in html, "missing .card.tasks class"
assert 'href="/tasks"' in html, "missing /tasks href in teacher hub"
assert 'مهامي' in html, "missing مهامي label"
assert 'عرض مهامك المسندة' in html, "missing description text"

# CSS rule .card.tasks::before present
assert '.card.tasks::before' in html, "missing .card.tasks::before CSS rule"
assert '#1565C0' in html, "expected blue gradient stop missing"
print("[1] teacher1 /teacher/hub: 6th task card + CSS rule present")

# Verify all 5 original cards still there
for needle in ['/teacher/attendance', '/points/board', '/teacher/lessons',
               '/teacher/parent-messages', '/teacher/evaluations']:
    assert needle in html, f"original card missing: {needle}"
print("[1a] all 5 original teacher hub cards intact")

# ── Test 2: teacher1 can click into /tasks (server already allows) ──
rv = c.get("/tasks")
print("[2] teacher1 /tasks ->", rv.status_code)
assert rv.status_code == 200

# ── Test 3: non-teachers still get redirected away from /teacher/hub ──
login("admin", "admin123")
rv = c.get("/teacher/hub", follow_redirects=False)
print("[3] admin /teacher/hub ->", rv.status_code, "(should 302→/dashboard)")
assert rv.status_code == 302
assert "/dashboard" in rv.headers.get("Location", "")

# ── Test 4: 8-route regression (admin) ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[4] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 5: dashboard task cards from C1 still present ──
rv = c.get("/dashboard")
html = rv.get_data(as_text=True)
assert 'dh-action-card mx-tasks-link" href="/tasks"' in html
assert 'dh-action-card mx-tasks-link" href="/tasks/recurring"' in html
print("[5] dashboard task cards from C1 still present (no regression)")

print("\nC2 smoke passed.")
