# Admin-Initiated Purchase — Discovery Report

**Date:** 2026-05-12
**Mode:** READ-ONLY discovery. No code or DB writes.
**Goal:** scope an "admin purchases reward on behalf of student" feature for /points/manage.

---

## §A — Parent-portal redemption flow

There are **three** existing redemption-creation paths:

### A.1 — `POST /api/parent/redeem` (`app.py:~26903`) — PUBLIC PARENT PORTAL

Used from the unauthenticated `/parent` PID-search store. Status = **`'requested'`**, `request_source = 'parent_pid'`. Waits for admin approval before any debit.

```sql
INSERT INTO redemptions(
    student_id, student_name, reward_id, reward_name,
    points_spent, status, request_source)
VALUES (?, ?, ?, ?, ?, 'requested', 'parent_pid')
```

Approval path: `POST /api/points/redemptions/<id>/approve` flips `'requested' → 'pending'`, which is when `_pts_balance` starts debiting. Rejection (`/reject`) flips it to `'rejected'`, never debited.

### A.2 — `POST /api/portal/student/redeem` (`app.py:~75929`) — LOGGED-IN STUDENT PORTAL

Student-themselves redemption from `/portal/parent-hub`. Permission: `role == 'student'`, `student_id` locked to `linked_student_id`. Status — needs re-checking but appears to follow the same approved flow.

### A.3 — `POST /api/points/redeem` (`app.py:36021`) — STAFF-INITIATED

The most relevant template for our work. Used by `/points/manage`. Permission: `_pts_can_grant(db, user, group_name)` — admin/manager always; teacher only if they own the student's group. Creates `status='pending'`, `request_source` not set (empty default).

```python
INSERT INTO redemptions(student_id, student_name, reward_id,
                        reward_name, points_spent, status)
VALUES (?, ?, ?, ?, ?, 'pending')
```

Stock is decremented when `stock > 0`. Stock `-1` means unlimited. Stock `0` returns `out of stock`.

### Validation order (same in all three paths)

1. student exists → else 404
2. permission gate (varies by path)
3. reward exists → else 404
4. `reward.is_active = 1` → else `'reward inactive'` 400
5. `_pts_balance(db, sid) >= reward.point_cost` → else `'insufficient points'` 400
6. `reward.stock != 0` → else `'out of stock'` 400
7. INSERT redemption + optional `UPDATE rewards SET stock = stock - 1`
8. `db.commit()` — no explicit transaction begin, relies on autocommit-off + single commit at end

No rollback semantics — Python `sqlite3` + the Postgres wrapper both commit on success or leave the connection unchanged on exception (the connection-level transaction is implicit).

---

## §B — Student search mechanism

### B.1 — JS-side fuzzy filter (existing — best fit for our modal)

`/dashboard` already ships an Arabic-aware client-side fuzzy search at `app.py:15092-15177`:

- **Bootstrap:** `srOpen()` fetches `GET /api/students` once → caches in `_srStudents`.
- **Normaliser** `_srNorm(s)` at line 15095 — folds:
  - `أ إ آ ٱ` → `ا` (alif variants)
  - `ة` → `ه`
  - `ى` → `ي`
  - U+0610-U+061A, U+064B-U+065F, U+0670, U+06D6-U+06ED → stripped (diacritics)
  - `\s+` → single space, lowercased, trimmed
- **Scorer** `_srScore(query, candidate)` at line 15105 — substring > subsequence > char-overlap.
- **Score on both:** `s.student_name` AND `s.personal_id` — exact-prefix on personal_id is naturally high-scoring since `_srScore` favours substrings.

### B.2 — Python-side normaliser

`_grp_arabic_normalize(s)` at `app.py:29058` does the same fold as the JS counterpart, used everywhere in the groups + students backend (installment-deep-resolve etc.).

`_grp_norm(s)` at `app.py:29071` is the symmetric NFC-aware fold used for facet matching.

For the modal we don't need a new Python-side search — the JS fuzzy filter against the already-fetched `/api/students` list is the established pattern.

---

## §C — Rewards table schema (`app.py:1083`)

```
id            INTEGER PK
name_ar       TEXT          (Arabic display name)
point_cost    INTEGER       (always positive)
icon          TEXT          (single emoji)
stock         INTEGER       (-1 = unlimited, 0 = out of stock, >0 = finite)
category      TEXT
is_active     INTEGER       (0 = hidden, 1 = visible)
image_url     TEXT          (legacy/external URL)
category_type TEXT          ('food', 'toy', '')
is_menu_item  INTEGER       (0/1)
image_bytes   BYTEA         (BYTEA pattern, served via /api/points/rewards/<id>/image)
image_mime    TEXT
created_at    DATETIME
```

For the admin-purchase modal we render: `name_ar` + `icon` (or `image_bytes` if present) + `point_cost` + `stock` (badge). Filter to `is_active = 1`.

---

## §D — `redemptions` table schema (`app.py:1097-1108`)

```
id              INTEGER PK
student_id      INTEGER       (FK → students.id)
student_name    TEXT          (denormalised — historic record even if student row changes)
reward_id       INTEGER       (FK → rewards.id)
reward_name     TEXT          (denormalised — same reason)
points_spent    INTEGER       (frozen at purchase time)
redeemed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
status          TEXT DEFAULT 'pending'
delivered_by    INTEGER       (user.id of who handed over)
delivered_at    DATETIME
request_source  TEXT DEFAULT '' (audit-trail: 'parent_pid', 'student_portal', 'staff', '')
```

### Status taxonomy (used by `_pts_balance` filter)

| status | counted as spent? | semantics |
|---|---|---|
| `'pending'` | ✅ debited | staff-initiated, awaiting hand-off |
| `'delivered'` | ✅ debited | physically handed over — terminal "good" state |
| `'requested'` | ❌ not debited | parent submitted, waiting on admin approve |
| `'approved'` | not seen as terminal — appears to be re-used as `'pending'` after approve | (admin approves a parent request → status flips to `'pending'`) |
| `'rejected'` | ❌ not debited | dead row |
| `'cancelled'` | ❌ not debited | refund |
| `''` (empty) | ✅ debited | legacy rows |

For admin-on-behalf direct purchase we want a status that:
- Debits immediately (so balance is accurate the moment the staff clicks confirm)
- Doesn't need a follow-up workflow
- Is distinguishable from staff-initiated `'pending'` rows in audit

**Recommendation: status = `'delivered'`, with `delivered_by = session.user.id` and `delivered_at = NOW()` stamped at INSERT time.** This treats the purchase as an immediate hand-over, which matches the owner's stated intent ("instant deduction, no approval workflow"). The redemption_id is still returned so a receipt/printout can be generated later.

For `request_source` — recommend a **new value `'admin_on_behalf'`** to keep this surface auditable separately from staff-initiated pending rows (which leave the column at `''`).

---

## §E — Balance calculation (`app.py:34875`)

```python
def _pts_balance(db, sid):
    earned = SELECT COALESCE(SUM(points_value), 0)
             FROM point_events WHERE student_id=?
    spent  = SELECT COALESCE(SUM(points_spent), 0)
             FROM redemptions
             WHERE student_id=?
               AND status NOT IN ('cancelled','requested','rejected')
    return int(earned) - int(spent)
```

Important: a new row with `status='delivered'` is automatically counted as `spent`. No additional balance-recalc logic needed — the helper already handles it.

---

## §F — Proposed implementation

### F.1 — New endpoint `POST /api/points/admin-purchase`

Gate: `_can_manage_points(user)` (admin OR allowlist `010307885`/`980909805`, plus ahmed_younis via admin role).

Body:
```json
{
  "student_id": 123,
  "reward_id": 45,
  "note": "..."     // optional, max 500 chars, stored as a server-side comment
}
```

Validation order (matches existing pattern §A):
1. permission → 403
2. body parse → 400
3. student exists → 404
4. reward exists + active → 404
5. stock check → 400
6. balance check → 400
7. note length ≤ 500 → 400

INSERT (atomic):
```sql
INSERT INTO redemptions(
  student_id, student_name, reward_id, reward_name,
  points_spent, status, request_source,
  delivered_by, delivered_at)
VALUES (?, ?, ?, ?, ?, 'delivered', 'admin_on_behalf',
        ?, CURRENT_TIMESTAMP)
```

Stock decrement: `UPDATE rewards SET stock=stock-1 WHERE id=? AND stock>0` (only when `stock > 0`).

Note storage: the `note` field doesn't have a dedicated column on `redemptions`. Two options:
- Option A (recommended): pass note to the audit log only. Keep the body field but write it to a server log via `print(...)` or a new audit table. Avoids schema migration.
- Option B: add a `note TEXT` column to `redemptions` via the dual-path migration block. More invasive, but visible alongside the row.

For v1 we'll go with Option A (audit-trail-only) — the schema stays untouched, the note is preserved in the server log + the response. Owner can request Option B as a v2 if they need note-in-the-DB.

Response:
```json
{
  "ok": true,
  "redemption_id": 789,
  "student_id": 123,
  "student_name": "...",
  "reward_id": 45,
  "reward_name": "...",
  "points_deducted": 30,
  "new_balance": 47,
  "actor_username": "010307885",
  "timestamp": "2026-05-12T15:32:00"
}
```

### F.2 — Reusable helpers vs new code

| Reusable | New |
|---|---|
| `_can_manage_points(user)` (just shipped) | endpoint route |
| `_pts_balance(db, sid)` | UI modal + 3 helper JS functions |
| `_grp_arabic_normalize(s)` / `_grp_norm(s)` | (not needed — JS does the search) |
| `_srNorm` + `_srScore` from `/dashboard` | (copy or expose in `/points/manage` if not already) |
| `GET /api/students` (full student dump) | (used by frontend) |
| `GET /api/points/rewards` (rewards list with stock + image-url) | (used by frontend) |
| `request_source` column | new value `'admin_on_behalf'` |

### F.3 — Frontend modal structure (POINTS_MANAGE_HTML)

Insert above the existing `<table>` of redemptions. Three-step modal:

1. **Student picker** — type-ahead against client-cached `/api/students` list. Show top 6 matches as compact cards. Selecting a row → fetches `GET /api/points/student/<sid>` for the current balance (this endpoint already exists for the avatar/balance bar).

2. **Reward picker** — grid of `/api/points/rewards` filtered to `is_active=1` and `stock != 0`. Each card shows: name + icon/image + cost + stock badge. Disable + dim cards that exceed the current balance.

3. **Confirmation** — preview line: `<student name> | <reward> | cost <X> | balance <Y> → <Y-X>`. Optional note textarea. Two buttons: تأكيد / إلغاء. On confirm → POST to `/api/points/admin-purchase`. On success → green toast + redirect back to step 1 (so user can buy for the next student).

Visual gating: wrap the trigger button in `<a class="... mx-points-manage-link">` so the existing CSS rule from C2 of yesterday's points-access work auto-hides it for non-allowlist roles.

---

## §G — Risk assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Parent-portal flow regression | very low | New endpoint is additive; no existing route touched |
| Balance miscalculation | low | Reuse `_pts_balance` — automatically debits `status='delivered'` rows |
| Stock decrement race | low | The `UPDATE … WHERE id=? AND stock>0` guard handles the only concurrent-write case correctly |
| Audit trail missing actor | medium → mitigated | Use `delivered_by` column (already exists) + `request_source='admin_on_behalf'` + server log |
| Search slowness on large student list | medium | Client-side fuzzy filter (already proven on `/dashboard`) handles ~1000 students fine; the bottleneck is the initial `/api/students` GET which loads <2 MB |
| Out-of-stock check vs balance check ordering | low | Match existing order: stock → balance (mirroring `/api/points/redeem`) |

---

## §H — Implementation plan (next commits)

**C2 (backend):** add `POST /api/points/admin-purchase` route. ≈80 lines.
**C3 (UI):** add modal HTML + JS to `POINTS_MANAGE_HTML`. ≈250 lines (50 markup + 200 JS).
**C4 (report):** final E2E verification.

Total estimated time: 45-60 min including smoke tests.

---

🎯 **Discovery complete. No surprises — `/api/points/redeem` and the parent-portal endpoint together provide a complete reference implementation. The new endpoint adds 80 lines, the UI adds ~250 lines, and the only schema-level addition is a new `request_source` value `'admin_on_behalf'`.**
