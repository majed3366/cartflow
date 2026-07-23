# CartFlow Commerce Intelligence Synthesis Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Peer to Product Performance stack; does **not** replace Knowledge, Guidance, or Presentation.  
**Audience:** Product, engineering, architecture  

> **Law:** Channels produce evidence. Synthesis combines evidence. Knowledge later interprets meaning. Guidance decides recommendations. Presentation communicates.  
> Synthesis never becomes a second Guidance or Presentation engine.

---

## 0. Architectural decision (inventory)

| Existing | Status | Relationship |
|----------|--------|--------------|
| Product Performance stack (Signals→…→Presentation) | PRODUCTION CLOSED | **Inputs** (Knowledge primary; not rewritten) |
| Business Findings / Reasoning | Implemented, not closed | **Not duplicated**; not SoT for CIS |
| Home Commercial Intelligence | Wired, await review | Downstream consumer later — **not owned here** |
| Commerce Signals V1 | Runtime, flag default off | Optional governed source adapter |
| Commerce Brain docs | Draft (main) | Not implemented as runtime SoT |

**Decision:** **NEW synthesis sublayer** (`cisyn_v1`) — not a replacement of KF/CGF/Home CI.  
**Naming:** `commerce_intelligence_synthesis_*` / table `commerce_intelligence_syntheses`.  
**Collision:** Avoid writing into `knowledge_statements` or `commercial_guidance_records`.

---

## 1. Purpose

Answer: *What commercially meaningful pattern is supported when CartFlow combines evidence across store, behavior, recovery, and purchase outcomes?*

Not: recommendations, UI, wording, actions, ROI, causal claims.

---

## 2. Placement

```text
Canonical Domain Truth / Product Performance foundations
        ↓
Commerce Intelligence Synthesis  ← THIS LAYER
        ↓
(Knowledge / Guidance / Presentation — future consumers; not modified in V1)
```

V1 produces a versioned output contract only. No Knowledge/Guidance rule changes. No merchant UI.

---

## 3. Ownership

Owns: cross-domain pattern qualification, registries, lineage, contradiction/insufficiency, temporal windows, source contribution accounting, deterministic refresh.

Does not own: raw collection, purchase/attribution/ROI truth, guidance, routing, presentation, AI.

---

## 4. Inputs (source contract registry `cisrc_v1`)

| Source domain | Contract | Adapter |
|---------------|----------|---------|
| knowledge | `generate_knowledge_v1` | required |
| product_hesitation | hesitation mapping APIs | optional |
| product_purchase | purchase mapping APIs | optional |
| commerce_signals | `load_store_commerce_signals_v1` | optional |

Forbidden: provider-specific fields, raw Meta/Twilio payloads, frontend state, ungoverned JSON.

---

## 5. Output

Table `commerce_intelligence_syntheses` / contract `commerce_intelligence_synthesis_v1`.

States: `qualified`, `observing`, `insufficient_evidence`, `conflicting_evidence`, `blocked`, `expired`, `superseded`, `failed`.

Mandatory: known / unknown / prohibited, source contributions, fingerprints, window, lineage.

---

## 6. Rule registry (`cisyn_v1`)

V1 rules (small set):

1. `product_interest_without_purchase`
2. `high_traffic_weak_conversion`
3. `whatsapp_return_without_purchase`
4. `shipping_hesitation_recovery_outcome`
5. `repeated_interest_pattern`
6. `recovery_influence_boundary`
7. `insufficient_evidence_store`
8. `conflicting_evidence_store`

Each defines required sources, min sample, window, support/conflict, abstention.

---

## 7. Boundaries

- No causality inflation  
- Purchase Truth / attribution classifications preserved when present in commerce_signals  
- Confidence **input** fields only (coverage, maturity, contradiction) — Evidence Confidence remains owner of confidence evaluation  
- Full candidate accounting; no silent loss  

---

## 8. Runtime

- Modules: `services/product_data/commerce_intelligence_synthesis_*`
- Flag: `CARTFLOW_COMMERCE_INTELLIGENCE_SYNTHESIS_V1`
- Probe: `GET /dev/commerce-intelligence-synthesis?store=demo`
- Alembic: `e4f5a6b7c8d9`
- Demo allowlist only

---

## 9. Forbidden / STOP

No UI, Composition, Guidance/Presentation changes, Knowledge writes, AI, automatic actions.  
After production close: **STOP** until review.
