"""C1 smoke - backend permission expansion for /points/manage."""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Set up the allowlist users locally so the smoke can exercise them.
# (Production already has raed + ahmed_ibrahim — local DB doesn't.)
SMOKE_USERS = [("raed", "raed_smoke_pw"),
               ("ahmed_ibrahim", "ahmed_smoke_pw")]
with A.app.app_context():
    db = A.get_db()
    for u, p in SMOKE_USERS:
        existing = db.execute("SELECT id FROM users WHERE username=?",
                              (u,)).fetchone()
        if existing:
            db.execute(
                "UPDATE users SET password=?, role='reception', "
                "is_active=1, can_be_assigned_tasks=1 WHERE username=?",
                (A.hp(p), u))
        else:
            db.execute(
                "INSERT INTO users(username, password, role, name, "
                "is_active, can_be_assigned_tasks) "
                "VALUES(?,?,?,?,1,1)",
                (u, A.hp(p), "reception", u))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: admin → /points/manage = 200 ──
login("admin", "admin123")
rv = c.get("/points/manage")
print("[1] admin /points/manage ->", rv.status_code)
assert rv.status_code == 200, f"admin should still get /points/manage: {rv.status_code}"

# ── Test 2: raed → /points/manage = 200 (NEW) ──
login("raed", "raed_smoke_pw")
rv = c.get("/points/manage", follow_redirects=False)
print("[2] raed /points/manage ->", rv.status_code)
assert rv.status_code == 200, (
    f"raed should get /points/manage now: {rv.status_code}")

# ── Test 3: ahmed_ibrahim → /points/manage = 200 (NEW) ──
login("ahmed_ibrahim", "ahmed_smoke_pw")
rv = c.get("/points/manage", follow_redirects=False)
print("[3] ahmed_ibrahim /points/manage ->", rv.status_code)
assert rv.status_code == 200

# ── Test 4: teacher1 → /points/manage = 302 (still blocked) ──
login("teacher1", "tea123")
rv = c.get("/points/manage", follow_redirects=False)
print("[4] teacher1 /points/manage ->", rv.status_code,
      "(should 302 → /dashboard)")
assert rv.status_code == 302
assert "/dashboard" in rv.headers.get("Location", "")

# ── Test 5: representative API endpoints ──
# /api/points/rewards POST (admin-only via _pts_user_role gate)
login("admin", "admin123")
body = {"name_ar": "C1 smoke reward", "point_cost": 10}
rv = c.post("/api/points/rewards",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body))
print(f"[5a] admin POST /api/points/rewards -> {rv.status_code}")
assert rv.status_code in (200, 201), rv.get_data(as_text=True)[:200]
created_reward_id = None
try:
    j = rv.get_json()
    created_reward_id = j.get("id") or (j.get("reward") or {}).get("id")
except Exception:
    pass

login("raed", "raed_smoke_pw")
body = {"name_ar": "C1 smoke reward (raed)", "point_cost": 20}
rv = c.post("/api/points/rewards",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body))
print(f"[5b] raed POST /api/points/rewards -> {rv.status_code} (NEW)")
assert rv.status_code in (200, 201), rv.get_data(as_text=True)[:200]
raed_reward_id = None
try:
    j = rv.get_json()
    raed_reward_id = j.get("id") or (j.get("reward") or {}).get("id")
except Exception:
    pass

login("teacher1", "tea123")
rv = c.post("/api/points/rewards",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"name_ar": "blocked", "point_cost": 1}))
print(f"[5c] teacher1 POST /api/points/rewards -> {rv.status_code} (still 403)")
assert rv.status_code == 403

# /api/points/reports/admin (admin-only)
login("admin", "admin123")
rv = c.get("/api/points/reports/admin")
print(f"[6a] admin GET /api/points/reports/admin -> {rv.status_code}")
assert rv.status_code == 200

login("raed", "raed_smoke_pw")
rv = c.get("/api/points/reports/admin")
print(f"[6b] raed GET /api/points/reports/admin -> {rv.status_code} (NEW)")
assert rv.status_code == 200

login("teacher1", "tea123")
rv = c.get("/api/points/reports/admin")
print(f"[6c] teacher1 GET /api/points/reports/admin -> {rv.status_code} (403)")
assert rv.status_code == 403

# /api/points/behaviors POST — admin/manager/teacher all allowed
# (teacher creates personal-only behaviors; admin/manager create global)
# Raed becomes admin-equivalent in the points subsystem, so the
# resulting row should be is_global=1.
login("raed", "raed_smoke_pw")
rv = c.post("/api/points/behaviors",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"name_ar": "C1 smoke behavior",
                             "type": "positive", "points_value": 5}))
print(f"[7] raed POST /api/points/behaviors -> {rv.status_code}")
assert rv.status_code in (200, 201), rv.get_data(as_text=True)[:200]
created_behavior_id = None
try:
    j = rv.get_json()
    created_behavior_id = j.get("id") or (j.get("behavior") or {}).get("id")
except Exception:
    pass

# ── Test 8: sanity — raed still BLOCKED from /database ──
login("raed", "raed_smoke_pw")
rv = c.get("/database", follow_redirects=False)
print(f"[8a] raed /database -> {rv.status_code} (should still be blocked)")
assert rv.status_code != 200, (
    f"raed should NOT have access to /database: {rv.status_code}")

# /admin/permissions (admin-only)
rv = c.get("/admin/permissions", follow_redirects=False)
print(f"[8b] raed /admin/permissions -> {rv.status_code} (should still be blocked)")
assert rv.status_code != 200

# ── Test 9: 8-route regression for admin ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[9] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    if created_reward_id:
        db.execute("DELETE FROM rewards WHERE id=?", (created_reward_id,))
    if raed_reward_id:
        db.execute("DELETE FROM rewards WHERE id=?", (raed_reward_id,))
    if created_behavior_id:
        db.execute("DELETE FROM behaviors WHERE id=?", (created_behavior_id,))
    for u, _ in SMOKE_USERS:
        db.execute("DELETE FROM users WHERE username=?", (u,))
    db.commit()

print("\nC1 smoke passed.")
