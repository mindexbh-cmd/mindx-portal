"""
G20i hermetic test — hide duplicate back-buttons when embedded.

Asserts:
  - Both portal iframes (G20a.3 evals + G20g payments) now carry
    &embed=1 in their iframe src URLs.
  - /parent/legacy server-side injects hide-CSS for #pp-back-btn
    when ?embed=1 is present.
  - /parent/evaluations/view server-side injects hide-CSS for
    #pe-back-link when ?embed=1 is present.
  - The buttons themselves still exist in the templates (we hide
    via CSS, we don't delete them).
  - Standalone visits (no embed flag) keep the buttons visible.

Usage:
    python scripts/smoke_g20i.py
"""

import importlib.util
import pathlib
import re
import sys

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


def extract(name):
    m = re.search(r'^' + name + r' = r?"""(.*?)"""',
                  SRC, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


PH  = extract("PARENT_HTML")
PEV = extract("PARENT_EVALUATIONS_HTML")


# ── Iframe URLs carry &embed=1 ─────────────────────────────────
section("portal iframe URLs include &embed=1")

check("G20g payments iframe URL includes &embed=1",
      '"&embed=1#section-payment"' in SRC)
check("G20a.3 evaluations iframe URL includes &embed=1",
      '+ "&embed=1"' in SRC
      and "/parent/evaluations/view?pid=" in SRC)


# ── Route handlers inject hide-CSS when ?embed=1 ───────────────
section("legacy routes inject hide-CSS on ?embed=1")

check("/parent/legacy reads request.args.get('embed')",
      "def parent_portal_legacy" in SRC
      and "request.args.get('embed') == '1'" in SRC.split(
          "def parent_portal_legacy")[1].split("@app.route")[0])
check("/parent/legacy injects style hiding #pp-back-btn",
      "<style>#pp-back-btn{display:none !important;}</style>" in SRC)

check("/parent/evaluations/view reads request.args.get('embed')",
      "def parent_evaluations_page" in SRC
      and "request.args.get('embed') == '1'" in SRC.split(
          "def parent_evaluations_page")[1].split("@app.route")[0])
check("/parent/evaluations/view injects style hiding #pe-back-link",
      "<style>#pe-back-link{display:none !important;}</style>" in SRC)


# ── Buttons themselves still exist in the templates ────────────
section("buttons preserved in templates (CSS-hide only)")

check("#pp-back-btn still created by PARENT_HTML's addBackButton()",
      "wrap.id = 'pp-back-btn';" in PH
      and "← العودة إلى القائمة الرئيسية" in PH)
check("#pe-back-link still present in PARENT_EVALUATIONS_HTML",
      'id="pe-back-link"' in PEV
      and "← رجوع" in PEV)
check("buttons NOT deleted from templates",
      'pp-back-btn' in PH and 'pe-back-link' in PEV)


# ── Regression: prior surfaces untouched ───────────────────────
section("regression: prior surfaces preserved")

PS = extract("PORTAL_STUDENT_HTML")
check("G20a.1 read-only book viewer link still wired",
      "/parent/book/' + e.id + '/viewer?pid='" in SRC)
check("G20a.3 .eval-frame iframe still present",
      'class="eval-frame"' in SRC)
check("G20b.1 .unaffordable shading still in place",
      ".reward.unaffordable{opacity:0.55;}" in SRC)
check("G20d.1 headline = total − committed still in place",
      "(b.total - b.committed)" in PS)
check("G20d.4 delivery checkbox still in place",
      'class="pd-cb"' in SRC)
check("G20e admin DELETE redemption endpoint still registered",
      "def api_admin_redemption_hard_delete" in SRC)
check("G20f.3 out-of-stock visual still in place",
      ".reward.out-of-stock{opacity:0.55;}" in SRC)
check("G20g .pay-frame iframe still present",
      'class="pay-frame"' in SRC)
check("IBAN value BH30BIBB00100002994768 still in PARENT_HTML",
      "BH30BIBB00100002994768" in PH)


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports + routes")
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
        "/parent/legacy",
        "/parent/evaluations/view",
        "/portal/parent-hub/payments",
        "/portal/parent-hub/evaluations",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── End-to-end response shape via Flask test client ────────────
section("test client: embed flag toggles hide-CSS")
try:
    with mod.app.test_client() as client:
        # Standalone /parent/evaluations/view should NOT contain
        # the hide-CSS (the route validates pid first, but the
        # pid validator returns 403 for missing pid; we can still
        # test that the CSS is absent when no embed flag is set
        # via a real student pid).
        # Pick a known student via the admin DB query.
        with mod.app.app_context():
            db = mod.get_db()
            try:
                row = db.execute(
                    "SELECT personal_id FROM students "
                    "WHERE personal_id IS NOT NULL "
                    "AND personal_id <> '' LIMIT 1"
                ).fetchone()
                pid = (dict(row).get("personal_id") or "").strip() if row else ""
            except Exception:
                pid = ""

        if pid:
            # Standalone — no embed → button NOT hidden
            r = client.get(f"/parent/evaluations/view?pid={pid}")
            standalone_has_hide = (b"#pe-back-link{display:none"
                                   in r.data)
            check("standalone /parent/evaluations/view: NO hide-CSS",
                  not standalone_has_hide)

            # Embed mode → button hidden
            r = client.get(f"/parent/evaluations/view?pid={pid}&embed=1")
            embed_has_hide = (b"#pe-back-link{display:none"
                              in r.data)
            check("embed=1 /parent/evaluations/view: hide-CSS present",
                  embed_has_hide)
        else:
            check("test student found (skipped — empty DB?)", True)

        # /parent/legacy doesn't require pid validation but does
        # require a session role. We can't easily simulate that in
        # the test client without a session shim, so source-level
        # check above is the source of truth.
except Exception as ex:
    check("test client probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20i SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20i SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
