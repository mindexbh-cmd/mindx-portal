"""Regression check for the emoji-fallback symbol (▪) on the 7
parent-message labels. Confirms both files (preview JS + Python
builder) contain identical post-edit labels, AND that the
rendered output of _pm_render_message ends up with the ▪ after
each emoji."""
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


# The 7 expected post-edit labels — must appear identically in
# both source-file locations. (We don't grep, we read the
# attribute strings out of the loaded module so it survives
# any future reformatting.)
EXPECTED_LABELS = [
    "📚 ▪ المجموعة: ",
    "📅 ▪ التاريخ: ",
    "✏️ ▪ المحتوى الذي تم تغطيته:",
    "🎯 ▪ المهارات التي تم التركيز عليها:",
    "📖 ▪ الكتب المستخدمة:",
    "📝 ▪ الواجب المنزلي:",
    "📌 ▪ ملاحظات لولي الأمر:",
]

OLD_LABELS_NO_BULLET = [
    "📚 المجموعة: ",
    "📅 التاريخ: ",
    "✏️ المحتوى الذي تم تغطيته:",
    "🎯 المهارات التي تم التركيز عليها:",
    "📖 الكتب المستخدمة:",
    "📝 الواجب المنزلي:",
    "📌 ملاحظات لولي الأمر:",
]


def main():
    # File 1: TEACHER_PARENT_MESSAGES_HTML preview JS
    print("File 1 — TEACHER_PARENT_MESSAGES_HTML preview JS:")
    html = appmod.TEACHER_PARENT_MESSAGES_HTML
    for lbl in EXPECTED_LABELS:
        _check(f"contains {lbl!r}", lbl in html)
    for old in OLD_LABELS_NO_BULLET:
        _check(f"no bare {old!r} (without ▪)", old not in html,
               "stale bare label still present" if old in html else "")

    # File 2: rendered output of the server builder. Exercising
    # the actual function — proves the labels reach the wire.
    print("\nFile 2 — _pm_render_message rendered output:")
    text = appmod._pm_render_message(
        "فاطمة", "أ. زهراء", "مجموعة 01", "2026-05-19",
        "محتوى الدرس", "المهارات", "الكتاب",
        "حل التمارين", "ملاحظات للأهل")
    for lbl in EXPECTED_LABELS:
        # The rendered text uses the labels with their following
        # value (e.g. '📚 ▪ المجموعة: مجموعة 01'). Trim trailing
        # space on the lookup so we match both cases.
        needle = lbl.rstrip()
        _check(f"renders {needle!r}", needle in text)
    for old in OLD_LABELS_NO_BULLET:
        needle = old.rstrip()
        # Old needle MUST NOT appear as a prefix on a line. Use
        # substring check: the new labels contain the emoji +
        # space + '▪' so the OLD substring "📚 المجموعة:" should
        # NOT appear anywhere (we replaced the bare form).
        _check(f"no stale {needle!r} in rendered text",
               needle not in text)

    # Byte-level check: every emoji followed by U+25AA (e2 96 aa)
    print("\nByte-level — U+25AA verification:")
    with open(os.path.abspath(
        os.path.join(_THIS, "..", "app.py")), "rb") as f:
        src = f.read()
    EMOJI_PREFIXES = {
        "📚": b"\xf0\x9f\x93\x9a \xe2\x96\xaa",
        "📅": b"\xf0\x9f\x93\x85 \xe2\x96\xaa",
        "✏": b"\xe2\x9c\x8f\xef\xb8\x8f \xe2\x96\xaa",
        "🎯": b"\xf0\x9f\x8e\xaf \xe2\x96\xaa",
        "📖": b"\xf0\x9f\x93\x96 \xe2\x96\xaa",
        "📝": b"\xf0\x9f\x93\x9d \xe2\x96\xaa",
        "📌": b"\xf0\x9f\x93\x8c \xe2\x96\xaa",
    }
    for emoji, prefix in EMOJI_PREFIXES.items():
        n = src.count(prefix)
        _check(f"emoji {emoji} → ▪ byte sequence appears 2× (one per file)",
               n == 2, f"got {n}")
    _check("no U+25A0 (■, large square) in app.py",
           src.count(b"\xe2\x96\xa0") == 0)

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        for f in fails:
            print(f"  FAIL: {f[0]}  {f[2]}")
        return 1
    print("ALL OK — ▪ fallback symbol wired across both files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
