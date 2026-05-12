"""C3 smoke - /tasks/recurring modal: assignee free-text → dropdown."""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: /tasks/recurring markup has <select id="recur-assignee"> ──
login("admin", "admin123")
rv = c.get("/tasks/recurring")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert '<select id="recur-assignee">' in html, "recur select missing"
# Old free-text input shape removed (just the recur one)
assert '<input type="text" id="recur-assignee">' not in html, \
    "old recur free-text input still present"
# Helper functions present
assert 'R_ASSIGNABLE_USERS' in html, "R_ASSIGNABLE_USERS cache var missing"
# Endpoint URL referenced (both /tasks and /tasks/recurring will include
# this string since both modals were swapped; either way it's present)
assert '/api/users/assignable' in html, "endpoint URL not referenced"
print("[1] /tasks/recurring markup: <select id=recur-assignee> + helpers")

# ── Test 2: round-trip — admin creates a template with the new dropdown ──
import datetime as dt
body = {
    "template_title": "C3 smoke recurring",
    "template_description": "Created via dropdown-swap smoke",
    "priority": "normal",
    "assigned_to_username": "teacher1",
    "estimated_hours": 1.0,
    "frequency": "daily"
}
rv = c.post("/api/recurring-tasks",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body))
j = rv.get_json()
print("[2] POST /api/recurring-tasks ->", rv.status_code, j)
assert rv.status_code == 200 and j["ok"] is True
rid = j.get("template_id") or j.get("id") or (j.get("template") or {}).get("id")
assert rid, f"no template id in response: {j}"
print(f"[2a] template created: id={rid}")

# ── Test 3: GET back, assignee preserved ──
rv = c.get(f"/api/recurring-tasks")
j2 = rv.get_json()
templates = j2.get("templates") or []
our = [t for t in templates if t["id"] == rid]
assert our and our[0]["assigned_to_username"] == "teacher1"
print(f"[3] template assignee in DB: teacher1 ✓")

# ── Test 4: PATCH reassign to admin ──
rv = c.patch(f"/api/recurring-tasks/{rid}",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"assigned_to_username": "admin"}))
print(f"[4] PATCH reassign -> {rv.status_code}")
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE recurring_id=?", (rid,))
    db.execute("DELETE FROM recurring_tasks WHERE id=?", (rid,))
    db.commit()

# ── Test 5: non-admin /tasks/recurring still gets the page with select ──
login("teacher1", "tea123")
rv = c.get("/tasks/recurring")
print(f"[5] teacher1 /tasks/recurring -> {rv.status_code}")
assert rv.status_code == 200
html2 = rv.get_data(as_text=True)
assert '<select id="recur-assignee">' in html2

# ── Test 6: 8-route regression (admin) ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[6] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 7: C2 dropdown (in /tasks) still intact ──
rv = c.get("/tasks")
html3 = rv.get_data(as_text=True)
assert '<select id="task-assignee">' in html3, "C2 select broken by C3"
print("[7] /tasks select (C2) still present")

print("\nC3 smoke passed.")
