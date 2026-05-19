"""Regression check for the IBAN card on /parent/legacy.

Asserts (without a real browser):
  1. The /parent/legacy response contains the IBAN card markup
     with the static IBAN value and the copy button.
  2. The IBAN card sits BETWEEN #pp-pick-card and #pp-upload-card
     in document order — so the parent sees it between selecting
     an installment and uploading their receipt.
  3. The copy JS handler is wired (modern clipboard API + the
     execCommand fallback).
  4. The page renders for a logged-in parent/student account.

Run: python scripts/verify_iban_card.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

IBAN = "BH30BIBB00100002994768"


def _login_as_parent_or_student(client):
    """Session-inject any role=parent or role=student row from the
    local DB. /parent/legacy gates on role in (parent, student)."""
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT * FROM users "
            "WHERE role IN ('parent','student') "
            "ORDER BY (CASE WHEN username='student_test' THEN 0 ELSE 1 END), id "
            "LIMIT 1"
        ).fetchone()
        if not row:
            return None
        user_d = dict(row)
    with client.session_transaction() as s:
        s["user"] = user_d
    return user_d


def main():
    client = appmod.app.test_client()
    u = _login_as_parent_or_student(client)
    if not u:
        print("FAIL — no parent/student account in local DB")
        return 1
    print(f"Logged in as {u.get('username')!r} (role={u.get('role')})")

    r = client.get("/parent/legacy", follow_redirects=False)
    if r.status_code != 200:
        print(f"FAIL — /parent/legacy returned {r.status_code}")
        return 1
    html = r.get_data(as_text=True)

    ok = True
    def check(label, predicate):
        nonlocal ok
        sign = "OK" if predicate else "FAIL"
        if not predicate: ok = False
        print(f"  [{sign}] {label}")

    check("page is HTML (has <body>)",          "<body>" in html)
    check("IBAN value appears in markup",       IBAN in html)
    check("#pp-iban-card element present",      'id="pp-iban-card"' in html)
    check("copy button id #pp-iban-copy-btn",   'id="pp-iban-copy-btn"' in html)
    check("data-iban attribute carries IBAN",   f'data-iban="{IBAN}"' in html)
    check("copy button label '📋 نسخ'",          "📋 نسخ" in html)
    check("'✓ تم النسخ' string in JS",          "✓ تم النسخ" in html)
    check("clipboard API path in JS",           "navigator.clipboard.writeText" in html)
    check("execCommand fallback present",       "document.execCommand('copy')" in html)
    check(".pp-iban-num style class present",   '.pp-iban-num' in html)
    check(".pp-iban-copy style class present",  '.pp-iban-copy' in html)

    # Document-order check: the IBAN card must sit BETWEEN the picker
    # and the upload section.
    iban_idx   = html.find('id="pp-iban-card"')
    pick_idx   = html.find('id="pp-pick-card"')
    upload_idx = html.find('id="pp-upload-card"')
    check("IBAN card is AFTER #pp-pick-card",
          0 <= pick_idx < iban_idx)
    check("IBAN card is BEFORE #pp-upload-card",
          0 <= iban_idx < upload_idx)

    print()
    if ok:
        print("ALL OK — IBAN card landed on /parent/legacy in the correct "
              "spot (between picker and upload). Copy JS wired with both "
              "clipboard API and execCommand fallback.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
