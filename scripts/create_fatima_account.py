"""Create a limited-admin manager account for Fatima Ibrahim
(personal_id 930909151) and lock her dashboard surface down to
the three curriculum-staff features:

    1. /admin/teacher-deliveries  (متابعة تسليمات المعلمات)
    2. /admin/lessons             (متابعة التقدم في الدروس)
    3. /admin/parent-messages     (ماذا تريد أن يعرف ولي الأمر)

Evaluations (/admin/evaluations) was removed from the whitelist on
2026-05-16 — the route is now gated by user_can_see_button(user,
"evaluations.admin"), and Fatima carries an is_visible=0 override
for that button_key.

Mechanism: standard `role='manager'` + per-user button_registry
overrides via `user_permissions` rows that set is_visible=0 for
every manager-default button outside the three-feature whitelist.
The button_registry was extended (migration
`permissions_v2_fatima_lockdown` in app.py) with new keys to give
DOM hooks to sidebar/quick/action items that previously had no
data-button-key attribute.

Idempotent: re-running the script after success is a no-op
(detects existing user via username, skips INSERT, re-asserts the
permission overrides).

Targets local SQLite by default; set DATABASE_URL=postgres://...
to target prod (Render).
"""
from __future__ import annotations

import hashlib
import os
import sys


USERNAME = "930909151"
NAME = "فاطمة إبراهيم"
ROLE = "manager"
DEPARTMENT = "شؤون المناهج والامتحانات"
LANDING_PAGE = ""  # login() only honours specific keyword landings
                   # (dashboard/teacher_hub/parent_hub/…); free-form URLs
                   # are silently ignored, so leave blank → falls through
                   # to /dashboard, where the sidebar surfaces the four
                   # target features via mx-staff-only.
PASSWORD_PLAIN = "930909151"


HIDDEN_BUTTONS = [
    # ── Existing manager-default buttons (already-registered) ──
    "dashboard.payment_tracking",
    "dashboard.lessons_summary",
    "dashboard.lesson_durations",
    "dashboard.search_student",
    "dashboard.send_messages",
    "dashboard.points_board",
    "dashboard.parent_receipts",
    "attendance.take_attendance",
    "attendance.export_excel",
    "database.export",
    "groups.add_group",
    "sidebar.attendance",
    "sidebar.groups",
    "sidebar.parent_receipts",
    # ── New keys added by permissions_v2_fatima_lockdown ──
    # Gate the route helpers (_ev_can_admin / _events_can_admin) in
    # addition to hiding the sidebar links, so the overrides block the
    # pages themselves — not just the visible nav.
    "evaluations.admin",
    "events.admin",
    # 4 dashboard action cards that previously had no DOM hook.
    "dashboard.parent_register_link",
    "dashboard.teacher_lessons",
    "dashboard.teacher_parent_messages",
    "dashboard.teacher_evaluations",
    # ── New keys added by permissions_v3_fatima_td_lockdown ──
    # Inside /admin/teacher-deliveries: hide the evaluations tab
    # + the stat tile that counts month evaluations.
    "td.tab_evaluations",
    "td.stat_evals",
    # On /dashboard: hide the alerts banner, آخر النشاطات + المجموعات
    # النشطة two-column panels, the amber+blue stat cards pointing
    # to evaluations/alerts subviews, and the "التقارير" quick card.
    "dashboard.alerts_banner",
    "dashboard.recent_activity",
    "dashboard.active_groups_today",
    "dashboard.stat_pending_evals",
    "dashboard.stat_missing_lessons",
    "dashboard.reports_quick_card",
]


def _password_hash(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def _connect():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        import psycopg2

        return ("pg", psycopg2.connect(url))
    import sqlite3

    db_path = os.environ.get("DB_PATH", "mindx.db")
    if not os.path.exists(db_path):
        raise SystemExit(f"local DB not found at {db_path}")
    return ("sqlite", sqlite3.connect(db_path))


def _placeholder(kind: str) -> str:
    return "%s" if kind == "pg" else "?"


def _fetch_user_id(kind: str, cur, username: str):
    q = _placeholder(kind)
    cur.execute(f"SELECT id FROM users WHERE username = {q}", (username,))
    row = cur.fetchone()
    return row[0] if row else None


def upsert_user(kind: str, cur) -> int:
    existing = _fetch_user_id(kind, cur, USERNAME)
    if existing:
        print(f"[fatima] user already exists (id={existing}); skipping INSERT")
        return existing
    pw = _password_hash(PASSWORD_PLAIN)
    q = _placeholder(kind)
    cols = "(username, password, name, role, department, landing_page, is_active, must_change_pw)"
    placeholders = ", ".join([q] * 8)
    landing = LANDING_PAGE or None
    values = (USERNAME, pw, NAME, ROLE, DEPARTMENT, landing, 1, 0)
    if kind == "pg":
        cur.execute(f"INSERT INTO users {cols} VALUES ({placeholders}) RETURNING id", values)
        new_id = cur.fetchone()[0]
    else:
        cur.execute(f"INSERT INTO users {cols} VALUES ({placeholders})", values)
        new_id = cur.lastrowid
    print(f"[fatima] inserted user id={new_id} username={USERNAME}")
    return new_id


def apply_button_overrides(kind: str, cur, user_id: int) -> int:
    q = _placeholder(kind)
    n = 0
    for bk in HIDDEN_BUTTONS:
        cur.execute(
            f"SELECT id FROM user_permissions WHERE user_id={q} AND button_key={q}",
            (user_id, bk),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                f"UPDATE user_permissions SET is_visible=0 "
                f"WHERE user_id={q} AND button_key={q}",
                (user_id, bk),
            )
        else:
            cur.execute(
                f"INSERT INTO user_permissions(user_id, button_key, is_visible) "
                f"VALUES ({q}, {q}, 0)",
                (user_id, bk),
            )
        n += 1
    print(f"[fatima] asserted {n} button-key overrides (is_visible=0)")
    return n


def write_audit(kind: str, cur, user_id: int) -> None:
    """Best-effort audit log entry. Schema differs slightly between
    legacy/Postgres deployments; swallow any column-mismatch error."""
    q = _placeholder(kind)
    details = (
        f"role={ROLE}; department={DEPARTMENT}; landing_page={LANDING_PAGE}; "
        f"hidden_buttons={len(HIDDEN_BUTTONS)}"
    )
    try:
        cur.execute(
            f"INSERT INTO audit_log(actor_username, action, target_type, target_id, details) "
            f"VALUES({q}, {q}, {q}, {q}, {q})",
            ("create_fatima_account.py", "user.create_limited_admin", "users", str(user_id), details),
        )
        print("[fatima] audit_log entry written")
    except Exception as ex:
        print(f"[fatima] audit_log skipped: {ex}")


def main() -> int:
    kind, conn = _connect()
    target = "prod (Postgres)" if kind == "pg" else f"local SQLite ({os.environ.get('DB_PATH', 'mindx.db')})"
    print(f"[fatima] target: {target}")
    cur = conn.cursor()
    try:
        user_id = upsert_user(kind, cur)
        apply_button_overrides(kind, cur, user_id)
        write_audit(kind, cur, user_id)
        conn.commit()
        print(f"[fatima] DONE. username={USERNAME} password={PASSWORD_PLAIN} user_id={user_id}")
    except Exception as ex:
        conn.rollback()
        print(f"[fatima] FAILED: {ex}", file=sys.stderr)
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
