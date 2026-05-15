"""Fetch Render production logs with filters.

Requires two env vars (set them in your shell, not in this repo):
    RENDER_API_KEY     = a Render personal API token
    RENDER_SERVICE_ID  = the srv-... id of the mindx-portal service

If either is missing, the script falls back to printing instructions
for the dashboard URL so you're never stuck.

Examples:
    python scripts/get_logs.py                       # last 100 lines
    python scripts/get_logs.py --since 30m           # last 30 minutes
    python scripts/get_logs.py --since 1h --keyword orphan
    python scripts/get_logs.py --level error
    python scripts/get_logs.py --since 2026-05-15T12:00:00Z

The Render Logs API:
    https://api.render.com/v1/logs?ownerId=...&resource=srv-...&...

Output is plain text, one line per log entry, sorted oldest -> newest.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def parse_since(s: str) -> dt.datetime:
    """Accept ISO timestamps or relative durations like '30m', '2h', '1d'."""
    m = re.match(r"^(\d+)([smhd])$", s.strip())
    if m:
        n = int(m.group(1)); unit = m.group(2)
        delta = {
            "s": dt.timedelta(seconds=n),
            "m": dt.timedelta(minutes=n),
            "h": dt.timedelta(hours=n),
            "d": dt.timedelta(days=n),
        }[unit]
        return dt.datetime.now(dt.timezone.utc) - delta
    # Try ISO 8601
    try:
        # Z suffix → +00:00 for python<3.11 compat
        s2 = s.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(s2)
    except Exception:
        raise SystemExit(f"can't parse --since {s!r}; use 30m/2h/1d or ISO")


def render_api_request(path: str, params: dict, api_key: str) -> dict:
    url = "https://api.render.com/v1" + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_logs(service_id: str, owner_id: str, since: dt.datetime,
               until: dt.datetime, api_key: str, limit: int = 500):
    """Returns list of {timestamp, message} dicts."""
    params = {
        "ownerId": owner_id,
        "resource": service_id,
        "startTime": since.astimezone(dt.timezone.utc).isoformat()
            .replace("+00:00", "Z"),
        "endTime":   until.astimezone(dt.timezone.utc).isoformat()
            .replace("+00:00", "Z"),
        "limit": limit,
        "direction": "backward",
    }
    body = render_api_request("/logs", params, api_key)
    # Schema as of 2025-10: {"logs":[{"timestamp":..., "message":...}], ...}
    logs = body.get("logs") or body.get("data") or []
    # Some accounts return them newest-first; normalize.
    logs.sort(key=lambda r: r.get("timestamp") or "")
    return logs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="1h",
                    help="relative (30m/2h/1d) or ISO timestamp")
    ap.add_argument("--until", default="",
                    help="ISO timestamp; default = now")
    ap.add_argument("--keyword", default="",
                    help="case-insensitive substring filter")
    ap.add_argument("--level", default="",
                    help="error | warn | info -- substring on the line")
    ap.add_argument("--limit", type=int, default=500)
    args = ap.parse_args()

    api_key = (os.environ.get("RENDER_API_KEY") or "").strip()
    service_id = (os.environ.get("RENDER_SERVICE_ID") or "").strip()
    owner_id = (os.environ.get("RENDER_OWNER_ID") or "").strip()

    if not (api_key and service_id and owner_id):
        print("[logs] RENDER_API_KEY / RENDER_SERVICE_ID / "
              "RENDER_OWNER_ID env vars not set.")
        print("[logs] Get them from:")
        print("       https://dashboard.render.com/u/settings#api-keys")
        print("       (service id is in the service URL: dashboard.render.com/web/srv-XXXX)")
        print("[logs] Falling back to dashboard link:")
        print("       https://dashboard.render.com/web/<service-id>/logs")
        return 2

    since = parse_since(args.since)
    until = (parse_since(args.until) if args.until
             else dt.datetime.now(dt.timezone.utc))

    try:
        logs = fetch_logs(service_id, owner_id, since, until,
                          api_key, limit=args.limit)
    except Exception as ex:
        print(f"[logs] API call failed: {ex}", file=sys.stderr)
        print("       URL fallback: "
              f"https://dashboard.render.com/web/{service_id}/logs",
              file=sys.stderr)
        return 1

    kw = args.keyword.lower()
    lvl = args.level.lower()
    printed = 0
    for r in logs:
        msg = (r.get("message") or "").rstrip()
        ts = r.get("timestamp") or ""
        if kw and kw not in msg.lower():
            continue
        if lvl and lvl not in msg.lower():
            continue
        print(f"{ts}  {msg}")
        printed += 1
    print(f"\n[logs] {printed} line(s) matched "
          f"(window: {since.isoformat()} -> {until.isoformat()})",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
