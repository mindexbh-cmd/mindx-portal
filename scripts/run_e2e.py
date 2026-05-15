"""End-to-end test runner.

Exercises critical user flows against a running app instance:

    python scripts/run_e2e.py                       # → http://localhost:5000
    python scripts/run_e2e.py --base https://prod   # against production

Exit code 0 on full pass; 1 on any failure. Every test takes a
screenshot at its key moment so failures are debuggable from
scripts/screenshots/. Captures 5xx + console errors across the
whole session.

The runner is intentionally light: it does NOT mutate production data
or rely on Arabic UI strings (which are entity-encoded in app.py).
Each test is a function returning (passed: bool, detail: str).
"""
from __future__ import annotations
import argparse
import os
import sys
import traceback
from typing import Callable, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from auto_test import BrowserSession  # noqa: E402


Result = Tuple[str, bool, str, str]  # (name, passed, detail, screenshot_path)


def _safe_run(name: str, fn: Callable[[BrowserSession], str],
              base_url: str) -> Result:
    shot = ""
    try:
        with BrowserSession(base_url=base_url) as s:
            detail = fn(s)
            # Take a final screenshot even on success so a human can
            # eyeball "did the page actually render?"
            shot = s.screenshot(f"e2e_{name}")
            if not s.check_no_500():
                bad = s.failing_responses()
                return (name, False,
                        f"5xx responses: {bad[:5]}", shot)
            errs = s.get_console_errors()
            if errs:
                # Console errors are non-fatal but recorded in detail.
                detail = (detail + f"  [console: {len(errs)} errors, "
                          f"first: {errs[0][:120]!r}]")
            return (name, True, detail, shot)
    except Exception as ex:
        return (name, False, f"{type(ex).__name__}: {ex}", shot or "")


# ── Test flows ─────────────────────────────────────────────────────

def test_health_quick(s: BrowserSession) -> str:
    resp = s.navigate("/api/health")
    if resp is None or resp.status != 200:
        raise AssertionError(f"/api/health status={resp and resp.status}")
    body = s.page.evaluate("() => document.body.innerText")
    if '"ok": true' not in body and '"ok":true' not in body:
        raise AssertionError(f"/api/health body did not report ok: {body[:200]}")
    return "health quick ok"


def test_health_deep(s: BrowserSession) -> str:
    resp = s.navigate("/api/health/deep")
    if resp is None or resp.status != 200:
        raise AssertionError(
            f"/api/health/deep status={resp and resp.status}")
    return "health deep ok"


def test_admin_login_and_home(s: BrowserSession) -> str:
    s.login_as("admin")
    # The post-login landing differs by role configuration. We just
    # require we're off /login and the page rendered without a 5xx.
    if "/login" in s.page.url:
        raise AssertionError("admin still on /login after submit")
    return f"admin landed on {s.page.url}"


def test_admin_loads_dashboard(s: BrowserSession) -> str:
    s.login_as("admin")
    resp = s.navigate("/dashboard")
    if resp is None or resp.status >= 400:
        raise AssertionError(
            f"/dashboard status={resp and resp.status}")
    return "dashboard rendered"


def test_admin_loads_attendance(s: BrowserSession) -> str:
    s.login_as("admin")
    resp = s.navigate("/attendance")
    if resp is None or resp.status >= 400:
        raise AssertionError(
            f"/attendance status={resp and resp.status}")
    return "attendance rendered"


def test_admin_loads_database(s: BrowserSession) -> str:
    s.login_as("admin")
    resp = s.navigate("/database")
    if resp is None or resp.status >= 400:
        raise AssertionError(
            f"/database status={resp and resp.status}")
    return "database rendered"


def test_admin_loads_points_board(s: BrowserSession) -> str:
    s.login_as("admin")
    resp = s.navigate("/points/board")
    # /points/board may 302 when no group is selected. Treat 2xx/3xx
    # as ok, only fail on 4xx/5xx.
    if resp is None or resp.status >= 400:
        raise AssertionError(
            f"/points/board status={resp and resp.status}")
    return "points board rendered"


def test_teacher_login(s: BrowserSession) -> str:
    s.login_as("teacher")
    if "/login" in s.page.url:
        raise AssertionError("teacher still on /login")
    return f"teacher landed on {s.page.url}"


TESTS: List[Tuple[str, Callable[[BrowserSession], str]]] = [
    ("health_quick",        test_health_quick),
    ("health_deep",         test_health_deep),
    ("admin_login",         test_admin_login_and_home),
    ("admin_dashboard",     test_admin_loads_dashboard),
    ("admin_attendance",    test_admin_loads_attendance),
    ("admin_database",      test_admin_loads_database),
    ("admin_points_board",  test_admin_loads_points_board),
    ("teacher_login",       test_teacher_login),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get(
        "E2E_BASE_URL", "http://localhost:5000"),
        help="base URL of the running app")
    ap.add_argument("--smoke", action="store_true",
        help="run only the minimal subset (health + admin login)")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    tests = TESTS
    if args.smoke:
        tests = [t for t in TESTS if t[0] in (
            "health_quick", "admin_login")]

    print(f"[e2e] running {len(tests)} test(s) against {base}")
    results: List[Result] = []
    for name, fn in tests:
        r = _safe_run(name, fn, base)
        results.append(r)
        marker = "PASS" if r[1] else "FAIL"
        print(f"  [{marker}] {r[0]:24s} -- {r[2]}")
        if r[3]:
            print(f"         screenshot: {r[3]}")

    passed = sum(1 for r in results if r[1])
    print(f"\n[e2e] {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
