"""Phase 2 C17 smoke - GET /api/expenses/my-summary."""
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

# 1. teacher1 → 403
login("teacher1", "tea123")
rv = c.get("/api/expenses/my-summary")
print("[1] teacher1 ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. Admin seeds 2 expenses
c.get("/")
login("admin", "admin123")
admin_ids = []
for body in [
    {"category_id": 1, "amount": 200, "description": "admin exp 1",
     "expense_date": "2026-04-10"},
    {"category_id": 2, "amount": 90, "description": "admin exp 2",
     "expense_date": "2026-04-12"},
]:
    rv = c.post("/api/expenses", json=body)
    eid = (rv.get_json() or {}).get("id")
    if eid: admin_ids.append(eid)

# 3. raed logs in + seeds 3 of his own
c.get("/")
login("980909805", "raed123")
raed_ids = []
for body in [
    {"category_id": 1, "amount": 25, "description": "raed exp 1",
     "vendor_name": "Carrefour", "expense_date": "2026-03-01"},
    {"category_id": 5, "amount": 40, "description": "raed صيانة",
     "vendor_name": "ورشة", "expense_date": "2026-03-15"},
    {"category_id": 5, "amount": 35, "description": "raed exp 3",
     "vendor_name": "ورشة", "expense_date": "2026-04-01"},
]:
    rv = c.post("/api/expenses", json=body)
    eid = (rv.get_json() or {}).get("id")
    if eid: raed_ids.append(eid)
print("[setup] admin:", admin_ids, "raed:", raed_ids)

# 4. Raed GET my-summary -> only sees own
rv = c.get("/api/expenses/my-summary")
data = rv.get_json() or {}
print("[4] raed my-summary ->", rv.status_code)
print("    username:", data.get("username"))
print("    my_total_expenses:", data.get("my_total_expenses"))
print("    my_expense_count:", data.get("my_expense_count"))
print("    by_category:")
for cat in data.get("my_by_category") or []:
    print("      -", cat.get("name_ar"), "total=", cat.get("total"),
          "count=", cat.get("count"))
print("    last_5:")
for e in data.get("my_last_5_entries") or []:
    print("      - id=", e.get("id"), "amount=", e.get("amount"),
          "desc=", e.get("description"),
          "category=", e.get("category_name"))

assert rv.status_code == 200
assert data.get("username") == "980909805"
assert data.get("my_expense_count") == 3
assert abs(data.get("my_total_expenses") - 100.0) < 0.01  # 25+40+35
# raed must NOT see admin's expenses
for e in data.get("my_last_5_entries") or []:
    assert "admin" not in (e.get("description") or "")
# Only 2 categories (تشغيلي + صيانة)
assert len(data.get("my_by_category") or []) == 2

# 5. Admin GET my-summary -> only sees admin's
c.get("/")
login("admin", "admin123")
rv = c.get("/api/expenses/my-summary")
data = rv.get_json() or {}
print("[5] admin my-summary ->", rv.status_code)
print("    my_total_expenses:", data.get("my_total_expenses"))
print("    my_expense_count:", data.get("my_expense_count"))
assert data.get("my_expense_count") == 2
assert abs(data.get("my_total_expenses") - 290.0) < 0.01  # 200+90

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for eid in admin_ids + raed_ids:
        db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.commit()

print("\nAll C17 smoke checks passed.")
