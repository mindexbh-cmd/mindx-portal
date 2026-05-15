# CHANGE_LOG.md

Chronological history of significant work on the mindex-portal codebase, grouped by week. Maintained by `memory-keeper-agent`. For per-commit detail, run `git log --since=<date>`.

Span: 2026-04-02 (project start) → ongoing.
Total commits as of 2026-05-15: **1308** across 43 days.

| Period | Commits | Highlights |
|---|---:|---|
| Apr 02–06 | ~30 | Project bootstrap — `app.py` + `login.html` + Google Sheets import |
| Apr 07–13 | ~60 | Attendance + violations + group filters; first round of UI fixes |
| Apr 14–20 | ~120 | Database editor + custom tables + label system; taqseet payment logic |
| Apr 21–27 | ~160 | Curriculum library; books_v2 introduction; admin pages |
| Apr 28–May 03 | ~250 | Dashboard redesign; parent hub Phase 1; Excel import unification |
| May 04 | 123 | Points/behaviors/avatars/eggs feature wave; achievements seed import |
| May 05–08 | ~150 | Parent shop (cart-based redemption); rewards; store-link with expenses |
| May 09–11 | ~50 | Books library hardening; PDF viewer custom rendering; parent portal fixes |
| May 12 | 196 | Phase 2 push notifications foundation; parent-shop polish |
| May 13–14 | ~140 | TWA / APK build pipeline; push UI + admin panel; books chunked upload |
| May 15 | 44 | Infrastructure-as-code: agent team, hooks, slash commands, memory keeper, DB audit |

## Weekly notes

### Week of 2026-04-02 (project genesis)

- **2026-04-02**: First commits — `app.py` skeleton, `login.html` upload, runtime pinned to Python 3.12.
- **2026-04-05**: Auto-import students from Google Sheets feature lands; first real `app.py` work.
- **2026-04-06**: `/api/students/groups` endpoint; violations stats fix (`high` + `total_pts` fields).

### Week of 2026-04-13

- Database editor (`/database`) takes shape with the generic table renderer.
- Label system introduced (`column_labels`, `group_col_labels`, `att_col_labels`).
- First payment / taqseet logic.

### Week of 2026-04-20

- Books_v2 schema lands (`books_v2`, `books_v2_groups`, `books_v2_teachers`, `book_folders`, `book_folder_groups`).
- Curriculum library (`curriculum_files`, `curriculum_assignments`, `curriculum_access_log`).
- Admin permissions UI starts to take shape.

### Week of 2026-04-27 (dashboard redesign)

- 2026-04-29 — Full dashboard redesign safepoint tagged (`dashboard-restyle-safepoint-20260429-160915`, `dashboard-full-redesign-20260429-165722`).
- Major UX work on attendance: anomaly warning, completeness check, summary block, scroll fix, empty-status fix.

### Week of 2026-05-04 (points feature wave — 123 commits in one day)

- `point_events` table introduced; `behaviors` catalog seeded.
- Avatars + level system; achievements scaffolding (later determined unused).
- Egg-hatch gamification mechanic.
- **2026-05-04 19:18 → 19:19**: `student_points_log` bulk-seeded (1865 rows in a 9-second window). Confirmed never referenced afterward — likely a feature-attempt that was replaced by `point_events`.

### Week of 2026-05-11

- 2026-05-12 — **196 commits** in one day. Push notifications Phase 2 foundation lands; parent shop cart redemption (`cart_items`, `redemptions`) polish.
- Parent portal Unicode-bidi-mark tolerance fix (~10% of CPR lookups were failing on invisible characters).
- Parent shop "اطلب الآن" disable when points insufficient; `cart_items` checkout writes `requested` status (no immediate point debit).

### Week of 2026-05-13 (TWA + push + books)

- 2026-05-13 — Books library hardening: chunked uploads land on disk instead of BYTEA; orphan probe recognises BYTEA-only rows; soft-delete of `books_v2.id=4` orphan test row.
- 2026-05-14 — TWA / APK build pipeline: `twa-manifest.json`, `.github/workflows/build-apk.yml`, `assetlinks.json` route, multiple Bubblewrap version pinning iterations (settled on 1.23.0).
- Push notifications: admin send panel on `/points/manage`, admin broadcast log (`notifications` table), smart-timing permission prompt, urgent/vibrate/tag SW handlers.
- VAPID generator rewritten using `cryptography` directly (avoid heavy py-vapid CLI flakiness).

### 2026-05-15 (infrastructure-as-code day)

Recorded in tight detail because this is when the agent team / safety net / memory keeper landed.

| Hash | Title |
|---|---|
| `f7e62c9` | fix(safety): repair `_pg_pool` reference + add `/api/health{,/deep}` |
| `8defcba` | feat(testing): autonomous engineering infrastructure (scripts/) |
| `8ca8a45` | chore(agents): un-ignore `.claude/agents/` |
| `7943f55` `fa3e479` `3d116f6` `7ab7a0e` `fb6decb` `27689db` `3acd9f4` `998a675` `dfbef67` `918ce33` `7efd636` | 11 custom subagents (one per commit) |
| `7810ae5` | docs(agents): CLAUDE.md agent registry |
| `30e33b3` | feat(agents): add database-architect-agent (12th custom) |
| `aba3399` | docs(db): comprehensive read-only audit of production Postgres |
| `ff18e8c` | feat(commands): 10 project slash commands |
| `b17328b` | feat(hooks): 5 lifecycle hooks |
| `c16cbf9` | feat(agents): import 9 professional subagents from VoltAgent |
| `ce970c8` | docs(mcp): MCP server documentation + opt-in template |
| `119348e` | docs(claude): comprehensive Professional setup section in CLAUDE.md |
| `3fd37db` | feat(agents): add memory-keeper-agent (13th custom) |
| `6caa418` | feat(memory): memory-keeper onboarding — initial corpus (9 files, 1252 lines) |
| `caa0279` | feat(commands): /context — memory-keeper handoff generation |
| `f59efb5` | feat(hooks): memory-tracking + HANDOFF-aware session start (6th hook) |
| `bf5c521` | docs: integrate memory-keeper into coordinator pipeline + SOP |
| `b8d5079` | feat(agents): add prompt-engineer-agent + /plan command (14th custom agent + 12th slash command + demo plan) |

## How to append

memory-keeper appends new entries here in passive-tracking mode (PostToolUse on `feat:`/`fix:`/`refactor:` commits). Format for a single-day entry:

```
### 2026-MM-DD
- `<short-hash>` — <commit subject> (<scope inference>)
```

Group by week once a week is complete; keep the most recent week as per-day until the week closes.
