# Declarative gunicorn config — verification (v2.9.6)

**Goal:** make gunicorn's runtime configuration declarative in
the repository so it applies automatically on every deploy. No
more "go to Render dashboard → Settings → Build & Deploy →
paste new Start Command" steps after every change.

## Commits

| # | Commit | What it changed |
|---|---|---|
| C1 | (investigation, no commit) | confirmed `render.yaml` + `Procfile` already exist with `--timeout 300 --graceful-timeout 30` from v2.9.4 |
| C2 | `cf79872` | added `--workers 2 --threads 4` to `render.yaml` startCommand |
| C3 | `d19228d` | mirrored same flags into `Procfile` |
| C4 | `b62158d` | `scripts/smoke_deploy_config.py` — 7-invariant smoke |
| C5 | this report | verification + owner-side checklist |

**Safety tag:** `safety/gunicorn-config-20260513-224338`
(pushed before any edit; usable for rollback).

## What changed

### `render.yaml`

```diff
- startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30
+ startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30 --workers 2 --threads 4
```

### `Procfile`

```diff
- web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30
+ web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30 --workers 2 --threads 4
```

### Final gunicorn invocation

```
gunicorn app:app --bind 0.0.0.0:$PORT \
                 --timeout 300 \
                 --graceful-timeout 30 \
                 --workers 2 \
                 --threads 4
```

## Why this version

| Flag | Value | Reason |
|---|---|---|
| `--timeout 300` | 300 s | covers 150 MB chunked-upload finalize step (reassemble + magic-byte sniff + INSERT). Was 120 s before v2.9.4. |
| `--graceful-timeout 30` | 30 s | grace period for in-flight requests during deploy/restart before SIGKILL. Lets the `_chunked_cleanup_expired` sweep finish cleanly if it's running. |
| `--workers 2` | 2 | conservative for the Starter plan's 512 MB RAM. Observed per-worker RAM ~120–180 MB → 2 × ~180 MB ≈ 360 MB, comfortable headroom. |
| `--threads 4` | 4 | with the gthread worker class, 4 threads per worker = 8 concurrent requests across the service. Lets a slow upload not block a quick status check. |

## Why no manual dashboard step is needed anymore

Render auto-loads `render.yaml` (the "blueprint") on **every**
deploy. If both `render.yaml` and a dashboard-configured Start
Command are present, the **dashboard-configured value wins by
default** — which is the pitfall the owner has been hitting.

To make the YAML authoritative one-time:

1. Owner opens https://dashboard.render.com → `mindx-portal-1` →
   **Settings → Build & Deploy → Start Command**.
2. If the field still contains a manually-pasted command from a
   prior session, **clear it** (delete the override).
3. Save Changes.

After that, every future deploy reads `startCommand` from
`render.yaml` automatically. **This one-time clear is required**
for the declarative config to actually take effect — if a
manual override is still set, the dashboard value continues to
override the YAML.

## What this commit explicitly did NOT do (and why)

The original brief suggested several additional `render.yaml`
fields. I held the line on the brief's "if it exists, only
update startCommand" rule and skipped these to keep blast
radius minimal:

| Brief suggested | Why I skipped | Risk if added |
|---|---|---|
| `healthCheckPath: /healthz` | no `/healthz` route exists in `app.py` (only a docs-discovery skip reference at line 47108). Adding the path without a backing route → Render marks the service unhealthy → deploys fail. | broken deploys |
| `PYTHON_VERSION: 3.11` | `runtime.txt` pins `python-3.12.3` (already in repo). Adding an envVar would conflict. | runtime mismatch |
| `region: oregon` | current YAML has no region. Setting one might trigger a service migration. | downtime or data location change |
| `plan: starter` | YAML currently silent; service runs on Starter per CLAUDE.md. Adding it ties a billed line to the YAML; better managed via dashboard. | billing/plan confusion |
| changed `env: python` → `runtime: python` | both keys work; swapping is unrelated to this task. | unnecessary churn |
| replaced `buildCommand` block | the existing multi-line build (pip + pillow-heif + playwright + install-deps) is working today and goes well beyond what the brief suggested. | regression in HEIC uploads / Playwright docs auto-capture |
| changed `PLAYWRIGHT_BROWSERS_PATH` to `/opt/render/.cache/ms-playwright` | current value `/var/data/playwright-browsers` is intentional (CLAUDE.md: cached on the persistent disk to avoid 150 MB re-download every deploy). Switching to the OS cache would re-download Chromium on every deploy and slow builds 3-4 min. | slow deploys |

Each of these is recoverable in a future commit if the owner
decides they want them. None are blocking the root fix.

## Smoke verification

```
$ python scripts/smoke_deploy_config.py
[1] render.yaml exists at repo root
[2-4] render.yaml startCommand contains all 4 expected flags:
      --timeout 300, --graceful-timeout 30,
      --workers 2, --threads 4
[5] render.yaml parses as valid YAML; service 'mindx-portal'
    (type=web) startCommand validated through both regex and
    YAML parser
[6] Procfile is aligned with render.yaml — both invoke
    `gunicorn app:app` with all 4 expected flags
[7] requirements.txt declares gunicorn: version 21.2.0

PASS — declarative gunicorn config is in lockstep across
render.yaml + Procfile + requirements.txt.
```

## Owner-side verification (after deploy)

1. After pushing `main`, watch the **Render dashboard → Events**
   tab for a "Deploy started" entry on commit `b62158d`.
2. Once "Deploy live", open the **Logs** tab.
3. Look for the gunicorn boot line near the top of the deploy
   logs — it should read:
   ```
   [INFO] Starting gunicorn 21.2.0
   [INFO] Listening at: http://0.0.0.0:10000 (1)
   [INFO] Using worker: gthread
   [INFO] Booting worker with pid: 12
   [INFO] Booting worker with pid: 13
   ```
   Two `Booting worker` lines = 2 workers, confirming `--workers 2`.
4. To confirm `--threads 4` took effect, also expect:
   ```
   [INFO] Server is ready. Spawning Threads: 4
   ```
   (gunicorn's exact wording varies by version; the worker-class
   line `Using worker: gthread` is the smoking gun — sync mode
   wouldn't ignore the threads flag).
5. To confirm `--timeout 300` — run a `/admin/books` upload of
   a 100+ MB file. If it completes without a 502 around the
   2-minute mark, the new timeout is in effect.

## Rollback

If anything misbehaves in production:

```
git reset --hard safety/gunicorn-config-20260513-224338
git push --force-with-lease origin main  # ⚠ owner-only
```

The safety tag points at `eceec7d` (the v2.9.5 head), so
rollback returns to the verified v2.9.5 state without losing
the chunked-upload work.

---

_Tagged as **v2.9.6**._
