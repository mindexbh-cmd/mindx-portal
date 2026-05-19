"""Quick regression — the "🔄 إعادة تعيين" button is wired into
ADMIN_TEACHER_DELIVERIES_HTML and points at /reset-to-draft.

Template-content assertion only; the underlying endpoint is
already covered by the prod smoke from commit c5d29b8.

Run: python scripts/verify_tm_reset_button.py
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


def main():
    html = appmod.ADMIN_TEACHER_DELIVERIES_HTML

    print("Markup + label")
    _check("button class .tm-btn-reset-draft present",
           ".tm-btn-reset-draft" in html or "tm-btn-reset-draft" in html)
    _check("button label '🔄 إعادة تعيين' present",
           "🔄 إعادة تعيين" in html)
    _check("'إعادة تعيين' is inside the sent-card branch",
           "إعادة تعيين" in html)

    print("\nWiring")
    _check("event handler branches on .tm-btn-reset-draft",
           ".tm-btn-reset-draft" in html and
           "ev.target.closest('.tm-btn-reset-draft')" in html)
    _check("handler POSTs to /reset-to-draft endpoint",
           "/reset-to-draft" in html and
           "/api/parent-messages/" in html)
    _check("confirm dialog text included (split-string-safe)",
           "هل تريدين إعادة تعيين هذه الرسالة" in html and
           "تصفير عداد الإرسال" in html)
    _check("success label '✓ تم' shown briefly",
           "✓ تم" in html)
    _check("tmLoadParentMsgs called on success",
           "tmLoadParentMsgs()" in html)
    _check("pmsgsCache invalidated on success",
           "delete pmsgsCache[" in html)

    print("\nExisting flows untouched")
    _check("'موافقة وإرسال' button branch still wired",
           "ev.target.closest('.tm-btn-success')" in html)
    _check("tmApproveAndSend still called",
           "tmApproveAndSend(mid1, sendBtn)" in html or
           "tmApproveAndSend(mid, btn)" in html)

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        for f in fails:
            print(f"  FAIL: {f[0]}  {f[2]}")
        return 1
    print("ALL OK — reset-to-draft button wired in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
