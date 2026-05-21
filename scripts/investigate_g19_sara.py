"""G19.1 — read-only investigation of سارة السيد هادي's 80-point gap.

Hits admin-side endpoints with admin_test credentials. No mutations.
Reports raw data so the operator can decide what (if anything) to fix.

Usage:
    python scripts/investigate_g19_sara.py [--base https://...]
"""
import argparse
import json
import sys

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://mindx-portal-1.onrender.com")
    args = ap.parse_args()
    BASE = args.base.rstrip("/")

    s = requests.Session()
    s.headers.update({"User-Agent": "g19-investigate/1.0"})
    r = s.post(BASE + "/login",
               data={"username": "admin_test",
                     "password": "TestAdmin2026!"},
               allow_redirects=True, timeout=30)
    print(f"\n=== admin login: {r.status_code} url={r.url} ===\n")

    # 1. Find سارة السيد هادي in the students table.
    r = s.get(BASE + "/api/students", timeout=30)
    if r.status_code != 200:
        print(f"FATAL: /api/students returned {r.status_code}")
        return 1
    j = r.json()
    rows = j.get("students", []) if isinstance(j, dict) else j
    # Look for ANY row containing 'سارة' and 'هادي' (or 'سارة السيد')
    matches = []
    for row in rows:
        name = (row.get("student_name") or "").strip()
        if "سارة" in name and ("هادي" in name or "السيد" in name):
            matches.append(row)
    print(f"=== students.student_name LIKE '%سارة … هادي%' — found {len(matches)} ===\n")
    for m in matches:
        print(f"  id={m.get('id'):<6} name={(m.get('student_name') or ''):<40} "
              f"group={(m.get('group_name_student') or ''):<20} "
              f"pid={m.get('personal_id')}")
    if not matches:
        print("  (no rows matched — operator may have a different spelling)")
        # Try a looser match
        for row in rows[:5]:
            print(f"  sample row: {row}")
        return 1

    # Multiple matches? List all student_ids; operator can flag which one.
    sids = [m["id"] for m in matches]
    print(f"\n=== probing each matched student_id: {sids} ===")

    for sid in sids:
        name = next((m["student_name"] for m in matches
                     if m["id"] == sid), "(?)")
        print(f"\n────────────────────────────────────────────────")
        print(f"  STUDENT id={sid} name={name!r}")
        print(f"────────────────────────────────────────────────")

        # 2. Balance + recent 10 events
        r = s.get(BASE + f"/api/points/student/{sid}", timeout=30)
        if r.status_code == 200:
            d = r.json()
            print(f"  /api/points/student/{sid}:")
            print(f"    balance: {d.get('balance')}")
            print(f"    recent_events: {len(d.get('events', []))}")
            for ev in d.get("events", [])[:20]:
                print(f"      • {(ev.get('awarded_at') or '')[:19]} "
                      f"{int(ev.get('points_value') or 0):+5d}  "
                      f"behavior={ev.get('behavior_name')!r:<30} "
                      f"by={ev.get('awarded_by_name')!r}")
        else:
            print(f"  /api/points/student/{sid} → {r.status_code}")

        # 3. Per-student report (all-time + week + month + behavior dist + 12-week sparkline)
        r = s.get(BASE + f"/api/points/reports/student/{sid}", timeout=30)
        if r.status_code == 200:
            d = r.json()
            tot = d.get("totals", {})
            print(f"  /api/points/reports/student/{sid}:")
            print(f"    totals: all_time={tot.get('all_time')} "
                  f"month={tot.get('month')} week={tot.get('week')}")
            print(f"    balance (from helper): {d.get('balance')}")
            print(f"    group_avg: {d.get('group_avg')}  trend: {d.get('trend')}")
            bhv = d.get("behaviors", [])
            print(f"    behavior distribution ({len(bhv)} rows):")
            running = 0
            for b in bhv:
                cnt = int(b.get("cnt") or 0)
                pts = int(b.get("pts") or 0)
                running += pts
                print(f"      • {(b.get('behavior_name') or '(null)'):<35} "
                      f"count={cnt:<3} sum={pts:+5d}")
            print(f"    behavior sum (top 10): {running}")
            print(f"    12-week sparkline:")
            for w in d.get("weekly", []):
                bar = "█" * min(40, int((w.get("points") or 0) / 2))
                print(f"      {w.get('week_end')}  {int(w.get('points') or 0):+4d}  {bar}")
        else:
            print(f"  /api/points/reports/student/{sid} → {r.status_code}")

        # 4. Redemptions for this student (admin endpoint).
        r = s.get(BASE + f"/api/points/redemptions?student_id={sid}", timeout=30)
        if r.status_code == 200:
            redemptions = r.json().get("rows", [])
            print(f"  redemptions for student_id={sid}: {len(redemptions)} rows")
            for rd in redemptions:
                print(f"    • id={rd.get('id')} "
                      f"{(rd.get('redeemed_at') or '')[:19]} "
                      f"status={rd.get('status')!r:<14} "
                      f"reward={rd.get('reward_name')!r:<30} "
                      f"cost={rd.get('points_spent')} "
                      f"source={rd.get('request_source')!r}")
        else:
            print(f"  /api/points/redemptions?student_id={sid} → {r.status_code}")

        # 5. History (with student_name fuzzy match)
        # The history endpoint accepts student_id directly.
        r = s.get(BASE + f"/api/points/history?student_id={sid}&limit=200",
                  timeout=30)
        if r.status_code == 200:
            hist = r.json().get("rows", [])
            print(f"  /api/points/history (all-statuses) for sid={sid}: "
                  f"{len(hist)} rows")
            for h in hist[:30]:
                print(f"    • {(h.get('redeemed_at') or '')[:19]} "
                      f"status={h.get('status')!r:<14} "
                      f"reward={h.get('reward_name')!r:<30} "
                      f"cost={h.get('points_spent')} "
                      f"source={h.get('request_source')!r} "
                      f"by={h.get('delivered_by_username')!r}")
        else:
            print(f"  /api/points/history?student_id={sid} → {r.status_code}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
