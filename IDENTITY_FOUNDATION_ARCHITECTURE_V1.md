# CartFlow Identity Foundation Architecture V1

**Status:** Approved — Product Identity Foundation Implementation V1 applied (READY)  
**Date (UTC):** 2026-07-19  
**Type:** Permanent architectural governance (docs only — no Knowledge expansion, no Home redesign)  
**Trigger evidence:** [`PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md`](PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md)  
**Sibling authorities:**  
- [`IDENTITY_AUTHORITY_ARCHITECTURE_V1.md`](IDENTITY_AUTHORITY_ARCHITECTURE_V1.md) — *which merchant / which store* (MQIC)  
- Time Authority — *as of when*  
- This document — *which domain entity* (Product, Customer, Cart line, Channel, …)

**Companion artefacts:**

| Deliverable | Document |
|-------------|----------|
| Investigation Checklist | [`IDENTITY_INVESTIGATION_CHECKLIST_V1.md`](IDENTITY_INVESTIGATION_CHECKLIST_V1.md) |
| Foundation Contract | [`IDENTITY_FOUNDATION_CONTRACT_V1.md`](IDENTITY_FOUNDATION_CONTRACT_V1.md) |
| Authenticity Rules | [`IDENTITY_AUTHENTICITY_RULES_V1.md`](IDENTITY_AUTHENTICITY_RULES_V1.md) |
| Readiness Checklist | [`IDENTITY_READINESS_CHECKLIST_V1.md`](IDENTITY_READINESS_CHECKLIST_V1.md) |
| First application | [`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md) |

---

## 0. Why this exists

Commercial Knowledge was built while Product Identity was not fully validated. Proven outcomes:

- Fixture-driven merchant knowledge («منتج X» / Product X)
- Broken evidence loaders
- Incomplete projections
- Identity degradation inside simulation
- Merchant surfaces unable to display authentic entities

**The defect was not Commercial Knowledge itself.**  
**The defect was the absence of a mandatory Identity Foundation gate.**

This architecture makes that gate permanent for every future knowledge domain.

---

## 1. Primary question

### What must be true before CartFlow may speak about a domain entity as knowledge?

**Answer:** the domain must have a completed **Identity Foundation** — a governed, end-to-end identity chain from creation through snapshot, projection, and honest failure — **before** Truth Validation for knowledge, Knowledge Layer work, or Commercial Intelligence begins.

Identity Foundation answers: *what is this entity, and can we prove we know it?*  
Identity Authority answers: *for which merchant store?*  
Time Authority answers: *as of when?*

All three are required for lawful merchant-facing understanding speech.

---

## 2. Permanent architectural order

No Knowledge implementation may bypass this order:

```text
Domain
  ↓
Identity Investigation
  ↓
Identity Foundation
  ↓
Truth Validation
  ↓
Knowledge Layer
  ↓
Commercial Intelligence
  ↓
Merchant Surface
```

| Stage | Purpose | May produce merchant claims? |
|-------|---------|------------------------------|
| **Domain** | Named knowledge subject (Product, Hesitation Reason, …) | No |
| **Identity Investigation** | Prove where identity is created, lost, fabricated | No |
| **Identity Foundation** | Canonical identity, SoT, snapshot, projection, authenticity | No merchant knowledge claims |
| **Truth Validation** | Domain facts durable and correctly owned | Facts only — not intelligence |
| **Knowledge Layer** | Governed patterns from validated truth | Only after Foundation ready |
| **Commercial Intelligence** | Merchant questions answered with evidence | Only after Foundation + Truth |
| **Merchant Surface** | Presentation of admitted knowledge | Never invents identity |

**Hard stop:** If Identity Foundation is incomplete, Knowledge Layer and Commercial Intelligence for that domain are **forbidden** — including “temporary” fixtures on merchant production paths.

---

## 3. What Identity Foundation is

Identity Foundation is a **reusable architectural pattern**, not a Product-only fix.

For **every** domain, Foundation must define:

| Requirement | Meaning |
|-------------|---------|
| **Canonical identity** | Stable key + grain (what one “thing” is) |
| **Source of truth** | Single owning store/module per identity fact |
| **Immutable identifiers** | Fields that must not rewrite history when corrected |
| **Human-readable identity** | Display name/label merchants may see |
| **Provider mapping** | How Zid / Salla / Shopify / demo / sim map into canonical form |
| **Snapshot strategy** | When and how identity is frozen for history |
| **Projection strategy** | How identity reaches read models / surfaces |
| **Historical consistency** | What older rows may lack; how unresolved is spoken |
| **Simulator compatibility** | Sim must not invent or degrade merchant-facing identity |
| **Failure modes** | How identity can be missing, split, or colliding |
| **Fallback policy** | Allowed degrade paths (never silent fabrication) |
| **Authenticity guarantees** | Binding rules from [`IDENTITY_AUTHENTICITY_RULES_V1.md`](IDENTITY_AUTHENTICITY_RULES_V1.md) |

---

## 4. Scope of “identity domains”

Identity Foundation applies to any domain that will feed Knowledge or Commercial Intelligence, including (non-exhaustive):

| Domain example | Entity grain |
|----------------|--------------|
| **Product** | Platform product / variant / SKU / name-tier |
| **Customer contact** | Phone / channel identity (already partially governed elsewhere) |
| **Cart / session** | Cart id, session id, recovery key |
| **Purchase** | Order / purchase truth key |
| **Hesitation reason** | Reason taxonomy identity |
| **Recovery channel** | WhatsApp / provider message identity |
| **Store / merchant** | MQIC — owned by Identity Authority (not re-owned here) |

**Store / merchant identity** remains owned by Identity Authority Architecture. This Foundation does **not** redefine MQIC; it requires domain entities to be scoped under a resolved MQIC.

---

## 5. Relationship to existing layers

| Layer | Relationship |
|-------|--------------|
| Merchant Trust Constitution | Authenticity strengthens trust; fabrication violates trust |
| Identity Authority (MQIC) | Tenant scope for all domain identities |
| Product Data Foundation | Product domain’s engineering substrate — must satisfy this gate |
| Proof of Value / Decision Governance | May not claim understanding of an entity without Foundation readiness |
| Knowledge Routing | Routes only knowledge whose domain Identity Foundation is Ready |
| Execution Governance | High/Critical work packages for knowledge domains must show Foundation readiness in DoR |

---

## 6. Gate model

```text
Identity Investigation complete
        ↓
Foundation artefacts filled (contract + map)
        ↓
Readiness Checklist = READY
        ↓
Architecture / Product approval
        ↓
Truth Validation → Knowledge → Commercial Intelligence → Surface
```

Readiness states: **NOT STARTED · IN INVESTIGATION · FOUNDATION DRAFT · READY · BLOCKED**.  
See [`IDENTITY_READINESS_CHECKLIST_V1.md`](IDENTITY_READINESS_CHECKLIST_V1.md).

---

## 7. First application

**Product Identity** is the first domain mapped under this governance:  
[`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md).

Product Identity implementation work (capture, loader, projection, simulator honesty) must follow Foundation readiness — **not** proceed as an isolated “fix Product X” patch, and **not** unblock Commercial Knowledge Expansion until Product Identity Foundation is **READY** and approved.

---

## 8. Non-goals (this document)

- Does not implement Product Identity fixes
- Does not expand Commercial Knowledge
- Does not redesign Home or Carts
- Does not replace Identity Authority / MQIC
- Does not authorize fixture-backed merchant knowledge

---

## 9. Approval and STOP

**STOP** after governance ratification path:

1. Product + Architecture review this Architecture + companions  
2. Approve or request changes  
3. Product Identity Foundation work proceeds under the map  
4. Commercial Knowledge Expansion resumes **only after** Product Identity Foundation = **READY** (approved)

**Current status:** Proposed. Not yet binding until Approved.
