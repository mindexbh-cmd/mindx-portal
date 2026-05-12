# Points Allowlist Fix — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/points-allowlist-fix-20260512-155535`
**Phase commits:** C1 (this report = C2)

## Commit log

```
<this report>  docs: points allowlist fix verification
9fd1a7e        fix(points): swap allowlist to numeric login usernames (C1)
24edadd        (earlier "points access expansion verification" — pre-fix)
0ea4ec6        feat(points): grant raed + ahmed_ibrahim … (the buggy commit)
```

## The bug

`0ea4ec6` shipped:

```python
POINTS_MANAGER_USERNAMES = {"raed", "ahmed_ibrahim"}
```

This was supposed to grant points-manage admin rights to two named managers. But on production the column `users.username` is the **numeric personal ID**, not a display name. So when those two log in, `session["user"]["username"]` is `"010307885"` / `"980909805"` — and `"010307885" in {"raed", "ahmed_ibrahim"}` is `False`. The grant didn't take effect.

The audit at `reports/user_accounts_audit.md` (also today) caught this by:

1. Dumping the local users table and finding the two rows:
   - `id=8 username='010307885' name='أحمد إبراهيم' role='manager'`
   - `id=9 username='980909805' name='رائد' role='manager'`
2. Grepping for every other allowlist constant — all of them use the numeric IDs:
   - `_EVENTS_VIOLATIONS_FULL_ACCESS_USERNAMES = {"010307885", "980909805"}`
   - `_EXPENSES_ACCESS_USERNAMES = {"980909805"}`
   - `_BOOKS_V2_FULL_ACCESS_USERNAMES = {"010307885", "980909805"}`
3. Concluding the points set was the only outlier.

## The fix (C1, commit `9fd1a7e`)

Single-block change in `app.py`:

```python
POINTS_MANAGER_USERNAMES = {
    "010307885",   # أحمد إبراهيم — manager
    "980909805",   # رائد — manager
}
```

Plus a 9-line comment block above the set explaining why it switched and pointing future readers at the audit + sibling allowlists.

No other code change. `_can_manage_points`, `_pts_user_role`, `_require_points_admin_response`, the `/points/manage` route, the dashboard injection, the sidebar/card classes — all already read this set as the source of truth.

## E2E scenario walkthrough

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | Login as `010307885` (أحمد إبراهيم) | session.user.username == "010307885" | ✅ smoke [7a] |
| 2 | Visit `/dashboard` | renders 200, body data-can-manage-points="1" | ✅ smoke [8a] |
| 3 | Sidebar "إدارة نظام النقاط" entry | visible (mx-points-manage-link gating CSS un-hides for data-can-manage-points=1) | ✅ via existing CSS rule |
| 4 | Dashboard card `#dh-points-manage` | revealed by JS reveal block for canPts="1" | ✅ via existing JS at HOME_HTML |
| 5 | Click → `/points/manage` | 200 | ✅ smoke [7b] |
| 6 | Login as `980909805` (رائد) → `/points/manage` | 200 | ✅ smoke [7c] |
| 7 | `/dashboard` for `980909805` | data-can-manage-points="1" injected | ✅ smoke [8] |
| 8 | Login as `021005931` (أحمد يونس, role=admin) | already had access — unaffected by this fix | ✅ implicit (role short-circuit) |
| 9 | Login as legacy literal "raed" / "ahmed_ibrahim" | now returns False (those usernames don't exist on prod anyway) | ✅ smoke [3a]+[3b] |
| 10 | Login as a teacher | still blocked | ✅ smoke [5] |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean | ✅ |
| `POINTS_MANAGER_USERNAMES == {"010307885", "980909805"}` | ✅ smoke [1] |
| `_can_manage_points` returns True for both numeric IDs | ✅ smoke [2a]+[2b] |
| `_can_manage_points` returns False for legacy literal strings | ✅ smoke [3] |
| `_can_manage_points` returns True for admin role (any username) | ✅ smoke [4]+[4a] |
| `_can_manage_points` returns False for teachers / reception / students | ✅ smoke [5] |
| `_pts_user_role` spoofs new IDs as "admin" inside the points subsystem | ✅ smoke [6a]+[6b] |
| `_pts_user_role` no longer spoofs legacy literal strings | ✅ smoke [6c] |
| Login + `/points/manage` round-trip for both IDs → 200 | ✅ smoke [7] |
| Dashboard exposes `data-can-manage-points="1"` for both | ✅ smoke [8] |
| Admin 8-route regression all 200 | ✅ smoke [9] |
| No other allowlist or role-policy modified | ✅ (only `POINTS_MANAGER_USERNAMES` changed) |
| No schema change | ✅ |
| No DB write at deploy time | ✅ |

## How to prevent this in the future

**Rule:** when hard-coding usernames for permission allowlists, **always verify against the live `users.username` column, not the `users.name` (display) or any other field.** A safe template for new allowlists:

```python
# Production reality: users log in with numeric personal IDs (the
# `users.username` column). The display string in `users.name` is a
# different field — never put it in an allowlist.
#
# Sanity-check before committing:
#     SELECT username, name, role FROM users WHERE username IN (...)
# and confirm each row exists with the expected (name, role).
_MY_FEATURE_ALLOWLIST = {
    "010307885",  # أحمد إبراهيم — manager
    "980909805",  # رائد — manager
}
```

Three concrete safeguards the existing codebase already uses and we should keep using:

1. **Numeric-IDs-only convention** — every existing allowlist (`_EVENTS_VIOLATIONS_FULL_ACCESS_USERNAMES`, `_EXPENSES_ACCESS_USERNAMES`, `_BOOKS_V2_FULL_ACCESS_USERNAMES`) sticks to numeric login IDs. Don't deviate.
2. **Inline Arabic-name comment** — `"010307885",   # أحمد إبراهيم — manager` lets a future reader sanity-check the mapping without opening the DB.
3. **Single source of truth** — `_can_*` / `_has_*` helpers read the set once. Per-endpoint hard checks (`if user.get("username") == "raed":`) should not exist.

The audit report can be cross-referenced when reviewing any future allowlist commit:
`reports/user_accounts_audit.md` — has the verified ID↔name mapping for admin/raed/ahmed_ibrahim/ahmed_younis.

## Rollback

`safety/points-allowlist-fix-20260512-155535` is the commit immediately before C1. To revert:

```bash
git revert --no-edit 9fd1a7e
git push origin main
```

Reverting restores the literal-string set (which was effectively a no-op grant). If the owner wants to back out the entire points-manage allowlist concept, also revert `414a50e` (C2 UI) and `0ea4ec6` (C1 backend) — sequence documented in `reports/points_access_expansion.md`.

## Note on the spec text

The owner's spec for this fix listed:

> 010307885 → raed
> 980909805 → ahmed_ibrahim

The DB-verified mapping is the reverse:

> 010307885 → أحمد إبراهيم (ahmed_ibrahim)
> 980909805 → رائد (raed)

The SET-valued grant is identical regardless of per-ID labeling — both IDs are in the allowlist, so both managers receive access. The inline comment in `app.py` follows the DB-verified mapping (matching the existing `_EVENTS_VIOLATIONS_FULL_ACCESS_USERNAMES` comments). The final deliverable message attributes IDs to people using the DB-verified mapping.

---

🎯 **Allowlist fix shipped. Both numeric IDs now grant points-manage access on prod. ahmed_younis (admin role) unaffected — he already had full access via the admin role short-circuit. Convention now consistent with every other allowlist in the file.**
