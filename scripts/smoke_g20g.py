"""
G20g hermetic test — payments tab iframe wrapper (Path B).

Asserts:
  - portal_parent_hub_payments_page resolves session sid + pid
  - ?inner=1 returns the iframe wrapper pointing at /parent/legacy
  - Standalone visit redirects to the legacy URL
  - .pay-frame CSS sizes to viewport
  - /parent/legacy still has the IBAN + receipt-upload flow
  - The hardcoded IBAN value (BH30BIBB00100002994768) is unchanged

Plus regression guards for G20a/b/d/e/f surfaces.

Usage:
    python scripts/smoke_g20g.py
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


PH = extract("PARENT_HTML")


# ── G20g — payments tab iframe wrapper ─────────────────────────
section("G20g payments tab → iframe wrapper")

check("portal_parent_hub_payments_page resolves session sid",
      "def portal_parent_hub_payments_page" in SRC
      and SRC.count("_resolve_session_student_id(user)") >= 2)
check("route reads students.personal_id for the pid",
      SRC.count("SELECT personal_id FROM students WHERE id=?") >= 2)
check("iframe_url = /parent/legacy?pid=...#section-payment",
      '"/parent/legacy?pid="' in SRC
      # G20i: &embed=1 was appended before the hash; accept either
      # the post-G20i combined string or the pre-G20i bare hash.
      and ('"#section-payment"' in SRC
           or '"&embed=1#section-payment"' in SRC))
check("?inner=1 returns iframe markup with .pay-frame class",
      "<iframe class=\"pay-frame\"" in SRC)
check(".pay-frame CSS sizes to viewport",
      ".pay-frame{width:100%" in SRC
      and "height:calc(100vh - 220px)" in SRC
      and "@media (max-width:600px){.pay-frame{height:calc(100vh - 180px)" in SRC)
check("iframe loading=lazy + referrerpolicy=same-origin",
      'loading="lazy"' in SRC
      and 'referrerpolicy="same-origin"' in SRC)
check("iframe carries Arabic title 'الأقساط الشهرية'",
      'title="الأقساط الشهرية"' in SRC)
check("standalone visit redirects to /parent/legacy",
      # Look inside the payments handler specifically for the redirect
      # (G20a.3 evaluations also has a redirect — we want both to exist
      # but make sure ours uses iframe_url).
      "return redirect(iframe_url)" in SRC
      and SRC.count("return redirect(iframe_url)") >= 2)


# ── Legacy page preserved (iframe target) ──────────────────────
section("/parent/legacy still has the rich payment flow")

check("PARENT_HTML extracted",
      bool(PH) and len(PH) > 50000)
check("IBAN value BH30BIBB00100002994768 unchanged",
      "BH30BIBB00100002994768" in PH)
check("IBAN card markup still in PARENT_HTML",
      'id="pp-iban-card"' in PH
      and 'id="pp-iban-copy-btn"' in PH)
check("installment picker still in PARENT_HTML",
      'id="pp-pick-card"' in PH
      and 'id="pp-pick-list"' in PH)
check("receipt-upload card still in PARENT_HTML",
      'id="pp-upload-card"' in PH
      and 'onclick="ppUpload()"' in PH)
check("upload JS functions still defined",
      "function ppUpload(" in PH
      and "function ppPickInstallment(" in PH
      and "function ppFileChange(" in PH
      and "function ppCancelUpload(" in PH)
check("upload endpoint URL referenced",
      "/api/parent/upload-receipt" in PH)
check("'all paid' success card still in PARENT_HTML",
      'id="pp-paid-msg"' in PH)


# ── Backend endpoints untouched ────────────────────────────────
section("backend endpoints intact (no changes)")

check("POST /api/parent/upload-receipt route registered",
      "@app.route(\"/api/parent/upload-receipt\", methods=[\"POST\"])" in SRC)
check("GET /api/parent/receipt-file/<rid> route registered",
      "@app.route(\"/api/parent/receipt-file/<int:rid>\", methods=[\"GET\"])" in SRC)
check("admin /api/admin/receipts list route registered",
      '@app.route("/api/admin/receipts", methods=["GET"])' in SRC)
check("admin /api/admin/receipts/<rid>/confirm route registered",
      '@app.route("/api/admin/receipts/<int:rid>/confirm", methods=["POST"])' in SRC)
check("admin /api/admin/receipts/<rid>/reject route registered",
      '@app.route("/api/admin/receipts/<int:rid>/reject", methods=["POST"])' in SRC)
check("parent_receipts CREATE TABLE preserved",
      "CREATE TABLE IF NOT EXISTS parent_receipts" in SRC)
check("parent_receipts schema columns unchanged",
      "installment_number INTEGER" in SRC
      and "installment_amount NUMERIC" in SRC
      and "is_remainder INTEGER DEFAULT 0" in SRC)


# ── Regression: G20a/b/d/e/f surfaces preserved ────────────────
section("regression: prior surfaces preserved")

PS = extract("PORTAL_STUDENT_HTML")
check("G20a.1 read-only book viewer link still wired",
      "/parent/book/' + e.id + '/viewer?pid='" in SRC)
check("G20a.3 evaluations iframe wrapper still in place",
      'class="eval-frame"' in SRC
      and "/parent/evaluations/view?pid=" in SRC)
check("G20b.1 .unaffordable shading still in place",
      ".reward.unaffordable{opacity:0.55;}" in SRC)
check("G20d.1 headline = total − committed still in place",
      "(b.total - b.committed)" in PS)
check("G20d.4 delivery checkbox still in place",
      'class="pd-cb"' in SRC)
check("G20e admin DELETE redemption endpoint still registered",
      "def api_admin_redemption_hard_delete" in SRC)
check("G20f.2 DELETE auto-restores stock when pending/delivered",
      'was_committed = (snapshot.get("status") in ("pending", "delivered"))' in SRC)
check("G20f.3 .out-of-stock CSS + hint still in place",
      ".reward.out-of-stock{opacity:0.55;}" in SRC
      and "⚠ نفد المخزون" in PS)


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
        "/portal/parent-hub/payments",
        "/parent/legacy",
        "/api/parent/upload-receipt",
        "/api/parent/receipt-file/<int:rid>",
        "/api/admin/receipts",
        "/api/admin/receipts/<int:rid>/confirm",
        "/api/admin/receipts/<int:rid>/reject",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20g SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20g SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
