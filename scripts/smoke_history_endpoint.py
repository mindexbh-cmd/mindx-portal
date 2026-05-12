"""C5 smoke - GET /api/points/history with filters."""
import os, sys, io, json, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Seed 5 different redemption rows so filters have something to match
cleanup_ids = []
with A.app.app_context():
    db = A.get_db()
    seeds = [
        # (student_id, status, source, name, cost)
        (196, "pending",   "",                  "طالب الجزئي", 10),
        (199, "delivered", "admin_on_behalf",   "طالب بقايا",   20),
        (201, "rejected",  "parent_pid",        "طالب الفلو",   30),
        (4720, "cancelled", "",                 "تسنيم تيست",   40),
        (196, "rejected",   "parent_pid",       "طالب الجزئي",  50),
    ]
    for sid, st, src, name, cost in seeds:
        db.execute(
            "INSERT INTO redemptions(student_id, student_name, reward_id, "
            "reward_name, points_spent, status, request_source, "
            "rejection_reason) VALUES(?,?,1,?,?,?,?,?)",
            (sid, name, "history-smoke-reward", cost, st, src,
             "نفد المخزون" if st == "rejected" else None))
    db.commit()
    rows = db.execute(
        "SELECT id FROM redemptions WHERE reward_name='history-smoke-reward' "
        "ORDER BY id DESC LIMIT 5").fetchall()
    cleanup_ids = [int(dict(r)["id"]) for r in rows]
print(f"[setup] seeded {len(cleanup_ids)} rows: {cleanup_ids}")

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: admin no-filter → returns rows (at least our 5) ──
login("admin", "admin123")
rv = c.get("/api/points/history")
j = rv.get_json()
print(f"[1] no-filter -> {rv.status_code} total={j.get('total')}")
assert rv.status_code == 200 and j["ok"] is True
assert isinstance(j["rows"], list)
assert j["total"] >= 5
# Shape check
r = j["rows"][0]
for k in ("id", "student_name", "reward_name", "points_spent", "status",
         "redeemed_at", "request_source", "rejection_reason"):
    assert k in r, f"missing field: {k}"
print(f"[1a] response has all required fields ✓")

# ── Test 2: status filter ──
rv = c.get("/api/points/history?status=rejected")
j = rv.get_json()
all_rejected = all(r["status"] == "rejected" for r in j["rows"])
print(f"[2] status=rejected -> {j['total']} rows, all rejected? {all_rejected}")
assert all_rejected and j["total"] >= 2

# Verify rejection_reason is in the row
rej = [r for r in j["rows"] if r["id"] in cleanup_ids]
assert all(r["rejection_reason"] == "نفد المخزون" for r in rej), \
    "rejection_reason not surfaced"
print("[2a] rejection_reason field is populated for rejected rows ✓")

# ── Test 3: source filter ──
rv = c.get("/api/points/history?source=admin_on_behalf")
j = rv.get_json()
all_aob = all(r["request_source"] == "admin_on_behalf" for r in j["rows"])
print(f"[3] source=admin_on_behalf -> {j['total']} rows, all match? {all_aob}")
assert all_aob

rv = c.get("/api/points/history?source=parent")
j = rv.get_json()
all_parent = all(r["request_source"] in ("parent_pid", "parent_login")
                 for r in j["rows"])
print(f"[3a] source=parent -> {j['total']} rows, all match? {all_parent}")
assert all_parent

# ── Test 4: Arabic fuzzy name filter ──
# Searching "طالب الجزئى" (with ى) should match "طالب الجزئي" (with ي)
rv = c.get("/api/points/history?student_name_q=الجزئى")
j = rv.get_json()
print(f"[4] name_q=الجزئى -> {j['total']} rows")
assert j["total"] >= 1
hit = any("الجزئي" in (r["student_name"] or "") for r in j["rows"])
assert hit, "Arabic fold didn't match ى → ي"

# ── Test 5: date filter ──
today = datetime.date.today().isoformat()
rv = c.get(f"/api/points/history?date_from={today}&date_to={today}")
j = rv.get_json()
print(f"[5] today-only -> {j['total']} rows (our 5 seeded today)")
assert j["total"] >= 5

# ── Test 6: pagination ──
rv = c.get("/api/points/history?limit=2")
j = rv.get_json()
print(f"[6] limit=2 -> {len(j['rows'])} rows, has_more={j['has_more']}")
assert len(j["rows"]) <= 2
assert j["has_more"] is True

rv = c.get("/api/points/history?limit=2&offset=2")
j2 = rv.get_json()
print(f"[6a] offset=2 -> different page? {j['rows'][0]['id'] != j2['rows'][0]['id']}")
assert j["rows"][0]["id"] != j2["rows"][0]["id"]

# ── Test 7: limit capped at 200 ──
rv = c.get("/api/points/history?limit=99999")
j = rv.get_json()
print(f"[7] limit=99999 (should cap at 200) -> limit={j['limit']}")
assert j["limit"] == 200

# ── Test 8: teacher1 → 403 ──
login("teacher1", "tea123")
rv = c.get("/api/points/history")
print(f"[8] teacher1 -> {rv.status_code}")
assert rv.status_code == 403

# ── Test 9: 980909805 (allowlist) → 200 ──
with A.app.app_context():
    db = A.get_db()
    existing = db.execute("SELECT id FROM users WHERE username=?",
                          ("980909805",)).fetchone()
    if existing:
        db.execute(
            "UPDATE users SET password=?, role='manager', is_active=1 "
            "WHERE username=?", (A.hp("raed_pw"), "980909805"))
    else:
        db.execute(
            "INSERT INTO users(username, password, role, name, is_active, "
            "can_be_assigned_tasks) VALUES(?,?,?,?,1,1)",
            ("980909805", A.hp("raed_pw"), "manager", "رائد"))
    db.commit()
login("980909805", "raed_pw")
rv = c.get("/api/points/history")
print(f"[9] 980909805 -> {rv.status_code}")
assert rv.status_code == 200

# ── Test 10: 8-route regression ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[10] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for rid in cleanup_ids:
        db.execute("DELETE FROM redemptions WHERE id=?", (rid,))
    db.commit()

print("\nC5 history smoke passed.")
