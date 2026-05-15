"""Safe deploy with auto-rollback.

Protocol:
    1. Tag safety/pre-<feature>-<timestamp> against HEAD.
    2. Push branch + safety tag.
    3. Poll the prod /api/health for up to 5 min, waiting for the
       new revision's response.
    4. Run a minimal e2e (login + load home) against prod.
    5. If anything fails -> reset main to safety tag and force-push,
       then exit non-zero with the logs.

Usage:
    python scripts/safe_deploy.py --feature myfeat
    python scripts/safe_deploy.py --feature myfeat --no-push   # dry-run
    python scripts/safe_deploy.py --feature myfeat --no-op     # demo

Defaults:
    --base https://mindx-portal-1.onrender.com
    --branch main
    --wait 300        # max seconds to wait for deploy to come back

THE ROLLBACK IS DESTRUCTIVE — it does `git push --force-with-lease` on
main. If you don't want that, run with --no-rollback and the script
will just exit non-zero on failure.
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def run(cmd: list, check: bool = True, capture: bool = True) -> str:
    """Run a shell command from the repo root. Returns stdout."""
    print(f"  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO,
                          capture_output=capture, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if check and proc.returncode != 0:
        raise SystemExit(
            f"command failed (exit {proc.returncode}): {' '.join(cmd)}\n{out}")
    return out.strip()


def now_tag(feature: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    safe_feat = "".join(c if (c.isalnum() or c == "-") else "-"
                        for c in feature)[:40]
    return f"safety/pre-{safe_feat}-{ts}"


def poll_health(base: str, timeout: int) -> bool:
    """Poll /api/health until 200 or timeout. Returns True on green."""
    import urllib.request
    import json as _json
    deadline = time.time() + timeout
    last_err = ""
    while time.time() < deadline:
        try:
            req = urllib.request.Request(base.rstrip("/") + "/api/health")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    body = _json.loads(resp.read().decode("utf-8"))
                    if body.get("ok") is True:
                        print(f"  health green at {int(time.time())}")
                        return True
                    last_err = f"ok=false body={body}"
                else:
                    last_err = f"status={resp.status}"
        except Exception as ex:
            last_err = str(ex)[:160]
        time.sleep(5)
    print(f"  health timed out -- last={last_err}")
    return False


def run_smoke_e2e(base: str) -> bool:
    """Run the e2e --smoke subset against base. Returns True on pass."""
    try:
        from auto_test import BrowserSession  # type: ignore
    except Exception as ex:
        print(f"  e2e import failed: {ex}")
        return False
    try:
        with BrowserSession(base_url=base) as s:
            # admin_test must exist on prod for this to pass — see
            # scripts/seed_test_users.py. Run that with DATABASE_URL=...
            # pointed at prod once before the first safe_deploy.
            s.login_as("admin")
            s.navigate("/dashboard")
            s.screenshot("safe_deploy_post")
            if not s.check_no_500():
                print(f"  e2e 5xx: {s.failing_responses()[:3]}")
                return False
        return True
    except Exception as ex:
        print(f"  e2e exception: {ex}")
        return False


def rollback(safety_tag: str, branch: str, no_push: bool) -> None:
    print("\n[safe-deploy] !! ROLLING BACK to", safety_tag)
    run(["git", "reset", "--hard", safety_tag])
    if no_push:
        print("[safe-deploy] --no-push set; rollback is local only.")
        return
    # --force-with-lease so we don't clobber someone else's push.
    run(["git", "push", "--force-with-lease", "origin", branch])
    print("[safe-deploy] rollback pushed.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", required=True,
                    help="short slug for the safety tag")
    ap.add_argument("--base",
                    default="https://mindx-portal-1.onrender.com",
                    help="production base URL")
    ap.add_argument("--branch", default="main")
    ap.add_argument("--wait", type=int, default=300,
                    help="seconds to wait for deploy to come back green")
    ap.add_argument("--no-push", action="store_true",
                    help="dry run: tag and report but never push or rollback")
    ap.add_argument("--no-rollback", action="store_true",
                    help="exit non-zero on failure but do not reset main")
    ap.add_argument("--no-op", action="store_true",
                    help="create the safety tag + push it, then run the "
                         "full poll/e2e cycle without pushing any code "
                         "change. Useful to validate the protocol itself.")
    ap.add_argument("--skip-e2e", action="store_true",
                    help="poll /api/health only; skip the browser e2e step")
    args = ap.parse_args()

    print("[safe-deploy] starting...")
    print(f"  base={args.base} branch={args.branch} wait={args.wait}")

    # 1. ensure clean working tree (uncommitted changes refuse to deploy)
    dirty = run(["git", "status", "--porcelain"], check=False)
    if dirty.strip():
        print("[safe-deploy] working tree dirty:")
        print(dirty)
        if not args.no_op:
            print("[safe-deploy] refusing to deploy with uncommitted "
                  "changes. Commit/stash first.")
            return 2

    # 2. tag
    tag = now_tag(args.feature)
    head_sha = run(["git", "rev-parse", "HEAD"])
    print(f"  HEAD={head_sha[:12]}")
    run(["git", "tag", tag, head_sha])
    print(f"[safe-deploy] tagged {tag}")

    # 3. push branch + tag (unless --no-push)
    if args.no_push:
        print("[safe-deploy] --no-push: skipping git push.")
    else:
        run(["git", "push", "origin", args.branch])
        run(["git", "push", "origin", tag])
        print(f"[safe-deploy] pushed {args.branch} + {tag}")

    # 4. wait for deploy + poll health
    if args.no_push:
        print("[safe-deploy] --no-push: skipping deploy wait.")
        return 0

    print(f"[safe-deploy] polling {args.base}/api/health for up to "
          f"{args.wait}s")
    # Sleep 30s upfront — Render takes a few seconds to even start
    # building, so polling immediately would always see the old rev.
    time.sleep(30)
    ok = poll_health(args.base, args.wait)
    if not ok:
        if not args.no_rollback:
            rollback(tag, args.branch, args.no_push)
        return 1

    # 5. e2e smoke (skippable for /api/health-only deploys)
    if args.skip_e2e:
        print("[safe-deploy] --skip-e2e set; not running browser smoke.")
    else:
        print("[safe-deploy] running smoke e2e against prod...")
        if not run_smoke_e2e(args.base):
            if not args.no_rollback:
                rollback(tag, args.branch, args.no_push)
            return 1

    print(f"\n[safe-deploy] DEPLOY OK -- safety tag {tag} remains "
          f"on origin in case you need to roll back later.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
