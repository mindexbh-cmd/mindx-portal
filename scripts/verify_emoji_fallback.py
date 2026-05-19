"""Regression check for the pure-ASCII bold labels in parent
message templates.

Replaces the earlier ▪-fallback test. The labels are now plain
WhatsApp markdown bold (*label:*) — no emoji, no ▪, no
non-BMP characters anywhere in the label strings. This file
keeps the original name (verify_emoji_fallback.py) so callers
that wired it into CI don't break; the assertions are
inverted — we now assert the EMOJIS ARE GONE.

Three layers:
  1. TEACHER_PARENT_MESSAGES_HTML preview JS — 7 new bold
     labels present + 7 old emoji-prefixed labels absent.
  2. _pm_render_message rendered output — same 7 labels in
     the final wire text, no emoji bytes leak through.
  3. Source byte audit — zero U+1F4XX emojis and zero U+25AA
     remain in the message-builder regions.

Run: python scripts/verify_emoji_fallback.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_r = []


def _check(label, ok, detail=""):
    _r.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


NEW_LABELS_FULL = [
    "*المجموعة:*",
    "*التاريخ:*",
    "*المحتوى الذي تم تغطيته:*",
    "*المهارات التي تم التركيز عليها:*",
    "*الكتب المستخدمة:*",
    "*الواجب المنزلي:*",
    "*ملاحظات لولي الأمر:*",
]

# Anything containing one of these emojis followed by the
# matching label is from the previous decoration scheme and
# should not appear anywhere in the message builders.
OLD_PATTERNS = [
    "📚 المجموعة:", "📚 ▪ المجموعة:",
    "📅 التاريخ:",  "📅 ▪ التاريخ:",
    "✏️ المحتوى",   "✏️ ▪ المحتوى",
    "🎯 المهارات",  "🎯 ▪ المهارات",
    "📖 الكتب",     "📖 ▪ الكتب",
    "📝 الواجب",    "📝 ▪ الواجب",
    "📌 ملاحظات",   "📌 ▪ ملاحظات",
]


def main():
    print("Layer 1 — TEACHER_PARENT_MESSAGES_HTML preview JS")
    html = appmod.TEACHER_PARENT_MESSAGES_HTML
    # Find the buildPreviewText region so we don't cross-react
    # with HTML chrome elsewhere.
    start = html.find("buildPreviewText")
    end   = html.find("</script>", start)
    region = html[start:end] if (start >= 0 and end > start) else html
    for lbl in NEW_LABELS_FULL:
        _check(f"preview region has {lbl!r}", lbl in region)
    for old in OLD_PATTERNS:
        _check(f"preview region NO {old!r}", old not in region)

    print("\nLayer 2 — _pm_render_message live rendered output")
    text = appmod._pm_render_message(
        "فاطمة", "أ. زهراء", "مجموعة 01", "2026-05-19",
        "محتوى الدرس", "المهارات", "الكتاب",
        "حل التمارين", "ملاحظات للأهل")
    for lbl in NEW_LABELS_FULL:
        _check(f"rendered text has {lbl!r}", lbl in text)
    for old in OLD_PATTERNS:
        _check(f"rendered text NO {old!r}", old not in text)
    # The signature + brand stay intact regardless of the labels.
    _check("greeting prefix still present",
           "السلام عليكم ولي أمر" in text)
    _check("teacher signature still present",
           "— المعلمة:" in text)
    _check("brand signature still present",
           "مركز مايندكس للتعليم والتدريب" in text)

    print("\nLayer 3 — Byte audit on source (message-builder regions)")
    with open(os.path.abspath(
        os.path.join(_THIS, "..", "app.py")), "rb") as f:
        src = f.read()

    # Find the JS preview builder region by its function name +
    # the Python builder by its def line.
    js_start = src.find(b"function buildPreviewText")
    js_end   = src.find(b"</script>", js_start) if js_start >= 0 else -1
    py_start = src.find(b"def _pm_render_message(")
    # End at the closing `return "\n".join(lines)` of the function
    py_end   = src.find(b"return \"\\n\".join(lines).strip()",
                        py_start) if py_start >= 0 else -1
    if py_end > 0:
        py_end += 80   # include the return line + a margin

    regions = {
        "preview JS":     src[js_start:js_end] if js_start >= 0 else b"",
        "Python builder": src[py_start:py_end] if py_start >= 0 else b"",
    }
    EMOJI_BYTE_PATTERNS = {
        "📚": b"\xf0\x9f\x93\x9a",
        "📅": b"\xf0\x9f\x93\x85",
        "✏":  b"\xe2\x9c\x8f",
        "🎯": b"\xf0\x9f\x8e\xaf",
        "📖": b"\xf0\x9f\x93\x96",
        "📝": b"\xf0\x9f\x93\x9d",
        "📌": b"\xf0\x9f\x93\x8c",
        "U+25AA (▪)": b"\xe2\x96\xaa",
        "U+25A0 (■)": b"\xe2\x96\xa0",
    }
    for region_name, region_bytes in regions.items():
        _check(f"region {region_name!r} found ({len(region_bytes)} bytes)",
               len(region_bytes) > 100)
        for label, pat in EMOJI_BYTE_PATTERNS.items():
            n = region_bytes.count(pat)
            _check(f"  {region_name}: zero {label} bytes",
                   n == 0, f"got {n}")

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        for f in fails:
            print(f"  FAIL: {f[0]}  {f[2]}")
        return 1
    print("ALL OK — pure-ASCII bold labels wired across both files; "
          "zero emoji bytes survive in the message-builder regions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
