"""C3 smoke - POST /api/points/redemptions/<id>/deliver widened."""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Provision a 980909805 user with known password for the allowlist test
TEST_USERNAME, TEST_PW = "980909805", "smoke_pw"
with A.app.app_context():
    db = A.get_db()
    existing = db.execute("SELECT id FROM users WHERE username=?",
                          (TEST_USERNAME,)).fetchone()
    if existing:
        db.execute(
            "UPDATE users SET password=?, role='manager', is_active=1 "
            "WHERE username=?", (A.hp(TEST_PW), TEST_USERNAME))
    else:
        db.execute(
            "INSERT INTO users(username, password, role, name, is_active, "
            "can_be_assigned_tasks) VALUES(?,?,?,?,1,1)",
            (TEST_USERNAME, A.hp(TEST_PW), "manager", "رائد"))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

def post(url):
    return c.post(url, headers={"Content-Type": "application/json"},
                  data="{}")

# Helpers — create a fresh 'pending' redemption + the points to back it
def make_pending(student_id=196, reward_id=1, cost=10):
    """Returns the new redemption id."""
    with A.app.app_context():
        db = A.get_db()
        db.execute(
            "INSERT INTO point_events(student_id, behavior_name, "
            "points_value, awarded_by_name) "
            "VALUES(?,'deliver smoke seed',?,'smoke')", (student_id, cost*5))
        db.execute(
            "INSERT INTO redemptions(student_id, student_name, reward_id, "
            "reward_name, points_spent, status) VALUES(?,?,?,?,?,'pending')",
            (student_id, "test", reward_id, "test reward", cost))
        db.commit()
        r = db.execute(
            "SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
        return int(dict(r)["id"])

cleanup_ids = []

# ── Test 1: admin marks delivered ──
login("admin", "admin123")
rid = make_pending(); cleanup_ids.append(rid)
rv = post(f"/api/points/redemptions/{rid}/deliver")
j = rv.get_json()
print(f"[1] admin deliver {rid} -> {rv.status_code} {j}")
assert rv.status_code == 200 and j["ok"] is True
assert j["status"] == "delivered"
assert j["delivered_by_username"] == "admin"

# Verify DB state
with A.app.app_context():
    db = A.get_db()
    row = dict(db.execute(
        "SELECT status, delivered_by, delivered_at FROM redemptions WHERE id=?",
        (rid,)).fetchone())
print(f"[1a] DB row: {row}")
assert row["status"] == "delivered"
assert row["delivered_by"] is not None
assert row["delivered_at"] is not None

# ── Test 2: allowlist user (980909805) marks delivered ──
login(TEST_USERNAME, TEST_PW)
rid2 = make_pending(); cleanup_ids.append(rid2)
rv = post(f"/api/points/redemptions/{rid2}/deliver")
j2 = rv.get_json()
print(f"[2] 980909805 deliver {rid2} -> {rv.status_code} actor={j2.get('delivered_by_username')}")
assert rv.status_code == 200 and j2["delivered_by_username"] == TEST_USERNAME

# ── Test 3: teacher1 blocked (403) ──
login("teacher1", "tea123")
rid3 = make_pending(); cleanup_ids.append(rid3)
rv = post(f"/api/points/redemptions/{rid3}/deliver")
print(f"[3] teacher1 deliver -> {rv.status_code}")
assert rv.status_code == 403

# ── Test 4: already-delivered → 400 friendly ──
login("admin", "admin123")
# rid is already delivered from test [1]
rv = post(f"/api/points/redemptions/{rid}/deliver")
j = rv.get_json()
print(f"[4] re-deliver same id -> {rv.status_code} err={j.get('error')!r}")
assert rv.status_code == 400
assert "مُسلَّم" in j["error"]

# ── Test 5: deliver on a 'cancelled' row → 400 ──
with A.app.app_context():
    db = A.get_db()
    cur = db.execute(
        "INSERT INTO redemptions(student_id, student_name, reward_id, "
        "reward_name, points_spent, status) VALUES(196,?,1,?,5,'cancelled')",
        ("test", "test reward"))
    db.commit()
    r = db.execute("SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
    cancelled_rid = int(dict(r)["id"])
    cleanup_ids.append(cancelled_rid)
rv = post(f"/api/points/redemptions/{cancelled_rid}/deliver")
j = rv.get_json()
print(f"[5] deliver cancelled -> {rv.status_code} err={j.get('error')!r}")
assert rv.status_code == 400
assert "الموافَق عليها" in j["error"]

# ── Test 6: non-existent id → 404 ──
rv = post("/api/points/redemptions/999999/deliver")
print(f"[6] deliver non-existent -> {rv.status_code}")
assert rv.status_code == 404

# ── Test 7: 8-route regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[7] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for rid in cleanup_ids:
        db.execute("DELETE FROM redemptions WHERE id=?", (rid,))
    db.execute("DELETE FROM point_events WHERE behavior_name='deliver smoke seed'")
    db.commit()

print("\nC3 deliver smoke passed.")
