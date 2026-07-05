# CartFlow Knowledge Routing Readiness Review V1

**Status:** Architectural validation — pre-implementation gate  
**Date (UTC):** 2026-07-05  
**Scope:** Verify CartFlow is ready for a platform-owned Knowledge Routing layer  
**Authority:** [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) (KR-1…KR-12, KP-1…KP-10)  
**Audience:** Product, engineering, architecture review  

**Explicitly out of scope:** Routing implementation, services, UI changes, behavior changes.

---

## Executive summary

Knowledge Routing Foundation V1 is **architecturally complete** — eligibility, prioritization, lifetime, visibility, and the routed knowledge item contract are ratified.

Upstream layers (**Merchant Explanation V1**, **Merchant Decision Implementation V1**, **Proof Surface V1**, **Knowledge Layer V1**) exist and are mappable to the routing contract.

However, **active surface-owned selection and parallel copy producers remain**. Daily Brief Composer V2 and Knowledge Layer JS currently own responsibilities that foundation assigns to Routing. Decision output lacks routing-prep metadata required for traceability.

**Verdict: C — Architecture gaps remain.**

Implementation V1 should begin only after **Phase 0 closures** documented in §10 (documentation + routing-prep metadata — no routing engine yet).

---

## Section 1 — Knowledge sources inventory

### 1.1 Producers

| Producer | Path | Role | Merchant copy? | Classification |
|----------|------|------|----------------|----------------|
| **Purchase Truth** | `services/purchase_truth.py` | Durable purchase records | No | **Source of Truth** |
| **Recovery Truth Timeline** | `services/recovery_truth_timeline_v1.py` | Durable timeline events | No | **Source of Truth** |
| **Lifecycle Closure Records** | `services/lifecycle_closure_records_v1.py` | Terminal closure records | No | **Source of Truth** |
| **Customer Lifecycle States V1** | `services/customer_lifecycle_states_v1.py` | Sole lifecycle authority (`customer_lifecycle_state`) | **Yes** — per-state Arabic narrative | **Source of Truth** (state) + **parallel explanation copy** |
| **Knowledge Metrics** | `services/knowledge_metrics_v1.py` | Numeric aggregates | No | **Source of Truth** (metrics) |
| **Merchant Explanation V1** | `services/merchant_explanation_v1.py` | Unified cart explanation | **Yes** — catalog `_EXPLANATION_CATALOG` | **Source of Explanation** (canonical target) |
| **Merchant Decision Layer V1** | `services/merchant_decision_layer_v1.py` | Governed decisions | **Yes** — `decision_explanation` | **Source of Decision** |
| **Merchant Decision Registry** | `services/merchant_decision_registry_v1.py` | Decision metadata | No | **Decision metadata** |
| **Merchant Proof Surface V1** | `services/merchant_proof_surface_v1.py` | Proof composition | **Yes** — steps, `why_we_know_ar` | **Source of Presentation** (proof) |
| **Merchant Evidence Registry** | `services/merchant_evidence_registry_v1.py` | Evidence labels | **Yes** — `label_ar` | **Presentation registry** |
| **Knowledge Insights V1** | `services/knowledge_insights_v1.py` | KL insight cards | **Yes** — `title_ar`, `message_ar` | **Source of Presentation** (pattern insights) |
| **Knowledge Layer V1** | `services/knowledge_layer_v1.py` | Report orchestrator | No | **Presentation orchestrator** |
| **Merchant Claim Evidence V1** | `services/merchant_claim_evidence_v1.py` | Claim-level evidence on KL | Partial — registry labels | **Presentation** |
| **Merchant Daily Brief V1** | `services/merchant_daily_brief_v1.py` | Brief eligibility + v1 compose | **Yes** | **Presentation** (surface consumer) |
| **Merchant Daily Brief Composer V2** | `services/merchant_daily_brief_composer_v2.py` | Topic aggregation | **Yes** — headlines | **Presentation** (interim routing-like logic) |
| **Dashboard Attention Semantics** | `services/dashboard_attention_merchant_semantics_v1.py` | Intervention UX | **Yes** — may override labels | **Presentation** (intervention gate) |
| **Merchant Cart Fact V1** | `services/merchant_cart_fact_v1.py` | Headline chip | **Yes** | **Presentation** |
| **Legacy: Merchant Recovery Lifecycle Truth** | `services/merchant_recovery_lifecycle_truth.py` | Parallel lifecycle narrative | **Yes** | **Presentation (legacy)** — may still attach when legacy path enabled |
| **Legacy: CartFlow Merchant Lifecycle** | `services/cartflow_merchant_lifecycle.py` | Behavior-first narrative | **Yes** | **Presentation (legacy)** |
| **Legacy: Merchant Clarity** | `services/cartflow_merchant_clarity.py` | Clarity groups | **Yes** | **Presentation (legacy)** |
| **Shadow: CartFlow Lifecycle Truth** | `services/cartflow_lifecycle_truth.py` | Canonical evaluator | Unused in UI | **Source of Truth (shadow)** |

### 1.2 Normal-carts attach order (authoritative path)

From `main.py` `_merchant_normal_recovery_row_payload` (~16307–16575):

```
customer_lifecycle_states_v1
  → movement / continuation / follow-up clarity
  → merchant_decision_layer_v1 (V1-A merchant_decision_key)
  → merchant_cart_fact_v1
  → finalize lifecycle
  → dashboard_attention_merchant_semantics_v1
  → merchant_proof_surface_v1
  → merchant_explanation_v1          ← explanation wins label sync
  → merchant_decisions_v1
```

**Readiness note:** Explanation runs **after** attention semantics and **syncs back** into legacy lifecycle fields via `sync_merchant_explanation_to_lifecycle_fields`. Cart detail JS should read `merchant_explanation_v1` only; legacy fields are mirrors.

### 1.3 Classification summary

| Layer | Producers |
|-------|-----------|
| **Truth** | Purchase, Recovery timeline, Lifecycle closure, Lifecycle states (state key), Knowledge metrics |
| **Explanation** | `merchant_explanation_v1` (canonical); lifecycle states still emit parallel Arabic |
| **Decision** | `merchant_decision_layer_v1` + registry |
| **Presentation** | Proof surface, evidence registry, KL insights, daily brief/composer, attention semantics, cart fact, legacy lifecycle modules |

---

## Section 2 — Current surface ownership audit

### 2.1 Cart Detail

| Question | Answer |
|----------|--------|
| **Consumes** | `merchant_explanation_v1` (primary), legacy `customer_lifecycle_*` (fallback), `merchant_cart_fact_v1`, `customer_movement_line_ar`, follow-up fields, intervention fields (`merchant_intervention_executable`, `merchant_decision_key`) |
| **Decides locally** | Explanation vs legacy fallback (`merchantExplanationHtml`); executable action gate (`NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS`); archived/completed tab heuristics; follow-up reply preview in `followupCompactHtml` |
| **Should move to Routing** | Explanation variant selection (mostly server-side today); intervention executability visibility; proof block eligibility (`merchant_proof_surface_v1` attached but **not rendered** — dead `merchantProofSurfaceHtml`); honor `eligible_surfaces` |

**Files:** `static/merchant_dashboard_lazy.js` (~2298–2412 dead compact path; ~2828–2993 explanation render)

### 2.2 Daily Brief

| Question | Answer |
|----------|--------|
| **Consumes** | Published `merchant_decisions_v1` from cart rows (≤250) + KL report — via `merchant_daily_brief_v1.py` → Composer V2 |
| **Decides locally** | Eligibility filter (`is_decision_brief_eligible_v1`); priority sort + dedupe; achievement vs attention split (`is_achievement_decision`); aggregation keys; topic headlines (purchase/return-aware); attention cap (5); JS hero = `items[0]` |
| **Should move to Routing** | Eligibility → `eligible_surfaces`; achievement/attention → `narrative_role`; aggregation → `aggregation_key`; ordering → `routing_priority`; headline templates → routed narrative fields |

**Files:** `services/merchant_daily_brief_v1.py`, `services/merchant_daily_brief_composer_v2.py`, `static/merchant_daily_brief.js`

### 2.3 Merchant Home

| Question | Answer |
|----------|--------|
| **Consumes** | Embedded Daily Brief; KL via separate fetch; hesitation week rows (`merchant_reason_rows_week`, `merchant_reason_insight_ar`); month KPIs; VIP preview; operational onboarding alerts |
| **Decides locally** | Three independent fetches with no unified priority; reason insight generated in summary path (`main.py` ~19448) |
| **Should move to Routing** | Unified home slice per surface; hesitation pattern as routed item; brief hero + KL top cards from same `routing_priority` order |

**Files:** `templates/merchant_app.html`, `static/merchant_dashboard_lazy.js` `applySummary`

### 2.4 Knowledge Layer

| Question | Answer |
|----------|--------|
| **Consumes** | `GET /api/knowledge/report` — `insights[]`, claim evidence, registry |
| **Decides locally** | **`INSIGHT_PRIORITY` map**; `insightScore`; `pickTopInsights` (filter insufficient, sort, slice 3–5); per-key OIA builders with purchase/return/reply/hesitation branching |
| **Should move to Routing** | Entire selection pipeline; OIA text composition; hesitation reason localization maps |

**Note:** API enriches `merchant_decisions_v1` on KL report but **JS never reads it** — duplicate decision path vs Daily Brief.

**Files:** `static/merchant_knowledge_layer.js` (~53–66, ~423–446, OIA builders ~181–316)

### 2.5 Monthly Summary

| Question | Answer |
|----------|--------|
| **Consumes** | Metrics only — `merchant_month_*` counts/revenue (30d window) |
| **Decides locally** | Formatting only |
| **Should move to Routing** | Future trend/closure narrative items (`narrative_role: trend \| closure`) — not integrated today |

**Status:** Metrics-only is acceptable baseline; no routing violation yet.

### 2.6 Notifications

| Question | Answer |
|----------|--------|
| **Consumes** | **None** — `#ma-gtb-notify` is placeholder UI |
| **Decides locally** | N/A |
| **Should move to Routing** | Critical-action notification eligibility when channel ships |

**Status:** Greenfield — no migration debt.

---

## Section 3 — Merchant Explanation readiness

### 3.1 Completeness

| Criterion | Status |
|-----------|--------|
| Catalog covers all lifecycle states | **Yes** — 13 `explanation_id` entries including `return_without_purchase`, `purchase_confirmed`, `needs_merchant_attention` |
| Routing prep metadata | **Partial** — `explanation_id`, `knowledge_event_type`, `eligible_surfaces`, `action_required`, `attention_level` present |
| Sanitizer blocks engineering tokens | **Yes** — `validate_merchant_explanation_merchant_safe` |
| Cart detail reads explanation only | **Yes** — primary path in `merchantExplanationHtml`; legacy fallback if `version !== "v1"` |
| Diagnostic separation | **Yes** — `diagnostic_internal` not in merchant fields |

### 3.2 Copy still originating outside explanation layer

| Source | What leaks | Severity |
|--------|------------|----------|
| `customer_lifecycle_states_v1` | Full Arabic narrative before explanation attach | **Medium** — explanation syncs back; SoT still dual-writes copy |
| `dashboard_attention_merchant_semantics_v1` | Intervention label overrides pre-explanation | **Low** — explanation sync overwrites `customer_lifecycle_label_ar` after attach |
| `knowledge_insights_v1` | KL card `title_ar` / `message_ar` | **High** — not routed through explanation |
| `merchant_daily_brief_composer_v2` | Topic headlines (e.g. return monitor) | **High** — parallel narrative |
| `merchant_decision_layer_v1` | `decision_explanation.rationale_ar` | **Expected** — decision copy; should link via `explanation_id` |
| `merchant_cart_fact_v1` | Chip `label_ar` | **Low** — satellite fact; routable as separate item |
| Legacy modules (`merchant_recovery_lifecycle_truth`, `cartflow_merchant_lifecycle`) | Overlapping lifecycle copy | **Medium** — if legacy attach path enabled |
| `main.py` summary | `merchant_reason_insight_ar` | **Medium** — home hesitation guidance |

### 3.3 Explanation readiness verdict

**Ready as primary cart explanation provider.** Not yet sole platform explanation authority — KL insights and Brief headlines remain parallel.

---

## Section 4 — Decision Layer readiness

### 4.1 Fields exposed today (`merchant_decisions_v1` per decision)

| Field | Present | Routing-ready |
|-------|---------|---------------|
| `decision_id` | Yes | Yes |
| `decision_class` | Yes | Yes |
| `evidence_ids` | Yes | Yes |
| `proof_sources` | Yes | Yes |
| `confidence` | Yes | Yes (immutable per KR-5) |
| `commercial_goal` | Yes | Yes |
| `merchant_action` | Yes | Yes |
| `priority` | Yes | **Interim** — class-derived; becomes input to `routing_priority`, not surface sort |
| `expiration` | Yes | Maps to `surface_lifetime` / `expiration_rule` |
| `suppression_state` | Yes | Yes |
| `verification_status` | Yes | Yes |
| `decision_explanation` | Yes | Yes |
| `decision_timestamp` | Yes | Yes |
| `lifecycle_state` | Yes | Yes (decision lifecycle, not cart lifecycle) |
| `merge_key` | Yes | Maps to `aggregation_key` |
| `action_key` | Yes | Yes |

### 4.2 Missing routing metadata

| Field | Required by foundation | Status |
|-------|------------------------|--------|
| `explanation_id` | Link decision → explanation | **Missing** |
| `attention_level` | Notification / brief eligibility | **Missing** (on decision; exists on explanation only) |
| `eligible_surfaces` | Per-decision surface eligibility | **Missing** |
| `routing_priority` | Platform attention order | **Missing** |
| `knowledge_id` | Stable routed item ID | **Missing** |
| `knowledge_type` | Canonical type enum | **Missing** |
| `narrative_role` | achievement / attention / trend | **Missing** |

### 4.3 Decision readiness verdict

**Ready as decision input.** Requires **routing-prep metadata additions** (documentation + future attach fields) before routing engine can mint unified routed items without ad hoc mapping.

---

## Section 5 — Daily Brief / Composer V2 readiness

### 5.1 Responsibility split

| Responsibility | Current owner | Future owner | Status |
|----------------|---------------|--------------|--------|
| **Selection** (published + verified + not suppressed) | `merchant_daily_brief_v1.is_decision_brief_eligible_v1` | Knowledge Routing | **Temporary** |
| **Ordering** (priority + timestamp) | `_select_brief_decisions_v1` | Knowledge Routing (`routing_priority`) | **Temporary** |
| **Achievement vs attention split** | `is_achievement_decision` | Routing `narrative_role` | **Temporary** |
| **Aggregation keys** | `aggregation_key_for_decision` | Routing `aggregation_key` | **Temporary** |
| **Topic headlines** | `_topic_headline_ar` (return/purchase templates) | Routed narrative field | **Temporary** |
| **Attention budget (cap 5)** | Composer + foundation PV-18 | Routing delivers pre-sorted list; Composer truncates | **Temporary** |
| **Layout / hero / queue UI** | `merchant_daily_brief.js` | Surface Composition | **Permanent** |
| **Empty state copy** | Brief service | Surface Composition | **Permanent** |

### 5.2 Foundation alignment

Foundation §7.3 explicitly documents Composer V2 as **interim** surface composition with priority migrating to routing. Composer V2 is **not a blocker** — it is the **first migration target**.

### 5.3 Daily Brief readiness verdict

**Ready as first routing consumer candidate** once routing emits brief-eligible pre-prioritized topics.

---

## Section 6 — Routing contract readiness

### 6.1 Contract field coverage

| Field | Can current knowledge be mapped? | Gap |
|-------|----------------------------------|-----|
| `knowledge_id` | **No** — not minted anywhere | Need minting convention |
| `knowledge_type` | **Partial** — `knowledge_event_type` on explanation; decision families mappable | Enum alignment doc |
| `routing_priority` | **No** | Routing engine |
| `eligible_surfaces` | **Partial** — explanation has `[cart_detail, cart_row]`; decisions lack field | Extend to all item types |
| `merchant_visibility` | **Partial** — explanation only | Extend |
| `admin_visibility` | **Partial** — `diagnostic_internal` pattern | Formalize |
| `surface_lifetime` | **Partial** — decision `expiration` | Map rules |
| `aggregation_key` | **Partial** — decision `merge_key`; Composer key function | Unify |
| `narrative_role` | **No** — Composer infers implicitly | Routing assigns |
| `traceability` | **Partial** — upstream IDs exist separately | Routing bundles |

### 6.2 Representable item types today

| Knowledge type (foundation §4) | Upstream today | Mappable? |
|------------------------------|----------------|-----------|
| `return_without_purchase` | explanation + monitor decision | **Yes** |
| `purchase_confirmed` | explanation + purchase truth | **Yes** |
| `recovery_needs_attention` | intervention decision | **Yes** |
| `hesitation_pattern` | KL insight + observation decision | **Partial** — insight not linked to decision ID |
| `cart_lifecycle_event` | explanation catalog | **Yes** |
| `merchant_achievement` | observation/monitor decisions | **Yes** (via Composer split) |

### 6.3 Contract readiness verdict

**Contract is complete; producers are not yet contract-compliant.** Mapping is feasible with `knowledge_id` minting spec + decision prep fields.

---

## Section 7 — Surface independence violations

Active violations (presentation logic owning selection/routing):

| # | Location | Violation | Type |
|---|----------|-----------|------|
| 1 | `merchant_daily_brief_composer_v2.py` `is_achievement_decision` | Achievement vs attention classification | Selection |
| 2 | `merchant_daily_brief_composer_v2.py` `_topic_headline_ar` | Return/purchase-aware headline templates | Selection + narrative |
| 3 | `merchant_daily_brief_composer_v2.py` `group_decisions_into_topics` | Priority sort + attention cap | Ordering |
| 4 | `merchant_daily_brief_v1.py` `_select_brief_decisions_v1` | Priority + dedupe selection | Ordering |
| 5 | `merchant_knowledge_layer.js` `INSIGHT_PRIORITY` + `pickTopInsights` | Insight selection + ordering | Selection + ordering |
| 6 | `merchant_knowledge_layer.js` OIA builders | Purchase/return/reply/hesitation branching | Selection |
| 7 | `merchant_dashboard_lazy.js` `merchantDecisionExecutable` | Executable action allowlist | Selection |
| 8 | `merchant_dashboard_lazy.js` `isCompletedDashboardRow` | Arabic label substring heuristics | Selection |
| 9 | `merchant_dashboard_lazy.js` `followupCompactHtml` | Reply detection for follow-up tab | Selection |
| 10 | `merchant_dashboard_lazy.js` `merchantLifecycleCompact` | Purchase/return/reply branching | **Dead code** — never called |
| 11 | `main.py` summary path | `merchant_reason_insight_ar` generation | Selection (hesitation guidance) |

**Consumers ignoring routing prep:**

| # | Location | Violation |
|---|----------|-----------|
| 12 | Cart detail JS | Ignores `merchant_explanation_v1.eligible_surfaces` |
| 13 | KL JS | Ignores API `merchant_decisions_v1` enrichment |
| 14 | All surfaces | No `routing_priority` producer or consumer |

---

## Section 8 — Migration plan

### 8.1 Responsibility migration sequence

| Current owner | Future routing owner | Phase |
|---------------|---------------------|-------|
| Daily Brief eligibility filter | Knowledge Routing `eligible_surfaces` | 1 |
| Daily Brief priority sort | Knowledge Routing `routing_priority` | 1 |
| Composer V2 achievement/attention split | Routing `narrative_role` | 1 |
| Composer V2 aggregation keys | Routing `aggregation_key` | 1 |
| Composer V2 topic headlines | Routed `headline_ar` / narrative field | 1 |
| KL JS `pickTopInsights` | Routing `routing_priority` + eligibility | 2 |
| KL JS OIA builders | Routed insight slices | 2 |
| Cart explanation visibility | Routing `eligible_surfaces` enforcement | 1 |
| Cart intervention executability gate | Routing `action_required` + surface rules | 2 |
| Proof surface cart detail display | Routing routes proof to `cart_detail` | 2 |
| Home reason insight | Routing `hesitation_pattern` item | 2 |
| Notification eligibility | Routing `notifications` surface flag | 3 |
| Monthly summary narratives | Routing aggregate + `narrative_role: trend` | 3 |

### 8.2 Recommended implementation phases

**Phase 0 — Pre-implementation closure (docs + prep metadata, no routing engine)**

1. Ratify `knowledge_id` minting convention in foundation amendment  
2. Document decision → explanation linking (`explanation_id` on decisions)  
3. Freeze new surface selection logic (no new `if purchase` branches)  
4. Mark Composer V2 + KL JS as explicit migration debt in implementation design doc  

**Phase 1 — Routing engine V1 (first consumer: Daily Brief)**

1. `services/knowledge_routing_v1.py` — mint routed items from explanation + published decisions  
2. Composer V2 becomes projection-only over routed brief slice  
3. Single store-scoped `routing_priority` ordering  

**Phase 2 — Cart detail + Knowledge Layer**

1. Cart detail honors `eligible_surfaces`; wire or drop dead proof helper  
2. KL consumes routed pattern items; retire `INSIGHT_PRIORITY`  

**Phase 3 — Home, notifications, monthly**

1. Unified home routed feed  
2. Notification channel consumes notification-eligible slice  
3. Monthly summary trend narratives from routed aggregates  

---

## Section 9 — Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Duplicate routing** — Composer + Routing both sort | High if Phase 1 incomplete | Conflicting brief order | Composer becomes read-only over routed feed; feature flag |
| **Routing loops** — routing reads surface output | Low | Corrupt ordering | Routing reads upstream only (explanation, decisions, proof, KL insights) |
| **Surface-owned filtering persists** | High today | KP-10 violation | Phase 1 retires Composer selection; lint/grep gate |
| **Conflicting priorities** — decision `priority` vs `routing_priority` vs KL score | High | Dashboard ≠ Brief | Deprecate surface sorts; single `routing_priority` |
| **Missing explanation ownership** — KL insights bypass explanation | Medium | Inconsistent merchant language | Route KL insights through `knowledge_type` + optional explanation link |
| **Traceability loss** — merged topics drop decision IDs | Low (Composer traces today) | Audit failure | Require `traceability` block on every routed item |
| **Attention semantics vs explanation drift** | Low | Wrong intervention label | Explanation attach remains authoritative for labels |
| **Legacy lifecycle modules** | Medium if path enabled | Duplicate copy | Disable legacy attach on normal-carts path |
| **Parallel decision collection** — Brief + KL API both gather decisions | Medium | Double work / drift | Single routed store feed per request |

---

## Section 10 — Phase 0 closure checklist (required before Implementation V1)

- [ ] **`knowledge_id` minting convention** documented in foundation amendment  
- [ ] **Decision routing prep fields** specified (`explanation_id`, `attention_level`, `eligible_surfaces` on decisions)  
- [ ] **`knowledge_routing_implementation_v1.md`** design doc with Composer V2 migration as first milestone  
- [ ] **Surface selection freeze** communicated — no new local priority/selection logic  
- [ ] **Legacy attach audit** — confirm normal-carts path skips `merchant_recovery_lifecycle_truth` duplicate copy  

---

## Section 11 — Readiness verdict

### Verdict: **C — Architecture gaps remain**

| Criterion | Assessment |
|-----------|------------|
| Foundation complete (KR/KP) | **Yes** |
| Upstream layers exist | **Yes** |
| Contract mappable | **Yes** |
| Surface violations inventoried | **Yes** — 11 active + 3 prep ignored |
| Decision routing metadata | **No** — missing fields |
| Sole explanation authority | **No** — KL + Composer parallel |
| `routing_priority` anywhere | **No** |
| Safe to build routing engine now | **Yes, with Phase 0 doc closures** |
| Safe to ship routing to merchants now | **No** |

### Interpretation

**C does not mean "abandon routing."** It means:

1. Complete **Phase 0** documentation closures (§10).  
2. Begin **Implementation V1** with Daily Brief as first consumer — migration **is** the gap closure.  
3. Do **not** add new surface selection logic before Phase 1 lands.

Once Phase 0 checklist is complete, **Knowledge Routing Implementation V1 may begin** with Composer V2 migration as the first deliverable.

---

## Section 12 — Related documents

| Document | Role |
|----------|------|
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | Routing contract + KR/KP principles |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | Explanation layer (routing input) |
| [`merchant_decision_implementation_v1.md`](merchant_decision_implementation_v1.md) | Decision execution engine |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Interim aggregation (migration target) |
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | Truth → Proof chain |

---

## Success criteria (review)

- [x] All 10 verification areas addressed  
- [x] Knowledge sources classified  
- [x] Surface ownership audited  
- [x] Explanation + Decision readiness assessed  
- [x] Composer V2 temporary vs future ownership distinguished  
- [x] Contract gaps identified  
- [x] Surface violations listed  
- [x] Migration plan produced  
- [x] Risks documented  
- [x] Single verdict: **C**
