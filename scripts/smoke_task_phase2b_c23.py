"""C23 smoke - recurring tasks CRUD (4 endpoints)."""
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

with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

login("admin", "admin123")

# 1. POST daily → success
rv = c.post("/api/recurring-tasks", json={
    "template_title": "C23 daily template",
    "department_id": events_dept,
    "priority": "normal",
    "assigned_to_username": "980909805",
    "estimated_hours": 1.5,
    "frequency": "daily"
})
j = rv.get_json()
print("[1] POST daily ->", rv.status_code, "id=", j.get("id"),
      "title:", j.get("template", {}).get("template_title"))
assert rv.status_code == 200
daily_rid = j["id"]

# 2. POST weekly missing day_of_week → 400
rv = c.post("/api/recurring-tasks", json={
    "template_title": "weekly bad",
    "assigned_to_username": "980909805",
    "estimated_hours": 1,
    "frequency": "weekly"
})
print("[2] weekly missing dow ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 3. POST weekly with bad day_of_week=7 → 400
rv = c.post("/api/recurring-tasks", json={
    "template_title": "weekly bad dow",
    "assigned_to_username": "980909805",
    "estimated_hours": 1,
    "frequency": "weekly",
    "day_of_week": 7
})
print("[3] weekly dow=7 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 4. POST weekly valid
rv = c.post("/api/recurring-tasks", json={
    "template_title": "C23 weekly",
    "assigned_to_username": "980909805",
    "estimated_hours": 2,
    "frequency": "weekly",
    "day_of_week": 2
})
j = rv.get_json()
print("[4] weekly OK ->", rv.status_code, "id=", j.get("id"))
weekly_rid = j["id"]

# 5. POST monthly with day_of_month=31 → 400 (cap at 28)
rv = c.post("/api/recurring-tasks", json={
    "template_title": "monthly bad",
    "assigned_to_username": "980909805",
    "estimated_hours": 1,
    "frequency": "monthly",
    "day_of_month": 31
})
print("[5] monthly dom=31 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 6. POST as raed assigning to admin → 403
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/recurring-tasks", json={
    "template_title": "raed→admin",
    "assigned_to_username": "admin",
    "estimated_hours": 1, "frequency": "daily"
})
print("[6] raed→admin recurring ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 7. raed POST own → success
rv = c.post("/api/recurring-tasks", json={
    "template_title": "C23 raed-own",
    "assigned_to_username": "980909805",
    "estimated_hours": 1, "frequency": "daily"
})
j = rv.get_json()
print("[7] raed POST own ->", rv.status_code, "id=", j.get("id"))
raed_rid = j["id"]

# 8. GET list — admin sees all 3 just-created
c.get("/")
login("admin", "admin123")
rv = c.get("/api/recurring-tasks")
j = rv.get_json()
print("[8] admin GET list ->", rv.status_code, "count=", len(j["templates"]))
# At least our 3
assert len(j["templates"]) >= 3

# 9. GET list with ?is_active=1 → all active
rv = c.get("/api/recurring-tasks?is_active=1")
print("[9] admin GET is_active=1 ->", rv.status_code,
      "count=", len(rv.get_json()["templates"]))

# 10. raed GET — only own
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/recurring-tasks")
j = rv.get_json()
print("[10] raed GET ->", rv.status_code, "count=", len(j["templates"]))
for t in j["templates"]:
    assert (t["assigned_to_username"] == "980909805"
            or t["created_by_username"] == "980909805")

# 11. PATCH daily→weekly with missing day_of_week → 400
c.get("/")
login("admin", "admin123")
rv = c.patch("/api/recurring-tasks/" + str(daily_rid),
             json={"frequency": "weekly"})
print("[11] PATCH daily→weekly (no dow) ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 12. PATCH daily→weekly with day_of_week=3 → 200
rv = c.patch("/api/recurring-tasks/" + str(daily_rid),
             json={"frequency": "weekly", "day_of_week": 3})
j = rv.get_json()
print("[12] PATCH daily→weekly OK ->", rv.status_code,
      "frequency:", j["template"]["frequency"],
      "dow:", j["template"]["day_of_week"])
assert rv.status_code == 200

# 13. PATCH immutable (created_at) → 400
rv = c.patch("/api/recurring-tasks/" + str(daily_rid),
             json={"created_at": "2020-01-01"})
print("[13] PATCH immutable ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 14. DELETE soft → is_active=0
rv = c.delete("/api/recurring-tasks/" + str(weekly_rid))
print("[14] DELETE weekly ->", rv.status_code)
assert rv.status_code == 200

# Confirm soft delete (row still exists, is_active=0)
with A.app.app_context():
    db = A.get_db()
    row = db.execute("SELECT is_active FROM recurring_tasks WHERE id=?",
                     (weekly_rid,)).fetchone()
    print("[15] weekly after delete: is_active=", dict(row)["is_active"])
    assert dict(row)["is_active"] == 0

# 16. raed deletes admin's template → 403
c.get("/")
login("980909805", "raed123")
rv = c.delete("/api/recurring-tasks/" + str(daily_rid))
print("[16] raed deletes admin's ->", rv.status_code)
assert rv.status_code == 403

# 17. Bogus rid → 404
rv = c.delete("/api/recurring-tasks/999999")
print("[17] bogus rid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for rid in [daily_rid, weekly_rid, raed_rid]:
        db.execute("DELETE FROM recurring_tasks WHERE id=?", (rid,))
    db.commit()

print("\nC23 smoke passed.")
