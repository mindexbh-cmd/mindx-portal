"""
G20m hermetic test — mobile full-page nav + conditional embed=1.

Asserts:

  G20m.1 — additive mobile nav interceptor
    - PORTAL_PARENT_PID_HUB_HTML carries a NEW <script> block
      after the existing inline JS containing a capture-phase
      document.addEventListener('click', handler, true) that
      bails on desktop via matchMedia(max-width:600px) and
      navigates to a full-page URL on mobile.
    - The 5 FULL_URLS entries mirror TAB_URLS minus ?inner=1.
    - The existing phActivateTab, TAB_URLS, button markup, and
      CARD_DEFS renderer are all unchanged (nothing removed).

  G20m.2 — conditional embed=1 redirect
    - portal_parent_hub_payments_page now uses standalone_url
      (no embed=1) for the redirect path and iframe_url (with
      embed=1) for the iframe markup. Same for evaluations.
    - Full-page GET (no ?inner=1) → 302 to legacy WITHOUT embed=1
    - Inner GET (?inner=1) → 200 iframe markup WITH embed=1 in src
    - The legacy /parent/legacy route's embed=1 hide-CSS injection
      (G20i) is preserved exactly — only the redirect targets
      changed.

Usage:
    python scripts/smoke_g20m.py
"""

import importlib.util
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"
SRC = APP_PY.read_text(encoding="utf-8")

failed = []


def check(label, ok, hint=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        if hint:
            print(f"         hint: {hint}")
        failed.append(label)
    return bool(ok)


def section(title):
    print(f"\n=== {title} ===")


# ── G20m.1 — additive mobile nav interceptor ───────────────────
section("G20m.1: additive capture-phase mobile nav interceptor")

check("G20m.1 marker comment present",
      "G20m.1: mobile-only full-page nav" in SRC)
check("FULL_URLS map present with 5 entries (attendance, payment, "
      "books, evaluations, points)",
      "FULL_URLS" in SRC
      and "attendance : '/portal/parent-hub/attendance'" in SRC
      and "payment    : '/portal/parent-hub/payments'" in SRC
      and "books      : '/portal/parent-hub/curriculum'" in SRC
      and "evaluations: '/portal/parent-hub/evaluations'" in SRC
      and "points     : '/portal/parent-hub/points'" in SRC)
check("capture-phase listener (third arg true) on document click",
      "document.addEventListener('click', function(ev){" in SRC
      and "}, true);" in SRC)
check("matchMedia(max-width:600px) gate present",
      "window.matchMedia('(max-width:600px)').matches" in SRC)
check(".mb-nav-btn closest() targeting",
      "ev.target.closest('.mb-nav-btn')" in SRC)
check("data-tab read + URL lookup + navigate",
      "btn.getAttribute('data-tab')" in SRC
      and "FULL_URLS[tab]" in SRC
      and "window.location.href = url" in SRC)
check("event.preventDefault + stopImmediatePropagation present",
      "ev.preventDefault()" in SRC
      and "ev.stopImmediatePropagation()" in SRC)

# Existing code untouched — these are the contract markers.
check("phActivateTab function definition still present (untouched)",
      "function phActivateTab(name)" in SRC)
check("window.phActivateTab still exposed",
      "window.phActivateTab = phActivateTab" in SRC)
check("inline onclick=\"phActivateTab(...)\" still on buttons",
      "onclick=\"phActivateTab(\\'' + c.key + '\\')\"" in SRC)
check("TAB_URLS map still present (unchanged)",
      "attendance : '/portal/parent-hub/attendance?inner=1'" in SRC)


# ── G20m.2 — conditional embed=1 ───────────────────────────────
section("G20m.2: conditional embed=1 on standalone redirect")

check("G20m.2 marker comment present in payments handler",
      "G20m.2: split into two URLs" in SRC)
# Payments handler: iframe_url has embed=1, standalone_url doesn't.
check("payments handler defines iframe_url WITH embed=1",
      '"/parent/legacy?pid=" + (pid or "")\n'
      '                  + "&embed=1#section-payment"' in SRC)
check("payments handler defines standalone_url WITHOUT embed=1",
      '"/parent/legacy?pid=" + (pid or "")\n'
      '                      + "#section-payment"' in SRC)
check("payments handler redirects to standalone_url",
      "return redirect(standalone_url)" in SRC)
# Evaluations handler same shape.
check("evaluations handler defines iframe_url WITH embed=1",
      '"/parent/evaluations/view?pid=" + (pid or "") + "&embed=1"' in SRC)
check("evaluations handler defines standalone_url WITHOUT embed=1",
      '"/parent/evaluations/view?pid=" + (pid or "")' in SRC
      and 'standalone_url = "/parent/evaluations/view?pid=" + (pid or "")'
      in SRC)
check("BOTH handlers redirect to standalone_url (count >= 2)",
      SRC.count("return redirect(standalone_url)") >= 2)
check("iframe markup STILL uses iframe_url (back-button hide preserved)",
      'src="\' + iframe_url + \'"' in SRC
      and SRC.count('src="\' + iframe_url + \'"') >= 2)

# G20i hide-CSS injection on /parent/legacy still in place.
check("G20i hide-CSS injection on /parent/legacy unchanged",
      "<style>#pp-back-btn{display:none !important;}</style>" in SRC)
check("G20i hide-CSS injection on /parent/evaluations/view unchanged",
      "<style>#pe-back-link{display:none !important;}</style>" in SRC)


# ── Runtime: routes preserved + behavior matrix via test client ─
section("runtime: routes + embed=1 behavior matrix")

spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

try:
    rules = [str(r) for r in mod.app.url_map.iter_rules()]
    for route in [
        "/portal/parent",
        "/portal/parent-hub/payments",
        "/portal/parent-hub/evaluations",
        "/portal/parent-hub/attendance",
        "/portal/parent-hub/points",
        "/portal/parent-hub/curriculum",
        "/parent/legacy",
        "/parent/evaluations/view",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# Use the Flask test client (no live server needed) to verify the
# conditional embed=1 contract at the HTTP layer.
try:
    with mod.app.test_client() as client:
        # The portal routes need a student session. Inject one
        # against the seeded test student via login.
        with mod.app.app_context():
            db = mod.get_db()
            try:
                row = db.execute(
                    "SELECT id, personal_id FROM students "
                    "WHERE personal_id = 'TEST-STUDENT-0001'"
                ).fetchone()
                pid = (dict(row).get("personal_id") or "").strip() if row else ""
            except Exception:
                pid = ""

        # Login as student_test (seeded in scripts/seed_test_users.py).
        login_resp = client.post(
            "/login",
            data={"username": "student_test",
                  "password": "TestStudent2026!"},
            follow_redirects=False,
        )
        check("login as student_test (test client)",
              login_resp.status_code in (200, 302),
              hint=f"status={login_resp.status_code}")

        # Payments — full page (no ?inner=1) should 302 WITHOUT embed=1.
        r = client.get("/portal/parent-hub/payments",
                       follow_redirects=False)
        loc = r.headers.get("Location", "")
        check("payments standalone: 302 to /parent/legacy",
              r.status_code == 302
              and "/parent/legacy?pid=" in loc,
              hint=f"status={r.status_code} loc={loc!r}")
        check("payments standalone: redirect has NO embed=1",
              "embed=1" not in loc, hint=f"loc={loc!r}")

        # Payments — inner (?inner=1) returns iframe markup WITH embed=1.
        r = client.get("/portal/parent-hub/payments?inner=1",
                       follow_redirects=False)
        body = r.data.decode("utf-8", errors="replace")
        check("payments inner: 200 iframe markup",
              r.status_code == 200 and "<iframe" in body)
        check("payments inner: iframe src carries embed=1",
              "embed=1" in body)

        # Evaluations — same pattern.
        r = client.get("/portal/parent-hub/evaluations",
                       follow_redirects=False)
        loc = r.headers.get("Location", "")
        check("evaluations standalone: 302 to /parent/evaluations/view",
              r.status_code == 302
              and "/parent/evaluations/view?pid=" in loc,
              hint=f"status={r.status_code} loc={loc!r}")
        check("evaluations standalone: redirect has NO embed=1",
              "embed=1" not in loc, hint=f"loc={loc!r}")

        r = client.get("/portal/parent-hub/evaluations?inner=1",
                       follow_redirects=False)
        body = r.data.decode("utf-8", errors="replace")
        check("evaluations inner: 200 iframe markup",
              r.status_code == 200 and "<iframe" in body)
        check("evaluations inner: iframe src carries embed=1",
              "embed=1" in body)

        # And the LEGACY routes still toggle the hide-CSS based on
        # the embed flag (G20i contract unchanged).
        if pid:
            r = client.get(f"/parent/evaluations/view?pid={pid}")
            has = b"#pe-back-link{display:none" in r.data
            check("legacy /parent/evaluations/view standalone: NO hide-CSS",
                  not has)
            r = client.get(f"/parent/evaluations/view?pid={pid}&embed=1")
            has = b"#pe-back-link{display:none" in r.data
            check("legacy /parent/evaluations/view embed=1: hide-CSS present",
                  has)
except Exception as ex:
    check("test client probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20m SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20m SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
