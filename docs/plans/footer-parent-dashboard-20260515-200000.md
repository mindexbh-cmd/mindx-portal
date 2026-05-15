# Plan: Footer for Parent Page — 2026-05-15

## Goal

Add a simple, RTL-friendly footer to the parent-facing portal showing the brand
line "مايندكس - مركز التعليم والتدريب | الإصدار 3.5.0". The footer must appear on
the unified parent-hub landing page (`/portal/parent-hub`) and on each parent-hub
sub-page (payments, attendance, points, messages, evaluations, curriculum) so the
brand and version are consistent everywhere a parent looks. The version string is
treated as a single configurable value via `get_setting('parent_hub','footer_version','3.5.0')`
to honor the Dynamic Configuration Rule (CLAUDE.md), so future bumps don't
require a code change.

**Surface goal**: add footer with brand + version on the parent page.
**Underlying need**: consistent brand attribution + a visible version stamp
(useful for support — operator can ask the parent "what version do you see?").
**Constraints**: minimal, additive, no schema change, must be RTL/Arabic-correct,
must be entered as HTML numeric entities per the Arabic encoding rule.
**Risks**: low — purely additive HTML/CSS in inline templates.

## Context

**Memory files referenced**
- `docs/memory/PROJECT_BIBLE.md` §4.1 (Page templating — inline string constants,
  no Jinja, `.replace("__PLACEHOLDER__", value)` only).
- `docs/memory/PROJECT_BIBLE.md` §5.6 (Parent hub — `/portal/parent-hub/*` views).
- `docs/memory/CONVERSATION_THEMES.md` (operator prefers Arabic for user-facing
  text + concise direct action).
- `docs/memory/HANDOFF.md` (project state — 502 routes, single-file `app.py`).

**CLAUDE.md sections that constrain this work**
- "Working with Arabic text" — inside HTML blobs, store Arabic as HTML numeric
  entities (`&#x...`); inside inline `<script>` blocks, use `\uXXXX` JS escapes.
- "Display labels (LABELS RULE)" — users never see internal names; route
  user-visible strings through proper helpers.
- "Dynamic Configuration System" — version is a config value via
  `get_setting('parent_hub','footer_version','3.5.0')`; no hardcoded literals
  for anything that may change. Default fallback `'3.5.0'`.

**Existing patterns to reuse**
- `PORTAL_PARENT_HUB_HTML` (app.py ~ line 78045) — the landing page template.
  This file already follows the inline-template pattern with `</body></html>"""`
  closing markers. The footer block is appended just before `</body>` in this and
  every sibling parent-portal template.
- Sibling templates that need the same footer:
  - `PORTAL_PARENT_HTML` (app.py ~ 77413)
  - `PORTAL_PARENT_PID_HUB_HTML` (app.py ~ 11873)
  - `PORTAL_PARENT_HUB_HTML` (78045)
  - `PORTAL_PARENT_PAYMENTS_HTML` (78259)
  - `PORTAL_PARENT_ATTENDANCE_HTML` (78335)
  - `PORTAL_PARENT_MESSAGES_HTML` (78454)
  - `PORTAL_PARENT_EVALUATIONS_HTML` (78722)
  - any other `PORTAL_PARENT_*_HTML` constant identified by Discovery
    (e.g. points, curriculum sub-pages).
- The existing nav-list color tokens from the parent hub
  (`#f3e5f5` / `#c4a8e8` / `#4a148c`) — reuse the lavender/purple palette so the
  footer doesn't visually clash. Confirmed in the parent-hub template.
- Route render pattern: `return PORTAL_PARENT_HUB_HTML.replace('__VERSION__', ver)`
  where `ver = get_setting('parent_hub','footer_version','3.5.0')`. Two
  placeholders only: `__VERSION__` and (optional) `__BRAND__` if the operator
  ever wants to A/B brand wording.

## Phases

### Phase 1: Discovery (read-only)
- **Time**: 20 min
- **Risk**: none (read-only)
- **Agents**: `code-architect-agent` (or do it inline — small surface)
- **Steps**:
  1. `Grep` `^PORTAL_PARENT.*HTML\s*=` to enumerate every parent-portal template
     constant and confirm the seven templates listed above is the complete set.
  2. For each constant, read the closing block (last 30 lines) and identify the
     `</body></html>"""` line — the footer attaches immediately above it.
  3. Read each handler that returns one of those constants and confirm whether
     it already does any `.replace(...)` calls; new placeholders piggy-back on
     the existing call sites.
  4. Confirm no parent template currently renders a footer (so we're adding,
     not replacing).
- **Output**: short note in this plan file (in-place), no separate report.

### Phase 2: Design
- **Time**: 15 min
- **Risk**: none
- **Decisions to record**:
  - Footer markup (single `<footer class="mx-portal-footer">…</footer>` block
    with one `<span>` for brand and one for version; separator " | " inline).
  - CSS lives in a small inline `<style>` block scoped via `.mx-portal-footer`.
    Properties: `text-align:center; padding:14px 8px; margin-top:24px;
    color:#6a4a8e; background:#f3e5f5; border-top:1px solid #c4a8e8;
    font-size:13px; line-height:1.5; direction:rtl;`.
  - Version delivery: server-side `.replace('__VERSION__', ver)` in each
    handler; `ver = get_setting('parent_hub','footer_version','3.5.0')`.
  - Single shared snippet (Python module-level constant
    `PORTAL_FOOTER_BLOCK = """<footer …>…</footer>"""`) so all templates render
    the identical markup; insert it via `.replace('</body>', PORTAL_FOOTER_BLOCK + '</body>')`
    in the handler — keeps templates clean and avoids touching seven string
    constants.
  - Arabic strings inside `PORTAL_FOOTER_BLOCK` written as HTML numeric entities
    per CLAUDE.md "Working with Arabic text" — never raw Arabic in `app.py`.
- **Output**: design captured in this section; ui-designer-agent reviews
  contrast + spacing before code lands.

### Phase 3: Implementation
- **Time**: 45 min
- **Risk**: LOW (additive, single file, single concern)
- **Commits planned** (one concern per commit, per CLAUDE.md commit discipline):
  1. `feat(parent-hub): seed footer_version setting + Arabic label`
     — extends both `init_db()` seed and the
     `settings_seed_v1` migration in the else branch with
     `('parent_hub', 'footer_version', 'إصدار البوابة', '3.5.0', 'string')`.
     Touches `app.py` only. Honors the Dual-path Schema Management rule from
     CLAUDE.md (write to BOTH branches).
  2. `feat(parent-hub): add brand+version footer to parent portal`
     — defines `PORTAL_FOOTER_BLOCK` (with HTML numeric entities for the Arabic
     text); modifies the seven `/portal/parent*` handlers to read
     `get_setting('parent_hub','footer_version','3.5.0')`, substitute
     `__VERSION__` inside `PORTAL_FOOTER_BLOCK`, and inject before `</body>`.
     Touches `app.py` only.
- **Reviewers per commit**:
  - After commit 1: `database-architect-agent` (check the dual-path edit,
    confirm migration tag is persisted on prod-shaped wrappers).
  - After commit 2: `arabic-quality-agent` (entity correctness, RTL),
    `ui-designer-agent` (contrast/spacing on lavender palette),
    `mobile-first-agent` (footer doesn't crowd the cart on 360px viewports).

### Phase 4: Verification
- **Time**: 30 min
- **Risk**: LOW
- **Steps**:
  - Local: `python app.py` → log in as `parent_test` / `TestParent2026!`,
    visit `/portal/parent-hub` and each sub-page, confirm footer renders with
    "مايندكس - مركز التعليم والتدريب | الإصدار 3.5.0" centered, RTL, lavender.
  - Local e2e: `python scripts/run_e2e.py` — confirms no regression in the
    eight existing tests; if a parent-hub-specific test exists in
    `scripts/run_e2e.py`, ensure it still passes.
  - Persona test: invoke `real-user-tester-agent` with prompt:
    "Log in as parent_test/TestParent2026!, walk every parent-hub sub-page,
     screenshot the footer at 360 / 768 / 1280 viewports, verify the version
     string '3.5.0' appears centered at the bottom and is readable."
  - DB sanity: `python scripts/db_query.py "SELECT page,component,value FROM
     settings WHERE page='parent_hub' AND component='footer_version'"` —
     confirm row exists with value `3.5.0`.
- **Pass criteria**: footer visible on all seven templates, version reads
  exactly `3.5.0`, no console errors, no e2e regressions.

### Phase 5: Deployment
- **Time**: 10 min monitoring (deploy itself ~3 min)
- **Risk**: LOW
- **CLI**: `python scripts/safe_deploy.py --feature footer-parent-dashboard`
- Behaviour: tags `safety/pre-footer-parent-dashboard-<ts>`, pushes, polls
  `/api/health`, runs admin/teacher login smoke against prod, auto-rollback on
  failure (per `PROJECT_BIBLE.md` §7.3).
- Post-deploy spot check: open prod
  `https://mindx-portal-1.onrender.com/portal/parent-hub` while logged in as
  `parent_test`, confirm footer renders.

### Phase 6: Documentation
- **Time**: 10 min
- **Agent**: `memory-keeper-agent` with prompt:
  "Record feature 'parent-portal footer' in `docs/memory/CHANGE_LOG.md`
   under 2026-05 and in `docs/memory/DESIGN_LOG.md` (palette: lavender footer
   on parent hub). Bump the parent-portal section in `PROJECT_BIBLE.md` §5.6 to
   note the footer + version stamp + the new `settings.parent_hub.footer_version`
   row. No DECISIONS_LOG entry needed (no architectural choice)."

## Approval gates
1. **After Phase 1** — confirm Discovery enumerated all parent-portal templates
   (operator must agree the seven listed templates is the right scope).
2. **After Phase 2** — approve footer copy, palette, and the
   `PORTAL_FOOTER_BLOCK` shared-snippet approach before any code lands.
3. **Before Phase 5** — confirm local e2e is green and persona test screenshots
   look right before pushing to prod.

## Risk assessment
- **Overall**: LOW.
- **Worst case**: Arabic text mojibake (entity escape error) shows the literal
  HTML entities or �?? to parents. Mitigation: arabic-quality-agent review in
  Phase 3, manual visual check in Phase 4.
- **Second worst case**: footer layout breaks the 360px viewport (overlaps the
  bottom nav / cart bar). Mitigation: mobile-first-agent review in Phase 3 +
  persona test in Phase 4.
- **Rollback**: `git reset --hard safety/pre-footer-parent-dashboard-<ts>`
  followed by `git push --force-with-lease origin main`. The
  `settings.parent_hub.footer_version` row is harmless if left in place after
  rollback (no read site without the new code), so no DB rollback needed.
  No schema DDL is run, so the Data Safety Rule is trivially satisfied.

## Time estimate
- **Total**: ~2 hours wall-clock.
- **Breakdown**:
  - Phase 1 Discovery: 20 min
  - Phase 2 Design: 15 min
  - Phase 3 Implementation (2 commits + reviewer turnaround): 45 min
  - Phase 4 Verification (local + persona): 30 min
  - Phase 5 Deploy + monitor: 10 min
  - Phase 6 memory-keeper update: 10 min

## Success criteria
- [ ] Footer "مايندكس - مركز التعليم والتدريب | الإصدار 3.5.0" renders centered
      at the bottom of every parent-portal page (`/portal/parent-hub` + every
      `/portal/parent-hub/<sub>` route).
- [ ] Arabic text displays correctly (no mojibake, no raw entities visible).
- [ ] Version string sourced from
      `get_setting('parent_hub','footer_version','3.5.0')` — verified by
      changing the value to `'3.5.1'` in the settings UI and seeing the page
      update on next load.
- [ ] Footer is legible at 360 px / 768 px / 1280 px viewports.
- [ ] `python scripts/run_e2e.py` — 8/8 still passing.
- [ ] No `app.py` SyntaxError post-edit (precommit hook clean).
- [ ] `safe_deploy.py` reports green; `/api/health` 200 within 5 minutes of push.
- [ ] memory-keeper has updated CHANGE_LOG, DESIGN_LOG, and PROJECT_BIBLE §5.6.
