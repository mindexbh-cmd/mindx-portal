"""C2 smoke - parent duplicate requests now allowed.

After the v2.6 fix, /api/parent/store/request no longer rejects
a second 'requested' row for the same (student, reward). This
smoke proves the gate is gone AND confirms the other validations
still hold.
"""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# ── Setup: fix a student with a known PID, seed balance,
# ensure reward id=1 is a menu-item ──
SID = 196
PID = "DUPSMOKE_PID"
RID_ACTIVE = 1  # ملصق نجمة, 10 pts, stock=-1, is_active=1
orig_pid = None
orig_menu_flag = None
created_rids = []
extra_rids = []  # cleanup helpers

with A.app.app_context():
    db = A.get_db()
    row = db.execute("SELECT personal_id FROM students WHERE id=?",
                     (SID,)).fetchone()
    orig_pid = dict(row).get("personal_id") if row else None
    db.execute("UPDATE students SET personal_id=? WHERE id=?",
               (PID, SID))
    rr = db.execute("SELECT is_menu_item FROM rewards WHERE id=?",
                    (RID_ACTIVE,)).fetchone()
    orig_menu_flag = int(dict(rr).get("is_menu_item") or 0) if rr else 0
    db.execute("UPDATE rewards SET is_menu_item=1 WHERE id=?",
               (RID_ACTIVE,))
    # Seed 500 points
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, "
        "points_value, awarded_by_name) "
        "VALUES(?, 'dup-removed smoke seed', 500, 'smoke')", (SID,))
    db.commit()

c = A.app.test_client()

def parent_request(pid, reward_id):
    return c.post('/api/parent/store/request',
                  headers={'Content-Type': 'application/json'},
                  data=json.dumps({"pid": pid, "reward_id": reward_id}))

# ── Test 1: first request → 200 ──
r1 = parent_request(PID, RID_ACTIVE)
j1 = r1.get_json()
print(f"[1] attempt 1 -> {r1.status_code} req_id={j1.get('request_id')}")
assert r1.status_code == 200 and j1["ok"] is True

# ── Test 2: SECOND IDENTICAL request → should also 200 now ──
r2 = parent_request(PID, RID_ACTIVE)
j2 = r2.get_json()
print(f"[2] attempt 2 (identical) -> {r2.status_code} req_id={j2.get('request_id')}")
assert r2.status_code == 200, (
    "duplicate-block regressed — got " + str(r2.status_code) + " " + str(j2))
assert j2["request_id"] != j1["request_id"], "should be a NEW row"

# ── Test 3: THIRD identical request → also 200 ──
r3 = parent_request(PID, RID_ACTIVE)
j3 = r3.get_json()
print(f"[3] attempt 3 (identical) -> {r3.status_code} req_id={j3.get('request_id')}")
assert r3.status_code == 200

# ── Test 4 + 5: verify 3 distinct rows + all are 'requested' ──
with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT id, status FROM redemptions "
        "WHERE student_id=? AND reward_id=? "
        "AND status='requested' "
        "AND id IN (?,?,?)",
        (SID, RID_ACTIVE,
         j1["request_id"], j2["request_id"], j3["request_id"])).fetchall()
    rows = [dict(r) for r in rows]
created_rids = [r["id"] for r in rows]
print(f"[4] DB rows: {len(rows)} (expected 3)")
assert len(rows) == 3
print(f"[5] all status='requested'? "
      f"{all(r['status']=='requested' for r in rows)}")
assert all(r["status"] == "requested" for r in rows)

# ── Test 6: clean up these 3 rows so later balance/stock tests work
# from a clean slate ──
with A.app.app_context():
    db = A.get_db()
    for rid in created_rids:
        db.execute("DELETE FROM redemptions WHERE id=?", (rid,))
    db.commit()

# ── Test 7: balance gate still works ── Send 60 more identical
# requests; cost=10 each, balance=500, so after 50 the next must
# fail with 400 "نقاطك غير كافية".
# Note: 'requested' rows DON'T debit (per _pts_balance), so the
# balance preview is constant. The check is "balance >= cost",
# i.e. balance=500 vs cost=10 always passes here. So the balance
# gate only fires if we set up a low-balance student.
# Quick check with a student who has 5 points and tries a 10-pt
# reward → 400.
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, "
        "points_value, awarded_by_name) "
        "VALUES(?, 'dup-removed broke balance', -495, 'smoke')",
        (SID,))   # bring balance down to 5
    db.commit()
r = parent_request(PID, RID_ACTIVE)
j = r.get_json()
print(f"[7] insufficient balance -> {r.status_code} err={j.get('error')!r}")
assert r.status_code == 400
assert "نقاطك غير كافية" in j["error"]

# Restore balance
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO point_events(student_id, behavior_name, "
        "points_value, awarded_by_name) "
        "VALUES(?, 'dup-removed balance restore', 495, 'smoke')",
        (SID,))
    db.commit()

# ── Test 8: stock gate still works ── Create an out-of-stock reward
# and try to redeem it.
with A.app.app_context():
    db = A.get_db()
    db.execute(
        "INSERT INTO rewards(name_ar, point_cost, stock, is_active, "
        "is_menu_item, category_type) "
        "VALUES('smoke nostock', 5, 0, 1, 1, 'toy')")
    db.commit()
    rr = db.execute(
        "SELECT id FROM rewards WHERE name_ar='smoke nostock' "
        "ORDER BY id DESC LIMIT 1").fetchone()
    nostock_rid = int(dict(rr)["id"])
r = parent_request(PID, nostock_rid)
j = r.get_json()
print(f"[8] out-of-stock -> {r.status_code} err={j.get('error')!r}")
assert r.status_code == 400
assert "نفد المخزون" in j["error"]

# ── Test 9: invalid reward_id → 404 ──
r = parent_request(PID, 99999999)
j = r.get_json()
print(f"[9] invalid reward_id -> {r.status_code} err={j.get('error')!r}")
assert r.status_code == 404

# ── Test 10: non-existent PID → 400 ──
r = parent_request("NOSUCHPID_X9X9", RID_ACTIVE)
j = r.get_json()
print(f"[10] non-existent PID -> {r.status_code} err={j.get('error')!r}")
assert r.status_code == 400

# ── Test 11: 8-route admin regression ──
c.post('/login', data={'username': 'admin', 'password': 'admin123'},
       follow_redirects=False)
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[11] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM rewards WHERE name_ar='smoke nostock'")
    db.execute("DELETE FROM point_events "
               "WHERE behavior_name LIKE 'dup-removed%'")
    # Any extra redemption rows created during balance/stock tests
    db.execute(
        "DELETE FROM redemptions "
        "WHERE student_id=? AND reward_id=? "
        "AND id NOT IN ("
        "  SELECT id FROM redemptions WHERE student_id=? AND reward_id=? "
        "  AND id NOT IN (?,?,?))",
        (SID, RID_ACTIVE, SID, RID_ACTIVE,
         j1["request_id"], j2["request_id"], j3["request_id"]))
    # Restore reward + student state
    if orig_pid is not None:
        db.execute("UPDATE students SET personal_id=? WHERE id=?",
                   (orig_pid, SID))
    else:
        db.execute("UPDATE students SET personal_id=NULL WHERE id=?",
                   (SID,))
    db.execute("UPDATE rewards SET is_menu_item=? WHERE id=?",
               (orig_menu_flag, RID_ACTIVE))
    db.commit()

print("\nParent-duplicate-removal smoke passed.")
