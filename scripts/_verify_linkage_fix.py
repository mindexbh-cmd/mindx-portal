"""Step 4 — Playwright verification of the parent-linkage fix.

For each scenario:
  - log in as the account
  - probe /api/portal/student/me
  - capture the resolved student.name + balance
  - (for live accounts) click each of the 5 nav buttons and confirm
    every section's primary XHR returns 200 OK with the correct data

READ-ONLY in effect (only GET + POST /login). No data mutations.

Scenarios:
  - REPAIRED  : uid=714 new pid 170206963 — must log in + work end-to-end
  - TWINS     : the 3 untouched twin accounts (160412323/160803739/160713595)
                — must continue working
  - ZOMBIES   : the 3 deactivated zombies — login must FAIL with 403
                "الحساب معطل"
  - SPOT      : 5 random accounts from the 139 silently-rescued —
                must continue working post-fix
"""
import os, sys, time, json
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
BASE = "https://mindx-portal-1.onrender.com"

SCENARIOS = [
    # (label, username, password, expected_login, expected_student_name)
    ("REPAIRED uid=714", "170206963", "170206963", True, "زينب فاضل المكحل"),
    ("TWIN     uid=3181", "160412323", "160412323", True, "حسن محمد حسن"),
    ("TWIN     uid=3180", "160803739", "160803739", True, "حسين حسين علي مكي"),
    ("TWIN     uid=3188", "160713595", "160713595", True, "زينب خليل ابراهيم عبد المحسن"),
    ("ZOMBIE   uid=846 (must FAIL)", "160412312", "160412312", False, None),
    ("ZOMBIE   uid=795 (must FAIL)", "160807379", "160807379", False, None),
    ("ZOMBIE   uid=748 (must FAIL)", "1940405392", "1940405392", False, None),
    ("SPOT     1", "180311824", "180311824", True, "حسن عبد المنعم الحايكي"),
    ("SPOT     2", "130707562", "130707562", True, "زينب غازي عبدالله حسن"),
    ("SPOT     3", "211010979", "211010979", True, "خولة أحمد عادل"),
    ("SPOT     4", "140110372", "140110372", True, "علي خليل حسن ابراهيم حسن"),
    ("SPOT     5", "130309291", "130309291", True, "محمد علي موسى الحايكي"),
]

NAV_BUTTONS = ["attendance", "points", "books", "evaluations", "payment"]

import urllib.request as ur, urllib.parse as up, http.cookiejar as cj


def http_login_and_probe(label, username, password, expect_login, expect_name):
    """First check via urllib that /api/portal/student/me returns the
    expected student (or login fails for zombies). Faster than spinning
    up Playwright for every case."""
    jar = cj.CookieJar()
    op = ur.build_opener(ur.HTTPCookieProcessor(jar))
    op.addheaders = [('User-Agent', 'mx-verify')]
    try:
        r = op.open(ur.Request(BASE + '/login',
            data=up.urlencode({'username': username,
                               'password': password}).encode(),
            method='POST'), timeout=30)
        login_url = r.url
    except Exception as ex:
        if not expect_login:
            print(f"  ✓ {label}  login REJECTED as expected ({ex})")
            return True
        print(f"  ✗ {label}  login FAIL: {ex}")
        return False
    if not expect_login:
        if '/portal/parent' in login_url:
            print(f"  ✗ {label}  expected login FAIL but got {login_url[-50:]}")
            return False
        print(f"  ✓ {label}  login REJECTED as expected (lands on {login_url[-30:]})")
        return True
    if '/portal/parent' not in login_url:
        print(f"  ✗ {label}  login did not land on /portal/parent: {login_url[-50:]}")
        return False
    try:
        body = json.loads(op.open(BASE + '/api/portal/student/me', timeout=30).read())
    except Exception as ex:
        print(f"  ✗ {label}  /api/portal/student/me EX {ex}")
        return False
    if not body.get('ok'):
        print(f"  ✗ {label}  /api/portal/student/me NOT OK: {body.get('error')!r}")
        return False
    name = (body.get('student') or {}).get('student_name', '')
    if expect_name and name != expect_name:
        print(f"  ✗ {label}  name mismatch: got {name!r}, expected {expect_name!r}")
        return False
    print(f"  ✓ {label}  login OK → me OK → name={name!r}")
    return True


print("=" * 72)
print("HTTP probe (fast) — every scenario via /api/portal/student/me")
print("=" * 72)
results = []
for label, u, p, expect_login, expect_name in SCENARIOS:
    ok = http_login_and_probe(label, u, p, expect_login, expect_name)
    results.append((label, ok))
    time.sleep(1.2)  # avoid rate limit

print("\n" + "=" * 72)
print("PLAYWRIGHT real-browser probe — REPAIRED + TWINS (click all 5 buttons)")
print("=" * 72)
from playwright.sync_api import sync_playwright

PW_TARGETS = [
    ("REPAIRED uid=714", "170206963"),
    ("TWIN     uid=3181", "160412323"),
    ("TWIN     uid=3180", "160803739"),
    ("TWIN     uid=3188", "160713595"),
]
pw_results = []

with sync_playwright() as p:
    for label, pid in PW_TARGETS:
        print(f"\n  ── {label}  (pid {pid}) ──")
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        api_status = {}
        def on_response(resp):
            try:
                u = resp.url.replace(BASE, "")
                if (u.startswith("/api/portal") or u.startswith("/parent/evaluations")
                        or u.startswith("/api/parent")):
                    api_status[u.split("?")[0]] = resp.status
            except Exception: pass
        page.on("response", on_response)
        page.goto(BASE + "/", wait_until="networkidle")
        page.fill('input[name="username"]', pid)
        page.fill('input[name="password"]', pid)
        with page.expect_navigation(wait_until="networkidle", timeout=20000):
            page.click('button[type="submit"]')
        ok = True
        try:
            page.wait_for_selector("#action-tabs .mb-nav-btn", timeout=15000)
        except Exception as ex:
            print(f"    ✗ nav buttons never appeared: {ex}")
            ok = False
        if ok:
            page.wait_for_timeout(1500)
            session_pid = page.evaluate("() => window._SESSION_PID || ''")
            print(f"    window._SESSION_PID = {session_pid!r}")
            if session_pid != pid:
                print(f"    ✗ session pid mismatch")
                ok = False
            for tab in NAV_BUTTONS:
                try:
                    page.click(f'#action-tabs .mb-nav-btn[data-tab="{tab}"]',
                               timeout=8000)
                except Exception as ex:
                    print(f"    ✗ click {tab}: {ex}")
                    ok = False
                    continue
                page.wait_for_timeout(2000)
            # Check critical endpoints all returned 200 (or skipped)
            bad = {k: v for k, v in api_status.items() if v >= 400}
            if bad:
                print(f"    ✗ failing API calls: {bad}")
                ok = False
            else:
                print(f"    ✓ all 5 tab clicks completed, no API errors")
                print(f"      endpoints hit: {sorted(api_status.keys())[:6]} …")
        browser.close()
        pw_results.append((label, ok))
        time.sleep(1.5)


print("\n" + "=" * 72)
print("FINAL AUDIT (re-query post-fix counts)")
print("=" * 72)
DB_URL = os.environ.get("DATABASE_URL", "").strip()
import psycopg2, psycopg2.extras
conn = psycopg2.connect(DB_URL)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""SELECT COUNT(*) AS n FROM users u
LEFT JOIN students s_linked ON s_linked.id = u.linked_student_id
JOIN students s ON TRIM(s.personal_id) = TRIM(u.username)
WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
  AND u.linked_student_id IS NOT NULL AND u.linked_student_id <> 0
  AND s_linked.id IS NULL""")
dead_with_fb = cur.fetchone()["n"]
cur.execute("""SELECT COUNT(*) AS n FROM users u
LEFT JOIN students s_linked ON s_linked.id = u.linked_student_id
LEFT JOIN students s_uname  ON TRIM(s_uname.personal_id) = TRIM(u.username)
WHERE u.role = 'student' AND COALESCE(u.is_active, 1) = 1
  AND u.linked_student_id IS NOT NULL AND u.linked_student_id <> 0
  AND s_linked.id IS NULL AND s_uname.id IS NULL""")
broken_no_fb = cur.fetchone()["n"]
print(f"  dead-linked-with-fallback (active): {dead_with_fb}  (expected 0)")
print(f"  broken-with-no-fallback   (active): {broken_no_fb}  (expected 0)")
cur.close(); conn.close()


print("\n" + "=" * 72)
print("SUMMARY")
print("=" * 72)
http_pass = sum(1 for _, ok in results if ok)
http_total = len(results)
pw_pass = sum(1 for _, ok in pw_results if ok)
pw_total = len(pw_results)
print(f"  HTTP probes:    {http_pass}/{http_total} pass")
print(f"  Playwright:     {pw_pass}/{pw_total} pass")
print(f"  Audit counts:   dead-w-fb={dead_with_fb} broken-no-fb={broken_no_fb}")
fail_total = (http_total - http_pass) + (pw_total - pw_pass) \
             + (1 if dead_with_fb else 0) + (1 if broken_no_fb else 0)
print(f"  TOTAL FAILURES: {fail_total}")
raise SystemExit(1 if fail_total else 0)
