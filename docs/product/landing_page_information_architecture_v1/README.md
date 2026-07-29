# Landing Page Information Architecture V1

**Status:** Architectural product definition — governance only.  
**Date (UTC):** 2026-07-29  
**Governing authority:** [`docs/product/landing_page_constitution_v1/`](../landing_page_constitution_v1/)  
**Surface (future):** `GET /` · `templates/cartflow_landing.html`

## Pack contents

| Document | Role |
|----------|------|
| [`LANDING_PAGE_INFORMATION_ARCHITECTURE_V1.md`](./LANDING_PAGE_INFORMATION_ARCHITECTURE_V1.md) | Approved section sequence, section fields, architectural review, decision table |
| [`SECTION_CONTRACTS_V1.md`](./SECTION_CONTRACTS_V1.md) | Binding per-section contracts (owner, claims, evidence class, readiness, mobile, removal test) |

## What this pack is

Structural architecture for the **future** CartFlow landing page:

- Exact section sequence **LP-01 … LP-16**
- One merchant question + one responsibility per section
- Cognitive journey from problem recognition → calm action
- Broader identity **earned** at Knowledge Layer (not claimed in Hero)
- Evidence readiness and maturity risks recorded

## What this pack is not

- No redesign of the current landing  
- No final Arabic copy  
- No Figma / wireframes  
- No screenshot selection  
- No 3D assets  
- No frontend implementation  
- No production UI change  
- No pricing / subscription architecture  

## Approved sequence (summary)

```text
LP-01 Navigation
LP-02 Hero
LP-03 Problem Recognition
LP-04 Recovery Limitation Reframe
LP-05 How CartFlow Works
LP-06 Widget Evidence
LP-07 WhatsApp Journey Evidence
LP-08 Dashboard Evidence
LP-09 Knowledge Layer Discovery
LP-10 Decision Value
LP-11 Continuous Value Journey
LP-12 Trust and Governance
LP-13 Integration Readiness
LP-14 FAQ
LP-15 Final CTA
LP-16 Footer
```

## Key architectural decisions

| Decision | Outcome |
|----------|---------|
| Proposed baseline LP-01…LP-16 | **All kept** after necessity / overlap / removal tests |
| LP-05 vs LP-06…LP-08 | Outline vs dedicated primary evidence — split required by One Purpose Per Section |
| Broader identity | Earned at **LP-09**; foreshadowed by evidence only from LP-08 |
| Integrations | Truthful states only — Zid supported (ops-gated); Salla/Shopify planned |
| Primary CTA | **Start Free** → `/signup`; **Book a Demo** deferred |
| Knowledge | Requires validation; no fabricated findings; illustrative must be labeled |

## Constitution compliance

This pack is subordinate to Landing Page Constitution V1, especially:

- Merchant Problem First  
- Landing Disclosure Law  
- One Purpose Per Section  
- Truth Policy  
- Visual Evidence Law  
- Screenshot Policy  
- Mobile First  
- Evidence Before Claims  
- Calm CTA Philosophy  

---

## STOP — Landing Page Information Architecture V1 requires constitutional and product approval before:

- Arabic copywriting
- Wireframing
- Screenshot selection
- 3D visual direction
- Figma design
- Frontend implementation

**No redesign is authorised by completing this pack.**
