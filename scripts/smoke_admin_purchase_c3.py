"""C3 smoke - /points/manage UI: admin-purchase modal markup."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Ensure 980909805 user exists for allowlist verification
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

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: admin /points/manage renders + has new button + modal ──
login("admin", "admin123")
rv = c.get("/points/manage")
print(f"[1] admin /points/manage -> {rv.status_code}")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
# Button in topbar
assert 'apOpen()' in html, "apOpen() button missing"
assert 'شراء نيابة عن طالب' in html, "Arabic button label missing"
# Modal markup
assert 'id="ap-modal"' in html
assert 'id="ap-q"' in html
assert 'id="ap-results"' in html
assert 'id="ap-student"' in html
assert 'id="ap-rewards"' in html
assert 'id="ap-confirm"' in html
# JS functions present
for fn in ['function apOpen()', 'function apClose()', 'function apSearch()',
          'function apPickStudent', 'function apPickReward',
          'function apConfirm()', 'function _apNorm', 'function _apScore']:
    assert fn in html, f"missing JS function: {fn}"
# Endpoint URL referenced
assert '/api/points/admin-purchase' in html
print("[1a] all 8 helper functions + endpoint URL present in served HTML")

# ── Test 2: allowlist user (980909805) renders the same UI ──
login("980909805", "raed_pw")
rv = c.get("/points/manage")
print(f"[2] 980909805 /points/manage -> {rv.status_code}")
assert rv.status_code == 200
html2 = rv.get_data(as_text=True)
assert 'apOpen()' in html2
assert 'id="ap-modal"' in html2

# ── Test 3: teacher1 → 302 (still blocked, no UI shipped to them) ──
login("teacher1", "tea123")
rv = c.get("/points/manage", follow_redirects=False)
print(f"[3] teacher1 /points/manage -> {rv.status_code}")
assert rv.status_code == 302
# /dashboard redirect target — teacher then bounces to /teacher/hub
assert "/dashboard" in rv.headers.get("Location", "")

# ── Test 4: full POST round-trip via the modal's endpoint ──
# Reuses logic from C2 smoke but exercises the same API the JS calls.
import json, datetime
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, points_value, "
        "awarded_by_name) VALUES(196, 'C3 ui smoke seed', 60, 'smoke')")
    db.commit()
login("admin", "admin123")
rv = c.post("/api/points/admin-purchase",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"student_id": 196, "reward_id": 1,
                             "note": "from C3 UI smoke"}))
j = rv.get_json()
print(f"[4] POST -> {rv.status_code} new_balance={j.get('new_balance')}")
assert rv.status_code == 200 and j["ok"] is True
created_redemption_id = j["redemption_id"]

# ── Test 5: 8-route admin regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[5] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 6: parent-portal flow markup untouched ──
# The parent-portal redemption endpoint should still work
rv = c.get('/api/points/rewards')
assert rv.status_code == 200
print("[6] /api/points/rewards still accessible (parent-portal dependency)")

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    if created_redemption_id:
        db.execute("DELETE FROM redemptions WHERE id=?",
                   (created_redemption_id,))
    db.execute("DELETE FROM point_events WHERE behavior_name='C3 ui smoke seed'")
    db.commit()

print("\nC3 smoke passed.")
