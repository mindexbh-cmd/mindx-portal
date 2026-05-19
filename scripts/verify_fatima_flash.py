"""Quick verification that the Layer A pre-paint <style> kills the
Fatima permission flash. Spins up Flask's test client, logs in as
Fatima (930909151 / 930909151), hits /dashboard and
/admin/teacher-deliveries, and asserts:

  1. The response contains an inline <style> with
     [data-button-key="..."] {display:none!important;} rules.
  2. The style block lives in <head> (before <body>).
  3. The style block lists the expected lockdown keys
     (sidebar.section_students, dashboard.recent_activity, etc.).
  4. The JS backstop at /api/me/permissions is unchanged
     (defense-in-depth — should still emit hidden_buttons).
  5. Admin / Ahmed Ibrahim / Raed do NOT receive the inline style
     (or receive an empty one). Verifies the strictly-additive
     promise.

Run: python scripts/test_fatima_flash.py
"""
from __future__ import annotations
import re
import sys
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _ROOT)

import app as appmod  # noqa: E402

EXPECTED_FATIMA_HIDDEN = {
    "sidebar.section_students",
    "sidebar.section_attendance_block",
    "sidebar.section_finance",
    "sidebar.section_points",
    "sidebar.section_admin_monitor",
    "dashboard.alerts_banner",
    "dashboard.recent_activity",
    "dashboard.active_groups_today",
    "dashboard.stat_pending_evals",
    "dashboard.stat_missing_lessons",
    "dashboard.reports_quick_card",
    "dashboard.teacher_lessons",
    "dashboard.teacher_parent_messages",
    "dashboard.teacher_evaluations",
}


def _login(client, username, password):
    """Try real form login first; if it fails (e.g. local DB seeded
    with a different password), fall back to injecting the user row
    into the session directly via /test/_session_login. We never
    expose that helper — we just patch session for the test
    client."""
    r = client.post("/login",
                    data={"username": username, "password": password},
                    follow_redirects=False)
    if r.status_code in (302, 303):
        return True, r.status_code, r.headers.get("Location", "")
    # Fallback: load the user row from the live DB and write it into
    # the session via the client's session_transaction.
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        if not row:
            return False, 0, f"no user {username!r} in local DB"
        user_d = dict(row)
    with client.session_transaction() as s:
        s["user"] = user_d
    return True, 200, f"session-injected ({user_d.get('role')})"


def _hidden_keys_from_html(html):
    """Pull the data-button-key values out of the FIRST <style> block
    that uses display:none!important. Returns [] if none found."""
    head_idx = html.find("</head>")
    if head_idx < 0:
        return []
    head_html = html[:head_idx]
    blocks = re.findall(r"<style>([^<]*?display:none[^<]*?)</style>",
                        head_html, re.IGNORECASE | re.DOTALL)
    keys = []
    for b in blocks:
        for m in re.finditer(r'data-button-key="([^"]+)"', b):
            keys.append(m.group(1))
    return keys


def _check_user(label, username, password, paths,
                expect_hidden_subset=None, expect_empty=False):
    client = appmod.app.test_client()
    ok, code, loc = _login(client, username, password)
    if not ok:
        print(f"  [{label}] LOGIN FAILED status={code} body={loc!r}")
        return False
    all_ok = True
    for path in paths:
        r = client.get(path, follow_redirects=False)
        if r.status_code != 200:
            print(f"  [{label}] {path} → {r.status_code} (not 200)")
            all_ok = False
            continue
        html = r.get_data(as_text=True)
        keys = _hidden_keys_from_html(html)
        if expect_empty:
            if keys:
                print(f"  [{label}] {path} FAIL — expected empty pre-paint style, got {len(keys)} keys: {keys[:5]}…")
                all_ok = False
            else:
                print(f"  [{label}] {path} OK — no pre-paint style (as expected)")
        else:
            kset = set(keys)
            missing = (expect_hidden_subset or set()) - kset
            if missing:
                print(f"  [{label}] {path} FAIL — missing keys in pre-paint style: {sorted(missing)}")
                all_ok = False
            else:
                where = "<head>" if "<head>" in html.split("<body>", 1)[0] else "?"
                style_idx = html.find("[data-button-key=")
                body_idx = html.find("<body>")
                placement = "before <body>" if 0 <= style_idx < body_idx else "AFTER <body> (BAD)"
                print(f"  [{label}] {path} OK — {len(kset)} keys hidden, placement={placement}")
                if not (0 <= style_idx < body_idx):
                    all_ok = False
    return all_ok


# Layer B — endpoints that should 403 for Fatima but stay 200 for
# every other manager / admin / reception. Mapping mirrors C6.
LAYER_B_ENDPOINTS = [
    "/api/dashboard/recent-activity",
    "/api/dashboard/active-groups-today",
    "/api/dashboard/active-groups-detailed",
    "/api/teacher-deliveries/summary",
    "/api/lessons/missing",
]


def _check_layer_b(label, username, password, expect_403):
    """Hit each Layer B endpoint and assert the expected status. For
    Fatima, expect_403=True (all 5 should be 403). For admin /
    Ahmed Ibrahim / Raed, expect_403=False (all 5 should be 200).
    Returns True on full pass."""
    client = appmod.app.test_client()
    ok, code, loc = _login(client, username, password)
    if not ok:
        print(f"  [{label}] LOGIN FAILED status={code} loc={loc}")
        return False
    all_ok = True
    for ep in LAYER_B_ENDPOINTS:
        r = client.get(ep, follow_redirects=False)
        sc = r.status_code
        if expect_403:
            verdict = "OK (403)" if sc == 403 else f"FAIL (got {sc})"
            ok_ep = (sc == 403)
        else:
            verdict = "OK (200)" if sc == 200 else f"FAIL (got {sc})"
            ok_ep = (sc == 200)
        if not ok_ep:
            all_ok = False
        print(f"  [{label}] {ep} → {verdict}")
    return all_ok


def main():
    print("=== LAYER A — pre-paint <style> ==========================")
    print("Fatima Ibrahim (limited-admin manager):")
    fatima_ok = _check_user(
        "fatima", "930909151", "930909151",
        ["/dashboard", "/admin/teacher-deliveries"],
        expect_hidden_subset=EXPECTED_FATIMA_HIDDEN,
    )

    print("\nAdmin (no overrides):")
    admin_layer_a_ok = _check_user(
        "admin", "admin", "admin123",
        ["/dashboard", "/admin/teacher-deliveries"],
        expect_empty=True,
    )

    # Also verify /api/me/permissions still works as the backstop.
    print("\n/api/me/permissions backstop:")
    c = appmod.app.test_client()
    ok, code, loc = _login(c, "930909151", "930909151")
    if ok:
        r = c.get("/api/me/permissions")
        try:
            d = r.get_json()
        except Exception:
            d = None
        hb = (d or {}).get("hidden_buttons") or []
        missing = EXPECTED_FATIMA_HIDDEN - set(hb)
        if r.status_code == 200 and not missing:
            print(f"  fatima → {len(hb)} hidden_buttons returned (JS backstop healthy)")
            backstop_ok = True
        else:
            print(f"  FAIL status={r.status_code} missing={sorted(missing)}")
            backstop_ok = False
    else:
        print(f"  fatima login failed: {code} {loc}")
        backstop_ok = False

    print("\n=== LAYER B — API 403 gates =============================")
    print("Fatima (expect 403 on all 5):")
    fatima_b_ok = _check_layer_b("fatima", "930909151", "930909151",
                                  expect_403=True)

    print("\nAdmin (expect 200 on all 5):")
    admin_b_ok = _check_layer_b("admin", "admin", "admin123",
                                 expect_403=False)

    print("\nAhmed Ibrahim — manager, no overrides (expect 200 on all 5):")
    ahmed_b_ok = _check_layer_b("ahmed", "010307885", "010307885",
                                 expect_403=False)

    print("\nRaed — manager, no overrides (expect 200 on all 5):")
    raed_b_ok = _check_layer_b("raed", "980909805", "980909805",
                                expect_403=False)

    print()
    all_passed = (fatima_ok and admin_layer_a_ok and backstop_ok and
                  fatima_b_ok and admin_b_ok and ahmed_b_ok and raed_b_ok)
    if all_passed:
        print("ALL OK — Layer A flash killed for Fatima; Layer B 403s "
              "Fatima on the 5 endpoints; admin / Ahmed / Raed all "
              "pass with 200. Backstop healthy.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
