# Commercial Decision Commitment V1 — Exact-SHA Deploy Gate

**Date (UTC):** 2026-09-05  
**Status:** READY FOR EXACT-SHA DEPLOY — **NOT EXECUTED**  
**Visual reopen:** NO  
**Scheduler:** UNTOUCHED  
**Env var mutation:** NO  

## Governing law

Observe → Evidence → Freeze runtime SHA → Prove line safety → Prepare mutation → **STOP**

---

## Phase 1 — Worktree classification (at freeze)

Branch: `candidate/commercial-opportunity-layer-v1`  
Parent tip before runtime: `3e4603fd`  
Live production (re-observed): `0f2ebc5a5730cc015988d47446501170ce0b815f`

### Classification

| Class | Paths |
|-------|--------|
| **A — CDC runtime** | `models.py` (CommercialDecisionCommitment), `schema_commercial_decision_commitment_v1.py`, `services/commercial_decision_commitment_v1/*`, `routes/commercial_decision_commitment_v1.py`, `main.py` (CDC router only), `services/home_executive_summary_v1/compose_v1.py` attach, `services/merchant_home_experience_activation_v1.py` attach, `static/merchant_ui_v2_workspace.js` / `home.js` commitment→CDA arc, `templates/merchant_app_v2.html` cachebust `cdc1` |
| **B — CDC tests** | `tests/test_commercial_decision_commitment_v1.py`, `tests/test_commercial_decision_commitment_production_readiness_v1.py` |
| **C — migration** | Additive model + `schema_commercial_decision_commitment_v1.py` (no Alembic file; `create_all` / ensure) |
| **D — docs** | `docs/architecture/commercial_decision_commitment_v1/**` (docs tip; not deploy target) |
| **E — Console** | Minimal live COL workspace/home CDA arc wiring only (no Decision Console V1.1 redesign) |
| **F — eval isolated** | `services/founder_evaluation_reality_v1/*` (test/seed only; no lab routes) |
| **G — unrelated preserved (NOT in runtime)** | visual-identity labs, Decision Console V1.1 packs, production closure evidence packs, OGL/config docs drift, capture scripts |
| **H — disposable** | `scripts/_cdc_observe_railway_v1.py`, `_cdc_railway_*.json` |
| **I — unknown** | **0** |

**UNRELATED RUNTIME CHANGES IN CANDIDATE:** **0**  
**SIMULATION LEAK:** **0**

---

## Phase 3 — `active_opportunity_key` proof

| Requirement | Proof |
|-------------|--------|
| Server-owned | Set only in `accept_commitment` / cleared in `close_commitment` (`service_v1.py`) |
| Client cannot supply | Route bodies `extra=forbid`; no `active_opportunity_key` field |
| Open value | `active_opportunity_key = opportunity_key` (= COL `opportunity_id`) |
| Close releases | `active_opportunity_key = None` once with `closed_at` |
| History preserved | Closed rows retained; new accept creates new `id` |
| Concurrent | UNIQUE(`store_slug`,`active_opportunity_key`) → IntegrityError; one active |
| Cross-store | Distinct `store_slug` in unique key |

Constraint: `uq_cdc_active_store_opportunity`  
Owner: `services/commercial_decision_commitment_v1/service_v1.py`

---

## Phase 4 — Frozen runtime SHA

| | SHA |
|--|-----|
| **RUNTIME CANDIDATE SHA** | `926739b511d1089668fe5542ef5abb521cf1db54` |
| BRANCH TIP (may advance with docs) | see after docs commit |
| Live ancestor of runtime | **YES** |

Deploy target = **RUNTIME CANDIDATE SHA only**.

---

## Phase 5 — Migration snapshot

| | |
|--|--|
| File | `schema_commercial_decision_commitment_v1.py` + `models.CommercialDecisionCommitment` |
| Alembic | none |
| Additive | YES |
| Backfill | none |
| Zero rows OK | YES |
| Scheduler | none |
| Snapshot max | 4096 bytes |

### Startup / deploy risk (not executed)

1. **When migration runs:** `db.create_all()` at API startup / first `ensure_commercial_decision_commitment_schema` on CDC access.  
2. **Automatic:** yes (SQLAlchemy create_all), idempotent if table exists.  
3. **App OK, migration fail:** attach fail-closed → empty CDC map; COL/Home continue.  
4. **Migration OK, app fail:** new empty table idle; live `0f2ebc5a` ignores unknown table.  
5. **Live tolerates new table:** YES (no reads of CDC on live).  
6. **Candidate tolerates missing table briefly:** ensure/create_all on first use; attach catch → empty.

**Safe sequence (not executed):** Deploy exact SHA → verify `/ping` `/health` → confirm table exists → no env changes → Scheduler untouched.

---

## Phase 6 — Regression (at freeze)

| Suite | Result |
|-------|--------|
| CDC unit + readiness | PASS (28) |
| COL `test_workspace_js_has_compressed_decision` | **PASS** on this candidate (marker restored) |
| Causal overlap with prior fail | Prior fail was dirty Decision Console rewrite; **not** on clean CDC candidate |

---

## Phase 10 — Production identity (re-observed)

| Field | Value | Trust |
|-------|--------|-------|
| Live API SHA | `0f2ebc5a5730cc015988d47446501170ce0b815f` | **Re-observed** `/dev/merchant-runtime-identity` + static MATCH |
| Project | `authentic-motivation` / `565c6a84-52db-4e8b-9709-c3801570297a` | Linked Railway project config |
| Environment | `production` / `1b684334-5b13-4d8e-9c3a-d5816d323850` | Linked config |
| API service | `smart-reply-ai` / `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` | Linked config |
| Scheduler service | `cartflow` / `882d9906-f7c6-4b29-9180-892be385fbb1` | Prior gate (unchanged law) |
| API / Scheduler config | `railway.api.toml` / `railway.scheduler.toml` | Repo |
| Autodeploy | **OFF** (exact-SHA path) | Prior verified; GraphQL re-auth **failed** this session |
| Live deployment id | **NOT RE-VERIFIED** (Railway GraphQL 403 / connection reset) | Use identity SHA as source of truth for line safety |
| COL flag | **DO NOT MUTATE** — leave current live state | Not re-queried |
| Scheduler SHA / deploy | **DO NOT TOUCH** | Not mutated |

---

## Phase 11 — Lineage

`git merge-base --is-ancestor 0f2ebc5a 926739b5` → **0**  
**CURRENT-PRODUCTION-LINE SAFE:** **YES**

---

## Phase 13 — Prepared mutation (DO NOT EXECUTE)

```graphql
mutation DeployCartFlowApiExactSha {
  serviceInstanceDeployV2(
    serviceId: "f3731fa1-43c5-4f72-b8e6-b39b0d028f15"
    environmentId: "1b684334-5b13-4d8e-9c3a-d5816d323850"
    commitSha: "926739b511d1089668fe5542ef5abb521cf1db54"
  )
}
```

Transport: `curl.exe -4` → Railway GraphQL.  
**Not** `railway up`.

---

## Absolute stop

DO NOT DEPLOY.  
DO NOT MODIFY RAILWAY ENVIRONMENT VARIABLES.  
DO NOT TOUCH SCHEDULER.  
DO NOT REOPEN VISUAL DESIGN.
