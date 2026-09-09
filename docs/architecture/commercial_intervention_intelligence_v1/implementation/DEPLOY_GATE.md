# Commercial Intervention Intelligence V1 — Exact-SHA Runtime Deploy Gate

**Date (UTC):** 2026-09-09 → 2026-09-10
**Scope:** API runtime only. No UI composition. No general release. No Scheduler deploy.

---

## 1. Pre-deploy re-observation (not assumed)

Read-only Railway GraphQL (`authentic-motivation` / production env) plus live HTTP.

| Fact | Observed |
|---|---|
| LIVE API SHA | `68176fa4df16ac7e56e9e7f8a7d960600a7bb70d` |
| LIVE API deployment ID | `3eb2b47f-a6a9-4498-8a06-afabf10675b2` (SUCCESS, 2026-09-09T19:30:26Z) |
| LIVE API identity header | `x-cartflow-git-sha: 68176fa4…` — matches Railway metadata |
| Autodeploy | **OFF** — 0 deployment triggers on the project |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Scheduler deployment ID | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` (2026-08-27T21:36:48Z) |
| API env state | 53 variable names, recorded for post-deploy comparison |
| Scheduler env state | 44 variable names |

Two operational facts had to be resolved before observation was trustworthy:
the cached Railway OAuth token had expired at `2026-09-09T10:25:37Z` (every query
returned `Not Authorized`), and the network path to `backboard.railway.com` resets
roughly two connections in three. The token was refreshed through the CLI; the
GraphQL client was changed to short-timeout fast retries rather than long waits.

## 2. Candidate

| Fact | Value |
|---|---|
| CANDIDATE SHA | `e3df486548208b64b90a590d4e4af23aed01d753` |
| Branch | `candidate/commercial-intervention-intelligence-v1` |
| Branch tip | `e3df4865…` — **tip == candidate**, no docs-only tip exists |
| Working tree | clean (`git status --porcelain` empty) |
| Live SHA ancestor of candidate | **YES** (`git merge-base --is-ancestor` → 0) |

Runtime (non-docs) delta versus the live SHA is exactly the authorized set:

```
services/commercial_action_language_v1/__init__.py            (+14, exports)
services/commercial_action_language_v1/intervention_v1.py     (new, 631)
services/commercial_decision_commitment_v1/snapshots_v1.py    (+35, CDC allowlist)
tests/test_commercial_intervention_intelligence_v1.py         (new, 529)
tests/test_commercial_guidance_economic_safety_v1.py          (+32/-3, test only)
```

No UI composition, no new service, no new lifecycle, no new ranker, no schema
change, no migration, no scheduler, no AI, no external integration. `main.py`,
`models.py`, and every route file are untouched.

The live SHA is not on `origin/main` — it lives on the previous candidate branch,
which is the established pattern for this service. The new candidate branch was
pushed to `origin` so Railway could fetch the commit; with autodeploy off this
push deployed nothing on its own.

## 3. Pre-deploy test gate

| Gate | Result |
|---|---|
| Simulation parity | **8/8** projections (`parity_check_v1.py`) |
| Runtime tests | **63 passed** (52 intervention + 11 economic safety) |
| Impacted regression (38 suites) | **8 failed / 478 passed** |
| Baseline at live SHA (same 38 suites) | **10 failed / 476 passed** |
| New failure IDs | **0** |

The 8 failures are identical in both runs and pre-existing: `test_business_themes_v1`,
`test_commerce_situations_v1`, `test_decision_workspace_v2_budget`,
`test_gate_2a_decision_workspace_v1`, `test_merchandising_mission_slice_v1`,
`test_merchant_ui_v2`, `test_mission_catalog_projection_v1`,
`test_products_commercial_truth_v1`. The 2 extra baseline failures are the new CDC
snapshot tests, which fail without the allowlist change — a control proving those
tests exercise real runtime behaviour.

### Explicit state proofs (33 checks, all PASS)

| Input | Eligibility | CTA |
|---|---|---|
| `CAPACITY_ONLY` | `WAIT_AND_RECHECK` | absent |
| `DUPLICATE_INTENT` | `INTERVENTION_NOT_JUSTIFIED` | absent |
| `MEASUREMENT_CONTAMINATION` | `CONFLICTING_SIGNALS` | absent |
| own CDC phase `under_measurement` | `ALREADY_UNDER_MEASUREMENT` | absent |
| Level 3 requested, empty manifest | `ECONOMIC_INPUTS_REQUIRED` | absent |
| `SAFE_TO_COEXIST` + production-ready + primary | `ELIGIBLE` | allowed |

Forcing `cta_ar` onto a blocked card is rejected by
`validate_intervention_card_v1` with `cta_on_blocked_card`.

**R17 (shipping 12/20):** `ELIGIBLE`, level **2**, evidence renders «12 من 20 (60٪)»
unchanged and the evidence mapping is not mutated by the layer, `why_this_is_safe_ar`
present, `guardrail_metric` == «لا تراجع في تحوّل السلة إلى شراء»,
`mind_change_condition` present, `blocked_candidates` = one L3 candidate blocked by
`ECONOMIC_INPUTS_REQUIRED` with 8 missing inputs, card validates with zero errors.

**Level 3 requested without economics:** `requested_candidate.eligibility_state`
= `ECONOMIC_INPUTS_REQUIRED`, `offered_level_instead` = 2, card level = 2. The
merchant is offered Level 2 only; the L3 candidate is surfaced as blocked, never
as an instruction.

## 4. CDC proof

Only the five new keys are accepted: `intervention_id`, `recommendation_level`,
`eligibility_state`, `conflict_group`, `economic_inputs_state`.

- Legacy snapshot with none of the new keys still parses.
- Unknown key (`revenue_gain`) still rejected with `decision_snapshot_unknown_keys`.
- `recommendation_level` of `5`, `-1`, `"two"`, `None` all rejected.
- Extended snapshot is **397 / 4096 bytes** — budget intact.
- No causal or result field present: keys are `accepted_at`, `conflict_group`,
  `economic_inputs_state`, `eligibility_state`, `intervention_id`,
  `opportunity_family`, `opportunity_key`, `opportunity_reason`,
  `recommendation_level`, `schema_version`, `truth_class`.

## 5. Cost proof

AST analysis of `intervention_v1.py`: imports are `__future__`, `typing`, and five
`*_contract_v1` modules — nothing else. No DB, AI, network, or scheduler import,
and no ORM/session verb call site anywhere in the module.

| Budget | Result |
|---|---|
| Query delta | **+0** |
| N+1 | **0** |
| AI | **0** |
| External | **0** |
| Scheduler | **0** |
| DB change | **none** |

## 6. Exact-SHA deploy

`serviceInstanceDeployV2(serviceId, environmentId, commitSha)` against the API
service only. No `railway up`, no branch-tip deploy, no docs-only tip, no env
mutation, no Scheduler deploy.

| Fact | Value |
|---|---|
| DEPLOYMENT ID | `9b80944b-1d04-44e3-9f4b-5da0a23b2e7e` |
| Deployed SHA | `e3df486548208b64b90a590d4e4af23aed01d753` |
| Transition | INITIALIZING → BUILDING → DEPLOYING → **SUCCESS** |

The mutation was guarded: it re-read the live deployment first and would have
aborted if the live SHA had drifted from `68176fa4…`.

### Post-deploy

| Check | Result |
|---|---|
| `x-cartflow-git-sha` | `e3df486548208b64b90a590d4e4af23aed01d753` — **exact match** |
| `/ping` | 200 |
| `/health` | 200 |
| `/health?db=1` | 200 |
| QueuePool `timeout_count` | **0** (QueuePool available) |
| API live deployment | `9b80944b…` |
| Scheduler deployment | `2b1e5665…` — unchanged |
| Scheduler SHA | `f91e799d…` — unchanged |
| API env var names | 53 → 53, identical list — no env mutation |
| Scheduler env var count | 44 → 44 |
| Autodeploy | still OFF (0 triggers) |

## 7. Live runtime contract proof

`services/commercial_action_language_v1/__init__.py` imports `intervention_v1` at
package load. `/api/dashboard/summary` imports
`merchant_home_experience_activation_v1`, which imports that package. A live 200
from Home therefore proves the new module imported cleanly inside the production
process — it is not merely present in the image.

| Live surface | Result |
|---|---|
| `/dev/living-store-home-review-session` | 200, bound store `demo` |
| Home `/api/dashboard/summary` | 200 (proves CAL package + `intervention_v1` load) |
| Products `/api/dashboard/products` | 200 |
| Carts `/api/dashboard/normal-carts` | 200 |
| Dashboard shell `/dashboard` | 200 |
| Intervention fields on merchant surface | **absent** — no UI exposure |

Contract values were then proven at the deployed SHA by running the 33-check proof
against a worktree pinned to `e3df4865…` (detached, clean). This is sound because
`intervention_v1` is pure: no DB, no network, no environment variable, no clock.
Its output is a function of its arguments alone, so the deployed bytes and the
pinned checkout cannot disagree.

**Scope limit, stated plainly:** no HTTP surface returns an intervention card yet,
because UI composition is out of scope for this gate. The live proof is therefore
*module-load observed in production* plus *contract values proven deterministically
at the deployed SHA*, not a merchant-visible response body.

## 8. Regression

Unchanged and verified: Home, Workspace visible composition, Products, Carts, COL
diagnosis, Catalog priority, Portfolio, CDC lifecycle, Product Exposure, Scheduler.
No route, template, or merchant payload changed; the intervention fields appear on
no surface. **No UI visual change.**

## 9. Technical debt

**NEW TECHNICAL DEBT: NONE.**
