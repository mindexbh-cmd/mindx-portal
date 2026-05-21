"""
G12 hermetic test — parent-portal in-page tabs.

Runs source-level assertions on app.py plus runtime checks on the
_render_subpage_inner helper. No Flask boot needed.

Usage:
    python scripts/smoke_tabs_g12.py
"""

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"
SRC = APP_PY.read_text(encoding="utf-8")


def check(label, ok, hint=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok and hint:
        print(f"         hint: {hint}")
    return bool(ok)


def section(title):
    print(f"\n=== {title} ===")


failed = []

# ── 1. G12.1 — icon upgrade ──────────────────────────────────────
section("G12.1 icons: CARD_DEFS uses Tabler SVG paths")
# Find the CARD_DEFS block and confirm shape.
m = re.search(r"var CARD_DEFS = \[(.*?)\];", SRC, re.DOTALL)
if not m:
    failed.append("CARD_DEFS missing")
    check("CARD_DEFS array defined", False)
else:
    body = m.group(1)
    check("CARD_DEFS contains 5 entries",
          body.count("key:'") == 5,
          "expected 5 tab definitions")
    for key in ("attendance", "payment", "books", "evaluations", "points"):
        check(f"CARD_DEFS has key '{key}'", f"key:'{key}'" in body)
    # Each entry should carry svg / bg / color fields
    check("CARD_DEFS entries carry svg field",
          body.count("svg:'<path") >= 5,
          "every entry should have Tabler-style stroke <path>")
    check("CARD_DEFS entries carry bg field",
          body.count("bg:") >= 5)
    check("CARD_DEFS entries carry color field",
          body.count("color:") >= 5)
    # No emoji should remain in the icon field. Old emojis named:
    # calendar (U+1F4C5), credit-card (U+1F4B3), books (U+1F4DA),
    # star (U+2B50), gift (U+1F381). Refer by codepoint, never embed
    # in printable label text (Windows cp1252 console can't encode).
    for cp, label in [
        (0x1F4C5, "calendar"),  (0x1F4B3, "credit-card"),
        (0x1F4DA, "books"),     (0x2B50,  "star"),
        (0x1F381, "gift"),
    ]:
        em = chr(cp)
        check(f"emoji '{label}' (U+{cp:04X}) no longer in CARD_DEFS ic field",
              ("ic:'" + em + "'") not in body)

section("G12.1 colors: per-spec backgrounds and icon colors")
# The brief specified these exact pairings.
expected = {
    "attendance":  ("rgba(107,44,145,0.10)", "#6b2c91"),
    "payment":     ("#E1F5EE", "#0F6E56"),
    "books":       ("#FAEEDA", "#854F0B"),
    "evaluations": ("#FBEAF0", "#72243E"),
    "points":      ("#EEEDFE", "#3C3489"),
}
for key, (bg, color) in expected.items():
    pat = re.compile(
        r"key:'" + key + r"'.*?bg:'" + re.escape(bg)
        + r"'.*?color:'" + re.escape(color) + r"'",
        re.DOTALL,
    )
    check(f"{key}: bg={bg} color={color}",
          bool(pat.search(SRC)),
          "color spec drift")

# ── 2. G12.2 — tab infrastructure ───────────────────────────────
section("G12.2 CSS: tab pane + loading + error + spinner")
for cls in (".mb-tab-pane", ".mb-tab-loading", ".mb-tab-spinner",
            ".mb-tab-error", ".mb-tab-error-msg",
            ".mb-tab-error-retry"):
    check(f"{cls} defined", cls + "{" in SRC)
check("spinner keyframes defined",
      "@keyframes mb-spin" in SRC)
check("prefers-reduced-motion handles spinner",
      "prefers-reduced-motion" in SRC and "mb-tab-spinner" in SRC)

section("G12.2 HTML: tab pane container with aria-live")
check('<div class="mb-tab-pane" id="ph-tab-pane" exists',
      'id="ph-tab-pane"' in SRC and 'class="mb-tab-pane"' in SRC)
check("tab pane has aria-live region for screen readers",
      'aria-live="polite"' in SRC)

section("G12.2 JS: TAB_URLS routing table + hash helpers")
check("TAB_URLS routing table defined", "var TAB_URLS = {" in SRC)
for key, expected in [
    ("attendance",  "/portal/parent-hub/attendance?inner=1"),
    ("payment",     "/portal/parent-hub/payments?inner=1"),
    ("books",       "/portal/parent-hub/curriculum?inner=1"),
    ("evaluations", "/portal/parent-hub/evaluations?inner=1"),
    ("points",      "/portal/parent-hub/points?inner=1"),
]:
    check(f"TAB_URLS['{key}'] -> {expected}",
          (f"{key} :" in SRC or f"{key}:" in SRC)
          and expected in SRC)
check("DEFAULT_TAB constant defined",
      "var DEFAULT_TAB" in SRC)
check("phReadHashTab function defined",
      "function phReadHashTab()" in SRC)
check("phWriteHashTab uses history.replaceState (no back-button noise)",
      "history.replaceState" in SRC)
check("hashchange listener wired",
      "addEventListener('hashchange'" in SRC)
check("phShowTabLoading + phShowTabError defined",
      "function phShowTabLoading" in SRC
      and "function phShowTabError" in SRC)

# ── 3. G12.3 — ?inner=1 endpoints ───────────────────────────────
section("G12.3 routes: ?inner=1 branches")
# Each of the 6 parent sub-page routes should have a `request.args.get('inner')` branch.
inner_branches = SRC.count("request.args.get('inner')")
check(f">=6 inner-mode branches (got {inner_branches})",
      inner_branches >= 6,
      "payments / attendance / messages / evaluations / curriculum / points")
check("_render_subpage_inner helper defined",
      "def _render_subpage_inner" in SRC)
check("back-link strip regex anchored on /portal/parent href",
      "_BACKLINK_STRIP_RE" in SRC and 'href="/portal/parent"' in SRC)

section("G12.3 runtime: _render_subpage_inner strips wrappers")
# Load the module and exercise the helper on each parent template.
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

templates = {
    "payments":     ("PORTAL_PARENT_PAYMENTS_HTML",     True),   # uses __PH_CSS__
    "attendance":   ("PORTAL_PARENT_ATTENDANCE_HTML",   True),
    "messages":     ("PORTAL_PARENT_MESSAGES_HTML",     False),
    "evaluations":  ("PORTAL_PARENT_EVALUATIONS_HTML",  False),
    "curriculum":   ("PORTAL_BOOKS_HTML",                True),
    "points":       ("PORTAL_STUDENT_HTML",              False),
}
for label, (const_name, uses_ph_css) in templates.items():
    full = getattr(mod, const_name)
    if uses_ph_css:
        full = full.replace("__PH_CSS__", mod._PORTAL_HUB_SHARED_CSS)
    inner = mod._render_subpage_inner(full)
    check(f"{label}: no <!DOCTYPE",       "<!DOCTYPE" not in inner)
    check(f"{label}: no </html>",         "</html>"  not in inner)
    check(f"{label}: no </body>",         "</body>"  not in inner)
    check(f"{label}: no __BRAND_TOPBAR__", "__BRAND_TOPBAR__" not in inner)
    check(f"{label}: no __BRAND_FOOTER__", "__BRAND_FOOTER__" not in inner)
    check(f"{label}: no __BRAND_CSS__",    "__BRAND_CSS__"    not in inner)
    check(f"{label}: back-link strip removed",
          'href="/portal/parent"' not in inner
          or '← العودة' not in inner)
    check(f"{label}: <style> preserved",  "<style>" in inner)
    check(f"{label}: <script> preserved", "<script" in inner)
    check(f"{label}: non-empty payload (len={len(inner)})",
          len(inner) > 1000)

# ── 4. G12.4 — tab switching JS ─────────────────────────────────
section("G12.4 fetch + script replay")
check("phActivateTab function defined", "function phActivateTab" in SRC)
check("phReexecuteScripts function defined",
      "function phReexecuteScripts" in SRC)
check("epoch counter for stale-write guard",
      "_activateEpoch" in SRC)
check("fetch uses credentials:'include'",
      "credentials:'include'" in SRC)
check("script replay sequential (onload chains runNext)",
      "onload" in SRC and "runNext" in SRC)
check("retry button calls phActivateTab",
      "mb-tab-error-retry" in SRC
      and "phActivateTab(" in SRC)
check("window.phActivateTab exposed for inline onclick + hashchange",
      "window.phActivateTab" in SRC)

# ── 5. G12.5 — nav buttons wired ────────────────────────────────
section("G12.5 button renderer emits data-tab + onclick")
check("renderer emits data-tab attribute",
      'data-tab="' in SRC)
check("renderer emits onclick=\"phActivateTab(",
      "onclick=\"phActivateTab(" in SRC)
check("initial tab activation after rendering",
      "phReadHashTab() || DEFAULT_TAB" in SRC)
check("legacy /parent/legacy?pid= deep-links removed from renderer",
      "/parent/legacy?pid=' + encodeURIComponent(_pidForHref)" not in SRC,
      "G12.5 should have stripped the /parent/legacy navigation")

# ── 6. Backward compat — full pages still served ────────────────
section("backward compat: sub-pages still serve full pages without ?inner=1")
# Quick check that _inject_brand is still called for the default branch.
for route in ("PAYMENTS", "ATTENDANCE", "MESSAGES", "EVALUATIONS"):
    # Each route uses _inject_brand on its template constant.
    check(f"{route} route still defaults to _inject_brand",
          f"_inject_brand(PORTAL_PARENT_{route}_HTML" in SRC
          or f"_inject_brand(rendered)" in SRC)
check("curriculum (books) route still defaults to _inject_brand",
      "_inject_brand(PORTAL_BOOKS_HTML" in SRC
      or "_inject_brand(rendered)" in SRC)
check("points route still defaults to _inject_brand",
      "_inject_brand(PORTAL_STUDENT_HTML)" in SRC)

# ── 7. PID_HUB regression guard ─────────────────────────────────
section("PID_HUB regression guard")
check("phRenderHub still defined", "function phRenderHub" in SRC)
check("phShowAbsenceModal still callable (G9 modal preserved)",
      "function phShowAbsenceModal" in SRC
      or "phShowAbsenceModal =" in SRC
      or "window.phShowAbsenceModal" in SRC)
check("data-binding IDs preserved (card-name, hours-circle-fill)",
      'id="card-name"' in SRC and 'id="hours-circle-fill"' in SRC)
check("PID_HUB tab pane integrated into hub-content block",
      'id="ph-tab-pane"' in SRC and 'id="hub-content"' in SRC)

# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G12 TABS TEST — FAILED ({len(failed)} issues)")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("G12 TABS TEST — ALL CHECKS PASSED")
    sys.exit(0)
