# Commercial Intervention Intelligence V1 — Live UI Composition & Founder Review

Live API SHA `c0710a39c33db296d060a659b300e5306ebbb3c8` · deployment `c5208c82-a70f-4c9e-aa23-ba7e0138cab6` · 2026-09-10 UTC

The merchant Decision Workspace now answers *what safe commercial intervention can be
tested now, why, what blocks a stronger one, what we will measure, and when we change
our minds* — as one guided decision, not eight boxes.

---

## 1. Pre-deploy re-observation (not assumed)

| Observed | Value |
| --- | --- |
| Live API SHA before task | `e3df486548208b64b90a590d4e4af23aed01d753` (matched the expected value) |
| Live API deployment before task | `9b80944b-1d04-44e3-9f4b-5da0a23b2e7e` |
| Autodeploy | OFF — 0 triggers |
| Scheduler service SHA / deployment | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` / `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| API env variables | 53 names (names only; values never read) |
| Scheduler env variables | 44 names |
| Live SHA is ancestor of candidate | YES |

## 2. What was built

Server projection — `services/commercial_action_language_v1/workspace_intervention_v1.py`:
reads the owners already present on the composed dashboard summary (COL `truth_class`,
Catalog `role`, Portfolio `conflict_type`, CDC `phase`), calls the deployed
`intervention_v1` contract, and attaches a paintable projection onto
`mission_catalog_v1.primary.intervention_v1`. It decides nothing.

Client composition — `static/merchant_ui_v2_workspace.js` + `merchant_ui_v2_workspace.css`:
`renderInterventionDecision()` paints the contract in reading order

    evidence → proposed intervention → safety and limit → action → measurement

Both workspace layouts (`renderColDecision` for normal merchants and the lab's
Live Decision Hierarchy) delegate the decision body to that one function, so the
decision is never painted twice. LDH keeps only what it owns: the lifecycle
journey, portfolio monitoring and the next mission.

Ownership unchanged: COL owns diagnosis, Mission Catalog owns priority, Mission
Portfolio owns conflict and capacity, CDC owns commitment, `intervention_v1` owns
eligibility, level and every merchant sentence. No frontend ranker, no frontend
eligibility engine, no duplicated intervention logic.

## 3. Cost

AST proof over the new module — imports are `__future__`, `typing`, and three contract
modules only; no DB, AI, network or scheduler import; zero ORM/session verb call sites.

| Metric | Value |
| --- | --- |
| Query delta | **+0** |
| N+1 | 0 |
| AI calls | 0 |
| External API calls | 0 |
| Scheduler work | 0 |
| DB schema change / migration | none |

## 4. Pre-deploy test gate

| Gate | Result |
| --- | --- |
| New contract/UI suite `tests/test_commercial_intervention_workspace_ui_v1.py` | 41 passed, 8 subtests |
| Runtime contract proofs (33 checks incl. R17, eligibility matrix, CDC allowlist) | ALL PASS |
| Impacted regression, 65 suites, candidate | 28 failed / 742 passed |
| Same 65 suites at the live base `e3df4865` | 28 failed / 701 passed |
| New failure IDs | **0** — identical failure set |

## 5. Exact-SHA deploy

`serviceInstanceDeployV2(serviceId, environmentId, commitSha)` only. No `railway up`,
no branch-tip deploy, no docs-only tip, no env mutation.

| Deploy | SHA | Deployment | Status |
| --- | --- | --- | --- |
| 1 | `5681c9619a340d9c09d23b2cf4436c778c17cafb` | `42596c85-ba4b-40c6-bd83-3bae3e6c0761` | SUCCESS |
| 2 | `4fcc3bb63334de03891e2c80fd2300cd7bc254e0` | `a8193a93-cd20-4815-a4ba-b14896e6a46c` | SUCCESS |
| 3 (live) | `c0710a39c33db296d060a659b300e5306ebbb3c8` | `c5208c82-a70f-4c9e-aa23-ba7e0138cab6` | SUCCESS |

## 6. Post-deploy proofs

| Proof | Result |
| --- | --- |
| `x-cartflow-git-sha` == candidate | PASS — `c0710a39…` |
| `/ping` | 200 |
| `/health` | 200 |
| `/health?db=1` | 200 |
| QueuePool `timeout_count` | 0 |
| Scheduler deployment / SHA | unchanged |
| API env variable names | 53 → 53, identical |
| Scheduler env variable names | 44 → 44 |
| Autodeploy | still OFF (0 triggers) |

## 7. Live contract on the real `/dashboard`

Tenant `cf_live_reality_lab`, scenario `R17_shipping_hesitation` applied and verified
through the lab's own owner path.

| Field | Live value |
| --- | --- |
| `family` | `shipping_friction` |
| `recommendation_level` | 2 |
| `eligibility_state` | `ELIGIBLE` |
| `conflict_group` | `disclosure_only` |
| evidence | `12 من 20 (60٪)` — unchanged |
| `guardrail_metric` | `لا تراجع في تحوّل السلة إلى شراء` |
| `blocked_candidates` | 1 — free/subsidised shipping, blocked on missing economic inputs |
| `cta_ar` | `اعتمد هذه المهمة` |

DOM markers on the live page: `data-cf-intervention-level="2"`,
`data-cf-intervention-eligibility="ELIGIBLE"`, `data-cf-intervention-cta="1"`,
`data-cf-intervention-blocked-count="1"`.

### Blocked state, proven live

Accepting the mission through the real CTA moved CDC to `ACTION_CHOSEN`:

| Stage | `cdc_phase` | `eligibility_state` | `cta_ar` |
| --- | --- | --- | --- |
| Before accept | none | `ELIGIBLE` | `اعتمد هذه المهمة` |
| After accept | `ACTION_CHOSEN` | `ALREADY_UNDER_MEASUREMENT` | **none** |
| After abandon | none | `ELIGIBLE` | `اعتمد هذه المهمة` |

The blocked card explains itself rather than showing an error:
`قيد القياس بالفعل: لا تبدأ تدخلاً موازياً على نفس الفرصة. ما ننتظره هو نتيجة نافذة القياس.`
No disabled control and no greyed clickable control is rendered.

The remaining blocked states — `CONFLICTING_SIGNALS`, `INTERVENTION_NOT_JUSTIFIED`
(duplicate intent), `WAIT_AND_RECHECK` (capacity only, and unknown inputs failing
closed), `INSUFFICIENT_EVIDENCE`, `ECONOMIC_INPUTS_REQUIRED` — are proven by
controlled composition in the test suite against the deployed contract, since the
lab cannot currently manufacture a live portfolio conflict. `CAPACITY_ONLY` presents
as `WAIT_AND_RECHECK` and never says `هذا التدخل غير مبرر`; `DUPLICATE_INTENT`
presents as `INTERVENTION_NOT_JUSTIFIED` with no second CTA.

### Level 3 stays blocked

The live card is Level 2 and states, under «لماذا لا نقترح تدخلاً أقوى؟», that free or
subsidised shipping is not proposed because shipping cost and margin are unknown. No
fake Level 3 recommendation is shown, and the eight missing input field names are
never sent to the browser — only their count.

## 8. Mobile review — 390 × 844

| File | What it shows |
| --- | --- |
| `intervention_top_mobile.png` | 390×844 — diagnosis, evidence, proposed intervention, safety, and the CTA all within the first screen |
| `intervention_safety_block_mobile.png` | 390×844 — why this is safe, why nothing stronger, what not to do |
| `intervention_measurement_mobile.png` | 390×844 — what we measure, the guardrail, when we recheck, what changes our mind |
| `intervention_full_mobile.png` | 390×1244 — the complete composition end to end (stitched from two captures at the same 390×844 viewport) |

Layout: document scroll width 390 — no horizontal clipping. The whole ELIGIBLE
decision including the CTA fits in one 844 px screen. Composition height 1186 px.

Desktop review copy: `C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Commercial_Intervention_Intelligence_V1_Live\`

## 9. Technical debt

**NEW TECHNICAL DEBT: NONE.**

## 10. Status

READY FOR FOUNDER LIVE REVIEW: **YES** · GENERAL RELEASE: **NO**
