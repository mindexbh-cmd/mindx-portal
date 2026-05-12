"""C2 smoke - admin-purchase search-fix: confirm the offending
line is gone and the Promise.all() path is reachable."""
import os, sys, io, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: /api/students still returns the expected shape ──
login("admin", "admin123")
rv = c.get('/api/students')
print(f"[1] /api/students -> {rv.status_code}")
assert rv.status_code == 200
j = rv.get_json()
assert 'students' in j and isinstance(j['students'], list)
print(f"[1a] response has 'students' field (count={len(j['students'])})")
# Confirm field names match what the modal reads
if j['students']:
    row = j['students'][0]
    assert 'id' in row, "row missing id"
    assert 'student_name' in row, "row missing student_name"
    assert 'personal_id' in row, "row missing personal_id"
    print("[1b] rows expose id + student_name + personal_id ✓")

# ── Test 2: served HTML no longer contains the bug line ──
rv = c.get('/points/manage')
assert rv.status_code == 200
html = rv.get_data(as_text=True)
# The offending line was exactly: document.getElementById('ap-note').value='';
# Make sure it's gone from apOpen's body
i_open = html.find('function apOpen()')
assert i_open > 0, "apOpen function not found"
# Take the body up to the next function declaration to scope our check
i_next = html.find('function apClose()', i_open)
apopen_body = html[i_open:i_next]
print(f"[2] apOpen body length: {len(apopen_body)} chars")
assert "document.getElementById('ap-note').value=''" not in apopen_body, \
    "the buggy line is STILL there!"
assert "do NOT clear" in apopen_body, "missing the explanatory comment"
print("[2a] buggy ap-note clear line removed ✓")
print("[2b] explanatory comment present ✓")

# ── Test 3: the Promise.all block is unchanged (we didn't break the load) ──
assert "Promise.all([" in apopen_body
assert "fetch('/api/students'" in apopen_body
assert "fetch('/api/points/rewards'" in apopen_body
assert "_AP_STUDENTS = (ar[0]" in apopen_body
print("[3] Promise.all(/api/students + /api/points/rewards) intact ✓")

# ── Test 4: apPickReward still injects an ap-note textarea ──
# (so the post-fix code path still has a textarea to read from)
i_pick = html.find('function apPickReward(')
i_pick_end = html.find('function apConfirm()', i_pick)
pick_body = html[i_pick:i_pick_end]
assert 'id="ap-note"' in pick_body, \
    "apPickReward no longer injects an ap-note textarea — would break confirm"
print("[4] apPickReward still creates a fresh <textarea id=ap-note> ✓")

# ── Test 5: apConfirm reads ap-note safely (after pick) ──
i_conf = html.find('function apConfirm()')
i_conf_end = html.find('function apReset()', i_conf)
conf_body = html[i_conf:i_conf_end]
assert "getElementById('ap-note').value" in conf_body, \
    "apConfirm no longer reads ap-note — note would be lost"
print("[5] apConfirm reads ap-note (only runs after pick) ✓")

# ── Test 6: end-to-end via the underlying API (smoke of C2/C3 still works) ──
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, points_value, "
        "awarded_by_name) VALUES(196, 'search-fix smoke seed', 60, 'smoke')")
    db.commit()
rv = c.post("/api/points/admin-purchase",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"student_id": 196, "reward_id": 1,
                             "note": "search-fix smoke"}))
j = rv.get_json()
print(f"[6] POST admin-purchase -> {rv.status_code} new_balance={j.get('new_balance')}")
assert rv.status_code == 200 and j["ok"] is True
created_rid = j["redemption_id"]

# ── Test 7: 8-route regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[7] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    if created_rid:
        db.execute("DELETE FROM redemptions WHERE id=?", (created_rid,))
    db.execute("DELETE FROM point_events WHERE behavior_name='search-fix smoke seed'")
    db.commit()

print("\nC2 search-fix smoke passed.")
