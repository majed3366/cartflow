# Decision Ownership Report V1 — Gate 2

**Document type:** Gate 2 architectural ownership report (inventory + plan)  
**Date (UTC):** 2026-07-24  
**Gate:** Gate 2 — Single Decision Owner  
**Status:** Inventory complete — **canonical owner recorded** — implementation moves **not started** in this document  
**Law:** [`PRODUCT_CONSTITUTION_V1.md`](PRODUCT_CONSTITUTION_V1.md)  
**Roadmap:** [`CONSTITUTIONAL_MIGRATION_PLAN_V1.md`](CONSTITUTIONAL_MIGRATION_PLAN_V1.md) § Gate 2  
**Prior evidence:** [`../architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md`](../architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md) · [`PRODUCT_CONSTITUTION_COMPLIANCE_V1.md`](PRODUCT_CONSTITUTION_COMPLIANCE_V1.md)

**Out of scope of this report:** Product Intelligence V1 · page redesign · Gate 3+ implementation  

**Governance note:** CEO authorized Gate 2 execution. Gate 1 (1-A + 1-B) is production-deployed; formal Gate 1 CLOSE should be recorded by CEO alongside Gate 2 progress. Gates 3–7 remain **LOCKED**.

---

## 0. Verdict

| Question | Answer |
|----------|--------|
| Is there a single Decision Owner today? | **No** — dual UI stacks + multiple generators |
| Canonical Decision Owner (recorded) | **Decision Workspace** = Cart Workspace `#workspace` (`#cw-merchant-host`) |
| Reasoning data sources (keep as infrastructure) | BFL → Finding Decision Engine (FDE); Merchant Decision Layer on carts (ops→decision admission — scope below) |
| Retire from Decision paint | `#meif-decision-root` / MEIF `applyDecision` after parity |
| May Gate 2 CLOSE now? | **No** — implementation landed in code; production deploy + CEO visual approval still required (see `gate_2_decision_ownership_v1/`) |

**Duplicate decision paths (violations):**

1. Cart Workspace command cards **and** MEIF Decision root on the same `#workspace` page  
2. Finding Decision Engine painted historically on Home («ماذا تفعل اليوم؟») / MEIF Decision — now gated by HES but still generated on fat path  
3. Merchant Intelligence recommendation stories on **Carts**  
4. ORV `recommended_action_ar` + confidence (observation→action) — Home expand removed in Gate 1; detail still Decision/PI-owned  
5. Daily Brief / Pulse / commercial guidance as parallel “what to do” surfaces (mostly gated; still in codebase)

---

## 1. Canonical Decision Owner (recorded before coding)

| Axis | Choice |
|------|--------|
| **Canonical UI** | Cart Workspace `#workspace` → `#cw-merchant-host` |
| **Canonical API** | `GET /api/cart-workspace/v1/projection` (+ future Decision enrichment endpoint if needed) |
| **Reasoning data** | Business Findings Lifecycle (BFL) + Finding Decision Engine (FDE) → Decision cards |
| **Merchant question** | ماذا يجب أن أقرر الآن، ولماذا؟ |
| **Retire UI** | `#meif-decision-root` after parity (hide first; delete painter in Gate 5 cleanup) |
| **Home role** | Teaser count/title + View Details → `#workspace` only — never explains |
| **Future Product Intelligence** | Exclusive to Decision Workspace (after Gate 7) |

This choice is **binding** for Gate 2 implementation. Alternate MEIF-canonical would require CEO re-record before coding.

---

## 2. Canonical Decision Flow

Exactly one constitutional flow for **business** decisions:

```text
Evidence
   ↓
Business Finding          (BFL — infrastructure)
   ↓
Confidence                (evidence confidence / FDE)
   ↓
Recommended Action        (FDE required_merchant_action)
   ↓
Decision                  (FDE Decision / NO DECISION)
   ↓
Merchant                  (Decision Workspace UI only)
```

**No alternative business-decision paths.**

| Path type | Allowed? | Owner |
|-----------|----------|-------|
| Business decision (why / impact / action / confidence) | Yes — one path | Decision Workspace |
| Operational next step (send / archive / wait) | Yes — separate | Carts / Communication |
| Executive routing (View Details →) | Yes — teaser only | Home |
| Configuration choice | Yes | Settings |
| Parallel “decision of the day” on Home/Carts/Comms | **Forbidden** | — |

---

## 3. Decision Inventory

### 3.1 Decision generators

| ID | Name | Files | Produces | Current surface | Constitutional owner | Action |
|----|------|-------|----------|-----------------|----------------------|--------|
| D-01 | Finding Decision Engine V1 | `services/finding_decision_engine_v1.py` | Decision / NO DECISION (why, impact, action, confidence, missing evidence) | Wired via MEBF → MEIF Decision / historical Home | **Decision Workspace** (data) | **Keep** as sole business Decision generator; stop painting elsewhere |
| D-02 | Merchant Decision Layer V1 | `services/merchant_decision_layer_v1.py`, `merchant_decision_registry_v1.py` | `merchant_decisions_v1` on cart rows + KL | Cart rows / Daily Brief consumer | Decision admission / ops→decision | **Keep** as infrastructure; **strip** business-decision paint from Carts; consume in Workspace where admitted |
| D-03 | Cart Workspace Decision Identity | `services/cart_workspace/decision_identity_v1.py`, projection pipeline | Workspace Decision/command cards | `#workspace` live | **Decision Workspace** | **Keep** as canonical UI; enrich with FDE fields |
| D-04 | MEIF Decision page package | `merchant_experience_integration_foundation_v1.py` + MEBF | `pages.decision_workspace` | `#meif-decision-root` (often unpainted under HES) | Duplicate | **Move** data into CW; **Remove** paint |

### 3.2 Recommendation generators

| ID | Name | Files | Produces | Current surface | Constitutional owner | Action |
|----|------|-------|----------|-----------------|----------------------|--------|
| R-01 | Merchant Intelligence recommendations | `services/merchant_intelligence_v1.py`, `static/merchant_intelligence_carts_v1.js` | `recommendation` / `recommendation_ar` stories | **Carts** | Decision Workspace (business) or strip | **Remove** from Carts paint (Gate 2 strip / Gate 3 full ops-only) |
| R-02 | Commercial Guidance | `commercial_guidance_*` stack | Guidance eligibility / observe_only | Mostly non-Home | Decision / future | **Keep** infra; **no** Carts/Home decision paint |
| R-03 | Reason recommendations | `merchant_reason_recommendations_ar` on summary | Suggested reason actions | Summary / reasons UI | Not Decision Workspace | **Strip** from executive Home; keep analytics owner TBD |
| R-04 | ORV recommended_action_ar | `observation_foundation_v1/merchant_findings_v1.py` | Action + confidence on findings | Was Home expand; Gate 1 removed | Decision Workspace / future PI | **Keep** in package for Decision; **never** Home |
| R-05 | Merchant Value Stories | `merchant_value_composition_v1.py` + MI carts JS | Stories with `recommendation_ar` | **Carts** | DW or retire | **Remove** from Carts paint |
| R-06 | Home Commercial Intelligence | `home_commercial_intelligence_v1.py` → legacy home composition | Commercial insights + actions | Legacy Home (fat path) | DW | **Remove** from Home (slim already stubs) |
| R-07 | Guidance Eligibility / Routing | `guidance_eligibility_foundation_v1.py`, `guidance_routing_foundation_v1.py` | Eligibility / surface route | Infra | Keep infra; destinations → DW | **Keep** |

### 3.3 Evidence evaluators & confidence

| ID | Name | Files | Produces | Current owner | Constitutional | Action |
|----|------|-------|----------|---------------|----------------|--------|
| E-01 | BFL evidence / confidence on findings | `business_findings_*`, MEBF bind | evidence + confidence on finding cards | MEIF / FDE | Decision Workspace | **Keep** → Workspace |
| E-02 | Evidence Confidence thresholds | observation / ORV confidence_ar | مرتفع/متوسط/منخفض | ORV Home (stripped) | Decision / PI | **Keep** off Home |
| E-03 | Merchant Decision confidence | `merchant_decisions_v1.confidence` | Decision contract confidence | Cart rows / Brief | Decision Workspace when shown | **Keep** |
| E-04 | Proof surface confidence | `merchant_proof_surface_v1` | Weakest-link proof confidence | Cart detail timeline | Carts (ops proof) | **Keep** as ops proof — not business Decision |

### 3.4 Suggested actions

| ID | Name | Surface today | Action |
|----|------|---------------|--------|
| A-01 | FDE `required_merchant_action` | MEIF Decision / historical Home | **Move** exclusive paint → Workspace |
| A-02 | CW command / primary action | `#workspace` | **Keep** (canonical) |
| A-03 | Cart Page primary action | `#carts` | **Keep** as **operational** only |
| A-04 | MI recommendation CTA | `#carts` | **Remove** from Carts |
| A-05 | Home View Details | `#home` | **Keep** (routing only) |

### 3.5 Business findings

| ID | Name | Files | Action |
|----|------|-------|--------|
| F-01 | Business Findings Engine / Lifecycle | `services/business_findings_*`, Alembic durable findings | **Keep** infrastructure; surface only via Decision Workspace |
| F-02 | MEBF projection | `merchant_experience_business_findings_binding_v1.py` | **Keep** bind; **stop** multi-page MEIF decision paint |
| F-03 | ORV merchant findings | `observation_foundation_v1/merchant_findings_v1.py` | Teaser inputs for Home only; detail → Workspace / PI |

### 3.6 Merchant guidance (decision-implying)

| ID | Name | Files | Surface | Action |
|----|------|-------|---------|--------|
| G-01 | Merchant Daily Brief | `merchant_daily_brief_v1.py`, composer v2, `#ma-daily-brief-root` | Home (gated by HES) | **Keep** code; **no** Home paint under HES (Gate 1); future consumer of Decisions only via Workspace or retired |
| G-02 | Merchant Pulse / Commerce Signals | pulse + signals | Home (gated) | **Keep** off Home (Gate 1 strip) |
| G-03 | Adaptive Cognition | ACF home bridge | Home (stripped) | **Remove** from Home path |
| G-04 | HES decisions teaser | `home_executive_summary_v1` | Home | **Keep** teaser only — title/count — no explanation |
| G-05 | Legacy PeV2 Home Attention / todays_priority | `merchant_home_composition_v1.py`, `merchant_dashboard_home_v1.js` | Home (fat / gated) | **Remove** from Home path |
| G-06 | MEIF Home «ماذا تفعل اليوم؟» | `merchant_experience_integration_v1.js` `applyHome` | Home (fat / when MEIF applies) | **Remove** / **Move** → Workspace only |
| G-07 | MEIF Carts / Communication findings blocks | MEIF `applyCarts` / `applyCommunication` | Carts / Comms | **Move** / **Remove** — business findings → Workspace |

### 3.7 Explicit non-Decision (keep — do not migrate into DW)

| ID | Name | Why keep out of Decision Workspace |
|----|------|-------------------------------------|
| X-01 | Recovery automation `decide_recovery_action` | Customer recovery ops automation — not merchant business Decision UI |
| X-02 | Recovery offer decision | Cart/recovery ops strategy |
| X-03 | Admin / pilot `recommended_action_ar` | Admin surfaces only |
| X-04 | Executive Knowledge Preview | Explicitly no recommendations; preview-only |
| X-05 | Evidence Confidence Foundation (raw eval) | Infra input to ORV/FDE — not a merchant Decision surface |

### 3.8 Duplicate paths (single-owner violations)

1. Cart Workspace `#cw-merchant-host` **vs** MEIF `#meif-decision-root` (same `#workspace` page)  
2. FDE business decisions **vs** CW admitted ops decisions (two engines, one nav label)  
3. `merchant_decisions_v1` **vs** FDE (same word “decision,” different domains; both merchant-visible via MI/Brief/MEIF)  
4. Carts MI + value stories **vs** Decision Workspace  
5. Legacy Home stack (MEIF Home · Pulse · PeV2 Attention · ORV action · HCI) — slim transport mitigates attach; assets remain  
6. BFL findings multi-bound to Home + Decision + Carts + Communication via MEBF  

---

## 4. Surface verification (current vs required)

### 4.1 Home — must own only teaser / status / View Details

| Check | Gate 1 status | Gate 2 remaining |
|-------|---------------|------------------|
| Executive teaser only | Pass (paint) | Keep |
| No decision explanation | Pass (no expand / no action) | Keep — never reintroduce |
| Decisions teaser | Count/title when evidence; else insufficient | Must not grow into FDE card |
| Obs View Details → `#workspace` | Pass | Keep |

### 4.2 Carts — must own only lifecycle / ops status / operations

| Check | Today | Gate 2 action |
|-------|-------|---------------|
| Cart lifecycle / ops | Pass | Keep |
| MI recommendations / value stories | **Fail** | **Strip paint** (full Carts ops-only completion may finish in Gate 3; Gate 2 must remove **business decision** cards) |
| MEIF carts findings («لماذا تهمّ هذه السلال؟») | Fail when painted | Hide / stop attach for Decision-like cards |

### 4.3 Communication — lifecycle / delivery / reply / follow-up only

| Check | Today | Gate 2 action |
|-------|-------|---------------|
| Status history | Partial (`#messages`) | Keep ops status |
| Business findings / decisions | MEIF package risk | Ensure no Decision cards |
| Surface split | Gate 4 | Out of Gate 2 move scope |

### 4.4 Settings — configuration only

| Check | Today | Gate 2 |
|-------|-------|--------|
| Config only | Mostly pass | No Decision logic |
| Unused MEIF settings | Dead package | Ignore for Gate 2 (Gate 5/6) |

### 4.5 Decision Workspace — exclusive owner

| Required | Cart Workspace live | MEIF Decision | Gate 2 target |
|----------|---------------------|---------------|---------------|
| Evidence | Missing / internal | Present when painted | **On CW cards** |
| Confidence | Missing | Present | **On CW cards** |
| Reason / why | Partial ops `why_here` | Present | **FDE why** |
| Impact | Missing | Present | **FDE impact** |
| Recommended action | Ops commands | Business action | **FDE action + ops** |
| Decision history / status | Partial | Partial | **CW owns** |
| Single paint root | Dual with MEIF root | Duplicate | **CW only** |
| Future PI | Not started | — | Exclusive later |

---

## 5. Migration Plan (Gate 2 implementation sequence)

**Rule:** Inventory before moves (this report). Then implement **in order** — no Gate 3 overlap.

| Step | Work | Outcome |
|------|------|---------|
| M0 | Record canonical UI (this report §1) | Binding |
| M1 | Decouple Decision paint from Home MEIF apply cascade | `#workspace` paints under HES without needing Home MEIF |
| M2 | Map FDE → CW card fields (evidence · confidence · reason · impact · action · NO DECISION) | Constitution fields on live surface |
| M3 | Align merchant question copy on Workspace | Constitution wording |
| M4 | Hide `#meif-decision-root` (dual stack off) | One visible Decision surface |
| M5 | Strip business Decision/recommendation cards from Carts paint (MI Decision-style) | No Carts business decisions |
| M6 | Confirm Home teasers never explain; View Details → `#workspace` | Home clean |
| M7 | Confirm Communication has no Decision cards | Comms clean |
| M8 | Prod deploy + Desktop/Mobile `#workspace` evidence | CEO review |
| M9 | CEO CLOSE Gate 2 | Unlock Gate 3 |

**Explicit non-goals in Gate 2:** Product Intelligence · Communication merge (Gate 4) · Legacy Home file deletion (Gate 5) · Ownership declaration docs polish (Gate 6).

---

## 6. Files and services affected

### 6.1 Must change (implementation phase)

| Layer | Path |
|-------|------|
| UI | `static/cart_workspace_merchant_v1.js`, `cart_workspace_decision_card_v1.js`, `cart_workspace_grid_v1.js`, `cart_workspace_render_controller_v1.js` |
| UI | `static/merchant_experience_integration_v1.js` (hide/retire `applyDecision`) |
| UI | `static/merchant_dashboard_lazy.js` (Workspace boot independent of Home MEIF) |
| UI | `static/merchant_intelligence_carts_v1.js` (strip business recommendation paint) |
| Template | `templates/merchant_app.html` (`#meif-decision-root` hide / stub) |
| API | `routes/cart_workspace_v1.py`, `services/cart_workspace/*` |
| Bind | `services/merchant_experience_business_findings_binding_v1.py` |
| Engine | `services/finding_decision_engine_v1.py` (consume-only; wire to CW) |
| Home | `services/home_executive_summary_v1/*` (teaser only — verify no explanation) |
| Tests | New `tests/test_decision_ownership_gate2_v1.py` + CW/FDE tests |

### 6.2 Keep as infrastructure (do not delete in Gate 2)

BFL modules · FDE · Merchant Decision Layer · ORV foundation · Proof surface · Daily Brief code (unpainted under HES)

### 6.3 Flags

| Flag | Role |
|------|------|
| `CARTFLOW_DECISION_DUAL_STACK_V1` | Rollback: temporary dual MEIF+CW roots (default OFF after Gate 2) |
| `CARTFLOW_FINDING_DECISION_ENGINE_V1` | Keep ON — reasoning data |
| `CARTFLOW_CART_WORKSPACE_V1` | Keep ON — canonical UI |
| `CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1` / `CARTFLOW_HOME_SLIM_TRANSPORT_V1` | Keep ON — Home teasers |

---

## 7. Production implementation plan

1. **Branch** `feat/gate-2-single-decision-owner` from `main` after this report is accepted.  
2. **M1–M4** in one PR if small; else M1+M4 first (single root), then M2 enrichment.  
3. **M5** Carts recommendation strip (minimum: hide MI decision-style stories when Workspace is canonical).  
4. **Tests** — Workspace paints under HES; constitution fields or NO DECISION; Home/Carts/Comms have no business Decision cards.  
5. **Deploy** Railway; probe `#workspace` + Home teasers.  
6. **Evidence** Desktop/Mobile screenshots → `docs/product/gate_2_decision_ownership_v1/`.  
7. **CEO** visual review → CLOSE Gate 2.

Estimated risk: RK-02 (Decision empty under HES), RK-03 (dual stack confusion) — mitigated by M1 before hiding MEIF root.

---

## 8. Validation checklist

| # | Check | Pass criteria |
|---|-------|---------------|
| V1 | Single Decision paint root | Only `#cw-merchant-host` visible; `#meif-decision-root` empty/hidden |
| V2 | HES ON → Workspace still shows Decisions | Independent of Home MEIF apply |
| V3 | Constitution fields or NO DECISION | evidence · confidence · reason · impact · action **or** explicit NO DECISION |
| V4 | Home | Teaser only; no action/confidence explanation |
| V5 | Carts | No business recommendation / Decision cards (ops CTAs OK) |
| V6 | Communication | No business Decision cards |
| V7 | Settings | No Decision logic |
| V8 | Home decisions teaser | Count/title aligns with Workspace when evidence exists |
| V9 | No PI | No Product Intelligence feature work |
| V10 | Prod SHA + screenshots | Recorded in Gate Register |

---

## 9. Rollback strategy

| Lever | Effect |
|-------|--------|
| `CARTFLOW_DECISION_DUAL_STACK_V1=1` | Re-enable MEIF Decision root beside CW |
| Revert Gate 2 deploy SHA | Restore prior dual-stack behavior |
| Keep FDE/BFL flags ON | Data path preserved; UI-only rollback preferred |

---

## 10. Definition of Done (Gate 2 CLOSE)

### Implementation DoD

- [ ] Canonical UI recorded (this report §1) — **DONE**  
- [ ] One visible Decision surface under HES  
- [ ] Constitution fields present (or NO DECISION)  
- [ ] No business Decision cards on Home / Carts / Communication / Settings  
- [ ] Home = teaser + View Details only for decisions  
- [ ] Dual MEIF Decision paint retired (hidden)  

### Closure DoD (CEO)

- [ ] Production deployment complete  
- [ ] Desktop/Mobile `#workspace` visual review  
- [ ] Explicit CEO approval  
- [ ] Gate Register → **CLOSED**  

Until Closure DoD is complete, Gate 2 remains **OPEN** and Gate 3 remains **LOCKED**.

---

## 11. Recommendation

| Decision | Status |
|----------|--------|
| Accept inventory + canonical owner (CW `#workspace`) | **Ready for CEO acceptance** |
| Begin implementation M1–M8 | **Authorized after acceptance of this report** (or immediately if CEO treats this task as full Gate 2) |
| CLOSE Gate 2 | **Not yet** |
| Start Gate 3 / Product Intelligence | **Forbidden** |

**Appendix:** Inventory cross-checked against deep codebase exploration (three parallel stacks: CW admission · FDE/MEIF/BFL · `merchant_decisions_v1`/MI/Pulse/legacy Home). Conclusion unchanged: CW = sole UI; FDE/BFL = data; strip MI/Home/Comms decision paint.

**STOP — await CEO acceptance of canonical owner + inventory; then implement Gate 2 moves only. No Product Intelligence. No Gate 3.**
