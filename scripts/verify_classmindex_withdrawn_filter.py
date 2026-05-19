"""Regression suite for classmindex-withdrawn-filter.

Two layers:

  A) Unit tests on _pts_active_filter_sql(db) — covering the 9
     scenarios the operator requested (settings unset / cleared /
     unsafe column / missing column / NULL / empty / whitespace /
     matching / non-matching).

  B) Integration check on /api/points/group with synthetic seed data:
     create a temp group with one "تم التسجيل" student, one NULL,
     one empty string, one whitespace-only, one "انسحاب". Hit the
     endpoint and assert only the first appears. Confirm
     point_events for ALL 5 stays in the DB (no deletion).

Run: python scripts/verify_classmindex_withdrawn_filter.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_results = []


def _check(label, ok, detail=""):
    _results.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


# ── Layer A: helper unit tests ────────────────────────────────────


def _run_helper_with(active_col_setting, active_val_setting,
                    column_exists=True, ensure_setting=None):
    """Drive _pts_active_filter_sql() under different settings
    states. Mutates the local settings table temporarily then
    restores. ensure_setting overrides via direct SQL because
    the regular set_setting helper isn't exported here."""
    saved_col = saved_val = None
    with appmod.app.app_context():
        db = appmod.get_db()
        # Snapshot current settings.
        for k in ("active_column", "active_value"):
            try:
                row = db.execute(
                    "SELECT value FROM settings "
                    "WHERE page='students' AND component=?", (k,)
                ).fetchone()
                if k == "active_column":
                    saved_col = (dict(row).get("value") if row else None)
                else:
                    saved_val = (dict(row).get("value") if row else None)
            except Exception:
                pass
        # Apply test overrides.
        def _set(k, v):
            try:
                db.execute(
                    "INSERT OR REPLACE INTO settings(page, component, "
                    "  label, value) "
                    "VALUES('students', ?, "
                    "  (SELECT label FROM settings WHERE page='students' "
                    "   AND component=?), ?)",
                    (k, k, v))
                db.commit()
            except Exception:
                try:
                    db.execute(
                        "UPDATE settings SET value=? "
                        "WHERE page='students' AND component=?",
                        (v, k))
                    db.commit()
                except Exception: pass
        _set("active_column", active_col_setting)
        _set("active_value",  active_val_setting)
        try:
            frag, val = appmod._pts_active_filter_sql(db)
        finally:
            # Restore
            _set("active_column", saved_col if saved_col is not None
                                  else "registration_term2_2026")
            _set("active_value",  saved_val if saved_val is not None
                                  else "تم التسجيل")
    return frag, val


def layer_a_helper_tests():
    print("\n=== Layer A — _pts_active_filter_sql helper ===")
    # 1. Defaults — settings have the seed values
    frag, val = _run_helper_with("registration_term2_2026", "تم التسجيل")
    _check("settings unset/defaults: fragment built",
           frag is not None,
           f"frag={frag!r} val={val!r}")
    _check("default fragment shape",
           frag == 'TRIM(COALESCE("registration_term2_2026", \'\')) = ?',
           f"got {frag!r}")
    _check("default value = 'تم التسجيل'",
           val == "تم التسجيل",
           f"got {val!r}")

    # 2. Cleared (empty string) → defaults still applied via the
    # "or hardcoded" defensive path.
    frag, val = _run_helper_with("", "")
    _check("settings cleared: still falls back to defaults",
           frag is not None and val == "تم التسجيل",
           f"frag={frag!r} val={val!r}")

    # 3. Custom column unsafe → falls back to registration_term2_2026
    frag, val = _run_helper_with("foo; DROP TABLE x", "تم التسجيل")
    _check("unsafe ident falls back to default column",
           frag == 'TRIM(COALESCE("registration_term2_2026", \'\')) = ?',
           f"got {frag!r}")

    # 4. Column doesn't exist on live table → (None, None)
    # Use a name that definitely isn't a real column. The helper
    # still needs to PASS _is_safe_ident, so use a valid ident that
    # just isn't a real students column.
    frag, val = _run_helper_with("noexist_col_xx", "تم التسجيل")
    _check("missing column → (None, None) — caller skips filter",
           frag is None and val is None,
           f"frag={frag!r} val={val!r}")


# ── Layer B: integration check with synthetic students ────────────


_TEST_GROUP = "_pts_filter_test_group"
_synth_ids = []


def _seed_synthetic_group(db):
    """Insert 5 synthetic students all in _TEST_GROUP with
    different registration values. Returns the inserted ids."""
    rows = [
        ("Synth Active 1", "تم التسجيل"),
        ("Synth Withdrawn (NULL)", None),
        ("Synth Withdrawn (empty)", ""),
        ("Synth Withdrawn (whitespace)", "   "),
        ("Synth Withdrawn (انسحاب)", "انسحاب"),
    ]
    ids = []
    for nm, reg in rows:
        try:
            cur = db.execute(
                "INSERT INTO students(student_name, group_name_student, "
                "registration_term2_2026) VALUES(?, ?, ?)",
                (nm, _TEST_GROUP, reg))
            db.commit()
            sid = cur.lastrowid
            if not sid:
                row = db.execute(
                    "SELECT id FROM students WHERE student_name=? "
                    "AND group_name_student=?", (nm, _TEST_GROUP)
                ).fetchone()
                sid = int(dict(row).get("id") or 0) if row else 0
            ids.append(int(sid))
        except Exception as ex:
            print(f"  insert failed for {nm}: {ex}")
            ids.append(0)
    # Add a synthetic point_event for every student so we can later
    # confirm event rows are preserved (data not deleted).
    for sid in ids:
        if not sid: continue
        try:
            db.execute(
                "INSERT INTO point_events(student_id, student_name, "
                "behavior_id, behavior_name, points_value, group_name, "
                "awarded_by, awarded_by_name, session_date) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, "Synth", 1, "test", 5, _TEST_GROUP,
                 0, "verify_script", "2026-05-19"))
            db.commit()
        except Exception:
            pass
    return ids


def _cleanup_synthetic(db, ids):
    """Hard-delete synthetic rows since they were created ONLY for
    the test (not real user data). Keeps the local DB clean."""
    for sid in ids:
        if not sid: continue
        try:
            db.execute("DELETE FROM point_events WHERE student_id=?",
                       (sid,))
            db.execute("DELETE FROM students WHERE id=?", (sid,))
        except Exception: pass
    try: db.commit()
    except Exception: pass


def layer_b_integration_test():
    print("\n=== Layer B — /api/points/group integration ===")
    with appmod.app.app_context():
        db = appmod.get_db()
        ids = _seed_synthetic_group(db)
    global _synth_ids
    _synth_ids = ids
    _check("5 synthetic students inserted",
           all(i > 0 for i in ids),
           f"ids={ids}")

    # Drive /api/points/group as admin.
    client = appmod.app.test_client()
    with appmod.app.app_context():
        db = appmod.get_db()
        admin = db.execute(
            "SELECT * FROM users WHERE role='admin' "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if not admin:
            _check("admin user available", False)
            return
        u = dict(admin)
    with client.session_transaction() as s:
        s["user"] = u
    r = client.get(f"/api/points/group?group={_TEST_GROUP}")
    j = r.get_json() or {}
    _check("endpoint HTTP 200", r.status_code == 200, f"got {r.status_code}")
    returned_names = [s.get("student_name") for s in (j.get("students") or [])]
    _check("only the 'تم التسجيل' student returned",
           returned_names == ["Synth Active 1"],
           f"got {returned_names}")

    # Verify point_events for ALL synthetic students still exist
    # (data is preserved; only the SELECT visibility changed).
    with appmod.app.app_context():
        db = appmod.get_db()
        rows = db.execute(
            "SELECT student_id, COUNT(*) AS n FROM point_events "
            "WHERE student_id IN (" +
            ",".join("?" for _ in ids) + ") GROUP BY student_id",
            tuple(ids)).fetchall()
        kept = {int(dict(r).get("student_id") or 0): int(dict(r).get("n") or 0)
                for r in rows}
    _check("point_events preserved for ALL 5 students",
           all(kept.get(i, 0) >= 1 for i in ids),
           f"per-student counts: {kept}")

    # Cleanup.
    with appmod.app.app_context():
        db = appmod.get_db()
        _cleanup_synthetic(db, ids)


def main():
    layer_a_helper_tests()
    layer_b_integration_test()
    print()
    fails = [r for r in _results if not r[1]]
    print(f"{len(_results) - len(fails)}/{len(_results)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — classmindex-withdrawn-filter wired correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
