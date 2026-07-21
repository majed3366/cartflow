# CartFlow Commerce Intelligence → Knowledge Integration V1

**Status:** Governed integration layer  
**Date (UTC):** 2026-07-22  
**Versions:** intake `ciknow_v1` · input `commerce_intelligence_synthesis_v1`  

> Synthesis identifies a supported commercial pattern.  
> Knowledge determines whether that pattern is durable and eligible to become something CartFlow knows.

---

## 1. Architectural position

```text
Governed Domain Evidence
        ↓
Commerce Intelligence Synthesis (cisyn_v1)
        ↓
Knowledge Intake (ciknow_v1)  ← THIS LAYER
        ↓
knowledge_statements (existing Knowledge Foundation table)
```

Does **not** modify Commercial Guidance, Routing, Presentation, or Home.

---

## 2. Existing Knowledge inventory

| Item | Status |
|------|--------|
| `generate_knowledge_v1` | ECF-only; **unchanged** |
| `knowledge_statements` | Reused (extended with CIS source lineage columns) |
| Knowledge types (ECF) | evidence_quality / metric_trend / gap / conflict |
| Multi-source intake | **Did not exist** — ciknow adds CIS path only |
| Naming | `ciknow_v1` does not collide with `cisyn_v1` / `kf_v1` |

**Decision:** Dedicated synthesis intake adapter. Do **not** extend `generate_knowledge_v1` (preserves ECF-only law and avoids CIS↔KF cycles).

---

## 3. Ownership

Owns: intake policy registry, eligibility, claim-boundary preservation, CIS→KF identity, accounting, supersession for ciknow rows.

Does not own: synthesis rules, Guidance, Presentation, ECF knowledge generation.

---

## 4. Input / forbidden inputs

**Input only:** `commerce_intelligence_synthesis_v1` via `generate_commerce_intelligence_syntheses_v1`.

Forbidden: Widget/WhatsApp/movement/cart/product/purchase tables, provider payloads, page APIs.

---

## 5. Eligibility (summary)

| Synthesis state | Intake |
|-----------------|--------|
| qualified | Evaluate → may create commercial / gap / influence knowledge |
| observing | Abstain (no established commercial knowledge) |
| insufficient_evidence | May create `commercial_evidence_gap` if policy allows |
| conflicting_evidence | May create `commercial_evidence_conflict` |
| blocked | Reject — no commercial conclusion |
| failed | Reject |

Deferred rules (D-CISYN-01/02): discount / VIP remain non-qualifying until synthesis qualifies.

---

## 6. Claim boundary invariant

```text
Knowledge claims ⊆ Synthesis allowed claims
```

Known / unknown / prohibited preserved. No causal inflation. No attribution collapse. No ROI inflation.

---

## 7. Runtime

- Modules: `services/product_data/commerce_intelligence_knowledge_*`
- Flag: `CARTFLOW_COMMERCE_INTELLIGENCE_KNOWLEDGE_INTEGRATION_V1`
- Probe: `GET /dev/commerce-intelligence-knowledge?store=demo`
- Alembic: `f5a6b7c8d9e0` (lineage columns on `knowledge_statements`)

---

## 8. Forbidden / STOP

No Guidance, Presentation, Surface Composition, Home UI, AI, or automatic actions.  
After production close: **STOP** until review.
