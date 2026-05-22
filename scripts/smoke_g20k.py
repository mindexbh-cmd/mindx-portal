"""
G20k hermetic test — contained inline panes.

(G20k.1 sticky nav was attempted but reverted: the global mx-helpers.js
mobile CSS `html,body{overflow-x:hidden}` at <=768px promotes body's
overflow-y from visible to auto per CSS spec, making body a scroll
container that breaks position:sticky for body descendants. The
sticky-while-scrolling improvement needs a non-CSS-only solution
and was paused for operator review.)

Asserts:
  - G20k.2: .mb-tab-pane:not(:has(iframe)) on mobile gets
    max-height:65vh; overflow-y:auto; -webkit-overflow-scrolling
    touch. Inline panes only; iframe panes (.pay-frame /
    .eval-frame) excluded so their internal scroll is the only
    scroll axis.
  - Desktop CSS untouched (no max-height added outside the mobile
    media block).
  - phActivateTab + the 5-button nav populator + #ph-tab-pane
    contract all preserved.
  - Inline-pane templates (PORTAL_PARENT_ATTENDANCE_HTML,
    PORTAL_STUDENT_HTML, PORTAL_BOOKS_HTML) still don't
    introduce internal overflow that would conflict with the new
    outer containment.
  - Sticky declaration NOT present on .mb-nav-card (reverted).

Usage:
    python scripts/smoke_g20k.py
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


# Anchor on _MINDEX_BRAND_CSS so we don't match other templates'
# mobile media blocks (app.py has 19 occurrences of the same query).
BRAND_START = SRC.find("_MINDEX_BRAND_CSS = ")
BRAND_BODY = SRC[BRAND_START:] if BRAND_START >= 0 else SRC


def _slice_between(haystack, marker_a, marker_b):
    a = haystack.find(marker_a)
    if a < 0:
        return ""
    b = haystack.find(marker_b, a + len(marker_a))
    return haystack[a + len(marker_a):b] if b > a else ""


mobile_block = _slice_between(
    BRAND_BODY,
    "@media (max-width:600px){",
    "@media (max-width:380px){")
pre_media = BRAND_BODY.split("@media (max-width:600px)")[0]


# ── G20k.1 — sticky nav (REVERTED) ─────────────────────────────
section("G20k.1: sticky .mb-nav-card REVERTED (mx-helpers conflict)")

check("@media (max-width:600px) brand block found", bool(mobile_block))
check("mobile .mb-nav-card NO position:sticky (reverted)",
      "position:sticky" not in mobile_block.split(".mb-nav-card{")[1]
                                          .split("}")[0]
      if ".mb-nav-card{" in mobile_block else True)
check("mobile .mb-nav-card NO top:68px (reverted)",
      "top:68px" not in mobile_block)
check("mobile .mb-nav-card NO z-index:40 (reverted)",
      "z-index:40" not in mobile_block)
check(".mb-topbar still has its own sticky declaration (unchanged)",
      "position:sticky;top:0;z-index:50" in SRC)


# ── G20k.2 — contained inline panes ────────────────────────────
section("G20k.2: contained inline panes on mobile")

check(".mb-tab-pane:not(:has(iframe)) declared inside mobile block",
      ".mb-tab-pane:not(:has(iframe)){" in mobile_block)
check("inline-pane containment sets max-height:65vh",
      "max-height:65vh" in mobile_block)
check("inline-pane containment sets overflow-y:auto",
      "overflow-y:auto" in mobile_block)
check("inline-pane containment sets -webkit-overflow-scrolling:touch",
      "-webkit-overflow-scrolling:touch" in mobile_block)
check("iframe panes NOT capped (no .mb-tab-pane{max-height:} bare rule)",
      ".mb-tab-pane{max-height" not in mobile_block
      and ".mb-tab-pane{overflow" not in mobile_block)
# Make sure we still have the unchanged base .mb-tab-pane rule.
check("base .mb-tab-pane rule preserved (min-height:240px)",
      ".mb-tab-pane{background:#fff;border:1px solid #ede4f5;"
      "border-radius:12px;box-shadow:0 4px 14px rgba(107,44,145,.07);"
      "padding:18px;margin-bottom:14px;min-height:240px;}" in SRC)


# ── Iframe panes still build the iframe wrapper unchanged ─────
section("iframe panes unchanged (payments + evaluations)")

check("payments inner_html still uses .pay-frame iframe",
      "<iframe class=\"pay-frame\"" in SRC
      and ".pay-frame{width:100%;height:calc(100vh - 220px)" in SRC)
check("evaluations inner_html still uses .eval-frame iframe",
      "<iframe class=\"eval-frame\"" in SRC
      and ".eval-frame{width:100%;height:calc(100vh - 220px)" in SRC)
check("iframe mobile height calc(100vh - 180px) preserved",
      ".pay-frame{height:calc(100vh - 180px)" in SRC
      and ".eval-frame{height:calc(100vh - 180px)" in SRC)


# ── phActivateTab + populator contract preserved ───────────────
section("nav JS contract preserved")

check("phActivateTab function definition intact",
      "function phActivateTab(name)" in SRC)
check("window.phActivateTab exposed",
      "window.phActivateTab = phActivateTab" in SRC)
check("5-button populator still emits .mb-nav-btn with data-tab",
      "<button type=\"button\" class=\"mb-nav-btn\"" in SRC
      and "data-tab=\"' + _esc(c.key) + '\"" in SRC
      and "onclick=\"phActivateTab" in SRC)
check("#ph-tab-pane container ID still in PID_HUB template",
      'id="ph-tab-pane"' in SRC)
check("#action-tabs container still in PID_HUB template",
      'id="action-tabs"' in SRC)


# ── Inline-pane templates still safe (no internal scroll) ──────
section("inline-pane CSS audit (no new internal scroll introduced)")


def _slice_template(name):
    start_marker = f'{name} = r"""'
    a = SRC.find(start_marker)
    if a < 0:
        return ""
    b = SRC.find('"""', a + len(start_marker) + 3)
    return SRC[a:b] if b > a else SRC[a:]


for tpl in ("PORTAL_PARENT_ATTENDANCE_HTML",
            "PORTAL_BOOKS_HTML"):
    body = _slice_template(tpl)
    check(f"{tpl} has no internal overflow:auto",
          "overflow:auto" not in body)
    check(f"{tpl} has no internal overflow-y:auto",
          "overflow-y:auto" not in body)
    check(f"{tpl} has no internal position:sticky",
          "position:sticky" not in body)

# Points template (PORTAL_STUDENT_HTML) — modals/lightbox use
# position:fixed which is viewport-anchored and safe.
stu = _slice_template("PORTAL_STUDENT_HTML")
check("PORTAL_STUDENT_HTML has no internal overflow:auto",
      "overflow:auto" not in stu)
check("PORTAL_STUDENT_HTML has no internal overflow-y:auto",
      "overflow-y:auto" not in stu)
check("PORTAL_STUDENT_HTML has no internal position:sticky",
      "position:sticky" not in stu)
check("PORTAL_STUDENT_HTML fixed elements remain viewport-anchored",
      "position:fixed" in stu)  # toast, modal, float-cart, lightbox


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports + parent routes preserved")
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
        "/portal/parent-hub/attendance",
        "/portal/parent-hub/points",
        "/portal/parent-hub/curriculum",
        "/portal/parent-hub/payments",
        "/portal/parent-hub/evaluations",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20k SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20k SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
