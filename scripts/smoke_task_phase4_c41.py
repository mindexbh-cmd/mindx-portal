"""C41 smoke - scheduler core function."""
import os, sys, io, datetime as dt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

cleanup_template_ids = []
cleanup_task_ids = []

with A.app.app_context():
    db = A.get_db()
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    five_days_ago = today - dt.timedelta(days=5)

    # Resolve a dept id
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

    # ── Create test templates ──
    # 1. DAILY template, last_gen 5 days ago
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, template_description, department_id, "
        "priority, assigned_to_username, estimated_hours, "
        "frequency, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,1)",
        ("C41 daily test", "Daily template smoke",
         events_dept, "normal", "admin", 1.0,
         "daily", five_days_ago.isoformat(), "admin"))
    daily_id = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C41 daily test",)).fetchone())["id"]
    cleanup_template_ids.append(daily_id)
    db.commit()

    # 2. WEEKLY template, day_of_week = today's mindex weekday,
    #    last_gen 5 days ago
    today_mindex_dow = (today.weekday() + 1) % 7
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, "
        "assigned_to_username, estimated_hours, frequency, "
        "day_of_week, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,1)",
        ("C41 weekly today", events_dept, "normal", "admin",
         1.0, "weekly", today_mindex_dow,
         five_days_ago.isoformat(), "admin"))
    weekly_today_id = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C41 weekly today",)).fetchone())["id"]
    cleanup_template_ids.append(weekly_today_id)

    # 3. WEEKLY template, day_of_week NOT today, last_gen 5 days ago
    other_dow = (today_mindex_dow + 3) % 7  # 3 days off
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, "
        "assigned_to_username, estimated_hours, frequency, "
        "day_of_week, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,1)",
        ("C41 weekly off-day", events_dept, "normal", "admin",
         1.0, "weekly", other_dow,
         five_days_ago.isoformat(), "admin"))
    weekly_off_id = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C41 weekly off-day",)).fetchone())["id"]
    cleanup_template_ids.append(weekly_off_id)

    # 4. MONTHLY template, day_of_month = today.day, last_gen 5 days ago
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, "
        "assigned_to_username, estimated_hours, frequency, "
        "day_of_month, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,?,1)",
        ("C41 monthly today", events_dept, "normal", "admin",
         1.0, "monthly", min(today.day, 28),
         five_days_ago.isoformat(), "admin"))
    monthly_id = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C41 monthly today",)).fetchone())["id"]
    cleanup_template_ids.append(monthly_id)

    # 5. INACTIVE template — should be SKIPPED
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, "
        "assigned_to_username, estimated_hours, frequency, "
        "last_generated_date, created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,0)",
        ("C41 inactive", events_dept, "normal", "admin",
         1.0, "daily", five_days_ago.isoformat(), "admin"))
    inactive_id = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C41 inactive",)).fetchone())["id"]
    cleanup_template_ids.append(inactive_id)
    db.commit()

    print("[setup] daily=", daily_id, "weekly_today=", weekly_today_id,
          "weekly_off=", weekly_off_id, "monthly=", monthly_id,
          "inactive=", inactive_id)
    print("[setup] today=", today, "mindex_dow=", today_mindex_dow)

    # ── Test 1: first scheduler run ──
    count, details = A._generate_due_recurring_tasks(db)
    print("[1] first run -> count=", count)
    for d in details: print("    -", d)
    # daily should generate 2 (yesterday + today, capped at 2)
    # weekly_today: 1 if today matches; the day_of_week == today's so 1 task today
    # weekly_off: 0 (doesn't match either yesterday or today)
    # monthly: 1 (today is the matching day_of_month)
    # inactive: 0
    daily_gen = [d for d in details if d["template_id"] == daily_id]
    weekly_today_gen = [d for d in details if d["template_id"] == weekly_today_id]
    weekly_off_gen = [d for d in details if d["template_id"] == weekly_off_id]
    monthly_gen = [d for d in details if d["template_id"] == monthly_id]
    inactive_gen = [d for d in details if d["template_id"] == inactive_id]

    assert len(daily_gen) == 2, f"daily should generate 2, got {len(daily_gen)}"
    assert len(weekly_today_gen) == 1, f"weekly_today should generate 1, got {len(weekly_today_gen)}"
    assert len(weekly_off_gen) == 0, f"weekly_off should generate 0, got {len(weekly_off_gen)}"
    assert len(monthly_gen) == 1, f"monthly should generate 1, got {len(monthly_gen)}"
    assert len(inactive_gen) == 0, f"inactive should be skipped, got {len(inactive_gen)}"
    print("[1] daily=2, weekly-match=1, weekly-off=0, monthly=1, inactive=0 ✓")

    # Track for cleanup
    for d in details:
        cleanup_task_ids.append(d["new_task_id"])

    # ── Test 2: idempotency (call again immediately) ──
    count2, details2 = A._generate_due_recurring_tasks(db)
    print("[2] second run -> count=", count2, "(expected 0)")
    assert count2 == 0, "second run should generate 0 (idempotent)"

    # ── Test 3: verify last_generated_date stamped on all active ──
    for tid, label, should_have_run in [
        (daily_id,        "daily",        True),
        (weekly_today_id, "weekly_today", True),
        (weekly_off_id,   "weekly_off",   False),  # untouched
        (monthly_id,      "monthly",      True),
        (inactive_id,     "inactive",     False),
    ]:
        row = dict(db.execute(
            "SELECT last_generated_date FROM recurring_tasks WHERE id=?",
            (tid,)).fetchone())
        lgd = row["last_generated_date"]
        if should_have_run:
            assert lgd == today.isoformat(), \
                f"{label} last_gen={lgd} expected={today.isoformat()}"
            print(f"    {label} last_gen = {lgd} (today) ✓")
        else:
            assert lgd == five_days_ago.isoformat(), \
                f"{label} last_gen should be untouched ({five_days_ago}), got {lgd}"
            print(f"    {label} last_gen = {lgd} (untouched) ✓")

    # ── Test 4: tasks have recurring_id back-link ──
    rows = db.execute(
        "SELECT recurring_id, due_date, title FROM tasks "
        "WHERE recurring_id IS NOT NULL AND title LIKE 'C41%'"
        " ORDER BY id").fetchall()
    print(f"[4] generated tasks with back-link ({len(rows)} rows):")
    for r in rows:
        d = dict(r); print(f"    rid={d['recurring_id']} due={d['due_date']} title={d['title']}")
    assert all(dict(r)["recurring_id"] is not None for r in rows)

    # ── Test 5: a template with last_gen = yesterday → only today ──
    db.execute(
        "UPDATE recurring_tasks SET last_generated_date=? WHERE id=?",
        (yesterday.isoformat(), daily_id))
    # remove the existing generated tasks first so the scheduler can re-fire
    db.execute("DELETE FROM tasks WHERE recurring_id=?", (daily_id,))
    db.commit()
    count3, details3 = A._generate_due_recurring_tasks(db)
    daily_gen3 = [d for d in details3 if d["template_id"] == daily_id]
    print(f"[5] daily last_gen=yesterday -> gen={len(daily_gen3)} (expected 1)")
    assert len(daily_gen3) == 1
    for d in details3:
        cleanup_task_ids.append(d["new_task_id"])

    # Cleanup
    for tid in cleanup_task_ids:
        if tid:
            db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    # Also clean tasks that may have been generated for templates
    for rid in cleanup_template_ids:
        db.execute("DELETE FROM tasks WHERE recurring_id=?", (rid,))
        db.execute("DELETE FROM recurring_tasks WHERE id=?", (rid,))
    db.commit()

print("\nC41 smoke passed.")
