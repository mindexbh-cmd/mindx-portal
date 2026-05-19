"""Regression check for the IBAN card on /portal/parent-hub/payments.

Asserts (without a real browser):
  1. The /portal/parent-hub/payments response contains the IBAN
     section markup with the static IBAN value and the copy button.
  2. The IBAN card sits INSIDE .wrap but BEFORE #root in document
     order — so it survives any failure of the dynamic API fetch.
  3. The copy JS handler is wired (idiomatic clipboard API + the
     execCommand fallback).
  4. The page still renders for a logged-in student (role=student
     gate from the route).

Run: python scripts/verify_iban_card.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

IBAN = "BH30BIBB00100002994768"


def _login_as_student(client):
    """Session-inject the seeded student_test row (avoid local-DB
    password drift — same pattern used in verify_fatima_flash.py)."""
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT * FROM users WHERE username=? OR role='student' "
            "ORDER BY (CASE WHEN username=? THEN 0 ELSE 1 END) LIMIT 1",
            ("student_test", "student_test")
        ).fetchone()
        if not row:
            return None
        user_d = dict(row)
    with client.session_transaction() as s:
        s["user"] = user_d
    return user_d


def main():
    client = appmod.app.test_client()
    u = _login_as_student(client)
    if not u:
        print("FAIL — no student account in local DB")
        return 1
    print(f"Logged in as {u.get('username')!r} (role={u.get('role')})")

    r = client.get("/portal/parent-hub/payments", follow_redirects=False)
    if r.status_code != 200:
        print(f"FAIL — /portal/parent-hub/payments returned {r.status_code}")
        return 1
    html = r.get_data(as_text=True)

    ok = True
    def check(label, predicate):
        nonlocal ok
        sign = "OK" if predicate else "FAIL"
        if not predicate: ok = False
        print(f"  [{sign}] {label}")

    check("page is HTML (has <body>)",        "<body>" in html)
    check("IBAN value appears in markup",     IBAN in html)
    check(".iban-card section present",       'class="section iban-card"' in html)
    check("copy button id present",           'id="iban-copy-btn"' in html)
    check("data-iban attribute carries IBAN", f'data-iban="{IBAN}"' in html)
    check("copy button label '📋 نسخ'",        "📋 نسخ" in html)
    check("'✓ تم النسخ' string is in JS",     "✓ تم النسخ" in html)
    check("clipboard API path in JS",         "navigator.clipboard.writeText" in html)
    check("execCommand fallback present",     "document.execCommand('copy')" in html)

    # Document-order check: the IBAN card must come BEFORE #root so
    # the dynamic-content fetch can't clobber it. Match the actual
    # element tag (not the substring, which also appears in the CSS
    # rules inside the <style> block).
    iban_el_idx = html.find('class="section iban-card"')
    root_idx    = html.find('id="root"')
    check(".iban-card element precedes #root in document order",
          0 <= iban_el_idx < root_idx)

    # Both should live inside the same .wrap.
    wrap_open      = html.find('<div class="wrap">')
    script_idx     = html.find("<script>")
    wrap_close_idx = html.rfind("</div>", 0, script_idx)
    check(".iban-card sits inside .wrap",
          0 <= wrap_open < iban_el_idx < wrap_close_idx)

    print()
    if ok:
        print("ALL OK — IBAN card markup, copy button, JS handler, and "
              "document order are correct. Ready for browser smoke test.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
