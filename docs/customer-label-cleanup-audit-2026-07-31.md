# Customer Label Cleanup Audit — 2026-07-31

## Decision

5.9.8 and 5.9.9 produced useful safety ideas, but they also left substantial experiment debt in the main branch.

Current cleanup posture:

- Keep production-critical v1 occurrence/evidence/display behavior until the next label architecture is ready.
- Freeze 5.9.9 v2 frontstage expansion; treat it as an archived compatibility experiment unless explicitly revived.
- Keep Step 9.1 review signal work as the likely next direction, but keep it shadow-only until it has real integration acceptance.
- Remove or untrack generated artifacts from `tmp/`; future artifacts should stay local.

## Production-Critical Keep

These files are still on active read/write paths and must not be removed without replacement tests:

| File | Why It Stays | Main Runtime References |
| --- | --- | --- |
| `backend_api/app/services/specific_issue.py` | Current Customer Issue / Customer Label occurrence projection, evidence gate, display gate, Top10 aggregation helpers. Large and debt-heavy, but active. | `workers/jobs.py`, `backend_api/app/routes/analysis.py`, `backend_api/app/routes/export.py`, `review_analyzer/exporter.py`, `review_analyzer/insight_engine.py` |
| `backend_api/app/services/customer_label_catalog.py` | Canonical label and alias resolution used by `specific_issue.py`; migration-backed catalog layer. | `specific_issue.py`, `customer_label_v2_shadow.py` |
| `migrations/058_customer_label_catalog_alias_candidates.sql` | Database schema for customer label catalog and candidates. Keep if production/staging DBs may already have applied it. | Database migration history |
| `backend_api/tests/fixtures/customer_label_*gold*.json` and focused gold tests | Regression protection for known label failures. They are bulky but useful until a smaller locked eval set replaces them. | Pytest |

## Keep But Refactor

These are live or semi-live, but should be reduced after the next label direction is chosen:

| Area | Risk | Recommended Refactor |
| --- | --- | --- |
| Waders-specific rules in `specific_issue.py` | Sample-overfit regex rules solve local cases but do not generalize to other categories. | Extract to a category-specific module or data file; keep only generic evidence/display gates in `specific_issue.py`. |
| Frontend duplicate label guards in `frontend/src/lib/customer-labels.ts` | Backend and frontend can disagree about which labels display. | Move canonical filtering to backend payload; frontend should render backend-approved occurrences only. |
| `customer_label_occurrences` schema v1 | Useful structure, but mixed with category-specific repair logic. | Preserve the schema idea; separate `signal_type`, `business_route`, `label_candidate`, and `display_occurrence` responsibilities. |

## Archive Or Isolate

These are mainly 5.9.9 v2 gray-run scaffolding. They are not useless, but should not remain as an active production direction while Step 9 is `FIX_REQUIRED_BEFORE_GRAY_EXPAND`.

| File | Current Use | Recommended Action |
| --- | --- | --- |
| `backend_api/app/services/customer_label_v2_shadow.py` | Runtime import only through default-off v2 frontstage path and tests/scripts. | Move behind an explicit experimental package or keep temporarily with `deprecated/experimental` status. |
| `backend_api/app/services/customer_label_v2_candidate_pool.py` | Used by tests/replay artifacts, not main production ingestion. | Archive with v2 experiment unless candidate review is revived. |
| `backend_api/app/services/customer_label_v2_maturity.py` | Used by v2 shadow/frontstage readiness. | Archive with v2 experiment. |
| `backend_api/app/services/customer_label_v2_frontstage.py` | Imported by active routes/exporter, but default flag is off. | Keep compatibility wrapper short-term; later remove route/export imports if v2 is abandoned. |
| `backend_api/app/services/customer_label_v2_frontstage_acceptance.py` | Test/runbook-only acceptance pack. | Archive. |
| `backend_api/app/services/customer_label_v2_frontstage_runbook.py` | Test/runbook-only rollback drill. | Archive. |
| `backend_api/app/services/customer_label_v2_bad_case_memory.py` | Replay/debug-only vector memory lite. | Archive unless used by a real review queue. |
| `scripts/customer_label_v2_waders_shadow_replay.py` | Large replay harness for v2 experiment. | Move to `scripts/archive/` or remove after preserving summary docs. |
| `docs/5.9.9-step*.md` | Historical record. | Keep final decision docs; compress detailed step docs later. |

## Step 9.1 Status

Step 9.1 is different from 5.9.9 v2: it addresses the upstream routing problem that caused labels to confuse product pros/cons with people, places, motives, expectations, accessories, logistics, old products, and generic emotion.

Current files are untracked and shadow-only:

- `backend_api/app/services/review_signal_shadow.py`
- `scripts/review_signal_step9_1_shadow_replay.py`
- `backend_api/tests/test_review_signal_step9_1_shadow.py`
- `backend_api/tests/test_review_signal_step9_1_gold_assimilation.py`
- `backend_api/tests/fixtures/review_signal_step9_1_airpods_minimal.json`
- `docs/5.9.9-step9.1-review-signal-layer-minimal.md`

Recommended action:

- Keep these isolated as the next experimental direction.
- Do not connect to frontstage or replace Customer Issue / Customer Label until a locked human eval set passes.
- If adopted, use it to shrink `specific_issue.py`, not to add another parallel display layer.

## Delete Or Untrack Candidates

Generated `tmp` artifacts should not be committed. The current tracked list is:

```text
tmp/5.9.9-step3-verifier-safety-gate/waders-shadow-summary.json
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool-reviewed.csv
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool-reviewed.json
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool.csv
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool.json
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/frontstage-read-path-contract.json
tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/waders-shadow-summary.json
tmp/5.9.9-step7.5-frontstage-readiness-dry-run/frontstage-readiness-dry-run.json
tmp/5.9.9-step7.6-frontstage-config-kill-switch-observability/frontstage-config-kill-switch-observability.json
tmp/5.9.9-step7.7-frontstage-gray-run-rollback-drill/gray-run-rollback-drill.json
tmp/5.9.9-step7.8-frontstage-go-no-go-acceptance-pack/go-no-go-acceptance-pack.json
tmp/5.9.9-step8-vector-bad-case-memory-lite/vector-bad-case-memory-lite.json
tmp/5.9.9-step9-erika-led-production-truth-check/session124-intake.json
```

Cleanup performed in this pass:

- Added `/tmp/` to `.gitignore`.
- Ran `git rm --cached` for the 13 tracked `tmp` files above.
- Local files remain on disk; they are only removed from Git tracking.

Equivalent command:

```bash
git rm --cached tmp/5.9.9-step3-verifier-safety-gate/waders-shadow-summary.json
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool-reviewed.csv
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool-reviewed.json
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool.csv
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/candidate-pool.json
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/frontstage-read-path-contract.json
git rm --cached tmp/5.9.9-step6-v2-frontstage-feature-flag-read-path/waders-shadow-summary.json
git rm --cached tmp/5.9.9-step7.5-frontstage-readiness-dry-run/frontstage-readiness-dry-run.json
git rm --cached tmp/5.9.9-step7.6-frontstage-config-kill-switch-observability/frontstage-config-kill-switch-observability.json
git rm --cached tmp/5.9.9-step7.7-frontstage-gray-run-rollback-drill/gray-run-rollback-drill.json
git rm --cached tmp/5.9.9-step7.8-frontstage-go-no-go-acceptance-pack/go-no-go-acceptance-pack.json
git rm --cached tmp/5.9.9-step8-vector-bad-case-memory-lite/vector-bad-case-memory-lite.json
git rm --cached tmp/5.9.9-step9-erika-led-production-truth-check/session124-intake.json
```

## Proposed Cleanup Order

1. Add `/tmp/` to `.gitignore` so new local artifacts stop entering Git.
2. Untrack the 13 committed `tmp` files above while keeping local copies.
3. Mark 5.9.9 v2 services as archived/experimental in docs and tests.
4. Remove v2 imports from active result/export paths only after confirming no production flag relies on them.
5. Refactor `specific_issue.py` into:
   - generic occurrence schema and gates,
   - category-specific rule modules,
   - aggregation helpers.
6. Move frontend label filtering toward backend-approved rendering only.
7. Promote Step 9.1 only after locked eval acceptance, then use it to replace rather than pile onto v1/v2 rules.

## Risk Notes

- Directly deleting `specific_issue.py` logic would break current results, exports, and worker enrichment.
- Directly deleting `customer_label_v2_frontstage.py` would break imports in active routes/exporter even if the flag is off.
- Deleting migrations is unsafe once applied anywhere; prefer leaving migration history intact.
- Removing gold fixtures too early will make future cleanup blind.
