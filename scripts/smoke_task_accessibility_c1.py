"""C1 smoke - dashboard task cards visible per role."""
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

# Three new cards by href
HREF_TASKS    = 'href="/tasks"'
HREF_RECUR    = 'href="/tasks/recurring"'
HREF_ANALYTIC = 'href="/tasks/dashboard/admin"'

# ── Test 1: admin sees all 3 cards in /dashboard ──
login("admin", "admin123")
rv = c.get("/dashboard")
assert rv.status_code == 200, f"admin /dashboard expected 200, got {rv.status_code}"
html = rv.get_data(as_text=True)
# All 3 hrefs present in the dashboard cards block (the only place
# in HOME_HTML that uses dh-action-card)
grid_start = html.find('dh-actions-grid')
assert grid_start > 0, "dh-actions-grid not in body"
# The dh-action-card markers are unique to the grid in HOME_HTML;
# scanning the whole body from grid_start is fine.
grid_block = html[grid_start:]
assert HREF_TASKS    in grid_block, "missing /tasks card"
assert HREF_RECUR    in grid_block, "missing /tasks/recurring card"
assert HREF_ANALYTIC in grid_block, "missing /tasks/dashboard/admin card"

# All 3 cards carry mx-tasks-link gating
assert 'dh-action-card mx-tasks-link" href="/tasks"' in grid_block
assert 'dh-action-card mx-tasks-link" href="/tasks/recurring"' in grid_block
assert 'mx-tasks-link mx-admin-only" href="/tasks/dashboard/admin"' in grid_block

# Body has data-allow-tasks="1" for admin (so CSS un-hides them)
assert 'data-allow-tasks="1"' in html, "admin missing data-allow-tasks=1"
print("[1] admin /dashboard: all 3 task cards present + data-allow-tasks=1")

# ── Test 2: teacher → redirected to /teacher/hub (not affected by C1) ──
login("teacher1", "tea123")
rv = c.get("/dashboard", follow_redirects=False)
print("[2] teacher1 /dashboard ->", rv.status_code, "(should be 302→teacher hub)")
assert rv.status_code == 302
assert "/teacher/hub" in rv.headers.get("Location", "")

# ── Test 3: teacher hub still loads (unchanged by C1) ──
rv = c.get("/teacher/hub")
assert rv.status_code == 200, f"/teacher/hub expected 200, got {rv.status_code}"
print("[3] teacher1 /teacher/hub -> 200 (unchanged)")

# ── Test 4: 8-route regression ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[4] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 5: existing dashboard cards still present (no regression) ──
rv = c.get("/dashboard")
html = rv.get_data(as_text=True)
must_have = ['href="/database"', 'href="/attendance"',
             'href="/expenses"', 'href="/assets"',
             'href="/admin/books"', 'href="/points/board"']
for needle in must_have:
    assert needle in html, f"missing existing card: {needle}"
print("[5] all 6 sampled existing cards still present (no regression)")

print("\nC1 smoke passed.")
