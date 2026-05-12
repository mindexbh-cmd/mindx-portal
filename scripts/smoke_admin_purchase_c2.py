"""C2 smoke - POST /api/points/admin-purchase endpoint."""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# ── Setup: create allowlist user (980909805) + give a test student 200 pts ──
SID = 196   # طالب الجزئي
RID_CHEAP   = 1    # ملصق نجمة, 10 pts, stock=-1 (infinite)
RID_FINITE  = 10   # شوكولاتة C26, 50 pts, stock=5
RID_INACTIVE = 5   # test, 10 pts, stock=-1, is_active=0
TEST_USERNAME = "980909805"
TEST_PW = "smoke_raed_pw"

created_event_ids = []
created_redemption_ids = []

with A.app.app_context():
    db = A.get_db()
    # Ensure 980909805 user exists with known password + manager role
    existing = db.execute(
        "SELECT id FROM users WHERE username=?", (TEST_USERNAME,)).fetchone()
    if existing:
        db.execute(
            "UPDATE users SET password=?, role='manager', is_active=1 "
            "WHERE username=?", (A.hp(TEST_PW), TEST_USERNAME))
    else:
        db.execute(
            "INSERT INTO users(username, password, role, name, is_active, "
            "can_be_assigned_tasks) VALUES(?,?,?,?,1,1)",
            (TEST_USERNAME, A.hp(TEST_PW), "manager", "رائد"))
    # Seed point_events to give SID 200 points
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, points_value, "
        "awarded_by_name) VALUES(?,?,?,?)",
        (SID, "C2 smoke seed", 200, "smoke"))
    db.commit()
    ev = db.execute(
        "SELECT id FROM point_events WHERE behavior_name='C2 smoke seed' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if ev:
        created_event_ids.append(int(dict(ev)["id"]))

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

def post_purchase(body):
    return c.post("/api/points/admin-purchase",
                  headers={"Content-Type": "application/json"},
                  data=json.dumps(body))

# ── Test 1: admin purchases for the student (10 pts) ──
login("admin", "admin123")
rv = post_purchase({"student_id": SID, "reward_id": RID_CHEAP,
                    "note": "Test purchase by admin"})
j = rv.get_json()
print(f"[1] admin POST -> {rv.status_code}", j)
assert rv.status_code == 200 and j["ok"] is True
assert j["points_deducted"] == 10
assert j["new_balance"] == 190  # 200 - 10
assert j["actor_username"] == "admin"
assert j["redemption_id"], "missing redemption_id"
created_redemption_ids.append(int(j["redemption_id"]))

# Verify the row is status=delivered + request_source=admin_on_behalf
with A.app.app_context():
    db = A.get_db()
    row = dict(db.execute(
        "SELECT status, request_source, delivered_by, delivered_at "
        "FROM redemptions WHERE id=?",
        (j["redemption_id"],)).fetchone())
    print(f"[1a] row: {row}")
    assert row["status"] == "delivered"
    assert row["request_source"] == "admin_on_behalf"
    assert row["delivered_by"] is not None
    assert row["delivered_at"] is not None

# ── Test 2: allowlist user (980909805) purchases ──
login(TEST_USERNAME, TEST_PW)
rv = post_purchase({"student_id": SID, "reward_id": RID_CHEAP})
j = rv.get_json()
print(f"[2] 980909805 POST -> {rv.status_code} new_balance={j.get('new_balance')}")
assert rv.status_code == 200 and j["ok"] is True
assert j["actor_username"] == TEST_USERNAME
assert j["new_balance"] == 180  # 190 - 10
created_redemption_ids.append(int(j["redemption_id"]))

# ── Test 3: teacher1 blocked (403) ──
login("teacher1", "tea123")
rv = post_purchase({"student_id": SID, "reward_id": RID_CHEAP})
print(f"[3] teacher1 POST -> {rv.status_code}")
assert rv.status_code == 403

# ── Test 4: invalid payload (missing reward_id) ──
login("admin", "admin123")
rv = post_purchase({"student_id": SID})
print(f"[4] admin missing reward_id -> {rv.status_code}")
assert rv.status_code == 400

# ── Test 5: non-existent student ──
rv = post_purchase({"student_id": 999999, "reward_id": RID_CHEAP})
print(f"[5] non-existent student -> {rv.status_code}")
assert rv.status_code == 404

# ── Test 6: non-existent reward ──
rv = post_purchase({"student_id": SID, "reward_id": 999999})
print(f"[6] non-existent reward -> {rv.status_code}")
assert rv.status_code == 404

# ── Test 7: inactive reward ──
rv = post_purchase({"student_id": SID, "reward_id": RID_INACTIVE})
j = rv.get_json()
print(f"[7] inactive reward -> {rv.status_code} {j}")
assert rv.status_code == 400
assert "inactive" in (j.get("error") or "")

# ── Test 8: note > 500 chars ──
rv = post_purchase({"student_id": SID, "reward_id": RID_CHEAP,
                    "note": "x" * 501})
print(f"[8] note>500 -> {rv.status_code}")
assert rv.status_code == 400

# ── Test 9: insufficient balance ──
# Find current balance, attempt a reward costing balance+1
with A.app.app_context():
    db = A.get_db()
    bal = A._pts_balance(db, SID)
    print(f"[9pre] current balance = {bal}")
    # Create temporary expensive reward (insert + cleanup after)
    cur = db.execute(
        "INSERT INTO rewards(name_ar, point_cost, stock, is_active) "
        "VALUES(?,?,?,1)", ("smoke too-expensive", bal + 999, -1))
    db.commit()
    new_r = db.execute(
        "SELECT id FROM rewards WHERE name_ar='smoke too-expensive' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    expensive_rid = int(dict(new_r)["id"])
rv = post_purchase({"student_id": SID, "reward_id": expensive_rid})
j = rv.get_json()
print(f"[9] insufficient -> {rv.status_code} {j}")
assert rv.status_code == 400
assert "insufficient" in (j.get("error") or "")
# Verify no row was inserted for this attempt
with A.app.app_context():
    db = A.get_db()
    cnt = db.execute(
        "SELECT COUNT(*) FROM redemptions WHERE reward_id=?",
        (expensive_rid,)).fetchone()[0]
    print(f"[9a] redemption rows for failed attempt = {cnt}")
    assert cnt == 0

# ── Test 10: out-of-stock reward ──
with A.app.app_context():
    db = A.get_db()
    cur = db.execute(
        "INSERT INTO rewards(name_ar, point_cost, stock, is_active) "
        "VALUES(?,?,?,1)", ("smoke no-stock", 5, 0))
    db.commit()
    new_r = db.execute(
        "SELECT id FROM rewards WHERE name_ar='smoke no-stock' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    nostock_rid = int(dict(new_r)["id"])
rv = post_purchase({"student_id": SID, "reward_id": nostock_rid})
j = rv.get_json()
print(f"[10] out-of-stock -> {rv.status_code} {j}")
assert rv.status_code == 400
assert "stock" in (j.get("error") or "")

# ── Test 11: finite-stock reward decrement ──
with A.app.app_context():
    db = A.get_db()
    pre_stock = int(dict(db.execute(
        "SELECT stock FROM rewards WHERE id=?", (RID_FINITE,)).fetchone())["stock"])
    print(f"[11pre] reward {RID_FINITE} stock = {pre_stock}")
rv = post_purchase({"student_id": SID, "reward_id": RID_FINITE})
j = rv.get_json()
print(f"[11] finite-stock purchase -> {rv.status_code}")
assert rv.status_code == 200 and j["ok"] is True
created_redemption_ids.append(int(j["redemption_id"]))
with A.app.app_context():
    db = A.get_db()
    post_stock = int(dict(db.execute(
        "SELECT stock FROM rewards WHERE id=?", (RID_FINITE,)).fetchone())["stock"])
    print(f"[11a] reward {RID_FINITE} stock after = {post_stock}")
    assert post_stock == pre_stock - 1

# ── Test 12: 8-route admin regression ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[12] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 13: parent-portal redemption flow untouched ──
# Quick spot-check: GET /api/points/rewards still returns active rewards
rv = c.get('/api/points/rewards')
print(f"[13] /api/points/rewards -> {rv.status_code}")
assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    # Remove smoke redemptions
    for rid in created_redemption_ids:
        db.execute("DELETE FROM redemptions WHERE id=?", (rid,))
    # Restore finite-stock count
    db.execute(
        "UPDATE rewards SET stock=? WHERE id=?", (5, RID_FINITE))
    # Drop the two temporary rewards
    db.execute("DELETE FROM rewards WHERE name_ar IN "
               "('smoke too-expensive', 'smoke no-stock')")
    # Drop seeded point events
    for eid in created_event_ids:
        db.execute("DELETE FROM point_events WHERE id=?", (eid,))
    # Also delete any orphan smoke-seed events not in created_event_ids
    db.execute("DELETE FROM point_events WHERE behavior_name='C2 smoke seed'")
    db.commit()

print("\nC2 smoke passed.")
