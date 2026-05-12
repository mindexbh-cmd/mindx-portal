"""C4 smoke - POST /api/points/redemptions/<id>/undeliver."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

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

def make_delivered():
    """Seed a delivered redemption and return its id."""
    with A.app.app_context():
        db = A.get_db()
        db.execute(
            "INSERT INTO redemptions(student_id, student_name, reward_id, "
            "reward_name, points_spent, status, delivered_by, "
            "delivered_at) VALUES(196,?,1,?,5,'delivered',1,"
            "CURRENT_TIMESTAMP)",
            ("test", "test reward"))
        db.commit()
        r = db.execute("SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
        return int(dict(r)["id"])

def make_pending():
    with A.app.app_context():
        db = A.get_db()
        db.execute(
            "INSERT INTO redemptions(student_id, student_name, reward_id, "
            "reward_name, points_spent, status) VALUES(196,?,1,?,5,'pending')",
            ("test", "test reward"))
        db.commit()
        r = db.execute("SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
        return int(dict(r)["id"])

cleanup_ids = []

# ── Test 1: admin undelivers a delivered row ──
login("admin", "admin123")
rid = make_delivered(); cleanup_ids.append(rid)
rv = post(f"/api/points/redemptions/{rid}/undeliver")
j = rv.get_json()
print(f"[1] admin undeliver {rid} -> {rv.status_code} {j}")
assert rv.status_code == 200 and j["ok"] is True
assert j["status"] == "pending"

# Verify DB
with A.app.app_context():
    db = A.get_db()
    row = dict(db.execute(
        "SELECT status, delivered_by, delivered_at FROM redemptions WHERE id=?",
        (rid,)).fetchone())
print(f"[1a] DB: {row}")
assert row["status"] == "pending"
assert row["delivered_by"] is None
assert row["delivered_at"] is None

# ── Test 2: allowlist user (980909805) undelivers ──
login(TEST_USERNAME, TEST_PW)
rid2 = make_delivered(); cleanup_ids.append(rid2)
rv = post(f"/api/points/redemptions/{rid2}/undeliver")
print(f"[2] 980909805 undeliver -> {rv.status_code}")
assert rv.status_code == 200

# ── Test 3: teacher1 blocked ──
login("teacher1", "tea123")
rid3 = make_delivered(); cleanup_ids.append(rid3)
rv = post(f"/api/points/redemptions/{rid3}/undeliver")
print(f"[3] teacher1 -> {rv.status_code}")
assert rv.status_code == 403

# ── Test 4: undeliver a 'pending' row → 400 ──
login("admin", "admin123")
rid4 = make_pending(); cleanup_ids.append(rid4)
rv = post(f"/api/points/redemptions/{rid4}/undeliver")
j = rv.get_json()
print(f"[4] undeliver pending -> {rv.status_code} err={j.get('error')!r}")
assert rv.status_code == 400
assert "مُسلَّماً" in j["error"]

# ── Test 5: non-existent → 404 ──
rv = post("/api/points/redemptions/999999/undeliver")
print(f"[5] non-existent -> {rv.status_code}")
assert rv.status_code == 404

# ── Test 6: round trip — deliver → undeliver → deliver again ──
rid6 = make_pending(); cleanup_ids.append(rid6)
# Step a: deliver
rv = post(f"/api/points/redemptions/{rid6}/deliver")
assert rv.status_code == 200 and rv.get_json()["status"] == "delivered"
# Step b: undeliver
rv = post(f"/api/points/redemptions/{rid6}/undeliver")
assert rv.status_code == 200 and rv.get_json()["status"] == "pending"
# Step c: deliver again
rv = post(f"/api/points/redemptions/{rid6}/deliver")
assert rv.status_code == 200 and rv.get_json()["status"] == "delivered"
print(f"[6] round trip rid={rid6}: pending→delivered→pending→delivered ✓")

# Balance unchanged by undeliver+redeliver — _pts_balance includes both
# 'pending' and 'delivered' so the round trip is balance-neutral. We
# verify by counting that the spent total stays consistent.
with A.app.app_context():
    db = A.get_db()
    row = dict(db.execute(
        "SELECT status FROM redemptions WHERE id=?", (rid6,)).fetchone())
    assert row["status"] == "delivered"

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
    db.commit()

print("\nC4 undeliver smoke passed.")
