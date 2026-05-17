"""Smoke tests for the date-range parameters on the teacher-deliveries
coverage API. Exercises the new resolver + endpoints introduced in
021b04e..3e52a1b.

Run two ways:

  # 1. Direct unit-style — imports app.py and tests the resolver only.
  python scripts/test_deliveries_range.py

  # 2. End-to-end — needs a running local server (python app.py)
  #    and seeded test users.
  python scripts/test_deliveries_range.py --e2e
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

# Force UTF-8 stdout so the Arabic labels we emit don't crash on
# Windows cp1252. Safe no-op on Linux/macOS.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _ok(label: str, expected, actual) -> bool:
    ok = expected == actual
    flag = "PASS" if ok else "FAIL"
    print(f"  [{flag}] {label}")
    if not ok:
        print(f"         expected: {expected!r}")
        print(f"         got:      {actual!r}")
    return ok


def _ok_pred(label: str, predicate: bool, detail: str = "") -> bool:
    flag = "PASS" if predicate else "FAIL"
    print(f"  [{flag}] {label}" + (f"  ({detail})" if detail else ""))
    return predicate


def unit_tests() -> bool:
    print("== Unit tests — _ev_coverage_resolve_range ==")
    sys.path.insert(0, ".")
    import app  # noqa: F401 — exercising importability counts as a test
    resolve = app._ev_coverage_resolve_range
    today = dt.date.today()
    cur_first = today.replace(day=1).isoformat()
    today_iso = today.isoformat()
    cur_ym = today.strftime("%Y-%m")

    all_ok = True

    # Case 1: explicit valid range
    f, t, m, lbl = resolve("2026-04-15", "2026-05-15", None)
    all_ok &= _ok("range 2026-04-15..2026-05-15 from",  "2026-04-15", f)
    all_ok &= _ok("range 2026-04-15..2026-05-15 to",    "2026-05-15", t)
    all_ok &= _ok("range 2026-04-15..2026-05-15 months", ["2026-04", "2026-05"], m)
    all_ok &= _ok_pred("range label non-empty", bool(lbl), f"lbl={lbl!r}")

    # Case 2: legacy ?month=
    f, t, m, lbl = resolve(None, None, "2026-04")
    all_ok &= _ok("legacy month=2026-04 from",   "2026-04-01", f)
    all_ok &= _ok("legacy month=2026-04 to",     "2026-04-30", t)
    all_ok &= _ok("legacy month=2026-04 months", ["2026-04"], m)

    # Case 3: empty everything → current month default
    f, t, m, lbl = resolve(None, None, None)
    all_ok &= _ok("empty defaults from",   cur_first, f)
    all_ok &= _ok("empty defaults to",     today_iso, t)
    all_ok &= _ok("empty defaults months", [cur_ym],  m)

    # Case 4: from > to → silent swap
    f, t, m, lbl = resolve("2026-05-17", "2026-05-01", None)
    all_ok &= _ok("swap from",   "2026-05-01", f)
    all_ok &= _ok("swap to",     "2026-05-17", t)
    all_ok &= _ok("swap months", ["2026-05"],  m)

    # Case 5: same-day range
    f, t, m, lbl = resolve("2026-05-17", "2026-05-17", None)
    all_ok &= _ok("same-day from",   "2026-05-17", f)
    all_ok &= _ok("same-day to",     "2026-05-17", t)
    all_ok &= _ok("same-day months", ["2026-05"],  m)

    # Case 6: range > 365 days clamps from upward
    f, t, m, lbl = resolve("2024-01-01", "2026-05-17", None)
    all_ok &= _ok_pred("365-day cap clamps from",
                       (dt.date.fromisoformat(t) - dt.date.fromisoformat(f)).days == 365,
                       f"actual span: {(dt.date.fromisoformat(t) - dt.date.fromisoformat(f)).days} days")

    # Case 7: malformed inputs fall to current-month default
    f, t, m, lbl = resolve("garbage", "also-bad", None)
    all_ok &= _ok("garbage from",   cur_first, f)
    all_ok &= _ok("garbage to",     today_iso, t)
    all_ok &= _ok("garbage months", [cur_ym],  m)

    # Case 8: multi-month label format
    _, _, _, lbl = resolve("2026-04-15", "2026-05-15", None)
    all_ok &= _ok_pred("multi-month label includes both Arabic month names",
                       ("أبريل" in lbl   # أبريل
                        and "مايو" in lbl),    # مايو
                       f"lbl={lbl!r}")

    # Case 9: same-month label drops year on first piece
    _, _, _, lbl = resolve("2026-05-01", "2026-05-17", None)
    all_ok &= _ok_pred("same-month label has single year token",
                       lbl.count("2026") == 1,
                       f"lbl={lbl!r}")

    return all_ok


def e2e_tests(base: str) -> bool:
    print(f"== E2E tests — {base} ==")
    all_ok = True

    def _get_json(path: str, cookie: str | None = None) -> dict:
        req = urllib.request.Request(base + path)
        if cookie:
            req.add_header("Cookie", cookie)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Login as admin_test (seeded by scripts/seed_test_users.py)
    login_body = urllib.parse.urlencode({
        "username": "admin_test",
        "password": "TestAdmin2026!",
    }).encode()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor()
    )
    try:
        with opener.open(base + "/login", data=login_body, timeout=10) as resp:
            assert resp.status in (200, 302)
    except Exception as e:
        print(f"  [SKIP] login failed: {e}")
        return False

    def _fetch(path: str) -> dict:
        with opener.open(base + path, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    # Smoke 1: default (no params)
    try:
        j = _fetch("/api/monthly-evaluations/teachers/coverage")
        all_ok &= _ok_pred("default fetch returns ok", j.get("ok") is True)
        all_ok &= _ok_pred("default fetch has from/to/range_label",
                           "from" in j and "to" in j and "range_label" in j)
        all_ok &= _ok_pred("default fetch has legacy month/month_label",
                           "month" in j and "month_label" in j)
    except Exception as e:
        print(f"  [FAIL] default fetch raised: {e}")
        all_ok = False

    # Smoke 2: explicit range
    try:
        j = _fetch("/api/monthly-evaluations/teachers/coverage"
                   "?from=2026-04-01&to=2026-05-17")
        all_ok &= _ok("range from",   "2026-04-01", j.get("from"))
        all_ok &= _ok("range to",     "2026-05-17", j.get("to"))
        all_ok &= _ok("range months", ["2026-04", "2026-05"], j.get("months"))
    except Exception as e:
        print(f"  [FAIL] range fetch raised: {e}")
        all_ok = False

    # Smoke 3: legacy ?month=
    try:
        j = _fetch("/api/monthly-evaluations/teachers/coverage?month=2026-04")
        all_ok &= _ok("legacy month from",   "2026-04-01", j.get("from"))
        all_ok &= _ok("legacy month to",     "2026-04-30", j.get("to"))
        all_ok &= _ok("legacy month months", ["2026-04"],  j.get("months"))
    except Exception as e:
        print(f"  [FAIL] legacy month fetch raised: {e}")
        all_ok = False

    return all_ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e2e", action="store_true",
                    help="Also run end-to-end tests against --base.")
    ap.add_argument("--base", default="http://localhost:5000",
                    help="Base URL for e2e tests")
    args = ap.parse_args()

    u_ok = unit_tests()
    e_ok = True
    if args.e2e:
        e_ok = e2e_tests(args.base)

    overall = u_ok and e_ok
    print("")
    print("== Summary ==")
    print(f"  unit:  {'PASS' if u_ok else 'FAIL'}")
    if args.e2e:
        print(f"  e2e:   {'PASS' if e_ok else 'FAIL'}")
    print(f"  total: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
