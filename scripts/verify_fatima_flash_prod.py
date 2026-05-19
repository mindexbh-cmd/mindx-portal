"""Production-side verifier for fatima-flash-fix (Layers A + B).
Uses real HTTP login (no test_client; this targets the live Render
deployment by default). Confirms:

  Layer A — /dashboard pre-paint <style> contains the lockdown
            keys for Fatima but is empty for admin_test.
  Layer B — the 5 gated endpoints return 403 for Fatima and 200
            for admin_test.

Run:
  python scripts/verify_fatima_flash_prod.py
  python scripts/verify_fatima_flash_prod.py --base http://localhost:5000
"""
from __future__ import annotations
import argparse
import re
import sys

try:
    import requests
except Exception:
    print("requests not installed — pip install requests", file=sys.stderr)
    sys.exit(2)

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"

LAYER_B_ENDPOINTS = [
    "/api/dashboard/recent-activity",
    "/api/dashboard/active-groups-today",
    "/api/dashboard/active-groups-detailed",
    "/api/teacher-deliveries/summary",
    "/api/lessons/missing",
]

EXPECTED_FATIMA_HIDDEN_SUBSET = {
    "sidebar.section_students",
    "sidebar.section_finance",
    "dashboard.alerts_banner",
    "dashboard.recent_activity",
    "dashboard.active_groups_today",
    "dashboard.stat_missing_lessons",
}


def _login(base, username, password):
    s = requests.Session()
    s.headers.update({"User-Agent": "verify_fatima_flash_prod"})
    r = s.post(base + "/login",
               data={"username": username, "password": password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        return None, f"login HTTP {r.status_code}: {r.text[:200]!r}"
    return s, None


def _hidden_keys_from_html(html):
    head_idx = html.find("</head>")
    head_html = html[:head_idx] if head_idx >= 0 else html
    blocks = re.findall(r"<style>([^<]*?display:none[^<]*?)</style>",
                        head_html, re.IGNORECASE | re.DOTALL)
    keys = []
    for b in blocks:
        for m in re.finditer(r'data-button-key="([^"]+)"', b):
            keys.append(m.group(1))
    return keys


def _check_layer_a(label, sess, base, expect_subset, expect_empty):
    r = sess.get(base + "/dashboard", allow_redirects=False, timeout=30)
    if r.status_code != 200:
        print(f"  [{label}] /dashboard → HTTP {r.status_code} (not 200)")
        return False
    html = r.text
    keys = _hidden_keys_from_html(html)
    body_idx = html.find("<body>")
    style_idx = html.find("[data-button-key=")
    placement = "before <body>" if 0 <= style_idx < body_idx else ("AFTER <body> (BAD)" if style_idx >= 0 else "n/a (no style)")
    if expect_empty:
        if keys:
            print(f"  [{label}] /dashboard FAIL — expected empty style, got {len(keys)} keys: {keys[:5]}…")
            return False
        print(f"  [{label}] /dashboard OK — no pre-paint style (as expected)")
        return True
    missing = (expect_subset or set()) - set(keys)
    if missing:
        print(f"  [{label}] /dashboard FAIL — missing keys: {sorted(missing)}")
        return False
    print(f"  [{label}] /dashboard OK — {len(set(keys))} keys hidden, placement={placement}")
    return placement == "before <body>"


def _check_layer_b(label, sess, base, expect_403):
    all_ok = True
    for ep in LAYER_B_ENDPOINTS:
        r = sess.get(base + ep, allow_redirects=False, timeout=30)
        want = 403 if expect_403 else 200
        ok = (r.status_code == want)
        all_ok = all_ok and ok
        verdict = f"OK ({r.status_code})" if ok else f"FAIL got {r.status_code}, want {want}"
        print(f"  [{label}] {ep} → {verdict}")
    return all_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--fatima-user", default="930909151")
    ap.add_argument("--fatima-pass", default="930909151")
    ap.add_argument("--admin-user", default="admin")
    ap.add_argument("--admin-pass", default="admin123")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")

    # Quick deploy probe.
    try:
        v = requests.get(base + "/version", timeout=15).json()
        print(f"  /version sha={v.get('sha')} routes={v.get('total_routes')}")
    except Exception as ex:
        print(f"  /version FAILED: {ex}")
        return 1

    # Fatima session.
    print("\nFatima Ibrahim:")
    f_sess, err = _login(base, args.fatima_user, args.fatima_pass)
    if not f_sess:
        print(f"  LOGIN FAILED: {err}")
        return 1
    f_a = _check_layer_a("fatima", f_sess, base,
                         EXPECTED_FATIMA_HIDDEN_SUBSET, expect_empty=False)
    print("\nFatima — Layer B (expect 403 on all 5):")
    f_b = _check_layer_b("fatima", f_sess, base, expect_403=True)

    # Admin session.
    print("\nAdmin:")
    a_sess, err = _login(base, args.admin_user, args.admin_pass)
    if not a_sess:
        print(f"  LOGIN FAILED: {err}")
        return 1
    a_a = _check_layer_a("admin", a_sess, base, None, expect_empty=True)
    print("\nAdmin — Layer B (expect 200 on all 5):")
    a_b = _check_layer_b("admin", a_sess, base, expect_403=False)

    print()
    if f_a and f_b and a_a and a_b:
        print("ALL OK — prod deploy verified: flash killed for Fatima, "
              "5 endpoints return 403, admin works untouched.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
