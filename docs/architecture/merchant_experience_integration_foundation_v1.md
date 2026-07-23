# CartFlow Merchant Experience Integration Foundation V1 (MEIF)

**Status:** Governed merchant-facing integration layer (architecture + runtime)  
**Date (UTC):** 2026-07-22  
**Authority:** Subordinate to Surface Composition, Knowledge, Commercial Guidance (via composition), and Merchant Operational State.  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** UI redesign, visual refresh, Figma, new business logic, new Knowledge types, new Guidance logic, Truth/CIS/SCF rule changes, AI reasoning

> **Law:** Merchant Experience Integration is the canonical bridge between platform intelligence and merchant-facing pages.  
> Pages consume integration packages. Pages never recreate business decisions.

---

## 0. Purpose

Integrate existing governed platform layers into the merchant experience so that what the platform already knows is truthfully visible to merchants.

| This layer does | This layer must never |
|-----------------|------------------------|
| Inventory pages + Integration Map | Redesign pages / Figma |
| Package SCF + Knowledge + Ops for pages | Invent Knowledge / Guidance |
| Translate Knowledge to merchant language | Strengthen claims / invent certainty |
| Suppress false empty-states vs ops truth | Modify Truth / CIS / SCF rules |
| Expose Decision Workspace + Communication as real surfaces | Hardcode page-owned recommendations |
| Probe readiness / consumption / trust | Add cosmetic redesign without integration |

---

## 1. Placement

```text
Canonical Domain Truth
        ↓
Evidence
        ↓
Commerce Intelligence Synthesis
        ↓
Knowledge
        ↓
Commercial Guidance
        ↓
Surface Composition
        ↓
Merchant Experience Integration  ← THIS LAYER
        ↓
Merchant Pages
```

---

## 2. Phase 1 — Experience Inventory (Integration Map)

Canonical map: `services/product_data/merchant_experience_integration_registry_v1.py` (`imap_v1`).

| Page | Merchant question | Governed sources | Obsolete / replaced |
|------|-------------------|------------------|---------------------|
| Home | What should I know now? | SCF + Guidance (via SCF) + Knowledge + Ops | Skeleton / zero-KPI theatre when durable carts exist |
| Decision Workspace | Why is this happening, and what should I review? | SCF + Knowledge + Guidance (via SCF) | Hidden nav / blank hash |
| Carts | What cart attention is needed? | SCF + Ops | False “please wait” with durable carts |
| Communication | What needs follow-up? | SCF + Ops | Settings WhatsApp fallback |
| Settings | How do I control the platform? | SCF | Nav defaulting to WhatsApp |

For each page the map records: owner, current vs governed sources, duplicated logic, obsolete logic, placeholders, missing integrations, nav target.

---

## 3. Ownership

| Question | Owner |
|----------|-------|
| What is true operationally (counts)? | Merchant Operational State (read-only durable facts) |
| What should each surface receive? | Surface Composition |
| What guidance exists / where routed? | Commercial Guidance → Routing → Presentation → SCF |
| How is Knowledge said to merchants? | **MEIF translation** (presentation only) |
| What package does a page render? | **MEIF** |
| How is it painted? | Merchant page consumers (minimal binding) |

---

## 4. Input boundary

**Allowed:**

- Surface Composition (`generate_surface_compositions_v1`)
- Knowledge (`generate_knowledge_v1`) — for merchant-language presentation only
- Commercial Guidance **only via** Surface Composition lineage (no new guidance evaluation)
- Merchant Operational State (durable counts: abandoned carts, purchase truth, hesitation reasons, recovery schedules, mock WA)

**Forbidden:**

- New Knowledge types / Guidance eligibility / SCF composition rules
- Page-owned business decisions or recommendations
- Raw event inventing / AI reasoning
- Cosmetic redesign as a substitute for integration

---

## 5. Runtime contracts

| Concern | Contract |
|---------|----------|
| Flag | `CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1` (default **on**) |
| Generator | `generate_merchant_experience_integration_v1` |
| Summary seam | `attach_merchant_experience_to_summary_v1` → `summary.merchant_experience_integration_v1` |
| Probe | `GET /dev/merchant-experience?store=demo` (wiring-only in `main.py`) |
| Page consumer | `static/merchant_experience_integration_v1.js` |
| Version | `meif_v1` / `meif_v1_gen` |

### Home package sections

Executive Summary · Critical Attention · Operational Health · Knowledge Highlights · Commercial Guidance Highlights  

Plus operational truth counts. No page-owned KPI invention; false zero theatre suppressed when durable carts exist.

### Decision Workspace

Always navigable when MEIF is on (`#workspace`). Answers: *Why is this happening, and what should I review?* Consumes Knowledge + Guidance-bearing compositions — never raw events.

### Carts

If durable carts exist → `forbid_please_wait=true`; false empty-states suppressed.

### Communication

Own hash `#communication` — not Settings WhatsApp. Consumes governed communication state + SCF items.

### Navigation integrity

| Entry | Target |
|-------|--------|
| Home | `#home` |
| Decision Workspace | `#workspace` |
| Carts | `#carts` |
| Communication | `#communication` |
| Settings | `#settings` (not WhatsApp default) |

---

## 6. Knowledge translation

`merchant_experience_knowledge_translation_v1.py`:

- Technical → merchant Arabic presentation
- Never strengthens claims
- Never invents certainty
- Soft-wraps unmatched technical statements as “technical note” rather than shipping ECF internals as daily ops language

Platform Knowledge statements remain unchanged.

---

## 7. Surface consumption audit

Every visible MEIF item carries:

- `information_class`
- `source_lineage` / `source_type` / `source_id`
- `surface_owner`
- `presentation_intent`
- `freshness_state` / `visibility` / `priority`

Ungoverned page invention is out of scope for MEIF packages; legacy composers are bypassed when MEIF applies Home.

---

## 8. MEV1 high/critical resolution targets

Integration checklist embedded in generator `mev1_high_resolution`:

H01, H02, D01, C01, M01, K01, G02, S01, S02, T01, L01  

(Remaining High items that require Guidance product policy / Time Authority / SCF input expansion are **not** solved by inventing new intelligence in MEIF; they are noted for later governed layers.)

---

## 9. Tests

`tests/test_merchant_experience_integration_v1.py`:

- Integration map validity
- Knowledge translation (no claim strengthening)
- False empty-state prevention
- Navigation integrity
- Summary KPI override when durable carts
- Demo isolation / determinism
- Feature flag
- Probe allowlist
- `main.py` wiring-only

Verify helper: `scripts/_verify_merchant_experience_v1.py`

---

## 10. STOP

After production deploy + Reality Validation V2 comparison against MEV1:

**Do not begin visual redesign** until Reality Validation V2 confirms the merchant experience truthfully reflects what the platform already knows.
