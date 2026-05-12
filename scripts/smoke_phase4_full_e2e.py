"""Phase 4 full E2E — every scenario from the spec, end-to-end."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
PNG_B64 = base64.b64encode(PNG).decode()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# Seed a clean chocolate reward (start stock=0, finite)
with A.app.app_context():
    db = A.get_db()
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("شوكولاتة E2E", 50, "🍫", 0, "food", 1))
    try: chocolate_id = cur.lastrowid
    except Exception: chocolate_id = None
    if not chocolate_id:
        chocolate_id = dict(db.execute("SELECT id FROM rewards "
                                        "WHERE name_ar=? ORDER BY id DESC LIMIT 1",
                                        ("شوكولاتة E2E",)).fetchone())["id"]
    store_cat = dict(db.execute("SELECT id FROM expense_categories "
                                 "WHERE name_ar LIKE 'مشتريات للمتجر%'"
                                 ).fetchone())["id"]
    db.commit()

print("=== SETUP ===")
print("chocolate reward id =", chocolate_id, "start stock = 0")
print("store category id =", store_cat)
print()

# ════════════ SCENARIO A: Admin records chocolate purchase ════════════
print("=== SCENARIO A: chocolate purchase 20×0.500 BHD ===")
login("admin", "admin123")
exp_before = dict(A.get_db().execute("SELECT COUNT(*) AS c FROM expenses").fetchone() if False else (lambda: 0)) if False else None
with A.app.app_context():
    db = A.get_db()
    esl_before = dict(db.execute("SELECT COUNT(*) AS c FROM expense_store_link").fetchone())["c"]
    stock_before = dict(db.execute("SELECT stock FROM rewards WHERE id=?",
                                    (chocolate_id,)).fetchone())["stock"]
print("[A0] before: esl_rows=", esl_before, "chocolate stock=", stock_before)

rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10.000,
    "description": "20 شوكولاتة كادبوري للمتجر",
    "vendor_name": "Carrefour", "expense_date": "2026-05-12",
    "receipt_b64": PNG_B64, "receipt_filename": "rcpt.png",
    "store_link": {"reward_id": chocolate_id, "quantity": 20}
})
j = rv.get_json()
print("[A1] POST ->", rv.status_code, j)
assert rv.status_code == 200
assert j["linked"] is True
assert j["link_details"]["unit_cost"] == 0.5
exp_id = j["id"]

# Verify expense + esl + stock
with A.app.app_context():
    db = A.get_db()
    e = dict(db.execute("SELECT amount, description FROM expenses WHERE id=?",
                         (exp_id,)).fetchone())
    esl = dict(db.execute("SELECT quantity, unit_cost FROM expense_store_link "
                          "WHERE expense_id=?", (exp_id,)).fetchone())
    stock = dict(db.execute("SELECT stock FROM rewards WHERE id=?",
                             (chocolate_id,)).fetchone())["stock"]
print("[A2] expense:", e)
print("[A3] esl:", esl)
print("[A4] chocolate stock:", stock_before, "→", stock)
assert e["amount"] == 10.0
assert esl["quantity"] == 20
assert esl["unit_cost"] == 0.5
assert stock == stock_before + 20  # +20

# Verify receipt served
rv = c.get("/api/expenses/" + str(exp_id) + "/receipt")
print("[A5] receipt ->", rv.status_code, rv.headers.get("Content-Type"),
      "len=", len(rv.data))
assert rv.status_code == 200 and "image/png" in rv.headers.get("Content-Type", "")
print()

# ════════════ SCENARIO B: Failed transaction = nothing committed ════════════
print("=== SCENARIO B: invalid reward_id rolls back EVERYTHING ===")
with A.app.app_context():
    db = A.get_db()
    exp_count_before = dict(db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone())["c"]
    esl_count_before = dict(db.execute("SELECT COUNT(*) AS c FROM expense_store_link").fetchone())["c"]
    stock_before2 = dict(db.execute("SELECT stock FROM rewards WHERE id=?",
                                     (chocolate_id,)).fetchone())["stock"]

rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 5.000,
    "description": "ينبغي أن يفشل بالكامل",
    "vendor_name": "Test", "expense_date": "2026-05-12",
    "store_link": {"reward_id": 999999, "quantity": 10}
})
j = rv.get_json()
print("[B1] POST bogus reward ->", rv.status_code, j)
assert rv.status_code == 400

with A.app.app_context():
    db = A.get_db()
    exp_count_after = dict(db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone())["c"]
    esl_count_after = dict(db.execute("SELECT COUNT(*) AS c FROM expense_store_link").fetchone())["c"]
    stock_after2 = dict(db.execute("SELECT stock FROM rewards WHERE id=?",
                                    (chocolate_id,)).fetchone())["stock"]
print("[B2] expense count:", exp_count_before, "==", exp_count_after, "?",
      exp_count_before == exp_count_after)
print("[B3] esl count:", esl_count_before, "==", esl_count_after, "?",
      esl_count_before == esl_count_after)
print("[B4] chocolate stock:", stock_before2, "==", stock_after2, "?",
      stock_before2 == stock_after2)
assert exp_count_before == exp_count_after
assert esl_count_before == esl_count_after
assert stock_before2 == stock_after2
print("ATOMICITY CONFIRMED: nothing committed when reward bogus")
print()

# ════════════ SCENARIO C: Admin views analytics ════════════
print("=== SCENARIO C: admin sees chocolate in redemption_costs ===")
rv = c.get("/api/expenses/dashboard")
j = rv.get_json() or {}
print("[C1] dashboard ->", rv.status_code)
rc = j.get("redemption_costs") or []
mine = [x for x in rc if x.get("reward_id") == chocolate_id]
assert mine, "chocolate should appear in redemption_costs"
print("[C2] chocolate row:", mine[0])
assert mine[0]["avg_unit_cost"] == 0.5
assert mine[0]["redemption_count"] == 0  # no redemptions yet
assert mine[0]["estimated_total_cost"] == 0.0

# Simulate a redemption
with A.app.app_context():
    db = A.get_db()
    cur = db.execute("INSERT INTO redemptions("
                     "student_id, student_name, reward_id, reward_name, "
                     "points_spent, status) VALUES(?,?,?,?,?,?)",
                     (1, "اختبار", chocolate_id, "شوكولاتة E2E", 50, "delivered"))
    try: redid = cur.lastrowid
    except Exception: redid = None
    if not redid:
        redid = dict(db.execute("SELECT id FROM redemptions "
                                 "WHERE reward_id=? ORDER BY id DESC LIMIT 1",
                                 (chocolate_id,)).fetchone())["id"]
    db.commit()
print("[C3] simulated redemption id=", redid)

rv = c.get("/api/expenses/dashboard")
j = rv.get_json() or {}
mine2 = [x for x in (j.get("redemption_costs") or []) if x.get("reward_id") == chocolate_id]
print("[C4] after redemption:", mine2[0])
assert mine2[0]["redemption_count"] == 1
assert abs(mine2[0]["estimated_total_cost"] - 0.5) < 0.001
print()

# ════════════ SCENARIO D: Stock history modal data ════════════
print("=== SCENARIO D: admin reads chocolate stock history ===")
rv = c.get("/api/rewards/" + str(chocolate_id) + "/stock-history")
j = rv.get_json() or {}
print("[D1] reward:", j.get("reward"))
print("[D2] entries count:", len(j.get("entries") or []))
print("[D3] totals:", j.get("totals"))
assert len(j.get("entries") or []) == 1
e0 = j["entries"][0]
assert e0["quantity"] == 20
assert e0["unit_cost"] == 0.5
assert e0["expense_vendor"] == "Carrefour"
assert j["totals"]["total_quantity_added"] == 20
assert j["totals"]["total_cost"] == 10.0
assert j["totals"]["avg_unit_cost"] == 0.5
print()

# ════════════ SCENARIO E: Raed permissions ════════════
print("=== SCENARIO E: raed restricted from analytics ===")
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/expenses/dashboard")
print("[E1] raed dashboard ->", rv.status_code)
assert rv.status_code == 403
rv = c.get("/api/rewards/" + str(chocolate_id) + "/stock-history")
print("[E2] raed stock-history ->", rv.status_code)
assert rv.status_code == 403
rv = c.get("/api/rewards/stock-history/counts")
print("[E3] raed counts ->", rv.status_code)
assert rv.status_code == 403

# But raed CAN still create store-link expenses
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 2.500,
    "description": "raed يضيف 5 إلى المخزون",
    "vendor_name": "Lulu", "expense_date": "2026-05-12",
    "store_link": {"reward_id": chocolate_id, "quantity": 5}
})
j = rv.get_json()
print("[E4] raed creates store-link ->", rv.status_code, "linked=", j.get("linked"))
assert rv.status_code == 200
assert j["linked"] is True
raed_exp_id = j["id"]

# Raed cannot see analytics — confirmed
# Raed's /expenses page has NO analytics section
rv = c.get("/expenses")
body_r = rv.get_data(as_text=True)
assert 'exp-redemption-costs-panel' not in body_r
print("[E5] raed /expenses has no analytics panel ✓")
print()

# ════════════ SCENARIO F: Regression — Phase 2/3 endpoints still alive ════════════
print("=== SCENARIO F: regression on all Phase 2/3 surfaces ===")
c.get("/")
login("admin", "admin123")
endpoints = [
    "/api/expenses/categories",
    "/api/expenses",
    "/api/expenses/dashboard",
    "/api/expenses/my-summary",
    "/api/assets",
    "/expenses",
    "/assets",
    "/dashboard",
    "/parent",
    "/groups",
    "/attendance",
    "/database",
]
for ep in endpoints:
    rv = c.get(ep)
    print("[F]", ep, "->", rv.status_code)
    assert rv.status_code == 200, ep

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM redemptions WHERE id=?", (redid,))
    db.execute("DELETE FROM expense_store_link WHERE reward_id=?", (chocolate_id,))
    db.execute("DELETE FROM expenses WHERE id IN(?,?)", (exp_id, raed_exp_id))
    db.execute("DELETE FROM rewards WHERE id=?", (chocolate_id,))
    db.commit()

print()
print("ALL PHASE 4 E2E SCENARIOS PASSED.")
