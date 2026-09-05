# Commercial Decision Commitment V1 — Production Readiness & Persistence Proof

**Date (UTC):** 2026-09-05  
**Mode:** Proof only — no feature / visual / deploy  
**Live observation:** `GET https://smartreplyai.net/dev/merchant-runtime-identity` → `git_sha`  
**Static corroboration:** live `merchant_ui_v2_{home,workspace}.js` + `commercial_decision_arc_production_v1.js` byte-match `0f2ebc5a…`

---

## 14 — Production line safety

| Item | Value |
|------|--------|
| CURRENT LIVE SHA | `0f2ebc5a5730cc015988d47446501170ce0b815f` |
| BRANCH TIP (committed) | `3e4603fd2481128ad732da340aa829e7d7c5d938` |
| CDC implementation | Present in **working tree** (not yet a clean commit SHA) |
| Live is ancestor of branch tip | **YES** (`git merge-base --is-ancestor 0f2ebc5a… HEAD` → 0) |
| CURRENT LINE SAFE | **YES** |

Candidate for a future exact-SHA gate must be a **clean commit** containing CDC; this proof does not create that commit or deploy.

---

## 1 — Migration safety

**No Alembic migration file.** DDL is additive SQLAlchemy model + `schema_commercial_decision_commitment_v1.ensure_*` (`db.create_all()`).

| Property | Result |
|----------|--------|
| Additive only | PASS — new table only |
| Destructive ALTER | NONE |
| Production backfill | NOT REQUIRED (zero rows OK) |
| Existing tables | UNTOUCHED |
| Nullable measurement/close fields | PASS |
| Rollback | Drop table / stop attach — no rewrite of peer tables |
| Forward failure | `ensure_*` logs warning; dashboard attach fail-closed to empty map |

### Table DDL (normative from `models.CommercialDecisionCommitment`)

**Table:** `commercial_decision_commitments`

**Columns:**  
`id` PK CHAR(36); `store_slug`; `opportunity_key`; `opportunity_family`; `opportunity_reason`; `active_opportunity_key` NULL; `action_chosen_at`; `action_summary`; `decision_snapshot_json`; `measurement_started_at` NULL; `measurement_due_at` NULL; `measurement_start_authority` NULL; `measurement_start_ref` NULL; `baseline_snapshot_json` NULL; `metric_key` NULL; `baseline_metric_value` NULL; `recheck_condition_frozen` NULL; `created_at`; `updated_at`; `closed_at` NULL; `close_reason` NULL; `close_note` NULL; `superseded_by_id` NULL

**Constraints / indexes:**

| Name | Definition |
|------|------------|
| PK | `id` |
| `uq_cdc_active_store_opportunity` | UNIQUE (`store_slug`, `active_opportunity_key`) — portable active uniqueness (`active_opportunity_key` = opportunity_key when open, NULL when closed) |
| `ix_cdc_store_opportunity` | (`store_slug`, `opportunity_key`) |
| `ix_cdc_store_closed_due` | (`store_slug`, `closed_at`, `measurement_due_at`) |
| Foreign keys | **none** |

**Partial unique note:** Production DB is PostgreSQL (`database_host_class=railway_private`). V1 uses the portable NULL-sentinel unique (equivalent intent to `WHERE closed_at IS NULL`), not a PG-only partial index. Concurrent insert proof uses DB IntegrityError.

**Sources:** `models.py`, `schema_commercial_decision_commitment_v1.py`

---

## Proof results (tests)

Gate: `tests/test_commercial_decision_commitment_production_readiness_v1.py` + existing `tests/test_commercial_decision_commitment_v1.py` → **27 passed**.

| Area | Result |
|------|--------|
| Concurrent accept (DB unique) | PASS — 1 ok / 11 IntegrityError |
| Tenant isolation | PASS — wrong store → `commitment_not_found`; routes use auth cookie slug only |
| Accept ≠ execute | PASS — started/baseline/due NULL |
| Measurement authorities | PASS — cartflow_execution + confirm; external refused; second start idempotent; baseline immutable |
| Clock derivation | PASS — T&lt;due UNDER; T==due RECHECK; T&gt;due RECHECK; no sleep |
| Recheck remains open | PASS |
| All close reasons + purchase forbidden | PASS |
| Attach query delta | PASS — exactly 1 CDC SQL per attach; query_delta=1 |
| JSON bounds | PASS — max 4096 bytes; schema versions enforced |
| Zero-row COL unchanged | PASS |

### Persisted eval evidence

`production_readiness_v1/evidence/persisted_eval_states.json` — real rows on `cf_fe_v1_actionable`:

| State | commitment_id (prefix) | derived |
|-------|------------------------|---------|
| A accepted | `a800776b-…` | ACTION_CHOSEN |
| B under measurement | same | UNDER_MEASUREMENT |
| C recheck due | same | RECHECK_DUE (still open) |
| D closed + new | closed `a800776b-…` / new `87b79b68-…` | null / ACTION_CHOSEN |

---

## 9 — Scale / query cost

| Surface | CDC queries |
|---------|-------------|
| Home summary | **+1** (`list_open` by `store_slug`) |
| Workspace | **+0** incremental (shared summary attach) |
| N+1 | **0** |

Indexed path: `store_slug` (+ open filter). Cardinality: open commitments per store typically 0–5.

| Stores | Est. open rows (total) | Cost |
|--------|------------------------|------|
| 500 | ~0–2.5k | O(1) keyed list per request |
| 1,000 | ~0–5k | same |
| 10,000 | ~0–50k | same; index on store_slug |

Scheduler work: **0**. AI: **0**. External: **0**.

---

## 13 — Regression

| Suite | Result |
|-------|--------|
| CDC unit + readiness | 27 passed |
| COL + OGL + founder eval + console expr + config parity | 47 passed, **1 failed** |
| Production readiness + QueuePool equilibrium | 21 passed |

**Pre-existing failure (1):**  
`tests/test_commercial_opportunity_layer_v1.py::StaticAssetTests::test_workspace_js_has_compressed_decision` — expects marker `commercial-opportunity-workspace-v1` absent after Decision Console / visual-reset workspace rewrite. **Not fixed in this task.** Unrelated to CDC schema/service correctness.

Scheduler: **NOT TOUCHED**.

---

## FINAL SCORECARD

CURRENT LIVE SHA:  
`0f2ebc5a5730cc015988d47446501170ce0b815f`

CANDIDATE SHA:  
branch tip `3e4603fd2481128ad732da340aa829e7d7c5d938` + **uncommitted CDC working tree** (clean deployable SHA not cut in this task)

CURRENT LINE SAFE:  
YES

MIGRATION ADDITIVE:  
PASS

PARTIAL UNIQUE INDEX:  
PASS  
(portable UNIQUE on `active_opportunity_key`; equivalent to open-only uniqueness)

CONCURRENT ACCEPT:  
PASS

TENANT ISOLATION:  
PASS

ACCEPT ≠ EXECUTE:  
PASS

MEASUREMENT AUTHORITY:  
PASS

BASELINE IMMUTABLE:  
PASS

CLOCK DERIVATION:  
PASS

RECHECK REMAINS OPEN:  
PASS

CLOSURE:  
PASS

PURCHASE DOES NOT AUTO-CLOSE:  
PASS

HOME QUERY COUNT:  
1

WORKSPACE INCREMENTAL QUERY COUNT:  
0

N+1:  
0

INDEXED LOOKUP:  
PASS

JSON CONTRACT:  
PASS

MAX SNAPSHOT PAYLOAD:  
4096 bytes

ZERO-ROW BACKWARD COMPATIBILITY:  
PASS

PERSISTED EVAL STATES:  
ACTION_CHOSEN, UNDER_MEASUREMENT, RECHECK_DUE, closed+new ACTION_CHOSEN

TESTS:  
PASS  
(CDC 27; regression mostly green)

PRE-EXISTING FAILURES:  
1  
(`test_workspace_js_has_compressed_decision` — COL static marker drift)

SCHEDULER TOUCHED:  
NO

READY FOR CLEAN CANDIDATE + EXACT-SHA DEPLOY GATE:  
YES  
(proof complete; still requires clean commit packaging — **not authorized here**)

DEPLOY:  
NO

STOP.
