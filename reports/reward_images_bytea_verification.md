# Reward Images BYTEA Migration — Verification Report

**Date:** 2026-05-12
**Master safety tag:** `safety/reward-images-bytea-20260512-055623`
**Final HEAD commit:** `90103d3 fix: distinguish empty boolean from None in _reward_serve_image_url`

## Why this migration

Reward images uploaded via `/api/admin/rewards/upload-image` were written to `<repo>/static/rewards/` on the host filesystem. On Render, that directory is **ephemeral** — only `/var/data/` survives container restarts. Every uploaded image was lost on the next deploy, while the `rewards.image_url` column still pointed at the now-deleted file → broken-image glyph in the UI. (Full root-cause writeup in the previous diagnostic report.)

The migration ports the storage to a BYTEA column on the `rewards` table — same pattern `books_v2.file_data` uses for PDFs. Bytes live in the DB, served by a new dynamic route. Zero filesystem dependency.

## Commit Log

```
90103d3  fix: distinguish empty boolean from None in _reward_serve_image_url
1558764  fix: clear stale image_url for rewards with missing image_bytes
6f0b4f6  feat: base64 upload + image error fallback to icon
13e6602  feat: GET /api/rewards/<rid>/image serves reward image bytes
ee6844e  feat: store reward images as BYTEA in DB
8b8eeaa  migration: add image_bytes and image_mime columns to rewards
```

The 6th commit (`90103d3`) is a fix-forward on top of `13e6602`. The helper `_reward_serve_image_url` was returning the dynamic URL for rows where `image_bytes IS NULL` because the SELECT projects that check as a boolean (False/0, not None) and my `is not None` test was always True. The frontend's `onerror` fallback hid the mistake user-side (broken images would have swapped to the icon emoji), but API responses were wrong. Switched to `bool()` which handles all four shapes (`None`, `0/False`, `1/True`, actual bytes) correctly.

## REGRESSION CHECKS (all PASS on prod after deploy)

| Check | Result |
|---|---|
| App boots cleanly (no Python errors) | ✅ |
| `/parent` loads | ✅ HTTP 200 |
| `/api/parent/lookup` works | ✅ HTTP 200 with full payload |
| `/api/parent/store/menu` works | ✅ HTTP 200 |
| `/points/manage` loads | ✅ HTTP 200 |
| `/portal/parent-hub/points` (legacy shop, admin → 302 redirect) | ✅ HTTP 302 (as expected for admin role) |
| `/api/points/rewards` (admin GET) | ✅ HTTP 200, 5 rows |
| 4 seeded rewards still present, unchanged | ✅ ids 1,2,3,4 all `is_menu_item=0`, `is_active=1` |
| books_v2 view route still works (regression check on the pattern we copied) | ✅ HTTP 302 (the can_download=0 → iframe-viewer redirect, unchanged behaviour) |

## NEW BEHAVIOUR (all verified live on prod)

| Check | Result |
|---|---|
| Create reward via admin form with PNG (image_b64 in JSON body) | ✅ POST returns `{"id":11,"ok":true}` |
| New reward stored with `image_mime='image/png'`, BYTEA populated | ✅ verified by GET response |
| `GET /api/rewards/11/image` returns 200 with `Content-Type: image/png` and the exact PNG bytes | ✅ 68-byte response, `file` confirms `PNG image data, 1 x 1, 8-bit/color RGBA` |
| `/api/parent/store/menu` returns `image_url='/api/rewards/11/image'` for the new reward | ✅ verified |
| Existing "سيارة" row's broken `/static/rewards/...` URL was cleared by the backfill | ✅ confirmed: `image_url=''` post-deploy |
| Old `/api/admin/rewards/upload-image` endpoint removed | ✅ HTTP 404 (no cached JS still hits it — confirmed via grep) |
| Invalid base64 rejected with Arabic error | ✅ `400: "صيغة الصورة غير صحيحة"` |
| Wrong magic bytes rejected | ✅ `400: "صيغة غير مدعومة. المسموح: JPG / PNG / WebP"` |
| Inactive reward's image returns 404 (so soft-delete properly hides image too) | ✅ verified |
| Bogus reward id returns 404 | ✅ verified |
| Helper returns `image_url=''` for rows without bytes | ✅ all 4 seeded rewards now show `image_url=''` (their icon will render) |

## EDGE CASES

- **Reward with no image AND no icon** → JS sends default `🎁` emoji (`_ppFormatStoreCard` line: `var icon = (item.icon || '').trim() || '🎁'`).
- **Reward with no image AND custom icon** → custom icon renders.
- **Reward with both image and icon** → image wins; if the image 404s the JS `onerror` swaps the `<img>` for the icon emoji.
- **Re-upload replaces previous image** → PATCH with `image_b64` overwrites the row's `image_bytes` and `image_mime`, and clears the legacy `image_url`. Next GET returns the same `/api/rewards/<id>/image` URL but with new bytes (Cache-Control is `private, no-store` so the admin sees the new image immediately).
- **Explicit clear via empty `image_b64`** → PATCH `{image_b64: ""}` nulls out `image_bytes`, `image_mime`, AND `image_url`. The card falls back to the icon.

## Files Modified

| File | Total diff |
|---|---|
| `app.py` | 6 commits, ~270 net lines added (the migration + helper + endpoint + serve route + admin form rewrite + backfill + fix) |
| `reports/reward_images_bytea_verification.md` | this file |

## Untouched (per protocol)

- `books_v2` file_data path, upload, serve — unchanged
- Parent receipts upload — unchanged
- Curriculum upload — unchanged
- `/api/points/rewards` PATCH route's existing field handling (only ADDED `image_b64` decoder + clear logic)
- Legacy shop on `/portal/parent-hub/points` — unchanged, still shows the 4 seeded rewards with emoji icons
- The existing 4 seeded rewards (`name_ar`, `point_cost`, `icon`, `category`) — values intact

## Owner Action Item

**Re-upload the سيارة reward's image.** The backfill cleared the dead `/static/rewards/...` URL on the row, so the card currently shows the icon emoji fallback (or default 🎁 if no icon was set). To restore the image:

1. Open `/points/manage → المكافآت`
2. Click ✏️ "تعديل" on the سيارة row
3. Click the file picker, choose the image (JPG/PNG/WebP, ≤2 MB)
4. Status shows "✅ سيتم رفع الصورة عند الحفظ" (preview renders from the data URL)
5. Click "حفظ" → row is updated atomically (bytes go into the DB)
6. Refresh `/parent` and lookup with a real PID — the toy tab shows the image

This time the image survives every deploy/restart. The migration is complete.

## Safety Rollback

`safety/reward-images-bytea-20260512-055623` (tag pushed) is the commit immediately before this migration. To fully revert:

```
git reset --hard safety/reward-images-bytea-20260512-055623
git push --force-with-lease origin main
```

The migration is **additive-only** — `image_bytes` and `image_mime` columns become dormant but stay present in the DB. The backfill's `UPDATE rewards SET image_url=''` is NOT reversible from code (the original `/static/rewards/...` URLs are gone), but those URLs were already pointing at deleted files, so there's nothing to recover. Reverting purely restores the previous code path; admins would have to re-upload anyway.
