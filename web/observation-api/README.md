# Observation intake

Existing-repository, independent Cloudflare Worker + D1 + private R2 package. No imports from Blender or the viewer. The HTTP boundary accepts the existing `otw-observation-draft/0.1` metadata, preserving world/asset versions, coordinate uncertainty and null feature IDs. Accepted observations are evidence awaiting human review; no AI job, Issue or PR is created automatically.

## Initial limits

- 5,000,000 photo bytes, 30 posts/JST calendar day, 300 posts/JST calendar month, 2,000,000,000 reserved photo bytes globally.
- Fixed 30-day retention, hourly deletion in batches of 50. Outages can delay deletion. Private bucket only; no public photo URL is returned.
- SQL trigger atomically checks and reserves capacity before uploading. Pending/failed uploads consume post and storage allowances until expiration and confirmed deletion. This intentionally fails closed. Post counters include deleted records until the calendar period ends.
- Same submission ID and identical metadata returns the existing receipt when ready. Pending/expired IDs never repeat R2 PUT. A lost result requires operator inspection; there is no automatic retry loop. Tombstones are removed after 93 days.
- A shared pilot code is a temporary admission control, not individual authentication or a per-user rate limit. Rotate it if leaked. Do not embed it in frontend environment variables. Public launch needs individual authentication/bot and edge rate controls.

These limits are NOT a monetary billing cap. Rejected traffic, database operations, stored data, cleanup and provider-side backups can still incur charges. Budget alerts only notify. Keep the Worker Free plan if appropriate, inspect account billing and R2 lifecycle settings before enabling. Do not automatically upgrade a plan.

## Deployment (not performed by adding these files)

1. Use an authenticated Cloudflare Wrangler CLI to create D1 `otw-observations` and private R2 bucket `otw-observation-photos`. Set the returned database ID in `wrangler.jsonc`. Keep R2 public access disabled.
2. Run `wrangler d1 migrations apply otw-observations --remote` from this directory.
3. Set a random pilot code using `wrangler secret put SUBMISSION_TOKEN`. Keep it out of git and logs.
4. Deploy with `wrangler deploy`. Both admission switches default OFF. Set `ALLOWED_ORIGIN` to the viewer origin (no path).
5. Configure an R2 lifecycle expiration rule for prefix `observations/` at 30 days as a backup to hourly cleanup. D1 accounting remains conservative until cleanup confirms deletion.
6. After checking account billing and a private end-to-end test, set Worker `INTAKE_ENABLED` to `true` and execute `UPDATE limits SET enabled=1 WHERE id=1` against D1.
7. Build the viewer with `VITE_OBSERVATION_API_URL=https://<deployed-worker-host>` (GitHub Pages workflow reads repository variable `OBSERVATION_API_URL`). Without it, the send form stays hidden and local ZIP saving continues.

Stop admission immediately by setting `INTAKE_ENABLED=false` and redeploying (rejects before DB/body work), or `UPDATE limits SET enabled=0 WHERE id=1`. Cleanup continues. Manually adjust `daily_posts`, `monthly_posts`, `storage_bytes`, or reduce `photo_bytes` in the single limits row; no automatic increases. Update viewer limit text when changing policy. Never remove database rows to free space before confirmed R2 deletion.

Operator deletion: delete `observations/<receipt-id>.jpg` from private R2 first, then set the matching row to `status='deleted', metadata=NULL`. Preserve its count tombstone. User self-service deletion and operator UI are not implemented yet.

## Verification

`node --test tests/*.test.mjs`

`python -m unittest discover -s tests -p "test_*.py"`

SQLite tests exercise the real migration/trigger; Node tests cover request gates, streaming bounds, JST rollover and cleanup failure ordering. Cloudflare remote deployment and iPhone upload tests remain required.

References: [D1 SQL](https://developers.cloudflare.com/d1/sql-api/sql-statements/), [R2 Worker API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/), [budget alerts](https://developers.cloudflare.com/billing/manage/budget-alerts/).
