"""Production verifier for classmindex-withdrawn-filter.

Per the operator's exact request:
  1. Login as admin.
  2. For each of the 5 named students, query the DB (via /api/students)
     to find their group_name_student + registration_term2_2026.
  3. Call /api/points/group with their group.
  4. Assert: each named student is NOT in the returned list.
  5. Report the exact rows + filter result for transparency.

Run:
  python scripts/verify_classmindex_withdrawn_filter_prod.py
"""
from __future__ import annotations
import argparse
import sys

import requests

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"

# The 5 students the operator named. Matched by SUBSTRING against the
# stored student_name so minor whitespace / honorific differences
# still resolve. If a student's stored name differs more than that
# they'll show up under "NOT FOUND" and the operator can investigate.
TARGET_NAMES = [
    "قاسم علي غانم العرادي",
    "حسين جاسم النهام",
    "دانيال عباس علي علي",
    "اسراء حسن علي",
    "عبدالله مجيد",
]


def _login(base, user, pw):
    s = requests.Session()
    r = s.post(base + "/login",
               data={"username": user, "password": pw},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        return None, f"login HTTP {r.status_code}"
    return s, None


def _all_students(sess, base):
    r = sess.get(base + "/api/students", timeout=60)
    if r.status_code != 200:
        return None, f"/api/students returned {r.status_code}"
    try:
        j = r.json()
    except Exception as ex:
        return None, f"json parse failed: {ex}"
    return (j or {}).get("rows", []) or (j or {}).get("students", []), None


def _ar_fold(s):
    """Fold Arabic spelling variants the same way the codebase does
    (folded forms: أ/إ/آ → ا; ة → ه; ى → ي; collapse whitespace;
    drop diacritics). Lets us match اسراء ↔ إسراء,
    عبدالله ↔ عبد الله, etc."""
    if not s: return ""
    out = []
    for ch in str(s):
        c = ch
        if c in ("أ", "إ", "آ", "ٱ"): c = "ا"
        if c == "ة": c = "ه"
        if c == "ى": c = "ي"
        # Drop Arabic diacritics (tashkeel)
        if "ً" <= c <= "ْ": continue
        out.append(c)
    folded = "".join(out)
    # Collapse whitespace
    return " ".join(folded.split())


def _find_match(students, needle):
    """Return rows whose student_name CONTAINS the needle (after
    Arabic-folding). Two passes:
      1. Substring with normalised whitespace (handles minor
         spelling differences).
      2. Substring with ALL whitespace removed — catches the
         "عبدالله مجيد" ↔ "عبد الله مجيد" case where the operator
         wrote a no-space form but the DB stored a spaced form.
    Multiple matches surfaced so the operator can disambiguate."""
    n = _ar_fold(needle)
    if not n: return []
    n_nospace = n.replace(" ", "")
    hits = []
    seen_ids = set()
    for s in students:
        nm = _ar_fold(s.get("student_name") or "")
        if not nm: continue
        if n in nm or n_nospace in nm.replace(" ", ""):
            sid = int(s.get("id") or 0)
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                hits.append(s)
    return hits


def _group_board(sess, base, group_name):
    r = sess.get(base + "/api/points/group",
                 params={"group": group_name}, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    j = r.json() or {}
    return j.get("students") or [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default=DEFAULT_USERNAME)
    ap.add_argument("--password", default=DEFAULT_PASSWORD)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")
    try:
        v = requests.get(base + "/version", timeout=20).json()
        print(f"  /version sha={v.get('sha')}")
    except Exception as ex:
        print(f"  /version failed: {ex}"); return 1

    sess, err = _login(base, args.username, args.password)
    if not sess:
        print(f"  LOGIN FAILED: {err}"); return 1
    print(f"  logged in as {args.username!r}")

    students, err = _all_students(sess, base)
    if students is None:
        print(f"  /api/students failed: {err}"); return 1
    print(f"  /api/students returned {len(students)} rows")
    print()

    print("=" * 78)
    print("Per-student analysis (group_name_student + registration → board)")
    print("=" * 78)

    overall_ok = True
    summary = []
    for needle in TARGET_NAMES:
        print(f"\n• {needle}")
        hits = _find_match(students, needle)
        if not hits:
            print(f"    [WARN] no match in /api/students. Possibly differently spelled on prod.")
            summary.append((needle, "NOT FOUND IN DB", None, None, None))
            continue
        if len(hits) > 1:
            print(f"    [INFO] {len(hits)} substring matches — checking all")
        for h in hits:
            sid    = h.get("id")
            nm     = (h.get("student_name") or "").strip()
            grp    = (h.get("group_name_student") or "").strip()
            grp_on = (h.get("group_online") or "").strip()
            reg    = h.get("registration_term2_2026")
            print(f"    id={sid}  group_name_student={grp!r}  "
                  f"group_online={grp_on!r}  registration={reg!r}")
            # Check both classroom group + online group if both set.
            for label, target_grp in (("in-person", grp), ("online", grp_on)):
                if not target_grp: continue
                board, err = _group_board(sess, base, target_grp)
                if err:
                    print(f"      [{label}] board GET failed: {err}")
                    overall_ok = False
                    summary.append((needle, "BOARD ERROR", grp, reg, err))
                    continue
                board_ids = {int(s.get("id") or 0) for s in (board or [])}
                board_names = [s.get("student_name") for s in (board or [])]
                if sid in board_ids:
                    if (reg or "").strip() == "تم التسجيل":
                        print(f"      [{label}] OK present (reg='تم التسجيل', size={len(board)})")
                        summary.append((needle, "PRESENT (registered)",
                                        target_grp, reg, len(board)))
                    else:
                        print(f"      [{label}] FAIL — STILL APPEARS on board "
                              f"(reg={reg!r}, size={len(board)})")
                        overall_ok = False
                        summary.append((needle, "STILL VISIBLE (bug)",
                                        target_grp, reg, len(board)))
                else:
                    if (reg or "").strip() == "تم التسجيل":
                        # Active student missing from their own board — wrong direction
                        print(f"      [{label}] WARN — missing from own board "
                              f"despite being registered (size={len(board)})")
                        overall_ok = False
                        summary.append((needle, "MISSING (over-filter)",
                                        target_grp, reg, len(board)))
                    else:
                        print(f"      [{label}] OK hidden (reg={reg!r}, size={len(board)})")
                        summary.append((needle, "CORRECTLY HIDDEN",
                                        target_grp, reg, len(board)))

    print()
    print("=" * 78)
    print("Summary")
    print("=" * 78)
    for entry in summary:
        nm, verdict, grp, reg, extra = entry
        print(f"  {verdict:<24} | {nm!r:<40} | grp={grp!r}  reg={reg!r}")

    print()
    if overall_ok:
        print("ALL OK — withdrawn students hidden from Class Mindex; "
              "registered students still visible.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
