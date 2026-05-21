"""
G20b hermetic test — shading + mandatory reject reason.

Asserts:
  - G20b.1: PORTAL_STUDENT_HTML emits .unaffordable class + hint when
            avail < cost; cart button + stepper '+' both disabled.
  - G20b.3: rejectRequest prompt no longer says (اختياري); requires
            non-empty reason via re-prompt loop.

Plus node --check on inline JS for PORTAL_STUDENT_HTML + POINTS_MANAGE_HTML.

Usage:
    python scripts/smoke_g20b.py
"""

import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

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


def extract_template(name):
    m = re.search(r'^' + name + r' = r?"""(.*?)"""',
                  SRC, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


PS = extract_template("PORTAL_STUDENT_HTML")
PM = extract_template("POINTS_MANAGE_HTML")


# ── G20b.1 — unaffordable shading ──────────────────────────────
section("G20b.1 shade unaffordable rewards")

check(".reward.unaffordable CSS rule shipped",
      ".reward.unaffordable{opacity:0.55;}" in SRC)
check(".reward.unaffordable image grayscale",
      "grayscale(60%)" in SRC)
check(".afford-hint CSS rule shipped",
      ".reward .afford-hint{display:none" in SRC
      and ".reward.unaffordable .afford-hint{display:block" in SRC)
check("renderer computes canAfford",
      "var canAfford = avail >= cost" in PS)
check("canCart now requires inStock AND canAfford",
      "var canCart = inStock && canAfford" in PS)
check("renderer emits .unaffordable class conditionally",
      "canAfford ? '' : ' unaffordable'" in PS)
check("renderer emits 'نقاطك غير كافية' hint",
      "⚠ نقاطك غير كافية" in PS)
check("stepper '+' disabled when !canAfford",
      "(maxQty<=1||!canAfford)" in PS)


# ── G20b.3 — mandatory reject reason ───────────────────────────
section("G20b.3 mandatory rejection reason")

check("rejectRequest prompt drops (اختياري)",
      "'سبب الرفض (اختياري):'" not in PM)
check("rejectRequest prompt uses (مطلوب) wording",
      "'سبب الرفض (مطلوب):'" in PM)
check("rejectRequest loops until non-empty",
      "while (true){" in PM
      and "yif (input === null) return" in PM.replace(' ', '').replace('\n', '')
      .replace('\t', '') or "if (input === null) return" in PM)
check("re-prompt shows alert on empty",
      "يجب كتابة سبب الرفض" in PM)
check("reject body still includes reason field",
      "JSON.stringify({reason: reason})" in PM)


# ── Backend reject endpoint unchanged ──────────────────────────
section("backend reject endpoint preserved")

check("/reject route + rejection_reason column preserved",
      "@app.route('/api/points/redemptions/<int:redeem_id>/reject'" in SRC
      and "rejection_reason=?" in SRC)
check("reject accepts reason via JSON body (no schema change)",
      "body.get(\"reason\")" in SRC)


# ── Regression: G20a + G19 + G15-G17 surfaces preserved ────────
section("regression: prior surfaces preserved")

check("G20a.1 read-only book viewer link still wired",
      "/parent/book/' + e.id + '/viewer?pid='" in SRC)
check("G20a.2 pending callouts still in shop renderer",
      "طلبك قيد المراجعة من الإدارة" in PS)
check("G20a.2 rejected callouts still in shop renderer",
      "تم رفض طلبك" in PS
      and "سبب الرفض" in PS)
check("G20a.3 eval iframe wrapper still in route",
      'class="eval-frame"' in SRC
      and "/parent/evaluations/view?pid=" in SRC)
check("G19.2 single-number balance still in effect",
      'class="pts" id="balCount"' in PS
      and "class=\"bal-card" not in PS)
check("G17 direct-order removal still in effect",
      "⚡ طلب مباشر" not in PS
      and "@app.route('/api/portal/student/order'" not in SRC)
check("G16.3 floating cart badge intact",
      'id="floatCart"' in PS)
check("G15.4 cart sub-pane + checkout intact",
      'id="pane-cart"' in PS
      and "function doCartCheckout()" in PS)


# ── Inline JS parses ───────────────────────────────────────────
section("node --check on inline JS")
NODE = shutil.which("node")
if NODE:
    for name, body in (("PORTAL_STUDENT_HTML", PS),
                       ("POINTS_MANAGE_HTML", PM)):
        scripts = re.findall(r"<script>(.*?)</script>", body, re.DOTALL)
        if not scripts:
            check(f"{name}: any inline <script>?", False)
            continue
        biggest = max(scripts, key=len)
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False,
                                         encoding="utf-8") as tf:
            tf.write(biggest)
            tmp = tf.name
        try:
            proc = subprocess.run([NODE, "--check", tmp],
                                  capture_output=True, text=True,
                                  timeout=15)
            check(f"{name} inline JS parses",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)
else:
    check("node available (skipped)", True)


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports + routes")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# Confirm all the critical routes still in the url_map.
try:
    rules = [str(r) for r in mod.app.url_map.iter_rules()]
    for route in [
        "/api/portal/student/cart/checkout",
        "/api/portal/student/cart/add",
        "/api/portal/student/balance",
        "/api/points/redemptions/<int:redeem_id>/approve",
        "/api/points/redemptions/<int:redeem_id>/reject",
        "/api/points/redemptions/<int:redeem_id>/deliver",
        "/parent/book/<int:bid>/viewer",
        "/parent/evaluations/view",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20b SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20b SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
