"""C26 smoke - atomic store-link transaction."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# Resolve category ids + create test rewards
with A.app.app_context():
    db = A.get_db()
    op_cat   = dict(db.execute("SELECT id FROM expense_categories "
                                "WHERE name_ar=?",
                                ("تشغيلي (إيجار/كهرباء/إنترنت)",)).fetchone())["id"]
    store_cat = dict(db.execute("SELECT id FROM expense_categories "
                                 "WHERE name_ar=?",
                                 ("مشتريات للمتجر (مأكولات/ألعاب)",)).fetchone())["id"]
    # Create a finite-stock test reward
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("شوكولاتة C26", 50, "🍫", 5, "food", 1))
    try: finite_id = cur.lastrowid
    except Exception: finite_id = None
    if not finite_id:
        finite_id = dict(db.execute("SELECT id FROM rewards "
                                     "WHERE name_ar=? ORDER BY id DESC LIMIT 1",
                                     ("شوكولاتة C26",)).fetchone())["id"]
    # Create an infinite-stock test reward
    cur = db.execute("INSERT INTO rewards(name_ar, point_cost, icon, "
                     "stock, category, is_active) VALUES(?,?,?,?,?,?)",
                     ("لعبة C26", 100, "🎲", -1, "toy", 1))
    try: inf_id = cur.lastrowid
    except Exception: inf_id = None
    if not inf_id:
        inf_id = dict(db.execute("SELECT id FROM rewards "
                                  "WHERE name_ar=? ORDER BY id DESC LIMIT 1",
                                  ("لعبة C26",)).fetchone())["id"]
    db.commit()
print("[setup] finite=", finite_id, "stock=5; infinite=", inf_id, "stock=-1")
print("[setup] op_cat=", op_cat, "store_cat=", store_cat)

login("admin", "admin123")
expense_ids = []

def _get_stock(rid):
    with A.app.app_context():
        db = A.get_db()
        return int(dict(db.execute("SELECT COALESCE(stock,0) AS s "
                                    "FROM rewards WHERE id=?",
                                    (rid,)).fetchone())["s"])

def _expense_count():
    with A.app.app_context():
        db = A.get_db()
        return int(dict(db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone())["c"])

def _esl_count():
    with A.app.app_context():
        db = A.get_db()
        return int(dict(db.execute("SELECT COUNT(*) AS c FROM expense_store_link").fetchone())["c"])

# Test 1: backward compat - POST without store_link still works
exp_before = _expense_count()
rv = c.post("/api/expenses", json={
    "category_id": op_cat, "amount": 30, "description": "كهرباء",
    "expense_date": "2026-05-12"
})
print("[1] no store_link ->", rv.status_code, rv.get_json())
assert rv.status_code == 200
assert _expense_count() == exp_before + 1
expense_ids.append((rv.get_json() or {}).get("id"))

# Test 2: wrong category + store_link -> silently ignored
esl_before = _esl_count()
stock_before = _get_stock(finite_id)
rv = c.post("/api/expenses", json={
    "category_id": op_cat, "amount": 30,
    "description": "كهرباء مع محاولة ربط",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": 10}
})
j = rv.get_json()
print("[2] wrong cat + link ->", rv.status_code, "linked=", j.get("linked"))
assert rv.status_code == 200
assert j.get("linked") is False
assert _esl_count() == esl_before  # no ESL row
assert _get_stock(finite_id) == stock_before  # stock unchanged
expense_ids.append(j.get("id"))

# Test 3: SUCCESS - chocolate purchase, 20 units, 10 BHD = 0.500 unit cost
esl_before = _esl_count()
stock_before = _get_stock(finite_id)
exp_before = _expense_count()
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10.000,
    "description": "20 شوكولاتة كادبوري للمتجر",
    "vendor_name": "Carrefour", "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": 20}
})
j = rv.get_json()
print("[3] success path ->", rv.status_code, j)
assert rv.status_code == 200
assert j.get("linked") is True
assert j.get("link_details", {}).get("unit_cost") == 0.5
assert _expense_count() == exp_before + 1
assert _esl_count() == esl_before + 1
assert _get_stock(finite_id) == stock_before + 20  # 5 + 20 = 25
expense_ids.append(j.get("id"))

# Test 4: forced failure - invalid reward_id, NOTHING committed
esl_before = _esl_count()
exp_before = _expense_count()
stock_before = _get_stock(finite_id)
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10,
    "description": "محاولة بمنتج وهمي",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": 99999, "quantity": 10}
})
j = rv.get_json()
print("[4] bogus reward ->", rv.status_code, j)
assert rv.status_code == 400
assert "غير موجود" in (j.get("error") or "")
assert _expense_count() == exp_before  # NO new expense
assert _esl_count() == esl_before
assert _get_stock(finite_id) == stock_before  # no stock change

# Test 5: infinite stock reward (-1) → link created, stock stays -1
esl_before = _esl_count()
stock_before = _get_stock(inf_id)
assert stock_before == -1
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 50,
    "description": "5 ألعاب جديدة للمتجر",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": inf_id, "quantity": 5}
})
j = rv.get_json()
print("[5] infinite stock ->", rv.status_code, j)
assert rv.status_code == 200
assert j.get("linked") is True
assert _esl_count() == esl_before + 1  # link recorded
assert _get_stock(inf_id) == -1  # stock UNCHANGED
expense_ids.append(j.get("id"))

# Test 6: quantity=0 → 400, no DB change
exp_before = _expense_count()
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10,
    "description": "كمية صفر",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": 0}
})
j = rv.get_json()
print("[6] qty=0 ->", rv.status_code, j)
assert rv.status_code == 400
assert _expense_count() == exp_before

# Test 7: negative quantity → 400
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10,
    "description": "كمية سالبة",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": -3}
})
print("[7] qty=-3 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Test 8: decimal quantity (1.5) → 400
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10,
    "description": "كمية بكسر",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": 1.5}
})
print("[8] qty=1.5 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Test 9: missing reward_id → 400
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 10,
    "description": "بدون منتج",
    "expense_date": "2026-05-12",
    "store_link": {"quantity": 5}
})
print("[9] missing reward_id ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Test 10: raed can also use store-link (legitimately buys supplies)
c.get("/")
login("980909805", "raed123")
esl_before = _esl_count()
stock_before = _get_stock(finite_id)
rv = c.post("/api/expenses", json={
    "category_id": store_cat, "amount": 5.000,
    "description": "raed يشتري للمتجر",
    "expense_date": "2026-05-12",
    "store_link": {"reward_id": finite_id, "quantity": 10}
})
j = rv.get_json()
print("[10] raed store-link ->", rv.status_code, j)
assert rv.status_code == 200
assert j.get("linked") is True
assert _esl_count() == esl_before + 1
assert _get_stock(finite_id) == stock_before + 10
expense_ids.append(j.get("id"))

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for eid in expense_ids:
        if eid:
            db.execute("DELETE FROM expense_store_link WHERE expense_id=?", (eid,))
            db.execute("DELETE FROM expenses WHERE id=?", (eid,))
    db.execute("DELETE FROM rewards WHERE id IN(?,?)", (finite_id, inf_id))
    db.commit()
print("\nAll C26 smoke checks passed.")
