# Observation intake

## Deployment status — 2026-09-07

Live API: `https://otw-observation-api.open-tokyo-world-observation-api.workers.dev/v1/observations`. Allowed Origin: `https://ourjapan.github.io`. Intake enabled with a deploy-time `--var INTAKE_ENABLED:true` override; checked-in configuration deliberately remains OFF, so a plain deploy pauses intake. D1 limits are enabled at 30/day, 300/month, 5MB/photo and 2GB total. R2 public access is disabled and the `observations/` prefix expires after 30 days. GitHub repository variable `OBSERVATION_API_URL` is set; frontend integration/publication is coordinated separately.

Remote smoke passed: invalid credential 401, generated non-personal JPEG upload 201, identical retry 200, temporary one-post limit 429. The limit was restored to 30 afterward. One test post remains counted until normal retention expiry. No iPhone verification yet.

Remote D1 required a SQL compatibility fix: use `SELECT RAISE(...) WHERE ...` in the quota trigger instead of `CASE ... END`; the remote migration splitter rejected the original form even though local workerd accepted it. The corrected migration was applied successfully to the new remote database.

Existing-repository, independent Cloudflare Worker + D1 + private R2 package. No imports from Blender or the viewer. The HTTP boundary accepts the existing `otw-observation-draft/0.1` metadata, preserving world/asset versions, coordinate uncertainty and null feature IDs. Accepted observations are evidence awaiting human review; no AI job, Issue or PR is created automatically.

## Initial limits

- 5,000,000 photo bytes, 30 posts/JST calendar day, 300 posts/JST calendar month, 2,000,000,000 reserved photo bytes globally.
- Fixed 30-day retention, hourly deletion in batches of 50. Outages can delay deletion. Private bucket only; no public photo URL is returned.
- SQL trigger atomically checks and reserves capacity before uploading. Pending/failed uploads consume post and storage allowances until expiration and confirmed deletion. This intentionally fails closed. Post counters include deleted records until the calendar period ends.
- Same submission ID and identical metadata returns the existing receipt when ready. Pending/expired IDs never repeat R2 PUT. A lost result requires operator inspection; there is no automatic retry loop. Tombstones are removed after 93 days.
- A shared pilot code is a temporary admission control, not individual authentication or a per-user rate limit. Rotate it if leaked. Do not embed it in frontend environment variables. Public launch needs individual authentication/bot and edge rate controls.

These limits are NOT a monetary billing cap. Rejected traffic, database operations, stored data, cleanup and provider-side backups can still incur charges. Budget alerts only notify. Keep the Worker Free plan if appropriate, inspect account billing and R2 lifecycle settings before enabling. Do not automatically upgrade a plan.

## Deployment (not performed by adding these files)

Run `pnpm install --frozen-lockfile` first. Wrangler is pinned in this package; use `pnpm exec wrangler` for the commands below. `pnpm check:deploy` validates the Worker bundle without publishing. Use `pnpm exec wrangler login` to authenticate in your browser; never paste account tokens into chat or source files.

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

### Local integration smoke test

On a fresh local database: apply migrations with `pnpm exec wrangler d1 migrations apply otw-observations --local`, then enable its limits row with `pnpm exec wrangler d1 execute otw-observations --local --command "UPDATE limits SET enabled=1 WHERE id=1"`. Start `pnpm exec wrangler dev --ip 127.0.0.1 --port 8787 --var INTAKE_ENABLED:true --var SUBMISSION_TOKEN:local-test-only` and run `node tests/local-smoke.mjs` in a second terminal. This test consumes the local daily quota; use fresh local state for another run. It never sends to a remote host.

Verified with Wrangler 4.129.0/workerd: actual local D1 migration and trigger, R2 writes, unauthorized rejection, duplicate receipt reuse, and 36 unique submissions (35 concurrent after the first) accepting exactly 30 and rejecting six. Worker deployment dry-run also passes. These checks do not constitute a remote deployment or iPhone test.

References: [D1 SQL](https://developers.cloudflare.com/d1/sql-api/sql-statements/), [R2 Worker API](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/), [budget alerts](https://developers.cloudflare.com/billing/manage/budget-alerts/).
