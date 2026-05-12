"""C29 smoke - cost-per-redemption analytics."""
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

# Seed: 1 reward with 2 ESL entries + 3 redemptions
with A.app.app_context():
    db = A.get_db()
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("شوكولاتة C29", 50, "🍫", 20, "food", 1))
    try: rid = cur.lastrowid
    except Exception: rid = None
    if not rid:
        rid = dict(db.execute("SELECT id FROM rewards WHERE name_ar=? "
                               "ORDER BY id DESC LIMIT 1",
                               ("شوكولاتة C29",)).fetchone())["id"]
    store_cat = dict(db.execute("SELECT id FROM expense_categories "
                                 "WHERE name_ar LIKE 'مشتريات للمتجر%'"
                                 ).fetchone())["id"]
    exp_ids = []
    for amt, qty in [(10.000, 20), (8.000, 16)]:  # avg=10/20=0.5, 8/16=0.5 ; weighted=0.5
        cur = db.execute("INSERT INTO expenses("
                         "category_id, amount, description, vendor_name, "
                         "payment_method, expense_date, receipt_mime, "
                         "receipt_filename, notes, created_by_username) "
                         "VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (store_cat, amt, "C29 seed", "Carrefour",
                          "cash", "2026-05-01", "", "", "", "admin"))
        try: eid = cur.lastrowid
        except Exception: eid = None
        if not eid:
            eid = dict(db.execute("SELECT id FROM expenses WHERE description=? "
                                   "ORDER BY id DESC LIMIT 1",
                                   ("C29 seed",)).fetchone())["id"]
        exp_ids.append(eid)
        db.execute("INSERT INTO expense_store_link(expense_id, reward_id, "
                   "quantity, unit_cost) VALUES(?,?,?,?)",
                   (eid, rid, qty, amt / qty))
    # Seed 3 redemptions: 2 delivered, 1 pending, 1 cancelled (excluded)
    redemp_ids = []
    for status in ["delivered", "delivered", "pending", "cancelled"]:
        cur = db.execute("INSERT INTO redemptions("
                         "student_id, student_name, reward_id, reward_name, "
                         "points_spent, status) VALUES(?,?,?,?,?,?)",
                         (1, "اختبار", rid, "شوكولاتة C29", 50, status))
        try: redid = cur.lastrowid
        except Exception: redid = None
        if redid:
            redemp_ids.append(redid)
    db.commit()
print("[setup] reward id=", rid, "expense ids=", exp_ids,
      "redemption ids=", redemp_ids)

# 1. Raed → 403
login("980909805", "raed123")
rv = c.get("/api/expenses/dashboard")
print("[1] raed dashboard ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. Admin → 200 + redemption_costs included
c.get("/")
login("admin", "admin123")
rv = c.get("/api/expenses/dashboard")
j = rv.get_json() or {}
print("[2] admin dashboard ->", rv.status_code)
assert rv.status_code == 200
assert "redemption_costs" in j
rcosts = j.get("redemption_costs") or []
print("    - redemption_costs entries:", len(rcosts))
# Find our seeded reward
ours = [x for x in rcosts if x.get("reward_id") == rid]
assert len(ours) == 1, "seeded reward should appear"
ours = ours[0]
print("    - reward:", ours.get("reward_name"))
print("    - avg_unit_cost:", ours.get("avg_unit_cost"))
print("    - redemption_count:", ours.get("redemption_count"))
print("    - estimated_total_cost:", ours.get("estimated_total_cost"))
print("    - current_stock:", ours.get("current_stock"))
# Verify weighted avg: (10+8) / (20+16) = 18/36 = 0.5
assert abs(ours["avg_unit_cost"] - 0.5) < 0.001
# Pending + delivered = 3 (cancelled excluded)
assert ours["redemption_count"] == 3
# Estimated = 0.5 * 3 = 1.5
assert abs(ours["estimated_total_cost"] - 1.5) < 0.001

# 3. The estimated_redemption_total includes ours
ert = j.get("estimated_redemption_total") or 0
print("    - estimated_redemption_total:", ert)
assert ert >= 1.5

# 4. Frontend: admin /expenses has the analytics section markup
import html as _html
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
body_d = _html.unescape(body)  # decode &#x... entities
print("[4] /expenses (admin) len=", len(body))
checks = [
    ("section panel", 'exp-redemption-costs-panel' in body),
    ("section title (decoded)", "تكلفة الاستبدالات الفعلية" in body_d),
    ("totals pill", 'exp-redemption-total-val' in body),
    ("table tbody", 'exp-redemption-tbody' in body),
    ("renderer fn", '_expBuildRedemptionCosts' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 5. Raed /expenses must NOT have the analytics section
c.get("/")
login("980909805", "raed123")
rv = c.get("/expenses")
body_r = rv.get_data(as_text=True)
body_rd = _html.unescape(body_r)
print("[5] /expenses (raed) len=", len(body_r))
assert 'exp-redemption-costs-panel' not in body_r
assert "تكلفة الاستبدالات الفعلية" not in body_rd
print("    - raed view does NOT contain analytics section ✓")

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM redemptions WHERE id IN(" +
               ",".join([str(x) for x in redemp_ids]) + ")")
    db.execute("DELETE FROM expense_store_link WHERE reward_id=?", (rid,))
    for eid in exp_ids:
        db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.execute("DELETE FROM rewards WHERE id=?", (rid,))
    db.commit()

print("\nAll C29 smoke checks passed.")
