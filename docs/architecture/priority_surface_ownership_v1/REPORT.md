# Priority Surface Ownership Audit V1

**Date (UTC):** 2026-09-06  
**Mode:** READ-ONLY  
**Deploy:** NO  

---

## Core question — who owns what

| Concept | Current owner (backend) | Same as others? |
|---------|-------------------------|-----------------|
| **1. Commercial priority** | `mission_catalog_v1` (over COL candidates + CDC continuity boosts; mission-ready preferred for primary when no open CDC) | No |
| **2. Operational urgency** | `operational_guidance_v1` (OGL), with Home gravity also fed by `merchant_publication_v1` / HES `decisions` + diagnostic publication | No |
| **3. Current active mission** | CDC open commitment → Portfolio `active_mission` slot; else Catalog primary as *next* mission (not yet active) | No |
| **4. Blocking obligation** | OGL contact short-circuit (`no_phone > 0`) + publication `missing_contact` / diagnostic `contact_followup_blocked` | No |
| **5. What the merchant should do next** | **Ambiguous today** — Home gravity answers operational “do now”; Catalog strip answers commercial “mission now”; Workspace binds Catalog for mission CTAs and separately paints `is_primary_decision` zone_b cards | Split |

These five concepts are **not** one ranking.

---

## Phase 1 — Surface ownership map

### Home

#### «أهم قرار اليوم» / gravity well («مركز الجاذبية» / «ما الذي أحتاج فعله الآن؟»)

| Field | Value |
|-------|--------|
| **SOURCE** | HES section `id=decisions` (`services/home_executive_summary_v1/compose_v1.py` `_decisions_section`) from `merchant_publication_v1.primary_executive_decision` / teasers; body often overwritten by `diagnosis_language_v1` + **OGL `home_surface`** when OGL ok |
| **OWNER** | Executive publication + Operational Guidance (not Mission Catalog) |
| **PRIORITY SEMANTIC** | Operational / executive “what needs attention or action now” |
| **RANKING SOURCE** | DCE portfolio / commerce situations / `missing_contact` heuristics in `compose_merchant_publication_v1`; OGL pick order in `compose_operational_guidance_v1` |
| **CAN OVERRIDE WHAT** | Visually dominates first viewport; does **not** change Catalog primary |
| **CAN COEXIST WITH WHAT** | Commercial strip below; monitor satellites |

UI: `static/merchant_ui_v2_home.js` `split()` prefers `dominant` / `id===decisions` as gravity primary; OGL rows replace diagnosis/stance when present.

#### «ما أهم مهمة تجارية الآن؟»

| Field | Value |
|-------|--------|
| **SOURCE** | `summary.mission_catalog_v1` via `resolveCommercialLayer` → `missionCatalogToColLayer` (fallback legacy COL only if catalog missing) |
| **OWNER** | **Mission Catalog** |
| **PRIORITY SEMANTIC** | Commercial opportunity / mission-ready priority |
| **RANKING SOURCE** | `rank_mission_catalog_v1` = `score_opportunity_v1` + CDC boosts; primary prefers open-CDC continuity else **mission_ready** families |
| **CAN OVERRIDE WHAT** | Overrides raw COL primary for Home/Workspace commercial paint |
| **CAN COEXIST WITH WHAT** | Gravity/OGL; Catalog secondaries; Portfolio deferred |

Eyebrow on card: «أهم مهمة تجارية الآن».

#### «ما يراقبه CartFlow أيضاً»

| Field | Value |
|-------|--------|
| **SOURCE** | Non-primary HES sections (health / carts / communication / situations…) after duplicate filter |
| **OWNER** | HES composition (satellites) |
| **PRIORITY SEMANTIC** | Monitoring / secondary condition — not commercial primary |
| **RANKING SOURCE** | `executive_rank` + lane split (`know` / `watch` / `learning`), cap 3 |
| **CAN OVERRIDE WHAT** | Nothing commercial |
| **CAN COEXIST WITH WHAT** | Gravity + Catalog strip |

### Workspace

| Visible block | SOURCE | OWNER | PRIORITY SEMANTIC | RANKING SOURCE | CAN OVERRIDE | CAN COEXIST |
|---------------|--------|-------|-------------------|----------------|--------------|-------------|
| **Mission / Decision Console (COL strip)** | `mission_catalog_v1.primary` (`catalogPrimaryFromSummary`; fallback COL) | Mission Catalog (+ CDC phase on card) | Commercial active/next mission | Catalog rank | Session focus; not gravity | Zone_b cards |
| **Primary decision card (`is_primary_decision`)** | `/api/cart-workspace/v1/projection` zone_b | Workspace projection / DCE decisions | Operational/executive decision object | Projection primary flag | Parallel to catalog mission block | Catalog mission above |
| **Operational action / OGL blocks** | Card `operational_guidance_v1.workspace_surface` | OGL | Diagnosis → recommendation → action → recheck | Bound to card/diagnostic truth | Does not rerank Catalog | Mission CTAs |
| **Follow-up / next** | zone_b non-primary | Workspace projection | Secondary decisions | Projection order | No | Primary card |

Comment in Workspace JS: *“Catalog primary owns Workspace identity (Home ↔ Workspace match).”* — that match is **commercial mission identity**, not Home gravity.

---

## Phase 2 — Founder tenant trace (`cf_founder_evaluation`)

Proven live (Reality Identity Audit; unchanged this audit):

| Family | COL | OGL | Catalog | CDC | Portfolio | Home gravity | Home commercial | Workspace mission |
|--------|-----|-----|---------|-----|-----------|--------------|-----------------|-------------------|
| `communication_followup` | Often **COL primary** (no_phone≈39, family weight 80, high urgency) | **Wins OGL** — `no_phone > 0` short-circuit before hesitation | **Secondary** — inventory `lifecycle_support=col_only`; **not** in `MISSION_PROFILES` | none | does not own active slot | **Drives gravity** via OGL + publication/diagnostic contact path | Secondary (if surfaced) | Not catalog primary |
| `product_opportunity_focus` | COL secondary (or compete by score) | Skipped while no_phone>0 | **Primary** — mission_ready | none | free capacity; next = catalog primary | Not gravity title | **Primary strip** | **Primary Console** |
| `product_confidence` | Suppressed / conflict with focus when both trust reasons | n/a under contact OGL | Conflict group / not primary when focus wins | — | — | — | — | — |
| `shipping_friction` | Weak (count=2 in focus seed) | Not selected (contact first) | Not primary | — | — | — | — | — |
| `price_hesitation` | Absent in current reason window | — | — | — | — | — | — | — |

### Why Home gravity = communication while Catalog primary = merchandising

1. **Different selectors.** Gravity = HES + OGL. OGL law: if `no_phone > 0` → compose communication guidance and stop (`compose_operational_guidance_v1`). Catalog does not feed gravity.
2. **Catalog filters lifecycle.** With CDC open_count=0, `rank_mission_catalog_v1` picks primary from **mission_ready** families only when available → `product_opportunity_focus`. `communication_followup` remains `LIFECYCLE_COL_ONLY` → eligible as secondary/COL surface, not Catalog commercial primary.
3. **COL is evidence+score, not Home commercial paint.** Home `resolveCommercialLayer` prefers Catalog over raw COL. So COL can still list communication first while the merchant-facing commercial question shows focus.
4. **No CDC / Portfolio lock.** Portfolio `active_count=0`, `available_slots=1` — capacity is not displacing merchandising; coexistence is by design of two lanes, not deferral.

---

## Phase 3 — Semantic collision

| Claim | Verdict | Evidence |
|-------|---------|----------|
| **A. Two different “top priorities”** | **YES** | Gravity eyebrow «ما الذي أحتاج فعله الآن؟» + OGL contact vs Catalog question «ما أهم مهمة تجارية الآن؟» + merchandising on same Home |
| **B. Commercial mission displaced by operational issue** | **PARTIAL** | Catalog primary still merchandising; operational issue **visually dominates** first viewport, does not remove Catalog primary |
| **C. Operational obligation presented as commercial mission** | **RISK / PARTIAL** | COL titles communication with commercial-opportunity packaging (`eyebrow` / opportunity_id); Catalog correctly keeps it non–mission-ready, but COL/secondary language can still read as “mission” |
| **D. Commercial mission presented as operational obligation** | **NO** | Focus stays under commercial question / Console; OGL does not paint focus while contact blocks |
| **E. Clear coexistence with distinct semantics** | **INTENT YES / EXECUTION WEAK** | Backend already separates Catalog vs OGL/HES; UI labels partially distinguish («مهمة تجارية» vs «مركز الجاذبية») but both claim “most important now” without an explicit two-lane contract |

**Classification:** **A + weak E** — competing top-level *attention*, not a single broken ranker. Root collision = **two uncontracted “most important” owners on one page**.

---

## Phase 4 — Ownership options (evaluate only)

### OPTION A — Catalog owns all top-level priority; ops secondary

| Criterion | Assessment |
|-----------|------------|
| Truth integrity | Weak — buries non-deferrable contact under “secondary” while recovery is blocked |
| Merchant comprehension | One hero, but wrong hero when contact blocks follow-up |
| Reuse Catalog/CDC/Portfolio | Strong |
| Operational safety | Poor for contact/ops blockers |
| Visual simplicity | High |
| Future ads/acquisition/retention | Forces ops into commercial catalog → pollutes mission-ready set |
| Complexity | Medium (reroute gravity) |
| Duplicate ranking risk | Low commercial; ops still needs a queue |

### OPTION B — Operational gravity owns all top-level; commercial secondary

| Criterion | Assessment |
|-----------|------------|
| Truth integrity | Weak — demotes legitimate commercial missions when any ops issue exists |
| Merchant comprehension | “Always fix ops first” — may starve merchandising learning |
| Reuse | Underuses Catalog/CDC |
| Operational safety | Strong short-term |
| Visual simplicity | High |
| Future scale | Four domains all fight for gravity → worse |
| Complexity | Medium |
| Duplicate ranking | COL/Catalog become decorative |

### OPTION C — Two explicit lanes: Commercial Priority + Operational Obligation

| Criterion | Assessment |
|-----------|------------|
| Truth integrity | **Best fit to current code** (Catalog vs OGL/HES already split) |
| Merchant comprehension | Clear if labels/dominance rules are explicit |
| Reuse | Full Catalog/CDC/Portfolio + OGL as obligation lane |
| Operational safety | Contact remains non-masquerading obligation |
| Visual simplicity | Medium — needs hierarchy law, not one blob |
| Future scale | Domains add to commercial lane; obligations stay obligation lane |
| Complexity | Low–medium (mostly contract + copy/hierarchy; **no new commercial ranker**) |
| Duplicate ranking | Avoided if Catalog remains sole commercial ranker |

### OPTION D — Unified higher-order Decision Priority layer

| Criterion | Assessment |
|-----------|------------|
| Truth integrity | Possible but **creates a second (meta) ranking engine** over Catalog+OGL — violates required principle |
| Merchant comprehension | One number — hides why |
| Reuse | Replaces rather than reuses |
| Complexity | High |
| Duplicate ranking | **Yes** — explicitly a new engine |

---

## Phase 5 — Architecture law (candidate)

**Do NOT create a second commercial ranking engine.**

Tested law (adopt as recommendation):

> **Mission Catalog owns commercial opportunity priority.**  
> **Operational gravity (OGL + executive publication) owns non-deferrable operational obligations.**  
> **One must not masquerade as the other.**

Relative contract for operational obligations vs Catalog:

- Obligations may **visually precede** commercial primary on Home when blocking (e.g. contact).
- Obligations **do not** become Catalog `primary` unless promoted to a true mission-ready family with CDC profile (explicit product decision later).
- Obligations **do not** consume Portfolio mission capacity.
- Open **CDC** commercial commitment **dominates commercial lane** (Catalog/Portfolio continuity); it does not silence an independent blocking obligation unless product law says so (recommend: obligation still visible as obligation).

---

## Phase 6 — Future scale test

| Lane | Example |
|------|---------|
| Commercial Mission | «زد وضوح المنتج» |
| Operational Obligation | «أكمل وسيلة التواصل» |
| Advertising Mission | «اختبر قناة اكتساب» |
| Retention Obligation | «راجع شريحة إعادة الشراء» |

**Current model under Option C:** commercial missions (merch / ads / …) compete **only inside Catalog** (one commercial primary). Obligations (contact / retention ops) compete **inside an obligation lane** with their own severity — not as a fourth “Catalog primary.”  

**Without Option C (status quo labels):** four items can all read as “top priority” → fails scale.  

**With Option A/B:** forces cross-domain starvation.  

**With Option D:** one meta-ranker for four domains = second engine.

**Verdict:** Option C scales; current implementation is structurally close but **label/dominance contract incomplete**.

---

## Phase 7 — Recommendation

**RECOMMENDED MODEL: C**

| Rule | Specification |
|------|----------------|
| Home commercial primary | **Mission Catalog** |
| Operational urgency | **OGL + merchant_publication / HES gravity** |
| Coexistence | Two named lanes; never merge ranks |
| Visual dominance (no open CDC) | **Blocking operational obligation** may own gravity well; commercial strip remains authoritative commercial primary underneath / beside with distinct question |
| Visual dominance (open CDC) | **Catalog/Portfolio active commitment** owns commercial Console + commercial strip continuity; blocking obligation still obligation-lane if present |
| Workspace | **Catalog primary** = commercial mission / Decision Console; zone_b primary decision = executive/ops expansion — label distinctly; do not imply two commercial primaries |
| Portfolio capacity | Only **CDC mission slots**; READY does not consume (`ready_consumes_capacity: false`) |
| Ops consume mission capacity? | **NO** |

UI redesign: **MINOR** (naming, hierarchy, anti-masquerade) — not a new layout system.  
Implementation complexity if later authorized: **MEDIUM** for surface contract polish; **LOW** if docs-only law first.  
**Second ranking engine:** NO.

---

## FINAL REPORT

```
CURRENT COMMERCIAL PRIORITY OWNER:
mission_catalog_v1 (over COL + CDC boosts; mission_ready gate for primary when no open CDC)

CURRENT OPERATIONAL PRIORITY OWNER:
operational_guidance_v1 + merchant_publication_v1 / HES decisions gravity

CURRENT ACTIVE MISSION OWNER:
CDC open commitment → mission_portfolio_v1.active_mission; else none (Catalog primary = next commercial mission only)

CURRENT HOME GRAVITY OWNER:
HES decisions section + OGL home_surface (not Mission Catalog)

SEMANTIC COLLISION:
YES

ROOT COLLISION:
Home paints two “most important now” owners—operational gravity (contact) and Catalog commercial primary (merchandising)—without an explicit two-lane contract.

RECOMMENDED MODEL:
C

COMMERCIAL PRIMARY OWNER:
mission_catalog_v1

OPERATIONAL OBLIGATION OWNER:
operational_guidance_v1 (+ executive publication for gravity)

WORKSPACE OWNER:
mission_catalog_v1 for commercial mission/Console; workspace projection zone_b for executive decision cards (must stay semantically distinct)

ACTIVE CDC DOMINANCE RULE:
Open CDC owns commercial-lane continuity (Catalog/Portfolio slot); does not convert ops obligations into missions; blocking obligations remain visible as obligations.

OPERATIONAL ITEMS CONSUME MISSION CAPACITY:
NO

SECOND RANKING ENGINE REQUIRED:
NO

FUTURE DOMAIN SAFE:
YES (under Option C lane law)

UI REDESIGN REQUIRED:
MINOR

IMPLEMENTATION COMPLEXITY:
MEDIUM

READY FOR FOUNDER ARCHITECTURE REVIEW:
YES

DEPLOY:
NO
```

STOP.
