# Before / After Architecture — Gate 2 Decision Ownership

**Date (UTC):** 2026-07-24

---

## Before (duplicate Decision ownership)

```mermaid
flowchart TB
  Ev[Evidence] --> BFL[Business Findings / BFL]
  BFL --> FDE[Finding Decision Engine]
  FDE --> MEIF_D["MEIF #meif-decision-root"]
  FDE --> HOME["Home MEIF / HES explain"]
  FDE --> CARTS["Carts MI recommendations"]
  CW_OPS["Cart Workspace ops cards"] --> MERCHANT
  MEIF_D --> MERCHANT[Merchant]
  HOME --> MERCHANT
  CARTS --> MERCHANT
  COMMS["Communication findings"] --> MERCHANT
```

Problems:

- Three+ merchant paint paths for business reasoning  
- Under Home slim transport, FDE often never reached a Decision surface  
- Carts showed recommendations parallel to Workspace  

---

## After (single Decision Owner)

```mermaid
flowchart TB
  Ev[Evidence] --> BFL[Business Findings / BFL]
  BFL --> FDE[Finding Decision Engine]
  FDE --> ENRICH["CW enrichment\nbusiness_findings_enrichment_v1"]
  ENRICH --> CW["Cart Workspace #workspace\nSOLE Decision Owner"]
  OPS[Ops judgment cards] --> CW
  CW --> MERCHANT[Merchant]
  FDE -.teaser count only.-> HOME["Home HES\nView Details → Workspace"]
  HOME -->|navigate| CW
  CARTS["Carts — ops only"] -.->|no business Decision| X1(( ))
  COMMS["Communication — status only"] -.->|no Decision| X2(( ))
  MEIF_D["#meif-decision-root"] -.->|retired / dual-stack OFF| X3(( ))
```

Permitted flow only:

```text
Evidence → Business Finding → Confidence → Recommended Action → Decision
  → Cart Workspace → Merchant
```

---

## Ownership table

| Concern | Before | After |
|---------|--------|-------|
| Business Decision UI | MEIF + CW + Home + Carts | **CW only** |
| Home decisions | Explain / fat MEIF | Teaser + CTA → CW |
| Carts recommendations | Painted | Stripped |
| Communication findings | Painted | Status only |
| FDE data | Attached to MEIF packages | Enriched into CW projection |
| Rollback | N/A | `CARTFLOW_DECISION_DUAL_STACK_V1=1` |
