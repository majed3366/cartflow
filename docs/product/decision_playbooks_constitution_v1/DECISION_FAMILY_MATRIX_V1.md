# Decision Family Matrix V1

**Status:** Constitutional cross-family matrix.  
**Date (UTC):** 2026-07-28  
**Authority:** Companion to [`DECISION_PLAYBOOK_CATALOG_V1.md`](./DECISION_PLAYBOOK_CATALOG_V1.md) and [`DECISION_PLAYBOOKS_CONSTITUTION_V1.md`](./DECISION_PLAYBOOKS_CONSTITUTION_V1.md).  
**Non-goals:** No UI. No scoring engine. No implementation.

This matrix is the **at-a-glance law** for generators and reviewers: domain, evidence bar, readiness posture, validation class.

---

## Legend

| Column | Meaning |
|--------|---------|
| **EM Type** | Execution Methodology Type A Internal / B Platform / C Business |
| **Primary location** | CartFlow · Commerce Platform · Business Operation |
| **Evidence bar** | Relative minimum bar before playbook generation (**DP-004**) |
| **Default readiness posture** | Typical EM-001 starting posture when signals exist but are incomplete — not a fixed runtime value |
| **Validation class** | Primary EM-002 observation class |
| **Umbrella?** | If yes, must collapse to a concrete subordinate family before publish |

Evidence bar scale: **Low** · **Medium** · **High** · **Inherited** (must use subordinate family’s bar).

---

## Matrix

| Family ID | Family | EM Type | Primary location | Evidence bar | Default readiness posture | Validation class | Umbrella? |
|-----------|--------|---------|------------------|--------------|---------------------------|------------------|-----------|
| **PF-SHIPPING** | Shipping | B (often C) | Commerce Platform | High | NEEDS_MORE_EVIDENCE until threshold/cohort + leave-after-shipping linked | Lower abandonment after shipping · Higher completion | No |
| **PF-PAYMENT** | Payment | B (often C) | Commerce Platform | High | NEEDS_MORE_EVIDENCE until method/error + payment-stage drop linked | Lower payment abandonment · Higher completion | No |
| **PF-PRODUCT** | Product | B (often C) | Commerce Platform | Medium–High | NEEDS_MORE_EVIDENCE until named product + leave stage | Higher completion for named product | No |
| **PF-PRICING** | Pricing | B / C | Commerce Platform | High | Often EXTERNAL_DEPENDENCY / merchant judgement; READY only with clear price-linked diagnosis | Higher conversion for named object | No |
| **PF-RECOVERY-MSG** | Recovery Messages | A (or B) | CartFlow | Medium | READY when named message outcomes suffice; else NEEDS_MORE_EVIDENCE | Higher recovery · Higher return-to-checkout | No |
| **PF-WHATSAPP** | WhatsApp | A / B | CartFlow (+ provider) | Medium–High | EXTERNAL_DEPENDENCY when WABA/provider blocks; else READY/BLOCKED by config | Higher WhatsApp-path recovery / delivery | No |
| **PF-CHECKOUT** | Checkout | B | Commerce Platform | High | NEEDS_MORE_EVIDENCE until named stage drop | Lower stage abandonment · Higher completion | No |
| **PF-TRUST** | Trust | B / C | Commerce Platform | Medium | NEEDS_MORE_EVIDENCE until trust object + surface named | Lower trust-path abandonment | No |
| **PF-PRODUCT-IMAGES** | Product Images | B / C | Commerce Platform | Medium | READY when named product image gap is clear | Higher completion for named product | No |
| **PF-DELIVERY** | Delivery | B / C | Platform / Business Ops | High | Often EXTERNAL_DEPENDENCY or Business Operation | Lower delivery-linked abandonment | No |
| **PF-RETURNING** | Returning Visitors | A / B | CartFlow / Platform | Medium–High | READY when cohort + action path clear | Higher returning-cohort completion | No |
| **PF-LOW-CONV** | Low Conversion | Inherited | Inherited | **Inherited** | Must not READY as umbrella task | Inherited | **Yes** |
| **PF-HIGH-INTEREST** | High Interest / Low Purchase | B (usually) | Commerce Platform | High | Prefer subordinate family; NEEDS_MORE_EVIDENCE until leave stage + cause | Higher completion for high-interest object | **Yes** (prefer bind) |
| **PF-VIP** | VIP Customers | A (often C) | CartFlow | Medium | READY when VIP cohort + gap clear; else NEEDS_MORE_EVIDENCE | Higher VIP recovery / completion | No |
| **PF-COMMUNICATION** | Communication | A | CartFlow | Medium | READY when named message/channel gap clear | Higher recovery / reply / return | No |
| **PF-PLATFORM-CONFIG** | Platform Configuration | B | Commerce Platform | Medium–High | Often **BLOCKED** until config fixed | Path completion resumes | No |
| **PF-BUSINESS-OPS** | Business Operations | C | Business Operation | High | **EXTERNAL_DEPENDENCY** (ops) — never pretend Type A | Downstream commerce metric named by diagnosis | No |

---

## Routing implications (law, not navigation UI)

| Primary location | Merchant action locus | Forbidden routing |
|------------------|----------------------|-------------------|
| **CartFlow** | Internal CartFlow surface for that task | Dumping Type A tasks into platform Products by default |
| **Commerce Platform** | Platform settings / catalog / checkout owned by Zid·Salla·Shopify (or future) | Claiming CartFlow will perform the platform change |
| **Business Operation** | People / contracts / creative / offline process | Fake in-app “Done” without ops reality |

**Never use fixed navigation.** Routing follows family location + instance specificity (**Execution Methodology** Types A/B/C).

---

## Evidence → publication gate (all families)

```
Diagnosis
  ↓
Evidence
  ↓
Execution Readiness (EM-001)
  ↓
Playbook Validation (PBL-001 — seven YES)
  ↓
Playbook Publication
```

| Gate | Fail → |
|------|--------|
| Evidence < minimum / PBL-002 Minimum Evidence | Diagnosis only |
| Readiness < family Minimum Readiness for full playbook | Diagnosis only (or honest non-READY posture — no fake executable playbook) |
| Confidence < Minimum Confidence | Diagnosis only |
| Any PBL-001 question = NO | Diagnosis only · playbook suppressed |
| Incomplete PBL-002 metadata | Family cannot emit |

**Preference:** rather no playbook than a weak playbook (**PBL-001**).

Umbrella families (`PF-LOW-CONV`, unbound `PF-HIGH-INTEREST`) **fail the gate** until bound to a concrete subordinate task (and that family’s metadata).

---

## Validation class index

| Class | Typical families |
|-------|------------------|
| Higher purchase completion | Product, Pricing, Checkout, Images, Returning, High Interest |
| Lower abandonment (stage-specific) | Shipping, Payment, Checkout, Delivery, Trust |
| Higher recovery / return-to-checkout | Recovery Messages, WhatsApp, Communication, VIP |
| Path unblocked / errors down | Platform Configuration |
| Downstream ops-linked commerce metric | Business Operations |

Every instance must pick **one primary** validation class (secondary rollups allowed, not substitutes).

---

## STOP

Matrix is generation law only.

**No implementation. No UI. No production copy.**

Await constitutional approval with the rest of this pack.
