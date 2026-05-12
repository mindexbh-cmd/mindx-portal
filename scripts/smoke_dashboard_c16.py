"""Phase 2 C16 smoke - GET /api/expenses/dashboard."""
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
rv = c.get("/api/expenses/dashboard")
print("[1] teacher1 ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. raed (has expense access but not admin) → 403
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/expenses/dashboard")
print("[2] raed ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. Admin: seed some expenses then check
c.get("/")
login("admin", "admin123")

# Seed 3 expenses across 2 months and 2 vendors
ex_ids = []
for body in [
    {"category_id": 1, "amount": 100, "description": "كهرباء يناير",
     "vendor_name": "Batelco", "expense_date": "2026-01-15"},
    {"category_id": 2, "amount": 50, "description": "راتب يناير",
     "vendor_name": "موظف", "expense_date": "2026-01-20"},
    {"category_id": 1, "amount": 75, "description": "كهرباء فبراير",
     "vendor_name": "Batelco", "expense_date": "2026-02-15"},
]:
    rv = c.post("/api/expenses", json=body)
    eid = (rv.get_json() or {}).get("id")
    if eid: ex_ids.append(eid)

print("[setup] inserted expenses:", ex_ids)

rv = c.get("/api/expenses/dashboard")
data = rv.get_json() or {}
print("[3] admin GET ->", rv.status_code)
print("    total_expenses:", data.get("total_expenses"))
print("    expense_count:", data.get("expense_count"))
print("    total_revenue:", data.get("total_revenue"))
print("    net:", data.get("net"))
print("    by_category (top 3):")
for c2 in (data.get("by_category") or [])[:3]:
    print("      -", c2.get("name_ar"), "total=", c2.get("total"),
          "count=", c2.get("count"))
print("    by_month_last_6:")
for m in data.get("by_month_last_6") or []:
    print("      -", m.get("ym"), "total=", m.get("total"),
          "count=", m.get("count"))
print("    top_vendors:")
for v in data.get("top_vendors") or []:
    print("      -", v.get("vendor"), "total=", v.get("total"),
          "count=", v.get("count"))

assert rv.status_code == 200
assert data.get("ok") is True
assert data.get("total_expenses", 0) >= 225  # 100+50+75
assert any(c2.get("name_ar") and c2.get("total", 0) > 0
           for c2 in data.get("by_category") or [])
assert any(v.get("vendor") == "Batelco" for v in data.get("top_vendors") or [])
# Two distinct months in our seed → at least 2 buckets
assert len(data.get("by_month_last_6") or []) >= 2

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for eid in ex_ids:
        db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.commit()

print("\nAll C16 smoke checks passed.")
