# 50U Readiness Runbook

> Scope: 50 paid user readiness after Phase 7 read-only gray validation passed.
> Owner: Ops / Engineering / Customer Success.
> Rule: This runbook is operational documentation only. Do not run production uploads, reanalysis, QA, aggregate/export smoke, modern compare, or production business APIs without Erika's explicit authorization.

## Operating Rules

- Phase 1-6 Customer Issue / Customer Label core algorithms remain frozen.
- `Not Breathable` semantics remain frozen. Record anomalies first; do not change logic during 50U operations unless a separate fix task is opened and approved.
- Representative Evidence must come from a source review with a locatable evidence span. `cluster_propagated=true` and unverified evidence cannot be used as frontstage Representative Evidence.
- `50U-T2` quality warnings are currently a local deterministic helper, not a production `warnings_json` integration. Treat its warning types as manual investigation categories until a separate production integration is approved.
- Credit compensation must be append-only: write a positive `credit_ledger` refund entry. Never edit or delete historical ledger rows.
- Keep every incident tied to `user_id`, `job_id`, `session_id`, product identifier, time window, before/after counters, and exact user-visible impact.

## Key Systems

| Area | Source of truth | Notes |
|------|-----------------|-------|
| Upload job lifecycle | `upload_jobs` | Status should move `queued -> processing -> done` or `failed`; `trace_json` stores stage timings and errors. |
| Review/session data | `sessions`, `comments` | `sessions.warnings_json` currently stores taxonomy coverage warnings. `comments.review_date` is normalized filter/index date; raw `comments.date` remains display text. |
| Worker queue | RQ queue `clueai`, Redis, `worker`, `scheduler` containers | Default RQ timeout is `RQ_JOB_TIMEOUT_SECONDS=1800`. Scheduler scans stale `processing` jobs older than 15 minutes and retries up to 2 times. |
| LLM usage | `llm_usage_log` | Includes cache rows with `cache_hit=true`, zero tokens, zero cost. |
| Credit | `user_credits`, `credit_ledger` | `review_analyze` costs 1 credit per analyzed review; `insight` costs 6; export costs 1 per export route. |
| Analytics | `analytics_events` | Analysis completion writes `analysis_job_complete` best-effort and does not block the job. |
| Ops alerts | `FEISHU_OPS_WEBHOOK`, `OPS_WEBHOOK_PLATFORM`, `OPS_WEBHOOK_SECRET` | Used by stale-job scan, budget guard, and daily cost digest when configured. |

## Incident Record

Use this shape for every 50U incident or near miss:

```md
### Incident: <short title>

- Time window: <YYYY-MM-DD HH:mm TZ> to <YYYY-MM-DD HH:mm TZ>
- Severity: S0 / S1 / S2
- Reporter: <user / CS / ops / automated check>
- User ID:
- Product / variant:
- Upload job ID:
- Session ID:
- Sample size:
- User-visible symptom:
- Expected behavior:
- Actual behavior:
- Allowed production actions in this investigation:
- Explicitly forbidden actions:
- Credit before/after:
- LLM usage before/after:
- Analytics before/after:
- Upload job before/after:
- Evidence / label notes:
- Decision: observe / compensate / retry after approval / rollback / open fix task
- Follow-up owner and due time:
```

Severity guidance:

| Severity | Trigger | Required action |
|----------|---------|-----------------|
| S0 | Unexpected credit/LLM spend, data deletion/corruption, widespread upload failure, unauthorized production write | Stop rollout immediately, preserve evidence, get Erika approval before any compensating write. |
| S1 | Single-user upload blocked, job stuck/failed after retry, results missing or unusable | Stop that user's operation, diagnose from DB/logs, compensate only if ledger proves overcharge. |
| S2 | Label/evidence/date quality anomaly with results still available | Record exact examples, do not patch frozen logic inline, decide whether to open a follow-up fix. |

## SOP: Upload Failure

Symptoms:

- Upload request fails before a `job_id` is returned.
- A returned job stays `queued`, becomes `failed`, or has `processed_rows < total_rows`.
- User reaches results page but sees missing/partial analysis.

Read-only checks:

```sql
SELECT id, user_id, status, source_filename, product_id, product_ref_id, variant_ref_id,
       total_rows, processed_rows, session_id, retry_count, error_message,
       created_at, updated_at, completed_at,
       trace_json
FROM upload_jobs
WHERE user_id = <USER_ID>
ORDER BY created_at DESC
LIMIT 10;
```

```sql
SELECT id, total_reviews, positive_count, negative_count, warnings_json, created_at
FROM sessions
WHERE user_id = <USER_ID> AND id = <SESSION_ID>;
```

```sql
SELECT COUNT(*) AS comments,
       COUNT(*) FILTER (WHERE is_processed = 1) AS processed,
       COUNT(*) FILTER (WHERE aspects_json IS NOT NULL) AS has_analysis,
       COUNT(*) FILTER (WHERE review_date IS NOT NULL) AS normalized_dates
FROM comments
WHERE user_id = <USER_ID> AND session_id = <SESSION_ID>;
```

Container checks for Erika/ECS operator:

```bash
cd /opt/clueai/deploy
docker compose ps
docker compose logs api --tail 100
docker compose logs worker --tail 150
docker compose logs scheduler --tail 100
```

Decision tree:

| Observation | Meaning | Action |
|-------------|---------|--------|
| No `upload_jobs` row | Request failed before job creation, often validation/auth/quota precheck | Check API response and quota/credit balance. No job retry exists. |
| `status='queued'` for more than 5 minutes | Worker queue may not be consuming | Check worker container, Redis/RQ queue, scheduler logs. Do not re-upload without authorization. |
| `status='processing'` and `updated_at` older than 15 minutes | Stale-job scanner should auto-retry if `session_id` exists and retry count is below limit | Check whether scheduler is running; if no auto action occurs, escalate before manual retry. |
| `status='failed'` with `session_id` empty | Failure before session/comment creation | No results should exist; credit should normally be unchanged. |
| `status='failed'` with `session_id` present | Partial write or analysis failure | Compare comments, processed count, credit ledger, LLM rows. Stop before reanalysis unless approved. |
| `status='done'` but user cannot see results | Read path/UI/session permission issue | Check session ownership and results route separately under approved read-only scope. |

Do not:

- Re-upload the same file in production as a "quick retry" unless the production write-path smoke template has been approved.
- Call `/analysis/reanalyze` without a separate approval.
- Delete the session/job as cleanup before evidence is recorded.

## SOP: Worker Stuck / Job Stuck

Existing automation:

- `workers.periodic_jobs.scan_stale_jobs` scans `upload_jobs` with `status='processing'` and stale `updated_at`.
- Threshold: 15 minutes.
- Auto retry limit: 2 retries when `session_id` exists.
- If retries are exhausted, the job is marked `failed` and an ops alert is sent when `FEISHU_OPS_WEBHOOK` is configured.

Read-only checks:

```sql
SELECT id, user_id, session_id, status, total_rows, processed_rows,
       retry_count, error_message, created_at, updated_at, completed_at,
       trace_json->>'total_duration_ms' AS total_duration_ms,
       trace_json->>'error' AS trace_error
FROM upload_jobs
WHERE status IN ('queued', 'processing', 'failed')
ORDER BY updated_at ASC
LIMIT 50;
```

```sql
SELECT id, user_id, session_id, status, retry_count, error_message,
       trace_json->'stages' AS stages
FROM upload_jobs
WHERE id = <JOB_ID> AND user_id = <USER_ID>;
```

Container checks for Erika/ECS operator:

```bash
cd /opt/clueai/deploy
docker compose ps worker scheduler redis
docker compose logs worker --tail 200
docker compose logs scheduler --tail 200
docker compose exec worker rq info -u redis://redis:6379/0
```

Actions:

- If the worker container is down or unhealthy, restart/deploy through the normal deployment responsibility split.
- If Redis is down, stop uploads and preserve current job statuses.
- If stale scan did not run, verify the `scheduler` container before manual intervention.
- If the job is already `failed`, do not manually set it back to `queued` unless Erika approves a retry/reanalysis plan with expected credit and LLM cost.
- If a stuck job already consumed credit, reconcile before retry; a second run can double-charge unless compensation is planned.

## SOP: LLM Cost Anomaly

Triggers:

- Daily cost digest is higher than expected.
- A single user/job dominates LLM cost.
- LLM usage count is far above uploaded review count.
- Budget guard blocks user/global usage.

Read-only checks:

```sql
SELECT DATE(created_at) AS day,
       provider,
       model_name,
       COUNT(*) AS rows,
       SUM(tokens_in) AS tokens_in,
       SUM(tokens_out) AS tokens_out,
       SUM(cost_yuan) AS cost_yuan,
       SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
FROM llm_usage_log
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), provider, model_name
ORDER BY day DESC, cost_yuan DESC;
```

```sql
SELECT user_id, session_id,
       COUNT(*) AS rows,
       SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
       SUM(cost_yuan) AS cost_yuan,
       SUM(tokens_in) AS tokens_in,
       SUM(tokens_out) AS tokens_out
FROM llm_usage_log
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY user_id, session_id
ORDER BY cost_yuan DESC
LIMIT 20;
```

```sql
SELECT id, user_id, status, total_rows, processed_rows, session_id,
       trace_json->>'llm_calls' AS llm_calls,
       trace_json->>'cache_hits' AS cache_hits,
       trace_json->>'total_cost_yuan' AS total_cost_yuan,
       created_at, completed_at
FROM upload_jobs
WHERE created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

Expected relationships:

- For one upload job, `llm_usage_log` rows should roughly match analyzed comments, including cache rows.
- Non-cache LLM calls should be at or below analyzed reviews. Clustering/cache may reduce calls.
- `trace_json.total_cost_yuan` should be close to the sum of non-cache `llm_usage_log.cost_yuan` for that session/job.
- `analytics_events.properties.total_cost_yuan` for `analysis_job_complete` should match the same trace value when analytics logging succeeds.

Actions:

- If budget guard tripped, keep LLM writes stopped and notify Erika with user/job breakdown.
- If cost rows are duplicated, stop further write-path smoke and prepare a compensation/audit task.
- If `llm_usage_log` is missing but `trace_json` has cost, treat analytics/cost dashboards as incomplete and open an observability follow-up.

## SOP: Credit Mischarge And Compensation

Read-only checks:

```sql
SELECT balance, monthly_grant, trial_expires_at, last_refill_at, updated_at
FROM user_credits
WHERE user_id = <USER_ID>;
```

```sql
SELECT id, delta, reason, ref_id, balance_after, created_at
FROM credit_ledger
WHERE user_id = <USER_ID>
ORDER BY created_at DESC
LIMIT 50;
```

```sql
SELECT reason, ref_id, COUNT(*) AS rows, SUM(delta) AS delta_sum,
       MIN(created_at) AS first_seen, MAX(created_at) AS last_seen
FROM credit_ledger
WHERE user_id = <USER_ID>
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY reason, ref_id
ORDER BY last_seen DESC;
```

Expected charge map:

| Path | Ledger reason | Expected credit |
|------|---------------|-----------------|
| Upload analysis | `review_analyze` | `-1 * analyzed review count`, `ref_id=<job_id>` |
| Product insight / aggregate results | `insight` | `-6` per authorized insight request |
| Export | `export` | `-1` per authorized export request |
| Refund/top-up/monthly grant | `refund` / `topup` / `monthly_grant` | Positive deltas only |

Compensation rules:

- Confirm the incorrect debit from `credit_ledger`; do not rely only on user screenshots.
- Refund exactly the overcharged amount.
- Use `reason='refund'` and a `ref_id` that links to the original job/request or incident ID.
- Never mutate old ledger rows or manually set `balance` without a matching ledger entry.
- Get Erika approval before executing any refund in production.

Approved compensation command template for Erika/ECS operator:

```bash
cd /opt/clueai/deploy
docker compose exec api python -c "from review_analyzer.quota import credit_refund; credit_refund(<USER_ID>, <AMOUNT>, reason='refund', ref_id='<INCIDENT_OR_ORIGINAL_REF>')"
```

Post-compensation verification:

```sql
SELECT balance, updated_at
FROM user_credits
WHERE user_id = <USER_ID>;

SELECT id, delta, reason, ref_id, balance_after, created_at
FROM credit_ledger
WHERE user_id = <USER_ID>
ORDER BY created_at DESC
LIMIT 5;
```

## SOP: Analytics / Credit / LLM Usage Reconciliation

Run after an approved production write-path smoke or a real user incident.

```sql
SELECT id, user_id, status, total_rows, processed_rows, session_id,
       trace_json->>'llm_calls' AS llm_calls,
       trace_json->>'cache_hits' AS cache_hits,
       trace_json->>'total_cost_yuan' AS trace_cost_yuan,
       created_at, completed_at
FROM upload_jobs
WHERE user_id = <USER_ID> AND id = <JOB_ID>;
```

```sql
SELECT COUNT(*) AS comments,
       COUNT(*) FILTER (WHERE is_processed = 1) AS processed,
       COUNT(*) FILTER (WHERE aspects_json IS NOT NULL) AS analyzed,
       COUNT(*) FILTER (WHERE aspects_json->>'cluster_propagated' = 'true') AS propagated_comments
FROM comments
WHERE user_id = <USER_ID> AND session_id = <SESSION_ID>;
```

```sql
SELECT reason, ref_id, COUNT(*) AS rows, SUM(delta) AS delta_sum
FROM credit_ledger
WHERE user_id = <USER_ID>
  AND created_at BETWEEN <START_TS> AND <END_TS>
GROUP BY reason, ref_id
ORDER BY reason, ref_id;
```

```sql
SELECT COUNT(*) AS usage_rows,
       SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
       SUM(CASE WHEN NOT cache_hit THEN 1 ELSE 0 END) AS llm_calls,
       SUM(cost_yuan) AS cost_yuan
FROM llm_usage_log
WHERE user_id = <USER_ID> AND session_id = <SESSION_ID>;
```

```sql
SELECT id, event_name, properties, created_at
FROM analytics_events
WHERE user_id = <USER_ID>
  AND event_name = 'analysis_job_complete'
  AND properties->>'session_id' = '<SESSION_ID>'
ORDER BY created_at DESC;
```

Pass criteria:

- `upload_jobs.status='done'`.
- `processed_rows = total_rows`.
- `comments.processed = comments.comments`.
- `credit_ledger` contains the expected `review_analyze` delta once for the job.
- LLM usage rows are explainable by comments/cache. Missing analytics is non-blocking but must be recorded.
- No extra `insight`, `export`, `ask`, `competitor`, `copywriter`, or `translate` ledger deltas unless they were explicitly authorized.

## SOP: `review_date` / Date Filter Anomaly

Facts:

- `comments.date` is raw display text.
- `comments.review_date` is normalized date used for filtering/indexes.
- Amazon text dates such as `Reviewed in the United States on July 1, 2026` should normalize into `YYYY-MM-DD`.

Read-only checks:

```sql
SELECT COUNT(*) AS total,
       COUNT(review_date) AS normalized,
       COUNT(*) FILTER (WHERE review_date IS NULL AND COALESCE(date, '') <> '') AS unparsed_non_empty_raw_dates,
       MIN(review_date) AS earliest_review_date,
       MAX(review_date) AS latest_review_date
FROM comments
WHERE user_id = <USER_ID> AND session_id = <SESSION_ID>;
```

```sql
SELECT id, date, review_date, LEFT(content, 160) AS content_preview
FROM comments
WHERE user_id = <USER_ID>
  AND session_id = <SESSION_ID>
  AND date ILIKE 'Reviewed in%'
ORDER BY id
LIMIT 20;
```

```sql
SELECT id, date, review_date, LEFT(content, 160) AS content_preview
FROM comments
WHERE user_id = <USER_ID>
  AND session_id = <SESSION_ID>
  AND review_date BETWEEN DATE '<START_DATE>' AND DATE '<END_DATE>'
ORDER BY review_date DESC, id DESC
LIMIT 20;
```

Investigation notes:

- If raw `date` is empty, `review_date` may correctly be `NULL`.
- If Amazon text is non-empty but `review_date` is `NULL`, record the exact raw date string and open a parser/backfill follow-up.
- If UI date filter misses rows that the SQL range returns, investigate frontend/API filter parameter mapping.
- Do not backfill production dates manually during 50U operations without a migration/backfill plan and Erika approval.

## SOP: Customer Label / Evidence Anomaly

Record these cases even when the page still renders:

- `Not Breathable` appears too broad/narrow.
- Representative Evidence is missing for a visible Top Issue / Top Label with enough source reviews.
- Representative Evidence text cannot be found in any representative comment.
- A positive waterproof phrase enters `Water Leaks Through`.
- `cluster_propagated=true` occurrences dominate a Top row.
- Broad/internal labels such as `Quality`, `Waterproofing`, `Other`, or aspect-only labels appear as frontstage Top Issue/Label.
- `warnings_json` contains taxonomy warnings after an otherwise successful run.

Required record fields:

```md
- Session ID:
- User ID:
- Product/sub_category:
- Label type: issue / highlight
- Display label:
- Canonical key if visible:
- Mention count / review count / share:
- Representative Evidence:
- Evidence source comment ID:
- Evidence found in source comment: yes / no
- `evidence_verified`: true / false / unknown
- `cluster_propagated`: true / false / unknown
- Sentiment/rating of the source comment:
- Date filter applied:
- Why this is suspicious:
- Suggested next step: observe / add gold sample / open fix / block rollout
```

Manual 50U-T2 warning categories:

| Warning type | Meaning | Default response |
|--------------|---------|------------------|
| `customer_label_single_label_dominance` | One label dominates a category with high mention share | Sample top comments and confirm it is not a collapsed broad label. |
| `customer_label_low_representative_evidence_ratio` | Too many frontstage occurrences lack verified evidence | Stop release expansion for that category/session until examples are reviewed. |
| `customer_label_high_cluster_propagated_ratio` | Propagated occurrences dominate total occurrences | Confirm Top rows are not counted or represented by propagated evidence. |
| `customer_label_broad_internal_top_label` | Internal/broad label reached frontstage | Open catalog/alias governance task; do not rename live labels ad hoc. |
| `customer_label_long_tail_expansion` | Label set exploded relative to review count | Review candidate label quality and taxonomy boundary. |

## 50 User Pre-Launch Checklist

- [ ] Phase 7 fourth production read-only gray validation is recorded as PASS.
- [ ] `50U-T2` focused regression has passed on the deploy candidate.
- [ ] `50U-T3` runbook and production write-path smoke authorization template are reviewed.
- [ ] `50U-T1` production write-path smoke has explicit Erika approval, or launch is blocked until it does.
- [ ] Production smoke scope defines sample count, session count, max credit delta, max LLM cost, stop conditions, and compensation rules.
- [ ] `worker`, `scheduler`, `redis`, `api`, `frontend`, `nginx` are healthy after deploy.
- [ ] `FEISHU_OPS_WEBHOOK` or equivalent ops alert channel is configured if alerts are expected.
- [ ] Budget guard thresholds are intentionally configured or intentionally disabled and recorded.
- [ ] Credit refund policy and response owner are confirmed.
- [ ] Customer-facing response time expectations are confirmed for upload failure, stuck job, mischarge, and label quality issues.
- [ ] No unauthorized production upload, reanalysis, QA, aggregate/export smoke, modern compare, or production business API request has been performed in readiness prep.

## 50 User Daily Checks

Run once per business day during the first 50 paid users:

```sql
SELECT status, COUNT(*) AS jobs,
       SUM(total_rows) AS total_rows,
       SUM(processed_rows) AS processed_rows
FROM upload_jobs
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY status;
```

```sql
SELECT id, user_id, status, total_rows, processed_rows, retry_count,
       error_message, created_at, updated_at, completed_at
FROM upload_jobs
WHERE created_at >= NOW() - INTERVAL '24 hours'
  AND status <> 'done'
ORDER BY updated_at ASC;
```

```sql
SELECT user_id, SUM(cost_yuan) AS cost_yuan, COUNT(*) AS usage_rows,
       SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
FROM llm_usage_log
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY user_id
ORDER BY cost_yuan DESC
LIMIT 20;
```

```sql
SELECT reason, COUNT(*) AS rows, SUM(delta) AS delta_sum
FROM credit_ledger
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY reason
ORDER BY reason;
```

```sql
SELECT s.id, s.user_id, s.product_id, s.warnings_json, s.created_at
FROM sessions s
WHERE s.created_at >= NOW() - INTERVAL '24 hours'
  AND s.warnings_json IS NOT NULL
ORDER BY s.created_at DESC;
```

Daily pass criteria:

- No stuck `processing` jobs older than the stale threshold.
- Failed jobs are triaged or have an owner.
- LLM cost and per-user concentration are explainable.
- Credit ledger deltas match authorized actions.
- No repeated `warnings_json` or label/evidence anomaly pattern is emerging.

## 50 User Weekly Checks

- Run the `50U-T2` focused regression on the current branch before any release candidate.
- Review top 10 failed/stale jobs and their `trace_json` stage distribution.
- Review LLM cost per analyzed review and cache hit trend.
- Review credit refunds and reasons; every refund must link to an incident or support case.
- Review sessions with `warnings_json` and any manually recorded label/evidence anomalies.
- Review date normalization nulls for recent uploads, especially Amazon text dates.
- Review customer-facing support messages for repeated confusion around credits, upload status, or label explanations.
- Decide whether any anomaly should become a gold sample, catalog alias change, or separate fix task.
