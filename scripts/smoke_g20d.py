"""
G20d hermetic test — headline formula + delivery checkbox.

Asserts:
  - G20d.1: PORTAL_STUDENT_HTML headline = total − committed (NOT
            total − committed − reserved). 'requested' rows no longer
            reduce the displayed number.
  - G20d.4: POINTS_MANAGE_HTML loadPendingDelivery emits a checkbox
            + button, both wired to pdDeliver. Row stays visible
            after deliver with gray button + checked box.

Plus node --check on PORTAL_STUDENT_HTML + POINTS_MANAGE_HTML inline JS.

Usage:
    python scripts/smoke_g20d.py
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


def extract(name):
    m = re.search(r'^' + name + r' = r?"""(.*?)"""',
                  SRC, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


PS = extract("PORTAL_STUDENT_HTML")
PM = extract("POINTS_MANAGE_HTML")


# ── G20d.1 — headline = total − committed ─────────────────────
section("G20d.1 headline = total − committed")

check("renderer no longer uses 'b.available' for the headline",
      "var headline = (b && b.available !== undefined)" not in PS)
check("renderer uses (b.total - b.committed) for the headline",
      "(b.total - b.committed)" in PS)
check("countUp animates (total - committed), not .available",
      "countUp('balCount'" in PS
      and "_bh.total - _bh.committed" in PS)
check("renderer NOT animating to .available anymore",
      "countUp('balCount', bavail," not in PS)
check("STATE.balance fallback shape preserved",
      "{total:bal, committed:0, reserved:0, available:bal}" in PS)


# ── Internal gates STILL use .available ───────────────────────
section("cart gates still use .available (G16.4 + checkout)")

check("G16.4 proactive cart-aware check still on .available",
      "b.available|0" in PS or "b.available !== undefined" in PS)
check("Backend cart/checkout still gates on bal['available']",
      "bal[\"available\"]" in SRC
      and "summary[\"total\"] > bal[\"available\"]" in SRC)
check("Backend balance helper untouched",
      "def _g15_student_balance(db, sid):" in SRC
      and "status IN ('pending','delivered')" in SRC
      and "status='requested'" in SRC)


# ── G20d.4 — delivery checkbox UX ─────────────────────────────
section("G20d.4 delivery checkbox + row stays visible")

check(".pd-row marker on the outer card",
      'class="card pd-row" data-rid="' in PM)
check(".pd-cb checkbox emitted",
      'class="pd-cb"' in PM
      and 'type="checkbox"' in PM)
check("checkbox + button BOTH wired to pdDeliver",
      "onclick=\"pdDeliver(" in PM
      and PM.count("onclick=\"pdDeliver(") >= 2)
check("checkbox label says 'سُلِّم'",
      "سُلِّم" in PM)
check("button class .pd-btn for handler lookup",
      'class="btn btn-deliver pd-btn"' in PM)
check("button text still '✓ تم التسليم'",
      "✓ تم التسليم" in PM)


# ── G20d.4 — pdDeliver behavior ───────────────────────────────
section("G20d.4 pdDeliver handler logic")

check("pdDeliver locates row by data-rid",
      "querySelector('.pd-row[data-rid=\"'+rid+'\"]')" in PM)
check("pdDeliver finds .pd-btn + .pd-cb children",
      "row.querySelector('.pd-btn')" in PM
      and "row.querySelector('.pd-cb')" in PM)
check("cancel via checkbox un-checks it",
      "source.tagName === 'INPUT'" in PM
      and "source.checked = false" in PM)
check("optimistic lock disables both controls",
      "btn.disabled = true" in PM
      and "cb.disabled  = true" in PM)
check("success keeps row visible (no full reload)",
      "loadPendingDelivery();" not in PM.split("function pdDeliver")[1].split("function _pdRefreshBadge")[0]
      if "function pdDeliver" in PM and "function _pdRefreshBadge" in PM
      else False,
      "after deliver, only the badge should refresh; full loadPendingDelivery would make the row disappear")
check("success sets button to 'مُسلَّم' + gray",
      "✅ مُسلَّم" in PM
      and "#9e9e9e" in PM)
check("success keeps checkbox checked + disabled",
      "cb.checked = true" in PM
      and "cb.disabled = true" in PM)
check("failure path reverts the optimistic lock",
      "btn.disabled=false; btn.textContent='✓ تم التسليم'" in PM)
check("badge refresh still called on success",
      "_pdRefreshBadge();" in PM)


# ── Regression: G20a/G20b/G19/G17/G16/G15 surfaces ────────────
section("regression: prior surfaces preserved")

check("G20a.1 read-only book viewer link still wired",
      "/parent/book/' + e.id + '/viewer?pid='" in SRC)
check("G20a.2 pending callout still in shop renderer",
      "طلبك قيد المراجعة من الإدارة" in PS)
check("G20a.2 rejected callout still in shop renderer",
      "تم رفض طلبك" in PS)
check("G20a.3 eval iframe wrapper still in route",
      'class="eval-frame"' in SRC)
check("G20b.1 .unaffordable shading still in place",
      ".reward.unaffordable{opacity:0.55;}" in SRC)
check("G20b.3 mandatory reject prompt still uses (مطلوب)",
      "'سبب الرفض (مطلوب):'" in PM)
check("G19.2 single-number .pts hero still in place",
      'class="pts" id="balCount"' in PS)
check("G17 direct-order removal still in effect",
      "⚡ طلب مباشر" not in PS
      and "@app.route('/api/portal/student/order'" not in SRC)
check("G16.3 floating cart badge intact",
      'id="floatCart"' in PS)
check("G15.4 cart sub-pane + checkout intact",
      'id="pane-cart"' in PS
      and "function doCartCheckout()" in PS)


# ── node --check ─────────────────────────────────────────────
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


# ── Runtime ──────────────────────────────────────────────────
section("runtime: app.py imports + routes")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# _g15_student_balance arithmetic identity preserved.
try:
    with mod.app.app_context():
        db = mod.get_db()
        out = mod._g15_student_balance(db, 1)
        check(f"_g15_student_balance returns 4-key dict {out}",
              set(out.keys()) == {"total", "committed", "reserved", "available"})
        check("available = total − committed − reserved (formula intact)",
              out["available"] == out["total"] - out["committed"] - out["reserved"])
except Exception as ex:
    check("balance helper runtime probe", False, str(ex))


# ── Summary ──────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20d SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20d SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
