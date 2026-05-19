"""Regression suite for brand-and-resume-status.

Three parts:

  A) Brand fix — _pm_render_message + monthly-eval message
     builder now end with 'مركز مايندكس للتعليم والتدريب'
     instead of bare 'مايندكس'. The teacher preview template
     JS also got the same update.

  B) /send relaxation — partial-sent rows (sent_count > 0 but
     < total_count) are no longer refused. The response echoes
     resume_from = current sent_count. Fully-sent rows still
     refuse with the expected Arabic error.

  C) Template wiring — both admin templates carry the new
     4-branch badge / 3-branch button code and the resume
     cursor (resumeFrom / preSent) in the state machine.

Run: python scripts/verify_brand_and_resume.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_r = []


def _check(label, ok, detail=""):
    _r.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


def main():
    # ── Part A: brand-name signature lines ──────────────────────
    print("Part A — brand name in signatures")
    # Render a sample parent message and check the trailing line.
    text = appmod._pm_render_message(
        "فاطمة", "أ. زهراء", "مجموعة 01", "2026-05-19",
        "محتوى", "مهارات", "كتاب", "", "")
    last_line = text.strip().splitlines()[-1] if text else ""
    _check("_pm_render_message ends with the full brand name",
           last_line == "مركز مايندكس للتعليم والتدريب",
           f"got: {last_line!r}")
    _check("rendered text does NOT end with bare 'مايندكس'",
           not text.strip().endswith("\nمايندكس"),
           "stale brand")
    # Template preview JS also has the full name.
    teacher_html = appmod.TEACHER_PARENT_MESSAGES_HTML
    _check("teacher preview JS has the full brand name",
           "lines.push('مركز مايندكس للتعليم والتدريب')" in teacher_html,
           "string not found")
    _check("teacher preview no longer has bare 'مايندكس' signature",
           "lines.push('مايندكس')" not in teacher_html)
    # Source app.py — make sure no signature-pattern bare-name
    # remains in the message-builder regions.
    with open(os.path.abspath(os.path.join(_THIS, "..", "app.py")),
              encoding="utf-8") as f:
        src = f.read()
    for sig in ('lines.append("مايندكس")',
                "lines.push('مايندكس')"):
        _check(f"no remaining {sig!r} in source",
               sig not in src)

    # ── Part B: /send relaxation + resume_from ──────────────────
    print("\nPart B — /send relaxation + resume_from echo")
    client = appmod.app.test_client()
    with appmod.app.app_context():
        db = appmod.get_db()
        admin = db.execute("SELECT * FROM users WHERE role='admin' "
                            "ORDER BY id LIMIT 1").fetchone()
        if not admin:
            print("  FAIL — no admin in DB"); return 1
        u = dict(admin)
        # Pick first group with at least one student (any).
        gr = db.execute(
            "SELECT group_name FROM student_groups "
            "WHERE group_name IS NOT NULL "
            "  AND TRIM(group_name) <> '' ORDER BY id LIMIT 1"
        ).fetchone()
        group = (dict(gr).get("group_name") if gr else "") or "مجموعة 01"
    with client.session_transaction() as s:
        s["user"] = u
    # Create a draft row directly via SQL with synthetic counts
    # so we can exercise each /send branch.
    def _new_row(status, sent, total):
        with appmod.app.app_context():
            db = appmod.get_db()
            cur = db.execute(
                "INSERT INTO parent_messages(teacher_id, teacher_username, "
                "teacher_name, group_name, sent_date, content_covered, "
                "skills_focused, books_used, homework, parent_notes, "
                "whatsapp_status, whatsapp_sent_count, whatsapp_total_count, "
                "status, is_deleted, created_at, updated_at) "
                "VALUES(0, 'br_test', 'BR Test', ?, '2026-05-19', "
                "'c', 's', 'b', '', '', 'queued', ?, ?, ?, 0, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                (group, sent, total, status))
            db.commit()
            mid = cur.lastrowid
            if not mid:
                row = db.execute(
                    "SELECT id FROM parent_messages "
                    "WHERE teacher_username='br_test' ORDER BY id DESC LIMIT 1"
                ).fetchone()
                mid = int(dict(row).get("id") or 0) if row else 0
        return mid

    created_ids = []
    try:
        # Case 1: draft, sent=0 → accept, resume_from=0
        mid = _new_row("draft", 0, 0); created_ids.append(mid)
        r = client.post(f"/api/parent-messages/{mid}/send")
        j = r.get_json() or {}
        _check("draft + sent=0 → 200",       r.status_code == 200)
        _check("draft echoes resume_from=0",  j.get("resume_from") == 0,
               f"got {j.get('resume_from')}")

        # Case 2: status='sent' with partial sent=3/20 → accept
        mid = _new_row("sent", 3, 20); created_ids.append(mid)
        r = client.post(f"/api/parent-messages/{mid}/send")
        j = r.get_json() or {}
        _check("partial (sent < total) → 200 even when status='sent'",
               r.status_code == 200)
        _check("partial echoes resume_from=3",
               j.get("resume_from") == 3, f"got {j.get('resume_from')}")
        _check("partial echoes sent_count=3",
               j.get("sent_count") == 3, f"got {j.get('sent_count')}")

        # Case 3: fully sent → still refused
        mid = _new_row("sent", 5, 5); created_ids.append(mid)
        r = client.post(f"/api/parent-messages/{mid}/send")
        j = r.get_json() or {}
        _check("fully sent → 400",   r.status_code == 400)
        _check("fully sent error mentions إعادة الإرسال",
               "إعادة الإرسال" in (j.get("error") or ""),
               f"got {j.get('error')!r}")

        # Case 4: /send must NOT zero sent_count on a partial row.
        mid = _new_row("sent", 7, 20); created_ids.append(mid)
        r = client.post(f"/api/parent-messages/{mid}/send")
        with appmod.app.app_context():
            db = appmod.get_db()
            row = db.execute(
                "SELECT whatsapp_sent_count FROM parent_messages WHERE id=?",
                (mid,)).fetchone()
            cur_sent = int(dict(row).get("whatsapp_sent_count") or 0)
        _check("partial /send preserves sent_count = 7",
               cur_sent == 7, f"got {cur_sent}")
    finally:
        with appmod.app.app_context():
            db = appmod.get_db()
            for mid in created_ids:
                try:
                    db.execute("DELETE FROM parent_messages WHERE id=?", (mid,))
                    db.execute("DELETE FROM message_log "
                               "WHERE template_name=?",
                               ("parent-broadcast/" + str(mid),))
                except Exception: pass
            db.commit()

    # ── Part C: template wiring ─────────────────────────────────
    print("\nPart C — template wiring (badges + buttons + resume cursor)")
    pmsg = appmod.ADMIN_PARENT_MESSAGES_HTML
    tdel = appmod.ADMIN_TEACHER_DELIVERIES_HTML

    # /admin/parent-messages
    for marker in ("'✓ تم الإرسال'",
                   "'⏸️ لم يكتمل — المتبقي: '",
                   "'لم يبدأ بعد'",
                   "'مسودة'",
                   "doResume(",
                   "▶️ متابعة الإرسال",
                   "🔄 إعادة الإرسال",
                   "resumeFrom = parseInt"):
        _check(f"parent-messages template has {marker!r}",
               marker in pmsg)

    # /admin/teacher-deliveries
    for marker in ("tmPmState",
                   "▶️ متابعة الإرسال",
                   "لم يبدأ بعد",
                   "تم إرسال '",
                   "tm-btn-resume-send",
                   "resumeFrom"):
        _check(f"teacher-deliveries template has {marker!r}",
               marker in tdel)

    # The OLD '<span class="status-pill sent">تم الإرسال</span>'
    # rendering used a static label without the leading checkmark.
    # Confirm the bare label string is gone in the new branch.
    _check("parent-messages no longer uses bare 'lbl = \\'تم الإرسال\\'' literal",
           "lbl = 'تم الإرسال'" not in pmsg)

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — brand fix + resume flow wired correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
