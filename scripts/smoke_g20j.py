"""
G20j hermetic test — wording rename + mobile-prominent nav.

Asserts:
  - Fix A: "إكمال الدورة" removed from the progress-title in
    the parent hub; replaced with "الساعات المكتملة" inside the
    same <div class="mb-progress-title"> element. No calculation
    or overrun-banner change.
  - Fix B: Mobile-only CSS (inside @media max-width:600px) makes
    #hub-content a flex column with .mb-nav-card ordered FIRST
    (order) above .mb-card and .mb-tab-pane. (Mobile order was
    swapped in G20l 2026-05-22 — student-card now order:1, nav
    order:2, tab-pane order:3 — see smoke_g20l.py for the current
    contract.)
  - Fix B: Mobile-only visual prominence boost — .mb-nav-card gets
    a purple gradient/border/shadow, .mb-nav-hint becomes large
    purple bold, .mb-nav-btn bumps padding + icon size + label.
  - Desktop CSS (the base .mb-nav-* rules outside any media query)
    is UNCHANGED — no order properties added, original colors kept.
  - JS populator still emits .mb-nav-btn class (no contract drift).
  - The #action-tabs container ID + 5-button JS pipeline preserved.

Usage:
    python scripts/smoke_g20j.py
"""

import importlib.util
import pathlib
import re
import sys

# Force UTF-8 stdout so Arabic labels in print() don't crash on
# Windows cp1252 consoles. The other G20 smoke scripts get away
# with the default because they avoid Arabic in labels; we keep
# Arabic in assertion logic only and ASCII-fy the print labels.
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


# ── Fix A: wording rename ──────────────────────────────────────
section("Fix A: progress-title wording")

check('old wording "ikmaal al-dawra" removed from app.py',
      "إكمال الدورة" not in SRC)
check('new wording "al-saaat al-muktamila" present in progress-title',
      '<div class="mb-progress-title">الساعات المكتملة</div>' in SRC)
check('overrun banner "akhadha ziyada" still present (unchanged)',
      "أخذ زيادة" in SRC)
check('progress circle SVG IDs preserved (no calc change)',
      'id="hours-circle-fill"' in SRC
      and 'id="hours-circle-pct"' in SRC
      and 'id="hours-circle-cap"' in SRC)


# ── Fix B: mobile-only reorder ─────────────────────────────────
section("Fix B: mobile-only flex reorder")

# Pull out the @media (max-width:600px) block INSIDE _MINDEX_BRAND_CSS
# specifically — app.py has 19 occurrences of that media query across
# many templates. Anchor on _MINDEX_BRAND_CSS so we don't match an
# unrelated block.
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
check("@media (max-width:600px) brand block found", bool(mobile_block))

check("mobile makes #hub-content a flex column",
      "#hub-content{display:flex;flex-direction:column;}" in mobile_block)
# Mobile flex order — values updated by G20l (operator swap so the
# student-card appears FIRST and the nav directly below it). The
# G20j.2 reorder mechanism (making #hub-content a flex column on
# mobile so order works) is still in place — only the two order
# integers flipped. .mb-tab-pane stays at order:3.
check("mobile gives .mb-card order:1 (first — G20l swap)",
      "#hub-content > .mb-card{order:1;}" in mobile_block)
check("mobile gives .mb-nav-card order:2 (second — G20l swap)",
      "#hub-content > .mb-nav-card{order:2;}" in mobile_block)
check("mobile gives .mb-tab-pane order:3 (last)",
      "#hub-content > .mb-tab-pane{order:3;}" in mobile_block)


# ── Fix B: mobile prominence boost ─────────────────────────────
section("Fix B: mobile prominence boost")

check("mobile .mb-nav-card gets purple gradient background",
      "linear-gradient(180deg,#faf5ff" in mobile_block)
check("mobile .mb-nav-card gets thicker purple-tinted border",
      "border:1px solid #d6c2e9" in mobile_block)
check("mobile .mb-nav-card gets stronger shadow",
      "box-shadow:0 6px 18px rgba(107,44,145,.12)" in mobile_block)
check("mobile .mb-nav-hint goes large + purple + bold + centered",
      ".mb-nav-hint{font-size:14px;color:var(--mindex-purple);"
      "font-weight:800;letter-spacing:.3px;margin:0 0 12px;"
      "text-align:center;}" in mobile_block)
check("mobile .mb-nav-btn padding bumped to 14px",
      ".mb-nav-btn{padding:14px 4px" in mobile_block)
check("mobile .mb-nav-btn label bumped to 11px/700",
      ".mb-nav-btn .mb-nav-lbl{font-size:11px;font-weight:700;}"
      in mobile_block)


# ── Desktop CSS untouched ──────────────────────────────────────
section("desktop CSS unchanged")

# The base rules live OUTSIDE the @media blocks.
# We assert the original padding/colors are still there.
check("desktop .mb-nav-card original padding preserved (14px)",
      ".mb-nav-card{background:#fff;border-radius:12px;padding:14px;"
      "margin-bottom:14px;box-shadow:0 4px 14px rgba(107,44,145,.07);"
      "border:1px solid #ede4f5;}" in SRC)
check("desktop .mb-nav-hint original style preserved (11px, #888)",
      ".mb-nav-hint{font-size:11px;color:#888;font-weight:700;"
      "margin:0 0 10px;}" in SRC)
check("desktop .mb-nav-grid original 5-column grid preserved",
      ".mb-nav-grid{display:grid;grid-template-columns:repeat(5,1fr);"
      "gap:8px;}" in SRC)
check("desktop .mb-nav-btn original padding preserved (16px 6px)",
      ".mb-nav-btn{background:#fff;color:#212121;border:1px solid #ede4f5;"
      "border-radius:10px;padding:16px 6px;" in SRC)
# Desktop has no order properties on #hub-content children.
# Search the brand-CSS section BEFORE its first @media block.
pre_media = BRAND_BODY.split("@media (max-width:600px)")[0]
check("desktop #hub-content has NO flex/order overrides",
      "#hub-content > .mb-nav-card{order:" not in pre_media
      and "#hub-content{display:flex" not in pre_media)


# ── JS contract preserved ──────────────────────────────────────
section("JS populator contract preserved")

check("#action-tabs container still in PID_HUB template",
      'id="action-tabs"' in SRC)
check("JS populator still emits .mb-nav-btn class",
      "'<button type=\"button\" class=\"mb-nav-btn\"" in SRC
      or "class=\"mb-nav-btn\"" in SRC)
check("five-button JS pipeline (mb-nav-btn querySelectorAll) intact",
      "#action-tabs .mb-nav-btn" in SRC)


# ── Tiny-phone breakpoint ──────────────────────────────────────
section("@media (max-width:380px) tightens proportionally")

tiny_block = _slice_between(
    BRAND_BODY,
    "@media (max-width:380px){",
    "@media (prefers-reduced-motion:reduce){")
check("@media (max-width:380px) brand block found", bool(tiny_block))
check("tiny .mb-nav-hint stays readable (13px)",
      ".mb-nav-hint{font-size:13px;}" in tiny_block)
check("tiny .mb-nav-btn padding tightens",
      ".mb-nav-btn{padding:12px 3px;}" in tiny_block)
check("tiny .mb-nav-btn icon shrinks",
      ".mb-nav-btn .mb-nav-ic{width:34px;height:34px;}" in tiny_block)


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports + parent route preserved")
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
        "/parent",
        "/parent/legacy",
        "/portal/parent-hub",
    ]:
        check(f"route preserved: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20j SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20j SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
