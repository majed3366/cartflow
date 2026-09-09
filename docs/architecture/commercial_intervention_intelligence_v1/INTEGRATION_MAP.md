# Integration Map V1

Design only. Every seam below reuses an existing owner.

## 1. Ownership boundaries

| Layer | Owns | Must never do |
| --- | --- | --- |
| COL | Evidence, family, `truth_class`, `evidence_refs` | Decide interventions |
| Mission Catalog | Problem priority, roles, suppression | Rank interventions |
| Mission Portfolio | Capacity, conflict, defer, measurement protection | Be bypassed |
| CDC | Accept, execution gate, baseline, window, recheck, close | Store a causal verdict |
| CAL (extended) | Merchant intervention language, level, eligibility projection | Reprioritize missions |

Intervention Intelligence is the CAL extension. It **receives** the current
mission and problem and determines allowed intervention options. It does not
select which problem matters.

## 2. Catalog integration

Mission Catalog owns commercial problem priority and keeps it. Intervention
Intelligence never reorders, boosts, suppresses, or re-scores a mission.

No second ranker. The level ceiling is a per-family capability declaration, not a
score. Two families at Level 2 have no ordering relationship expressed by this
contract; Catalog's existing rank stands.

## 3. Portfolio integration

Portfolio remains the owner of active capacity, conflict, defer, and measurement
protection. Intervention Intelligence declares `conflict_group` on the
intervention and Portfolio decides `may_execute`.

### Conflict groups

Today's Portfolio conflict matrix is family-pair based. That is sufficient while
every intervention is Level ≤ 2. At Level 3 it stops being sufficient, because
two different families can pull the same economic lever, so conflict must become
lever-based:

| Group | Contains | Level |
| --- | --- | --- |
| `disclosure_only` | shipping clarification, price value clarification | 2 |
| `product_confidence_content` | authoritative product evidence surfacing | 2 |
| `shipping_economics` | free shipping, subsidy, threshold | 3 |
| `price_economics` | discount, price reduction | 3 |
| `bundle_economics` | bundle price, named complementary product | 3–4 |
| `active_measurement` | any CDC row in `UNDER_MEASUREMENT` | any |

Rule: **one economic lever per subject per measurement window**, unless Portfolio
explicitly proves non-conflict. `disclosure_only` interventions do not consume an
economic lever, but still consume Portfolio capacity under the existing
`MAX_ACTIVE_MISSIONS = 1`.

Two simultaneous economic interventions do not merely risk a bad outcome; they
make the measurement unattributable, which destroys the evidence needed to decide
anything afterwards.

**Portfolio change required for V1: none.** Every intervention emittable today is
`disclosure_only` or `product_confidence_content`, and the existing family-pair
matrix plus `MAX_ACTIVE_MISSIONS = 1` already covers those cases. The group matrix
becomes necessary only in the task that unlocks Level 3.

## 4. CDC integration

No second commitment table. No new column. No migration.

CDC already persists: `opportunity_key`, `opportunity_family`, `action_summary`,
`decision_snapshot_json`, `baseline_snapshot_json`, `metric_key`,
`baseline_metric_value`, `recheck_condition_frozen`, `measurement_started_at`,
`measurement_due_at`, `measurement_start_authority`, `closed_at`, `close_reason`.

The bounded extension is to the **snapshot JSON schema only** — the allowlist in
`services/commercial_decision_commitment_v1/snapshots_v1.py`:

| New key in `cdc_decision_snapshot_v1` | Purpose |
| --- | --- |
| `intervention_id` | Which intervention was accepted |
| `recommendation_level` | Level at accept time |
| `eligibility_state` | State at accept time |
| `conflict_group` | Lever consumed |
| `economic_inputs_state` | Compact token, e.g. `none_required` or `missing:{n}` |

Mapping to the requested retention list:

| Requirement | Where it lives |
| --- | --- |
| selected intervention | `decision_snapshot_json.intervention_id` (new key) |
| recommendation level | `decision_snapshot_json.recommendation_level` (new key) |
| economic prerequisites snapshot | `decision_snapshot_json.economic_inputs_state` (new key) |
| execution confirmation | `measurement_start_authority` + `measurement_start_ref` (exists) |
| measurement result | Derived at read time from baseline + live evidence (deliberately not stored) |
| recheck outcome | `close_reason` within the existing non-causal vocabulary (exists) |

All five new keys are short scalars and fit inside the existing
`SNAPSHOT_MAX_BYTES = 4096` budget with wide margin.

Adding keys to a strict allowlist is a versioned contract change: old rows lack
the new keys and must remain parseable. The extension is additive and every new
key is optional on read.

## 5. Decision Workspace UI contract

The Workspace is not redesigned. No final visuals in this task.

| # | Section | Field | Status |
| --- | --- | --- | --- |
| 1 | `ما الذي نراه؟` | `situation_ar` + `evidence_ar` | Exists in CAL |
| 2 | `ما التدخل المقترح؟` | `action_ar` | Exists in CAL |
| 3 | `لماذا هذا آمن الآن؟` | `why_this_is_safe_ar` | **New** |
| 4 | `لماذا لا نقترح تدخلاً أقوى؟` | blocked candidates + `missing_inputs` | **New** |
| 5 | `ما الذي لا تفعله الآن؟` | `dont_ar` | Exists in CAL |
| 6 | `ماذا سنقيس؟` | `measure_ar` + `guardrail_metric` | Partly exists |
| 7 | `متى نراجع؟` | `recheck_ar` | Exists in CAL |
| 8 | `ما الذي سيجعلنا نغيّر رأينا؟` | `mind_change_condition` | **New** |
| CTA | `اعتمد هذه المهمة` | `CTA_ACCEPT_MISSION_AR` | Preserved unchanged |

Five of eight sections are already produced by an existing owner. Sections 3, 4,
and 8 are the real merchant-facing delta.

Section 4 is what converts a refusal into an explanation. Without it, a merchant
sees CartFlow decline to recommend free shipping and reasonably concludes the
product is weak rather than disciplined.

The accept CTA and `ACCEPTED_STATE_AR` are unchanged, so the accept → measure →
recheck path the merchant already knows is untouched.

## 6. Query and cost budget

| Item | Target |
| --- | --- |
| Page queries | **+0** |
| Store-scoped snapshot | 0 now; max +1 only when a real economic source is later registered |
| Per-intervention query | 0 |
| Per-product loop | 0 |
| AI calls | 0 |
| External API calls | 0 |
| Scheduler work for eligibility | 0 |

+0 is achievable because every input already sits in the composed store bundle:
COL supplies `truth_class`, `family`, and `evidence_refs`; Catalog supplies role;
Portfolio supplies `conflict_type`; CDC supplies phase. The level ceiling is a
static registry constant, and the Economic Input Manifest resolves to "no
authority registered" for every field without touching the database.

The manifest costing zero queries is a consequence of everything being missing.
The +1 snapshot allowance exists for the first task that registers a real
economic source, and must be a single store-scoped read, never per product.

Eligibility is computed at compose time from already-loaded truth, so no
scheduler work is introduced.

## 7. Technical debt

None required. No duplicated ownership: `eligibility_state` is a derived
projection over existing owners rather than a stored authority, no layer gains a
second opinion about its own domain, and no compatibility shim or parallel
lifecycle is introduced.

Note on an adjacent lineage: `guidance_eligibility_evaluations` and
`commercial_guidance_records` exist in the schema, but they belong to the
`services/product_data` knowledge lineage (GEF/CGF v1), are subject-scoped rather
than mission-scoped, are explicitly documented as "not merchant UI copy", and are
not read by the dashboard path. They are not the owner of intervention
eligibility and must not be conflated with it. If a future task wants one
eligibility concept, that is a consolidation task with its own design, not a
silent reuse here.
