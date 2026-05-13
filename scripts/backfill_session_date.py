"""Backfill point_events.session_date for legacy rows.

Phase 1 introduced a session_date column on point_events but
existing rows have it NULL. The Phase 1 budget endpoint and the
upcoming end-of-session statistics (Phase 3) both filter by
session_date, so any legacy row needs a sensible value.

Resolution strategy per row (in order):
  1. Find the closest attendance row for the same (group_name,
     attendance_date within ±1 day of awarded_at) where this
     student appears with a present-equivalent status (حاضر،
     متأخر). Use that attendance_date.
  2. Otherwise: fall back to the local-date portion of
     awarded_at in Bahrain TZ (UTC+3). This is what
     _pts_bahrain_today() returns for new rows, so the bucket
     boundary is consistent for any future grants on the same
     day.

The script is **idempotent** — it only touches rows where
session_date IS NULL. Running it twice is a no-op.

Usage (local):
    DB_PATH=mindx.db python scripts/backfill_session_date.py
Usage (prod, on Render shell):
    python scripts/backfill_session_date.py

Exit codes:
    0 — finished successfully (always; failures per-row are
        counted but never abort)
    1 — fatal setup error (cannot open DB)
"""
import os
import sys
import io
import sqlite3
import datetime as dt

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")

DB_PATH = os.environ.get("DB_PATH", "mindx.db")


def _bahrain_date_from_awarded_at(awarded_at):
    """Parse an awarded_at value (SQLite stores it as
    'YYYY-MM-DD HH:MM:SS' UTC, or already as ISO with TZ) and
    return the Bahrain-TZ date string. Returns '' when the
    input is unparseable."""
    if not awarded_at:
        return ""
    s = str(awarded_at).strip()
    # Try common SQLite default first.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            t = dt.datetime.strptime(s[:19] if "." not in fmt else s,
                                     fmt)
            return (t + dt.timedelta(hours=3)).date().isoformat()
        except ValueError:
            continue
    # Last resort — first 10 chars look like YYYY-MM-DD?
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return ""


def _find_attendance_date(db, group_name, student_name, awarded_at):
    """Return an attendance_date for this student in this group
    within ±1 day of awarded_at, where the status is present-
    equivalent. NULL when no match."""
    if not group_name or not student_name:
        return None
    base = _bahrain_date_from_awarded_at(awarded_at)
    if not base:
        return None
    try:
        anchor = dt.date.fromisoformat(base)
    except ValueError:
        return None
    candidates = [
        (anchor - dt.timedelta(days=1)).isoformat(),
        anchor.isoformat(),
        (anchor + dt.timedelta(days=1)).isoformat(),
    ]
    row = db.execute(
        "SELECT attendance_date FROM attendance "
        "WHERE TRIM(group_name)=? "
        "  AND TRIM(student_name)=? "
        "  AND status IN ('حاضر','متأخر') "
        "  AND attendance_date IN (?,?,?) "
        "ORDER BY attendance_date "
        "LIMIT 1",
        (group_name.strip(), student_name.strip(),
         candidates[0], candidates[1], candidates[2]),
    ).fetchone()
    return row[0] if row else None


def main():
    if not os.path.exists(DB_PATH):
        print(f"[backfill] DB not found at {DB_PATH}", file=sys.stderr)
        return 1
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    cols = {r[1] for r in db.execute(
        "PRAGMA table_info(point_events)").fetchall()}
    if "session_date" not in cols:
        print("[backfill] session_date column missing — run the app once "
              "to apply the points_session_date_v1 migration first.")
        return 1

    rows = db.execute(
        "SELECT id, group_name, student_name, awarded_at "
        "FROM point_events "
        "WHERE session_date IS NULL OR session_date='' "
        "ORDER BY id").fetchall()
    total = len(rows)
    if not total:
        print("[backfill] nothing to do — no NULL session_date rows.")
        return 0

    print(f"[backfill] {total} legacy row(s) need session_date.")

    via_att = via_local = errors = 0
    for r in rows:
        rd = dict(r)
        sd = _find_attendance_date(
            db,
            rd.get("group_name") or "",
            rd.get("student_name") or "",
            rd.get("awarded_at"))
        if sd:
            source = "att"
        else:
            sd = _bahrain_date_from_awarded_at(rd.get("awarded_at"))
            source = "local"
        if not sd:
            errors += 1
            continue
        try:
            db.execute(
                "UPDATE point_events SET session_date=? WHERE id=?",
                (sd, rd["id"]))
            if source == "att":
                via_att += 1
            else:
                via_local += 1
        except Exception as ex:
            errors += 1
            print(f"[backfill]  row id={rd['id']} update failed: {ex}",
                  file=sys.stderr)

    db.commit()
    print(f"[backfill] done — via_attendance={via_att} "
          f"via_local_date={via_local} errors={errors}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
