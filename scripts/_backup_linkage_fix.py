"""Backup users (all role='student' rows) + the 4 affected students
rows to a timestamped JSON snapshot. Pure READ — no schema or data
mutations. Output: backups/users_students_pre-linkage-fix-<ts>.json
"""
import os
import sys
import json
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "backups")
os.makedirs(OUT_DIR, exist_ok=True)

DB_URL = os.environ.get("DATABASE_URL", "").strip()
if not DB_URL:
    print("DATABASE_URL not set — aborting (this backup is for prod only)")
    raise SystemExit(2)

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# --- users (every role='student' row, all columns) ---
cur.execute("SELECT * FROM users WHERE role = 'student' ORDER BY id")
users_rows = cur.fetchall()
users_count_active = sum(1 for r in users_rows
                         if (r.get("is_active") is None or r.get("is_active") == 1))
print(f"users role='student': {len(users_rows)} total ({users_count_active} active)")

# --- the 4 affected students rows (by id, since their personal_id may
# be polluted / off) ---
affected_sids = (4888, 4880, 5045, 5044)
cur.execute(
    "SELECT * FROM students WHERE id = ANY(%s) ORDER BY id",
    (list(affected_sids),))
students_rows = cur.fetchall()
print(f"affected students rows: {len(students_rows)} of {len(affected_sids)} expected")
for s in students_rows:
    print(f"  id={s['id']} name={s.get('student_name')!r} pid={s.get('personal_id')!r}")

# --- the 4 affected user accounts (by id, for cross-reference) ---
affected_uids = (846, 795, 748, 714)
cur.execute(
    "SELECT * FROM users WHERE id = ANY(%s) ORDER BY id",
    (list(affected_uids),))
affected_users = cur.fetchall()
print(f"affected user rows: {len(affected_users)} of {len(affected_uids)} expected")
for u in affected_users:
    print(f"  uid={u['id']} username={u.get('username')!r} name={u.get('name')!r}"
          f" linked_student_id={u.get('linked_student_id')}")


# Serialize — convert all values to JSON-safe (dates → isoformat, bytes → hex)
def json_safe(v):
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (bytes, bytearray, memoryview)):
        return {"__bytes_hex__": bytes(v).hex()}
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def clean(row):
    return {k: json_safe(v) for k, v in dict(row).items()}


ts = time.strftime("%Y%m%d-%H%M%S")
out_path = os.path.join(OUT_DIR, f"users_students_pre-linkage-fix-{ts}.json")
payload = {
    "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "source": "prod (DATABASE_URL)",
    "purpose": "pre-write backup for the parent-linkage repair (139 silently-rescued + 4 broken accounts)",
    "counts": {
        "users_role_student": len(users_rows),
        "users_role_student_active": users_count_active,
        "affected_students_expected": len(affected_sids),
        "affected_students_found": len(students_rows),
        "affected_users_expected": len(affected_uids),
        "affected_users_found": len(affected_users),
    },
    "users_role_student": [clean(r) for r in users_rows],
    "affected_students": [clean(r) for r in students_rows],
    "affected_users": [clean(r) for r in affected_users],
}
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

# Verify file
size = os.path.getsize(out_path)
print(f"\n✓ Backup written: {out_path}")
print(f"  size: {size:,} bytes")
print(f"  users dumped: {payload['counts']['users_role_student']}")
print(f"  affected students dumped: {payload['counts']['affected_students_found']}")
print(f"  affected users dumped: {payload['counts']['affected_users_found']}")

cur.close()
conn.close()
