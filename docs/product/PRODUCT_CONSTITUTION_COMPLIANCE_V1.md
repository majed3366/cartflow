# Product Constitution Compliance Report V1

**Document type:** Constitution compliance audit (no implementation)  
**Date (UTC):** 2026-07-24  
**Status:** Complete — **not 100% compliant** · blocks Product Intelligence V1  
**Law:** [`PRODUCT_CONSTITUTION_V1.md`](PRODUCT_CONSTITUTION_V1.md) (incl. Principle 0)  
**Evidence pack:** [`../architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md`](../architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md)  

**Out of scope:** Product Intelligence implementation · UI redesign · new merchant features  

**Execution roadmap:** [`CONSTITUTIONAL_MIGRATION_PLAN_V1.md`](CONSTITUTIONAL_MIGRATION_PLAN_V1.md) — **Execution Gates** G1–G7 (sequential; CEO closure required; no parallel; PI only after Gate 7)

---

## 0. Executive verdict

| Surface | Paint compliance | Transport / ownership compliance | Principle 0 (leads to decision) |
|---------|------------------|----------------------------------|----------------------------------|
| Home | **Mostly Compliant** (5 teasers) | **Non-compliant** (MEIF/ORV/legacy/KPI/boot) | Partial — View Details present; obs expand includes PI-like action |
| Decision Workspace | **Non-compliant** (dual stack; incomplete PI contract) | Split | Partial — ops commands yes; business reasoning incomplete |
| Carts | **Non-compliant** (MI / recommendations) | Eager load on Home boot | Partial — ops next step exists; business guidance violates |
| Communication | **Non-compliant** (split `#communication` / `#messages`) | Eager messages on boot | Partial |
| Settings | **Mostly Compliant** | Unused MEIF settings package | Compliant (config) |

**Overall:** Product does **not** fully comply with Product Constitution V1.  
**Product Intelligence V1:** **Blocked** until P1–P3 work packages below close exclusive Decision ownership, Carts ops-only, Communication unity, and Home slim transport.

---

## 1. Page compliance reviews

### 1.1 Home — violations

Constitution requires: Executive Summary only · five sections · View Details → · no ops / no business reasoning / no detailed reports · HP-1…HP-7.

| Check | Result | Violation |
|-------|--------|-----------|
| Executive Summary only (paint) | Pass | — |
| Five constitutional sections | Pass | health / decisions / observations / carts / communication |
| Every section ends with View Details | Pass (links present) | Observations expand **in-place** instead of routing to Decision Workspace |
| No operational management | Fail (transport) | Eager normal-carts + messages; KPI/month panels filled on boot |
| No business reasoning | Fail | Obs expand shows `recommended_action_ar` + confidence on Home |
| No detailed reports | Fail (transport) | Full MEIF + full ORV assemble on `/summary` |
| HP-1…HP-6 | Fail | Full MEIF/ORV/Pulse/legacy/Daily Brief/ACF on Home critical path |

**Reported violations (Home):**

1. Observation in-place expand with recommended action / confidence (PI bleed).  
2. Full MEIF five-page packages on every summary.  
3. Full ORV attach before slim (HP-4).  
4. Double MEIF attach (live + finalize).  
5. Legacy Home stack still shipped (ECC, Pulse, PeV2 experience, ORV sibling) — gated but present.  
6. Daily Brief + Adaptive Cognition attached on Home path.  
7. KPI / month / reason projections on summary critical path.  
8. Setup theatre can still compete with executive Home.  
9. Eager boot of Carts + Communication APIs from Home entry.

---

### 1.2 Decision Workspace — exclusive ownership & missing

Constitution: exclusive owner of business reasoning, evidence, confidence, recommended action, **future Product Intelligence**.

| Required capability | Live Cart Workspace | MEIF / Finding Decision Engine | Status |
|---------------------|---------------------|--------------------------------|--------|
| Evidence | Missing (internal refs only) | Present when painted | **Missing** on live path |
| Confidence | Missing | Present when painted | **Missing** on live path |
| Reason / why this matters | Partial (`why_here` ops) | Present | **Missing** vs constitution |
| Business impact | Missing | Present | **Missing** on live path |
| Recommended action | Ops commands | Business action when painted | **Partial** |
| Related products | Missing | Missing | **Missing** |
| Historical context | Missing | Missing | **Missing** |
| Exclusive PI ownership | Violated by Home obs + Carts MI | Split / often unpainted under HES | **Missing** |
| Single owner | Dual with MEIF Decision | Dual with CW | **Duplicate** |

**Everything currently missing (Decision):**

1. Unified single Decision product (CW **or** MEIF/FDE — not both).  
2. Merchant-facing evidence + confidence + business impact on the **live** Decision surface.  
3. Related products + historical context fields.  
4. Exclusive PI ownership (remove PI-like content from Home/Carts/Comms).  
5. MEIF Decision paint while HES claims Home (today: Decision MEIF root often empty).  
6. Constitution-aligned merchant question copy on both stacks.

---

### 1.3 Carts — violations

| Check | Result |
|-------|--------|
| Operational cart management | Present (list, filters, timeline, ops actions) |
| No recommendations | **Fail** — MI value stories / decision-style cards |
| No business guidance / intelligence | **Fail** — MI + MEIF carts findings |
| No decision logic | **Fail** — recommendation cards |

**Remove or relocate:** Merchant Intelligence / value stories · MEIF «لماذا تهمّ هذه السلال؟» · any business recommendation cards.  
**Keep:** Product · customer · value · status · timeline · stage · next **operational** action.

---

### 1.4 Communication — violations

| Check | Result |
|-------|--------|
| Owns lifecycle/status only | Partial on `#messages`; MEIF `#communication` often unpainted |
| Duplicate implementations | **Fail** — `#communication` vs `#messages` |
| No business intelligence | **Fail** — MEIF findings block; reasons/templates ownership unclear |

**Duplicates:** MEIF Communication package · `#messages` history · (nav) reasons / trigger-templates under communications family.

---

### 1.5 Settings — violations

| Check | Result |
|-------|--------|
| Configuration only | **Mostly pass** |
| No ops / PI | Pass (paint) |
| Dead packages | MEIF `pages.settings` built, never painted → **Remove or wire** |
| Scope creep | VIP threshold settings on `#vip`; month/KPI Home subpages — clarify owner |

---

## 2. Constitution Compliance Matrix

Status: **Compliant** · **Needs Move** · **Duplicate** · **Remove** · **Missing**

| Feature | Current Page | Constitutional Owner | Status |
|---------|--------------|----------------------|--------|
| HES five teasers (paint) | Home | Home | Compliant |
| HES View Details → carts/workspace/communication | Home | Home | Compliant |
| HES obs in-place expand + recommended action | Home | Decision Workspace | Needs Move |
| Full MEIF packages on `/summary` | Home transport | Per-page APIs | Needs Move |
| Double MEIF attach | Summary | Per-page APIs | Duplicate |
| ORV full assemble on summary | Home transport | Home slim / Decision detail | Needs Move |
| ORV sibling painter | Home (gated) | — | Remove |
| MEIF Home painter | Home (gated) | — | Remove |
| ECC Dashboard Home V1 | Home (gated) | — | Remove |
| Merchant Pulse UI on Home | Home (gated) | — | Remove |
| PeV2 `maApplyHomeExperience` | Home (gated) | — | Remove |
| Daily Brief on summary/Home | Home transport | — | Remove |
| Adaptive Cognition on Home finalize | Home transport | — | Remove |
| Commerce Signals + Pulse when UI off | Home finalize | — | Remove |
| KPI / month panels from summary | Home-month | Settings/analytics | Needs Move |
| Reason counts on summary | Summary | Comms/diagnostics | Needs Move |
| Setup theatre on Home | Home | Settings | Needs Move |
| Eager `/normal-carts` on boot | Any → Home | Carts | Needs Move |
| Eager `/messages` on boot | Any → Home | Communication | Needs Move |
| Cart Workspace (live `#workspace`) | Decision | Decision Workspace | Compliant intent / Missing PI fields |
| MEIF Decision + FDE cards | Decision (often unpainted) | Decision Workspace | Duplicate / Missing paint |
| BFL findings on Home MEIF | Home (gated) | Decision Workspace | Needs Move |
| Exclusive Product Intelligence surface | Nowhere unified | Decision Workspace | Missing |
| Related products on decisions | — | Decision Workspace | Missing |
| Historical context on decisions | — | Decision Workspace | Missing |
| Evidence/confidence/impact on live CW | — | Decision Workspace | Missing |
| Normal-carts ops list | Carts | Carts | Compliant |
| Cart filters / proof timeline | Carts | Carts | Compliant |
| MI value stories / intelligence on Carts | Carts | Decision or retire | Needs Move / Remove |
| MEIF Carts findings | Carts | Decision Workspace | Needs Move |
| VIP list | `#vip` | Carts | Compliant (ops) |
| VIP threshold config | `#vip` | Settings | Needs Move |
| MEIF `#communication` status | Communication (unpainted) | Communication | Missing paint / Duplicate |
| `#messages` history | Messages | Communication | Duplicate |
| MEIF Comms business findings | Communication | Decision Workspace | Needs Move / Remove |
| Trigger templates under comms nav | Trigger-templates | Settings | Needs Move |
| Reasons page under comms nav | Reasons | Comms or diagnostics | Needs Move (clarify) |
| WA readiness on summary | Summary | Settings/Communication | Needs Move |
| Settings / WA / Widget / Plans / Diagnostics | Settings siblings | Settings | Compliant |
| MEIF settings package (unpainted) | Summary build | Settings | Remove |

---

## 3. Architectural compliance (ownership declarations)

Constitution §6 requires every feature to declare: owning page · service · query · API · data source · decision type · leads to decision · validation.

| Area | Declarations present? | Violations |
|------|----------------------|------------|
| `home_executive_summary_v1` | Partial (`OWNERSHIP_V1` / `GOVERNANCE_V1` only) | Missing query/API/data-source/decision-type/V-checklist |
| MEIF pages | Partial (question strings) | No §6 block |
| Cart Workspace | Partial (mission question + API) | No §6 block |
| Finding Decision Engine | No | Full violation |
| ORV / Observation findings | No | Full violation |
| Normal-carts / messages / MI | No | Full violation |
| Settings siblings | No | Full violation |
| Legacy Home painters | No | Full violation + should Remove |

**Repo finding:** The §6 template exists only inside `PRODUCT_CONSTITUTION_V1.md`. No merchant feature PR currently carries the mandatory ownership block.

---

## 4. Required Moves

| # | What | From | To |
|---|------|------|-----|
| M1 | Observation detail + recommended action / confidence | Home expand | Decision Workspace (View Details → `#workspace`) |
| M2 | Slim Home teaser inputs only | Full MEIF/ORV on summary | Home-only lightweight summary contract |
| M3 | KPI / month / reason heavy queries | Summary critical path | Owning page APIs (Settings/analytics/Reasons) |
| M4 | Setup theatre primary | Home | Settings → Store Setup |
| M5 | Normal-carts fetch | Eager boot | Carts hash / lazy |
| M6 | Messages fetch | Eager boot | Communication hash / lazy |
| M7 | MI / value stories / business cards | Carts | Decision Workspace or retire |
| M8 | MEIF Carts/Comms findings | Carts / Communication | Decision Workspace |
| M9 | Trigger templates | Comms nav family | Settings |
| M10 | VIP threshold configuration | `#vip` | Settings |
| M11 | WA readiness card | Summary Home path | WhatsApp Settings / Communication |
| M12 | Finding Decision Engine paint | Unpainted under HES | Live Decision Workspace (sole stack) |

---

## 5. Required Removals

| # | What | Why |
|---|------|-----|
| R1 | ECC / Dashboard Home V1 production boot | Dead alternate Home |
| R2 | Pulse UI Home painter (+ attach when UI off) | Dead / non-executive Home |
| R3 | PeV2 `maApplyHomeExperience` Home painter | Dead alternate Home |
| R4 | ORV sibling Home painter | HES owns observation teaser |
| R5 | Daily Brief attach on Home summary path | Superseded by HES |
| R6 | Adaptive Cognition on Home finalize | Not Home executive teaser |
| R7 | Second MEIF attach on finalize when already present | Duplicate calculation |
| R8 | MEIF unused `pages.settings` package (or wire — prefer remove until needed) | Dead work on summary |
| R9 | Business recommendations / MI primary UI on Carts | Constitution forbid |
| R10 | Business findings blocks on Communication | Constitution forbid |

---

## 6. Required Merges

| # | Merge | Into | Why |
|---|-------|------|-----|
| G1 | Cart Workspace + MEIF Decision + Finding Decision Engine | **One Decision Workspace** | Exclusive business reasoning owner |
| G2 | `#communication` + `#messages` | **One Communication surface** | One question, one owner |
| G3 | HES + MEIF Home composition | **HES only** while HES is Home owner | No dual Home |

---

## 7. Required Missing Components

| # | Component | Owner | Notes |
|---|-----------|-------|-------|
| X1 | Sole Decision Workspace product contract | Decision | Evidence · confidence · reason · impact · action (+ products/history when available) |
| X2 | Exclusive PI hosting surface | Decision | No PI on Home/Carts/Comms/Settings |
| X3 | Home slim summary API / contract | Home | Teaser inputs without full MEIF/ORV |
| X4 | Observation / PI detail load on Decision only | Decision | Home View Details navigates away |
| X5 | Communication status primary paint | Communication | Lifecycle states: Sent/Delivered/Failed/Replied/Waiting/No Phone/Returned |
| X6 | Ownership declaration enforcement | Engineering process | §6 block on every merchant PR |
| X7 | Constitution question copy alignment | Decision | «What decision should I make, and why?» |

---

## 8. Implementation work packages (ordered)

> Compliance work only — **no Product Intelligence V1 feature build** inside these packages unless noted as “hosting surface readiness.”

### P1 — Home transport & paint purity (HP-1…HP-7)

1. Define slim Home summary contract (teaser fields only).  
2. Stop double MEIF attach; skip full MEIF page packages when HES-only.  
3. Defer full ORV; Home gets count/empty/slim only.  
4. Drop Daily Brief / ACF / Pulse attach from Home finalize when unused.  
5. Route observation View Details → `#workspace` (remove PI action expand on Home).  
6. Lazy-load normal-carts + messages by hash.

**Exit:** Home summary cost = executive teasers only; no PI action on Home.

### P2 — Single Decision Workspace owner

1. Choose sole Decision product (recommend: Cart Workspace hosts; consume FDE/BFL as data — or reverse; **one** UI).  
2. Paint evidence · confidence · reason · impact · action on that sole surface.  
3. Unblock Decision paint under HES (do not gate Decision apply on Home painter failure).  
4. Remove / stop shipping competing Decision roots.

**Exit:** One Decision surface answers «What decision should I make, and why?»

### P3 — Carts ops-only

1. Remove or relocate MI value stories / recommendation cards from Carts primary UI.  
2. Remove MEIF business findings from Carts.  
3. Keep ops next steps only (Wait / Contact / Scheduled / Purchased / Closed).  
4. Move VIP threshold config to Settings.

**Exit:** Carts matrix rows = Compliant for recommendations/intelligence.

### P4 — One Communication surface

1. Merge `#messages` into `#communication` (or hard redirect).  
2. Paint lifecycle statuses; remove business findings.  
3. Move trigger-templates to Settings; clarify Reasons ownership.  
4. Lazy Communication API.

**Exit:** One Communication owner; no PI.

### P5 — Legacy Home retirement

1. Remove production script/CSS boot for ECC, Pulse UI, PeV2 Home experience, ORV sibling (lab flags only if needed).  
2. Remove unused MEIF settings package generation from summary path.

**Exit:** Single Home paint path in production assets.

### P6 — Ownership declaration compliance

1. Add §6 ownership block to every remaining merchant-visible package doc/PR.  
2. Add lightweight CI/doc check or review gate for `Owning page:` presence on merchant PRs.

**Exit:** Principle 5 / §6 violations closed for active features.

### P7 — Decision hosting readiness for Product Intelligence V1

1. Confirm exclusive PI ownership (P2+P3+P4+P1.5 done).  
2. Confirm constitution fields present on Decision.  
3. CEO sign-off on Product Constitution V1 + this compliance closure.

**Exit:** Authorized to begin Product Intelligence V1 **implementation** (separate task).

---

## 9. Compliance scorecard

| Criterion | Met? |
|-----------|------|
| Every feature mapped to exactly one page | **No** (duplicates remain) |
| Duplicate responsibilities removed | **No** |
| Every page owns exactly one merchant question | **No** (Decision/Comms split) |
| Home requests only executive summaries | **No** |
| Architectural ownership matches product ownership | **No** |
| Ownership declarations complete | **No** |
| Principle 0 satisfied on all surfaces | **No** |
| Ready for Product Intelligence V1 | **No** |

---

## 10. STOP

Do **not** implement Product Intelligence.  
Do **not** redesign pages as a creative exercise.  
Do **not** add merchant features.

Execute compliance work packages **P1 → P7** (or CEO-waived subset with recorded risk) until this report’s scorecard is all **Yes**.

**Product Intelligence V1 begins only after** Product Constitution V1 CEO approval **and** P7 exit criteria.
