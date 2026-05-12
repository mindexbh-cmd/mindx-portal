"""C8 smoke - parent portal shows rejection reason."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Need to seed: a student with a PID, and a rejected redemption with
# rejection_reason set.
SID = 196
PID = "C8_SMOKE_PID"
REASON_TEXT = "المخزون نفذ — الرجاء الانتظار حتى التجديد"
RID_RIDS = []

with A.app.app_context():
    db = A.get_db()
    # Save original personal_id and set our smoke PID
    original_pid_row = db.execute(
        "SELECT personal_id FROM students WHERE id=?", (SID,)).fetchone()
    original_pid = dict(original_pid_row)["personal_id"] if original_pid_row else None
    db.execute("UPDATE students SET personal_id=? WHERE id=?", (PID, SID))
    # Insert a rejected redemption with a reason
    db.execute(
        "INSERT INTO redemptions(student_id, student_name, reward_id, "
        "reward_name, points_spent, status, request_source, "
        "rejection_reason) "
        "VALUES(?,?,?,?,?,'rejected','parent_pid',?)",
        (SID, "C8 smoke student", 1, "C8 smoke reward", 10, REASON_TEXT))
    db.commit()
    r = db.execute(
        "SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
    RID_RIDS.append(int(dict(r)["id"]))
print(f"[setup] seeded rejected redemption id={RID_RIDS[0]} with PID={PID}")

c = A.app.test_client()

# ── Test 1: backend — /api/parent/store/menu returns recent_rejected ──
rv = c.get(f"/api/parent/store/menu?pid={PID}")
j = rv.get_json()
print(f"[1] /api/parent/store/menu -> {rv.status_code}")
assert rv.status_code == 200 and j["ok"] is True
assert "recent_rejected" in j, "response missing recent_rejected field"
rejected = j["recent_rejected"]
print(f"[1a] recent_rejected count: {len(rejected)}")
assert len(rejected) >= 1, "no rejected rows in response"

# Verify the row has the expected fields
r = rejected[0]
for k in ("redemption_id", "reward_id", "reward_name", "points_spent",
         "rejected_at", "rejection_reason"):
    assert k in r, f"missing field: {k}"
assert r["rejection_reason"] == REASON_TEXT
print(f"[1b] rejection_reason returned: {r['rejection_reason']!r}")

# ── Test 2: HTML — /parent page contains the renderer + CSS class ──
rv = c.get("/parent")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert 'pp-rejected-card' in html, "rejected-card CSS class missing from HTML"
assert 'recent_rejected' in html or '_ppStoreState.rejected' in html, \
    "JS state field for rejected missing"
assert 'سبب الرفض' in html, "Arabic label missing"
print("[2] /parent page contains the rejection-display renderer + CSS")

# Verify the (لم يُذكر سبب) fallback string is present in the JS
assert '(لم يُذكر سبب)' in html, "fallback Arabic text missing"
print("[2a] '(لم يُذكر سبب)' fallback wired ✓")

# ── Test 3: same row, NULL rejection_reason → fallback should kick in ──
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO redemptions(student_id, student_name, reward_id, "
        "reward_name, points_spent, status, request_source, "
        "rejection_reason) "
        "VALUES(?,?,?,?,?,'rejected','parent_pid',NULL)",
        (SID, "C8 smoke null-reason", 1, "C8 smoke reward 2", 5))
    db.commit()
    r = db.execute(
        "SELECT id FROM redemptions ORDER BY id DESC LIMIT 1").fetchone()
    RID_RIDS.append(int(dict(r)["id"]))
rv = c.get(f"/api/parent/store/menu?pid={PID}")
j = rv.get_json()
null_row = [x for x in j["recent_rejected"]
            if x["redemption_id"] == RID_RIDS[1]][0]
print(f"[3] NULL-reason row returns rejection_reason='{null_row['rejection_reason']}'")
assert null_row["rejection_reason"] == ""
# Frontend handles the fallback via the (r.rejection_reason || '').trim()
# || '(لم يُذكر سبب)' pattern.

# ── Test 4: 8-route admin regression ──
c.post('/login', data={'username':'admin','password':'admin123'},
       follow_redirects=False)
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[4] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    for rid in RID_RIDS:
        db.execute("DELETE FROM redemptions WHERE id=?", (rid,))
    # Restore original PID
    if original_pid is not None:
        db.execute("UPDATE students SET personal_id=? WHERE id=?",
                   (original_pid, SID))
    else:
        db.execute("UPDATE students SET personal_id=NULL WHERE id=?", (SID,))
    db.commit()

print("\nC8 parent-rejection-display smoke passed.")
