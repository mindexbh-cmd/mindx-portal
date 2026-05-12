"""C39 smoke - recurring add/edit modal."""
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

# 1. /tasks/recurring contains the modal markup
login("admin", "admin123")
rv = c.get("/tasks/recurring")
body = rv.get_data(as_text=True)
print("[1] admin /tasks/recurring len=", len(body))
checks = [
    ("modal markup", 'id="recur-modal"' in body),
    ("title input", 'id="recur-title"' in body),
    ("dept select", 'id="recur-dept"' in body),
    ("assignee input", 'id="recur-assignee"' in body),
    ("priority pills", 'id="recur-pri-pills"' in body),
    ("frequency pills", 'id="recur-freq-pills"' in body),
    ("day-of-week row", 'id="recur-dow-row"' in body),
    ("day-of-month row", 'id="recur-dom-row"' in body),
    ("save btn", 'id="recur-save-btn"' in body),
    ("recurOpenAdd fn", "window.recurOpenAdd" in body),
    ("recurOpenEdit fn", "window.recurOpenEdit" in body),
    ("conditional dow/dom toggle in JS", "(SEL_FREQ === 'weekly')" in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. E2E: admin creates a weekly recurring template via API
rv = c.post("/api/recurring-tasks", json={
    "template_title": "C39 modal weekly",
    "priority": "normal",
    "assigned_to_username": "980909805",
    "estimated_hours": 1,
    "frequency": "weekly",
    "day_of_week": 3
})
j = rv.get_json()
print("[2] POST weekly template ->", rv.status_code, "id=", j.get("id"))
assert rv.status_code == 200
rid = j["id"]

# 3. PATCH to change frequency to monthly
rv = c.patch("/api/recurring-tasks/" + str(rid),
             json={"frequency": "monthly", "day_of_month": 15})
print("[3] PATCH to monthly ->", rv.status_code,
      "freq:", rv.get_json()["template"]["frequency"],
      "dom:", rv.get_json()["template"]["day_of_month"])
assert rv.status_code == 200
assert rv.get_json()["template"]["frequency"] == "monthly"
assert rv.get_json()["template"]["day_of_month"] == 15

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM recurring_tasks WHERE id=?", (rid,))
    db.commit()

print("\nC39 smoke passed.")
