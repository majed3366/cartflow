# Commercial Intervention Intelligence V1.1 — State-Aware Composition

Live API SHA `16387dd7f40e343d52d6a50dd3ca566a7710f54e` · deployment `e08961c3-9d52-4f79-8bfa-05828a01dbc1` · 2026-09-10 UTC

Presentation refinement only. CDC still owns lifecycle. The Workspace heading and
controls now follow that state, the safety explanation is one advisory block, and
accept / confirm / reverse share one CartFlow action family.

---

## 1. Pre-deploy re-observation (not assumed)

Before this candidate was deployed, production was:

| Observed | Value |
| --- | --- |
| Live API SHA | `c0710a39c33db296d060a659b300e5306ebbb3c8` |
| Live API deployment | `c5208c82-a70f-4c9e-aa23-ba7e0138cab6` |
| Autodeploy | OFF — 0 triggers |
| Scheduler SHA / deployment | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` / `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| Live SHA is ancestor of candidate | YES |

Re-observation after the exact-SHA deploy (this session): live identity header
`x-cartflow-git-sha: 16387dd7…`, deployment `e08961c3…`. No second deploy was issued.

## 2. What changed

Server projection (`workspace_intervention_v1.py`) now emits `heading_state` from
CDC's already-owned phase, and swaps only the merchant question:

| CDC / eligibility | Heading |
| --- | --- |
| READY / ELIGIBLE | ما التدخل المقترح الآن؟ |
| ACTION_CHOSEN | ما الذي اعتمدته الآن؟ |
| UNDER_MEASUREMENT | ما الذي نقيسه الآن؟ |
| RECHECK_DUE | ماذا أظهرت إعادة المراجعة؟ |
| WAIT / BLOCKED | لماذا ننتظر الآن؟ |

A committed card splits the deferral sentence from the running work, so
UNDER_MEASUREMENT leads with «قيد القياس بالفعل» and shows the current
intervention as context (`التدخل الجاري`), not as a new recommendation.
A blocked card never ends on an instruction to act.

Client: one compact advisory block (safe → not stronger → do not do), three
separated closing questions, and the reusable lifecycle family
`cf-lifecycle-action--primary|confirm|secondary`. LDH journey steps before the
server's current step read as history (`is-done`), so «اعتمد هذه المهمة» is not
an open invitation while the mission is already being measured.

## 3. Cost

| Metric | Value |
| --- | --- |
| Query delta | **+0** |
| N+1 | 0 |
| AI / external API / scheduler | 0 / 0 / 0 |
| DB schema / migration | none |
| Commercial truth / eligibility / CDC machine | unchanged |

## 4. Tests

`tests/test_commercial_intervention_state_composition_v1_1.py` + existing V1
workspace suite: **87 passed, 14 subtests**. Headings, control matrix, visual
classes, no duplicate primary, R17 `12 من 20`, no revenue claim, merchant-facing
`البيع المتقاطع` = 0, AST query delta +0.

## 5. Exact-SHA deploy

`serviceInstanceDeployV2` of runtime SHA `16387dd7` only. No `railway up`, no
docs-only tip, no env mutation.

| SHA | Deployment | Status |
| --- | --- | --- |
| `a48c2b29` (composition) then `16387dd7` (journey history) | `e08961c3-9d52-4f79-8bfa-05828a01dbc1` | SUCCESS — live |

## 6. Post-deploy proofs

| Proof | Result |
| --- | --- |
| `x-cartflow-git-sha` | `16387dd7…` exact match |
| `/ping` `/health` `/health?db=1` | 200 / 200 / 200 |
| QueuePool `timeout_count` | 0 |
| Scheduler | unchanged at `f91e799d` / `2b1e5665` |
| Autodeploy | still OFF |

## 7. Live proof — real `/dashboard`, `cf_live_reality_lab`

| Field | Live value |
| --- | --- |
| CDC phase | `UNDER_MEASUREMENT` |
| `heading_state` | `UNDER_MEASUREMENT` |
| Primary heading | ما الذي نقيسه الآن؟ |
| Heading before V1.1 | ما التدخل المقترح الآن؟ |
| Eligibility | `ALREADY_UNDER_MEASUREMENT` |
| `is_new_recommendation` | false |
| Suggestion | قيد القياس بالفعل: لا تبدأ تدخلاً موازياً… |
| Context | التدخل الجاري + the Level 2 shipping clarification |
| Evidence | `12 من 20 (60٪)` unchanged |
| CTA marker | `data-cf-intervention-cta="0"` |
| Accept button | **0** |
| Confirm button | **0** |
| Reversal | `cf-lifecycle-action--secondary` «تراجع عن المهمة» |
| Document width | 390 — no horizontal clipping |

HEADING MATCHES CDC STATE: **PASS**

## 8. Founder screenshots — 390 × 844

Canonical: `docs/product/commercial_intervention_intelligence_v1/v1_1/live/`

| File | What it shows |
| --- | --- |
| `state_aware_top_mobile.png` | Diagnosis + «ما الذي نقيسه الآن؟» + running work as context |
| `advisory_safety_compact_mobile.png` | One advisory block: safe → not stronger → do not do |
| `lifecycle_actions_mobile.png` | Journey as history + outline reversal; no accept-again |
| `measurement_recheck_mobile.png` | ماذا سنقيس؟ / متى نراجع؟ / ما الذي سيجعلنا نغيّر رأينا؟ |
| `full_workspace_mobile.png` | End-to-end composition (390×1200 logical, stitched) |

Desktop copy: `C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Commercial_Intervention_Intelligence_V1_1_Live\`

## 9. Technical debt

**NEW TECHNICAL DEBT: NONE.**

## 10. Status

READY FOR FOUNDER LIVE REVIEW: **YES** · GENERAL RELEASE: **NO**
