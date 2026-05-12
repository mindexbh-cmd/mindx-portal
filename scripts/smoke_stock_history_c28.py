"""C28 smoke - reward stock history endpoint + UI markup."""
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

# Setup: seed a reward + 2 esl entries linked to 2 expenses
with A.app.app_context():
    db = A.get_db()
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("شوكولاتة C28", 50, "🍫", 30, "food", 1))
    try: rid = cur.lastrowid
    except Exception: rid = None
    if not rid:
        rid = dict(db.execute("SELECT id FROM rewards "
                               "WHERE name_ar=? ORDER BY id DESC LIMIT 1",
                               ("شوكولاتة C28",)).fetchone())["id"]
    # store_cat
    store_cat = dict(db.execute("SELECT id FROM expense_categories "
                                 "WHERE name_ar LIKE 'مشتريات للمتجر%'"
                                 ).fetchone())["id"]
    # Seed 2 expenses
    exp_ids = []
    for amt, qty, desc, date in [
        (10.000, 20, "20 شوكولاتة دفعة أولى", "2026-04-15"),
        (8.000,  20, "20 شوكولاتة دفعة ثانية", "2026-05-01"),
    ]:
        cur = db.execute("INSERT INTO expenses("
                         "category_id, amount, description, vendor_name, "
                         "payment_method, expense_date, receipt_mime, "
                         "receipt_filename, notes, created_by_username) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (store_cat, amt, desc, "Carrefour", "cash",
                          date, "", "", "", "admin"))
        try: eid = cur.lastrowid
        except Exception: eid = None
        if not eid:
            eid = dict(db.execute("SELECT id FROM expenses WHERE description=? "
                                   "ORDER BY id DESC LIMIT 1",
                                   (desc,)).fetchone())["id"]
        exp_ids.append(eid)
        db.execute("INSERT INTO expense_store_link(expense_id, reward_id, "
                   "quantity, unit_cost) VALUES(?,?,?,?)",
                   (eid, rid, qty, amt / qty))
    db.commit()

print("[setup] reward id=", rid, "expense ids=", exp_ids)

# 1. teacher1 → 403 on counts
login("teacher1", "tea123")
rv = c.get("/api/rewards/stock-history/counts")
print("[1] teacher1 counts ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. raed → 403 (admin-only analytics)
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/rewards/stock-history/counts")
print("[2] raed counts ->", rv.status_code, rv.get_json())
assert rv.status_code == 403
rv = c.get("/api/rewards/" + str(rid) + "/stock-history")
print("[2a] raed history ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. Admin counts
c.get("/")
login("admin", "admin123")
rv = c.get("/api/rewards/stock-history/counts")
print("[3] admin counts ->", rv.status_code)
j = rv.get_json() or {}
assert rv.status_code == 200
assert j.get("ok") is True
print("    - count for rid:", j.get("counts", {}).get(str(rid),
       j.get("counts", {}).get(rid)))

# 4. Admin history detail
rv = c.get("/api/rewards/" + str(rid) + "/stock-history")
j = rv.get_json() or {}
print("[4] admin history ->", rv.status_code)
print("    - reward name:", (j.get("reward") or {}).get("name_ar"))
print("    - entries count:", len(j.get("entries") or []))
print("    - totals:", j.get("totals"))
assert rv.status_code == 200
assert len(j.get("entries") or []) == 2
totals = j.get("totals") or {}
assert totals.get("total_quantity_added") == 40
assert abs(totals.get("total_cost") - 18.0) < 0.001
assert abs(totals.get("avg_unit_cost") - 0.45) < 0.001

# 5. Bogus reward id → 404
rv = c.get("/api/rewards/999999/stock-history")
print("[5] bogus reward ->", rv.status_code, rv.get_json())
assert rv.status_code == 404

# 6. Empty-history reward
with A.app.app_context():
    db = A.get_db()
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("ممحاة C28", 10, "🩹", 0, "other", 1))
    try: empty_rid = cur.lastrowid
    except Exception: empty_rid = None
    if not empty_rid:
        empty_rid = dict(db.execute("SELECT id FROM rewards WHERE name_ar=? "
                                     "ORDER BY id DESC LIMIT 1",
                                     ("ممحاة C28",)).fetchone())["id"]
    db.commit()

rv = c.get("/api/rewards/" + str(empty_rid) + "/stock-history")
j = rv.get_json() or {}
print("[6] empty history ->", rv.status_code,
      "entries=", len(j.get("entries") or []),
      "total_qty=", (j.get("totals") or {}).get("total_quantity_added"))
assert rv.status_code == 200
assert len(j.get("entries") or []) == 0
assert (j.get("totals") or {}).get("total_quantity_added") == 0

# 7. /points/manage admin page contains the new column
rv = c.get("/points/manage")
body = rv.get_data(as_text=True)
print("[7] /points/manage len=", len(body))
checks = [
    ("history column header", "تاريخ المخزون" in body),
    ("counts fetch", "/api/rewards/stock-history/counts" in body),
    ("showStockHistory fn", "function showStockHistory" in body),
    ("history endpoint reference", "/stock-history" in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM expense_store_link WHERE reward_id IN(?,?)",
               (rid, empty_rid))
    for eid in exp_ids:
        db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.execute("DELETE FROM rewards WHERE id IN(?,?)", (rid, empty_rid))
    db.commit()

print("\nAll C28 smoke checks passed.")
