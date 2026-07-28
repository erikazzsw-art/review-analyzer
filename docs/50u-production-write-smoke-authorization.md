# 50U Production Write-Path Smoke Authorization Template

> Do not execute this smoke until Erika fills and approves the authorization block.
> This template exists to make production write-path scope explicit before `50U-T1`.

## Authorization Block

```md
### 50U-T1 Production Write-Path Smoke Authorization

- Approval date/time:
- Approver: Erika
- Executor:
- Production commit / deploy run:
- Product / variant:
- Source sample file:
- Sample review count:
- Session count:
- Max allowed credit delta:
- Max allowed LLM cost:
- Max allowed LLM non-cache calls:
- Allowed API endpoints:
- Explicitly forbidden API endpoints:
- Allowed DB operations:
- Explicitly forbidden DB operations:
- Stop conditions accepted: yes / no
- Credit compensation rule accepted: yes / no
- Session/job cleanup rule accepted: yes / no
- Notes:
```

Recommended smallest scope:

| Field | Recommended value |
|-------|-------------------|
| Sample review count | 10-20 reviews |
| Session count | 1 new upload session |
| Expected upload credit | `sample_review_count * 1` credits for `review_analyze` |
| Max upload credit cap | Expected upload credit only; no hidden extra credit deltas |
| Expected LLM non-cache calls | `<= sample_review_count`; cache/clustering may reduce it |
| Max LLM cost cap | Erika-filled RMB cap before execution, for example `<= ¥1.00` for the smoke budget |
| Polling window | Up to 30 minutes unless worker health suggests stopping earlier |

## Allowed Only If Approved

- `POST /uploads` for the approved small sample only.
- `GET /analysis/jobs/{job_id}` to poll the approved job.
- `GET /analysis/sessions/{session_id}/results` after the approved job reaches `done`.
- `GET /credits/balance` and `GET /credits/ledger` for the approved smoke user.
- Read-only SQL `SELECT` queries needed for before/after counters.

## Explicitly Forbidden Unless Separately Approved

- `POST /analysis/reanalyze`.
- `GET/POST /analysis/results` aggregate smoke.
- Any export route, including module export and full export.
- QA / ask-review endpoints.
- Modern compare / competitor compare.
- ASIN fetch or scraper jobs.
- Bulk uploads beyond the approved sample count/session count.
- Manual production SQL writes, except a separately approved credit refund or cleanup action.
- Any modification to Phase 1-6 core label algorithms or `Not Breathable` semantics.

## Preflight Snapshot

Run read-only snapshots immediately before the approved smoke. Replace placeholders before use.

```sql
SELECT balance, monthly_grant, trial_expires_at, updated_at
FROM user_credits
WHERE user_id = <USER_ID>;
```

```sql
SELECT COUNT(*) AS ledger_rows, COALESCE(SUM(delta), 0) AS ledger_delta
FROM credit_ledger
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>;
```

```sql
SELECT COUNT(*) AS usage_rows, COALESCE(SUM(cost_yuan), 0) AS cost_yuan
FROM llm_usage_log
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>;
```

```sql
SELECT COUNT(*) AS analytics_rows
FROM analytics_events
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>;
```

```sql
SELECT COUNT(*) AS jobs
FROM upload_jobs
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>;
```

Container health preflight for Erika/ECS operator:

```bash
cd /opt/clueai/deploy
docker compose ps
docker compose logs worker --tail 50
docker compose logs scheduler --tail 50
```

Pass criteria before starting:

- Containers are running and healthy enough for the intended path.
- The smoke user has enough credits for the expected `review_analyze` debit.
- No stale or failed production job is already being investigated for the same user/product.
- Start timestamp is recorded for after-the-fact reconciliation.

## Execution Log

```md
### Execution

- Start timestamp:
- Upload request:
- Returned job_id:
- Returned session_id:
- Poll results:
  - T+1m:
  - T+5m:
  - T+15m:
  - T+30m:
- Final job status:
- Results route status:
- Notes:
```

## Stop Conditions

Stop immediately and do not broaden the smoke when any item is true:

- Upload returns 5xx, auth/session error, or malformed response.
- No `job_id` is returned.
- Job remains `queued` for more than 5 minutes.
- Job remains `processing` with no `processed_rows` movement for more than 15 minutes.
- Job is marked `failed`.
- `processed_rows > total_rows` or comments/session counts do not match the approved sample.
- Credit ledger delta exceeds expected `review_analyze` debit.
- Any `insight`, `export`, `ask`, `competitor`, `copywriter`, or `translate` ledger delta appears without authorization.
- LLM non-cache calls exceed approved max.
- LLM cost exceeds approved cap.
- Analytics, LLM usage, or trace rows are missing in a way that prevents audit.
- Results contain unlocatable Representative Evidence, `cluster_propagated=true` Representative Evidence, or positive waterproof evidence under `Water Leaks Through`.
- `review_date` filtering/date span is visibly wrong for the smoke sample.
- Worker, scheduler, Redis, API, or DB health becomes unstable.

## After Snapshot

```sql
SELECT id, user_id, status, total_rows, processed_rows, session_id,
       retry_count, error_message, trace_json, created_at, updated_at, completed_at
FROM upload_jobs
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>
ORDER BY created_at DESC;
```

```sql
SELECT COUNT(*) AS comments,
       COUNT(*) FILTER (WHERE is_processed = 1) AS processed,
       COUNT(*) FILTER (WHERE aspects_json IS NOT NULL) AS analyzed,
       COUNT(*) FILTER (WHERE review_date IS NOT NULL) AS normalized_dates
FROM comments
WHERE user_id = <USER_ID> AND session_id = <SESSION_ID>;
```

```sql
SELECT id, delta, reason, ref_id, balance_after, created_at
FROM credit_ledger
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>
ORDER BY created_at;
```

```sql
SELECT model_name, provider, cache_hit, COUNT(*) AS rows,
       SUM(tokens_in) AS tokens_in,
       SUM(tokens_out) AS tokens_out,
       SUM(cost_yuan) AS cost_yuan
FROM llm_usage_log
WHERE user_id = <USER_ID>
  AND session_id = <SESSION_ID>
GROUP BY model_name, provider, cache_hit
ORDER BY cost_yuan DESC;
```

```sql
SELECT id, event_name, properties, created_at
FROM analytics_events
WHERE user_id = <USER_ID>
  AND created_at >= <START_TS>
ORDER BY created_at;
```

## Pass Criteria

- One approved upload session is created.
- Job reaches `done` within the approved polling window.
- `processed_rows = total_rows = approved sample review count`.
- Comments are inserted and processed for the new session.
- `credit_ledger` contains exactly the expected `review_analyze` debit and no unauthorized debit.
- `llm_usage_log` rows and total cost are within the approved cap.
- `analysis_job_complete` analytics event exists or, if missing, the non-blocking analytics failure is recorded.
- Session results are readable and contain no `embedding` payload leakage.
- Representative Evidence is locatable, verified, and not cluster-propagated.
- Date normalization and date filtering match the smoke sample.

## Rollback And Compensation

Default rule:

- Preserve the smoke session/job for audit unless Erika explicitly approves cleanup.
- Stop after the first failure; do not retry by re-uploading unless a new authorization block is approved.
- Use append-only refunds for credit errors.

Credit refund template for Erika/ECS operator:

```bash
cd /opt/clueai/deploy
docker compose exec api python -c "from review_analyzer.quota import credit_refund; credit_refund(<USER_ID>, <AMOUNT>, reason='refund', ref_id='<INCIDENT_OR_ORIGINAL_REF>')"
```

Cleanup template:

```md
- Cleanup needed: yes / no
- Rows affected estimate:
- Tables involved:
- Reason:
- Backup/PITR confirmed: yes / no
- Erika approval:
```

Production deploy rollback follows the standard deployment document. Do not mix code rollback with data compensation until the incident record states which symptom each action addresses.

## Result Report

```md
### 50U-T1 Production Write-Path Smoke Result

- Authorization block:
- Actual sample review count:
- Actual session count:
- Job ID:
- Session ID:
- Final status:
- Duration:
- Credit delta:
- LLM calls:
- LLM cost:
- Analytics rows:
- Date/review_date check:
- Representative Evidence check:
- Stop conditions hit:
- Compensation performed:
- Final decision: PASS / FAIL / STOP
- Follow-up:
```
