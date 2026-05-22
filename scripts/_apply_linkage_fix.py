"""Apply the parent-portal linkage repair — Path 2 (operator-approved
after the twin discovery).

  Phase A (Step 2):  bulk UPDATE 139 silently-rescued accounts —
                     move them from the username-fallback path to the
                     canonical linked_student_id path.

  Phase B (Step 3, revised):
    - DEACTIVATE 3 zombie accounts (uid 846, 795, 748) — never used
      (0 point_events, must_change_pw=1, untypeable usernames). The
      parents are already using the working twin accounts
      (uid 3181, 3180, 3188). Reversible (is_active flip).
    - REPAIR uid=714 (زينب فاضل المكحل — no twin exists):
        · strip bidi marks from students.id=5044 personal_id
        · users.id=714: username='170206963', linked_student_id=5044,
          password=hp('170206963'), must_change_pw=1

All writes inside a single Postgres transaction. COMMIT only when
every post-write assertion passes; ROLLBACK on any anomaly.
"""
import os
import sys
import time
import json
import hashlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_URL = os.environ.get("DATABASE_URL", "").strip()
if not DB_URL:
    print("DATABASE_URL not set — aborting")
    raise SystemExit(2)

import psycopg2
import psycopg2.extras


def hp(p):
    """Mirror of app.py:261 — sha256 of UTF-8-encoded plaintext."""
    return hashlib.sha256(p.encode()).hexdigest()


# Phase B revised
ZOMBIE_UIDS_TO_DEACTIVATE = (846, 795, 748)
TWIN_UIDS_MUST_BE_UNCHANGED = (3181, 3180, 3188)  # the correctly-set-up twins
REPAIR_UID            = 714
REPAIR_STUDENT_ID     = 5044
REPAIR_NEW_PID        = "170206963"

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def fail(msg):
    print(f"\n✗ ABORT: {msg}")
    conn.rollback()
    print("  ROLLED BACK — no writes committed.")
    cur.close(); conn.close()
    raise SystemExit(1)


def assert_eq(label, got, want):
    if got == want:
        print(f"  ✓ {label}: {got}")
        return
    fail(f"{label}: got {got!r}, expected {want!r}")


# ── Pre-flight ────────────────────────────────────────────────
print("=" * 72)
print("PRE-FLIGHT (read-only re-checks before opening writes)")
print("=" * 72)

# (1) Ambiguity gate (same as before)
cur.execute("""
    SELECT TRIM(u.username) AS un, COUNT(DISTINCT s.id) AS c
    FROM users u
    JOIN students s ON TRIM(s.personal_id) = TRIM(u.username)
    WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
    GROUP BY TRIM(u.username)
    HAVING COUNT(DISTINCT s.id) > 1
""")
assert_eq("ambiguous username→student matches (must be 0)",
          len(cur.fetchall()), 0)

# (2) Phase A preview count
cur.execute("""
    SELECT COUNT(*) AS n
    FROM users u
    LEFT JOIN students s_linked ON s_linked.id = u.linked_student_id
    JOIN students s ON TRIM(s.personal_id) = TRIM(u.username)
    WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
      AND u.linked_student_id IS NOT NULL AND u.linked_student_id <> 0
      AND s_linked.id IS NULL
""")
preview_n = cur.fetchone()["n"]
assert_eq("Phase A preview count (must be 139)", preview_n, 139)

# (3) Zombies still in their broken state (is_active=1 currently)
cur.execute(
    "SELECT id, is_active, must_change_pw FROM users WHERE id = ANY(%s) ORDER BY id",
    (list(ZOMBIE_UIDS_TO_DEACTIVATE),))
zombies_pre = cur.fetchall()
if len(zombies_pre) != 3:
    fail(f"zombie precheck: expected 3 rows, got {len(zombies_pre)}")
for z in zombies_pre:
    if z["is_active"] != 1:
        fail(f"zombie uid={z['id']} is_active={z['is_active']} (expected 1 — already deactivated?)")
print(f"  ✓ 3 zombies confirmed is_active=1, must_change_pw=1, ready to deactivate")

# (4) Twins MUST be untouched at the end — capture their state now
cur.execute(
    "SELECT id, username, linked_student_id, is_active, must_change_pw, password "
    "FROM users WHERE id = ANY(%s) ORDER BY id",
    (list(TWIN_UIDS_MUST_BE_UNCHANGED),))
twins_pre = {r["id"]: dict(r) for r in cur.fetchall()}
if len(twins_pre) != 3:
    fail(f"twin precheck: expected 3 rows, got {len(twins_pre)}")
for tuid, tr in twins_pre.items():
    print(f"  ✓ twin uid={tuid}: username={tr['username']!r} "
          f"linked={tr['linked_student_id']} active={tr['is_active']}")

# (5) NO other user account holds '170206963' (UNIQUE-collision check for the repair)
cur.execute(
    "SELECT id, username FROM users WHERE TRIM(username) = %s AND id <> %s",
    (REPAIR_NEW_PID, REPAIR_UID))
collision = cur.fetchall()
if collision:
    fail(f"repair UNIQUE collision: username='{REPAIR_NEW_PID}' is held by "
         f"{collision} (expected none other than uid={REPAIR_UID})")
print(f"  ✓ no other account holds username='{REPAIR_NEW_PID}'")

# (6) Repair target student row exists
cur.execute("SELECT id, student_name, personal_id FROM students WHERE id = %s",
            (REPAIR_STUDENT_ID,))
target = cur.fetchone()
if not target:
    fail(f"repair target students.id={REPAIR_STUDENT_ID} not found")
print(f"  ✓ repair target student id={REPAIR_STUDENT_ID}: "
      f"name={target['student_name']!r} pid={target['personal_id']!r}")

# (7) uid=714 still present
cur.execute("SELECT id, username, linked_student_id FROM users WHERE id = %s",
            (REPAIR_UID,))
repair_pre = cur.fetchone()
if not repair_pre:
    fail(f"repair uid={REPAIR_UID} not found")
print(f"  ✓ repair uid={REPAIR_UID} present: username={repair_pre['username']!r} "
      f"linked={repair_pre['linked_student_id']}")


# ── Writes (single transaction) ───────────────────────────────
print("\n" + "=" * 72)
print("OPENING TRANSACTION — Phase A + Phase B (Path 2)")
print("=" * 72)

# Phase A: bulk repoint (139 silently-rescued)
print("\nPhase A: bulk UPDATE 139 silently-rescued accounts …")
cur.execute("""
    UPDATE users u
    SET linked_student_id = s.id
    FROM students s
    WHERE u.role = 'student'
      AND COALESCE(u.is_active, 1) = 1
      AND TRIM(s.personal_id) = TRIM(u.username)
      AND u.linked_student_id IS DISTINCT FROM s.id
""")
phase_a_n = cur.rowcount
print(f"  rows affected: {phase_a_n}")
if phase_a_n < 139:
    fail(f"Phase A: expected ≥139 rows affected, got {phase_a_n}")

# Phase B.1: deactivate the 3 zombies
print("\nPhase B.1: deactivate 3 zombie accounts …")
cur.execute(
    "UPDATE users SET is_active = 0 WHERE id = ANY(%s)",
    (list(ZOMBIE_UIDS_TO_DEACTIVATE),))
n = cur.rowcount
print(f"  rows affected: {n}")
if n != 3:
    fail(f"Phase B.1: expected 3 rows affected, got {n}")

# Phase B.2: repair uid=714 (strip bidi from student + rename user)
print("\nPhase B.2: repair uid=714 (زينب فاضل المكحل) …")

# (a) Strip bidi marks from the student's personal_id
cur.execute(
    "UPDATE students SET personal_id = %s WHERE id = %s",
    (REPAIR_NEW_PID, REPAIR_STUDENT_ID))
n = cur.rowcount
print(f"  students.personal_id strip on id={REPAIR_STUDENT_ID}: rows={n}")
if n != 1:
    fail(f"students strip: expected 1 row, got {n}")

# (b) Confirm the cleaned pid now uniquely resolves
cur.execute(
    "SELECT id FROM students WHERE TRIM(personal_id) = %s",
    (REPAIR_NEW_PID,))
hits = cur.fetchall()
if len(hits) != 1 or hits[0]["id"] != REPAIR_STUDENT_ID:
    fail(f"post-strip resolution: pid '{REPAIR_NEW_PID}' returns {hits}, "
         f"expected single id={REPAIR_STUDENT_ID}")
print(f"  ✓ pid '{REPAIR_NEW_PID}' uniquely resolves to students.id={REPAIR_STUDENT_ID}")

# (c) Update the user row
pw_hash = hp(REPAIR_NEW_PID)
cur.execute("""
    UPDATE users
    SET username = %s,
        password = %s,
        must_change_pw = 1,
        linked_student_id = %s
    WHERE id = %s
""", (REPAIR_NEW_PID, pw_hash, REPAIR_STUDENT_ID, REPAIR_UID))
n = cur.rowcount
print(f"  users UPDATE on uid={REPAIR_UID}: rows={n}")
if n != 1:
    fail(f"users update: expected 1 row, got {n}")


# ── Post-write assertions (still inside the transaction) ──────
print("\n" + "=" * 72)
print("POST-WRITE VERIFICATION (pre-COMMIT)")
print("=" * 72)

# (1) Audit: dead-linked-with-fallback must be 0
cur.execute("""
    SELECT COUNT(*) AS n
    FROM users u
    LEFT JOIN students s_linked ON s_linked.id = u.linked_student_id
    JOIN students s ON TRIM(s.personal_id) = TRIM(u.username)
    WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
      AND u.linked_student_id IS NOT NULL AND u.linked_student_id <> 0
      AND s_linked.id IS NULL
""")
assert_eq("dead-linked-with-fallback (post-fix, must be 0)",
          cur.fetchone()["n"], 0)

# (2) Audit: broken-with-no-fallback must be 0 among ACTIVE accounts
#     (the 3 deactivated zombies are now is_active=0, so they fall
#     OUT of the audit's WHERE clause)
cur.execute("""
    SELECT COUNT(*) AS n
    FROM users u
    LEFT JOIN students s_linked ON s_linked.id = u.linked_student_id
    LEFT JOIN students s_uname  ON TRIM(s_uname.personal_id) = TRIM(u.username)
    WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
      AND u.linked_student_id IS NOT NULL AND u.linked_student_id <> 0
      AND s_linked.id IS NULL AND s_uname.id IS NULL
""")
assert_eq("broken-with-no-fallback among ACTIVE accounts (post-fix, must be 0)",
          cur.fetchone()["n"], 0)

# (3) Zombies are now is_active=0
cur.execute(
    "SELECT id, is_active FROM users WHERE id = ANY(%s) ORDER BY id",
    (list(ZOMBIE_UIDS_TO_DEACTIVATE),))
zombies_post = cur.fetchall()
for z in zombies_post:
    if z["is_active"] != 0:
        fail(f"zombie post-check uid={z['id']} is_active={z['is_active']} (expected 0)")
print(f"  ✓ all 3 zombies now is_active=0")

# (4) uid=714 fully repaired
cur.execute("""
    SELECT u.id, u.username, u.linked_student_id, u.must_change_pw, u.password,
           s.id AS sid, s.student_name, s.personal_id
    FROM users u
    LEFT JOIN students s ON s.id = u.linked_student_id
    WHERE u.id = %s
""", (REPAIR_UID,))
row = cur.fetchone()
if row["username"] != REPAIR_NEW_PID:
    fail(f"repair: username={row['username']!r}, expected {REPAIR_NEW_PID!r}")
if row["linked_student_id"] != REPAIR_STUDENT_ID:
    fail(f"repair: linked_student_id={row['linked_student_id']}, "
         f"expected {REPAIR_STUDENT_ID}")
if row["must_change_pw"] != 1:
    fail(f"repair: must_change_pw={row['must_change_pw']}, expected 1")
if row["password"] != hp(REPAIR_NEW_PID):
    fail(f"repair: password hash mismatch")
if row["personal_id"] != REPAIR_NEW_PID:
    fail(f"repair: students.personal_id={row['personal_id']!r}, "
         f"expected {REPAIR_NEW_PID!r}")
print(f"  ✓ uid={REPAIR_UID} repaired: username={row['username']!r} "
      f"linked={row['linked_student_id']} pid={row['personal_id']!r} "
      f"name={row['student_name']!r}")

# (5) Twins MUST be untouched (still is_active=1, same linked_student_id,
#     same username, same password hash, same must_change_pw)
cur.execute(
    "SELECT id, username, linked_student_id, is_active, must_change_pw, password "
    "FROM users WHERE id = ANY(%s) ORDER BY id",
    (list(TWIN_UIDS_MUST_BE_UNCHANGED),))
twins_post = {r["id"]: dict(r) for r in cur.fetchall()}
for tuid, tr_pre in twins_pre.items():
    tr_post = twins_post.get(tuid)
    if not tr_post:
        fail(f"twin uid={tuid} disappeared!")
    for col in ("username", "linked_student_id", "is_active", "must_change_pw", "password"):
        if tr_post.get(col) != tr_pre.get(col):
            fail(f"twin uid={tuid} mutation on column {col}: "
                 f"pre={tr_pre.get(col)!r} post={tr_post.get(col)!r}")
    print(f"  ✓ twin uid={tuid}: UNCHANGED")

# (6) students.id=5044 personal_id reads cleanly (no bidi)
cur.execute("SELECT personal_id FROM students WHERE id = %s", (REPAIR_STUDENT_ID,))
pid_now = cur.fetchone()["personal_id"]
if pid_now != REPAIR_NEW_PID:
    fail(f"students.id={REPAIR_STUDENT_ID} pid={pid_now!r} "
         f"(hex={pid_now.encode('utf-8').hex()}), expected '{REPAIR_NEW_PID}'")
print(f"  ✓ students.id={REPAIR_STUDENT_ID} pid={pid_now!r} (clean)")


# ── COMMIT ────────────────────────────────────────────────────
print("\n" + "=" * 72)
print("ALL POST-WRITE ASSERTIONS PASSED — COMMITTING …")
print("=" * 72)
conn.commit()
print("\n✓ COMMIT successful.")
print(f"  Phase A rows updated: {phase_a_n}")
print(f"  Phase B.1 zombies deactivated: {len(ZOMBIE_UIDS_TO_DEACTIVATE)}")
print(f"  Phase B.2 uid=714 repaired (username + password + linked_student_id "
      f"+ students.personal_id cleaned)")

# Summary
summary_path = os.path.join(
    ROOT, "backups",
    f"linkage-fix-path2-summary-{time.strftime('%Y%m%d-%H%M%S')}.json")
summary = {
    "committed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "path": "Path 2 (operator-approved after twin discovery)",
    "phase_a_rows_affected": phase_a_n,
    "phase_b_zombies_deactivated": list(ZOMBIE_UIDS_TO_DEACTIVATE),
    "phase_b_repaired_uid": REPAIR_UID,
    "phase_b_repaired_new_pid": REPAIR_NEW_PID,
    "phase_b_repaired_student_id": REPAIR_STUDENT_ID,
    "twins_left_untouched": list(TWIN_UIDS_MUST_BE_UNCHANGED),
    "pre_write_assertions": {
        "ambiguous_usernames": 0,
        "phase_a_preview_count": preview_n,
        "no_username_collision_for_repair": True,
    },
    "post_write_assertions": {
        "dead_linked_with_fallback": 0,
        "broken_no_fallback_among_active": 0,
        "zombies_deactivated": True,
        "uid_714_repaired": True,
        "twins_untouched": True,
        "students_id_5044_clean": True,
    },
}
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"  Summary: {summary_path}")

cur.close()
conn.close()
