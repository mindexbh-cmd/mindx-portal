"""Regression suite for fix-pm-send-flow.

Verifies the new sequential send pipeline at the API level (the
modal's JS state machine is exercised manually with a browser).

Cases:
  1. POST /send returns recipient list and DOES NOT flip status='sent'.
  2. POST /recipient/<rid>/mark-sent increments whatsapp_sent_count
     by exactly 1 per call. Per-call response carries the new count.
  3. mark-sent is idempotency-free on the server but tolerant —
     client tracks marked rids. Re-calling with the same rid bumps
     the count one more time (documents the design choice).
  4. mark-sent when status='sent' returns ok + already_finalized=True
     WITHOUT bumping the count further.
  5. mark-sent with rid=0 (no log row) still bumps the count.
  6. Markup is in place: ADMIN_PARENT_MESSAGES_HTML contains the
     new sequential modal markers (pmsOpenBtn, pmsConfirmBtn,
     pmsSkipBtn, pmsPauseBtn, pmsFinalSummary).
  7. The buggy auto-loop pattern is GONE — no setTimeout-driven
     window.open calls remain in _runSendSweep.

Run: python scripts/verify_pm_send_flow.py
"""
from __future__ import annotations
import os, re, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_results = []


def _check(label, ok, detail=""):
    _results.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


def _login_admin(client):
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT * FROM users WHERE role='admin' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row: return None
        u = dict(row)
    with client.session_transaction() as s:
        s["user"] = u
    return u


def _create_draft(client, group):
    """Create a parent_messages row directly via SQL (avoiding the
    create endpoint's recipient-count machinery — we want a known
    seeded total)."""
    with appmod.app.app_context():
        db = appmod.get_db()
        cur = db.execute(
            "INSERT INTO parent_messages("
            "teacher_id, teacher_username, teacher_name, group_name, "
            "sent_date, content_covered, skills_focused, books_used, "
            "homework, parent_notes, whatsapp_status, "
            "whatsapp_sent_count, whatsapp_total_count, status, "
            "is_deleted, created_at, updated_at) "
            "VALUES(0, 'verify', 'Verify Bot', ?, '2026-05-19', "
            "'test content', 'test skills', 'test books', '', '', "
            "'queued', 0, 0, 'draft', 0, "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (group,))
        db.commit()
        mid = cur.lastrowid
        if not mid:
            row = db.execute(
                "SELECT id FROM parent_messages WHERE teacher_username='verify' "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            mid = int(dict(row).get("id") or 0) if row else 0
    return mid


def _row_counts(mid):
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT status, whatsapp_status, whatsapp_sent_count, "
            "whatsapp_total_count FROM parent_messages WHERE id=?",
            (mid,)).fetchone()
        return dict(row) if row else {}


def main():
    client = appmod.app.test_client()
    admin = _login_admin(client)
    if not admin:
        print("FAIL — no admin user in local DB"); return 1
    print(f"Logged in as admin: {admin.get('username')!r}\n")

    # Need a real group with at least one student so /send returns
    # recipients. Use the first group with an active 'تم التسجيل'.
    with appmod.app.app_context():
        db = appmod.get_db()
        srow = db.execute(
            "SELECT group_name_student FROM students "
            "WHERE TRIM(COALESCE(registration_term2_2026,''))='تم التسجيل' "
            "  AND TRIM(COALESCE(group_name_student,''))<>'' "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        group = (dict(srow).get("group_name_student") if srow else "") or "مجموعة 01"

    mid = _create_draft(client, group)
    if not mid:
        print("FAIL — could not create test draft"); return 1
    print(f"Created test parent_messages id={mid} group={group!r}\n")

    # ── Case 1: /send returns recipients, doesn't flip 'sent' ───
    print("Case 1 — /send returns recipients, status still draft")
    r = client.post(f"/api/parent-messages/{mid}/send")
    j = r.get_json() or {}
    _check("/send HTTP 200", r.status_code == 200, f"got {r.status_code}")
    _check("/send ok=True", j.get("ok") is True)
    recipients = j.get("recipients") or []
    # Recipient count depends on the local DB seed (which groups
    # have active 'تم التسجيل' students with phones). The behaviour
    # we're verifying is "draft status preserved + total_count
    # matches recipient count" — both hold regardless of N.
    print(f"    /send returned {len(recipients)} recipient(s) "
          f"(env-dependent)")
    row = _row_counts(mid)
    _check("status stays 'draft' after /send",
           row.get("status") == "draft",
           f"got {row.get('status')!r}")
    _check("total_count populated by /send",
           int(row.get("whatsapp_total_count") or 0) == len(recipients),
           f"total={row.get('whatsapp_total_count')} recipients={len(recipients)}")
    _check("sent_count still 0 after /send",
           int(row.get("whatsapp_sent_count") or 0) == 0,
           f"got {row.get('whatsapp_sent_count')}")

    # ── Case 2: per-recipient mark-sent increments by 1 ─────────
    # (Server-side check — uses a synthetic rid because the local
    # DB may have no eligible students for this group.)
    print("\nCase 2 — per-recipient mark-sent bumps by exactly 1")
    rid = (recipients[0].get("log_id") if recipients else None) or 42  # synthetic
    before = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    r = client.post(f"/api/parent-messages/{mid}/recipient/{rid}/mark-sent")
    j = r.get_json() or {}
    after = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    _check("HTTP 200", r.status_code == 200)
    _check("response sent_count = before+1",
           j.get("sent_count") == before + 1,
           f"before={before} response={j.get('sent_count')}")
    _check("DB row sent_count incremented",
           after == before + 1,
           f"before={before} after={after}")
    # Another bump, on the same rid — should add another 1.
    r = client.post(f"/api/parent-messages/{mid}/recipient/{rid}/mark-sent")
    after2 = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    _check("repeat call bumps again (server-side not idempotent)",
           after2 == after + 1,
           f"after2={after2} expected={after+1}")
    print(f"    (design note: client guards against repeat clicks.)")

    # ── Case 3: rid=0 still bumps ───────────────────────────────
    print("\nCase 3 — mark-sent with rid=0 (no log row) still bumps")
    before = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    r = client.post(f"/api/parent-messages/{mid}/recipient/0/mark-sent")
    j = r.get_json() or {}
    after = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    _check("rid=0 returns ok",
           j.get("ok") is True,
           f"got {j}")
    _check("rid=0 bumped count",
           after == before + 1,
           f"before={before} after={after}")

    # ── Case 4: mark-sent after finalize returns already_finalized
    print("\nCase 4 — mark-sent after finalize is a no-op")
    r = client.post(f"/api/parent-messages/{mid}/finalize",
                    json={"sent_count": 1, "total_count": 1})
    j = r.get_json() or {}
    _check("/finalize ok", j.get("ok") is True)
    _check("status flipped to 'sent'",
           _row_counts(mid).get("status") == "sent")
    before = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    r = client.post(f"/api/parent-messages/{mid}/recipient/0/mark-sent")
    j = r.get_json() or {}
    after = int(_row_counts(mid).get("whatsapp_sent_count") or 0)
    _check("response carries already_finalized=True",
           j.get("already_finalized") is True,
           f"got {j}")
    _check("count NOT bumped after finalize",
           after == before,
           f"before={before} after={after}")

    # ── Case 5: HTML / JS markers are in place ──────────────────
    print("\nCase 5 — admin template carries the new markup + JS")
    html = appmod.ADMIN_PARENT_MESSAGES_HTML
    for marker in ('id="pmsOpenBtn"', 'id="pmsConfirmBtn"',
                   'id="pmsSkipBtn"', 'id="pmsPauseBtn"',
                   'id="pmsFinalSummary"', 'id="pmsProgressFill"',
                   'id="pmsCurrentName"', 'id="pmsCurrentPhone"',
                   'id="pmsCurrentText"', 'id="pmsBlockedHint"'):
        _check(f"markup has {marker}", marker in html)
    for fn in ('pmsRenderCurrent', 'pmsOpenCurrent',
               'pmsConfirmCurrent', 'pmsSkipCurrent',
               'pmsRenderDone', 'pmsFinish', 'pmsPause',
               '/recipient/'):
        _check(f"JS contains {fn!r}", fn in html)

    # ── Case 6: the buggy auto-loop pattern is GONE ─────────────
    print("\nCase 6 — old auto-loop pattern is no longer present")
    # The smoking gun was setTimeout(step, 600) right after a
    # window.open() in _runSendSweep. Confirm that exact pattern
    # is gone (we still use window.open inside the user-gesture
    # click handler, but no setTimeout-driven re-entry).
    suspect = re.search(r"setTimeout\(\s*step\s*,", html)
    _check("no 'setTimeout(step, …)' loop in admin template",
           suspect is None,
           f"match: {suspect.group(0) if suspect else 'none'}")
    suspect2 = re.search(
        r"window\.open\([^)]*\)\s*;\s*sentCount\+\+", html)
    _check("no 'window.open(...); sentCount++' incrementer pattern",
           suspect2 is None,
           f"match: {suspect2.group(0) if suspect2 else 'none'}")

    # Cleanup
    with appmod.app.app_context():
        db = appmod.get_db()
        try:
            db.execute("DELETE FROM parent_messages WHERE id=?", (mid,))
            db.execute("DELETE FROM message_log WHERE template_name=?",
                       ("parent-broadcast/" + str(mid),))
            db.commit()
        except Exception: pass

    print()
    fails = [r for r in _results if not r[1]]
    print(f"{len(_results) - len(fails)}/{len(_results)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — sequential send flow wired correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
