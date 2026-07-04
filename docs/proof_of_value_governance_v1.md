# CartFlow Proof of Value Governance V1

**Status:** Governance (authoritative commercial contract) — no implementation, no runtime change, no UI design  
**Date (UTC):** 2026-07-04  
**Phase:** Merchant Value Era — Foundation → **Governance** → (future) Contracts → Implementation → Metrics → Enforcement  
**Domain:** Merchant-visible proof — claims, confidence, metrics, surfaces, commercial integrity  
**Single source of evidence:** [`docs/proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) + [`docs/merchant_value_audit_v1.md`](merchant_value_audit_v1.md)  
**Precedence:** Subordinate to [`engineering_constitution_v1.md`](engineering_constitution_v1.md) for engineering truth; peer to Provider Reliability Governance, Dashboard Read Model Governance, Snapshot Generation Governance. Governs *merchant proof*; it does not override Purchase Truth, Lifecycle Truth (LT-C1), or Provider Truth ownership.

> This document defines **HOW merchant proof must work** — not how it currently works (Merchant Value Audit) and not how it will be built (future implementation). Future surfacing work does not get to *decide* proof behavior; it *implements this governance*.

**Canonical inputs (no new merchant value invented):**

| Document | Role |
|----------|------|
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | PV-1…PV-18, confidence model, metrics registry, CI rules |
| [`merchant_value_audit_v1.md`](merchant_value_audit_v1.md) | Current gaps, maturity **Level 1 Working**, audit baseline |
| [`cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) | Value domains, daily brief contract |
| [`SYSTEM_SUMMARY.md`](SYSTEM_SUMMARY.md) | Shipped surfaces, truth-layer owners |

---

## 0. Scope, authority, and traceability

**In scope:** every merchant-visible claim, metric, insight, recommendation, tier promise, and confidence label — across dashboard, APIs exposed to merchants, marketplace listings, sales, and support scripts referencing product outcomes.

**Out of scope (governed elsewhere, must not be weakened):** Purchase Truth minting, LT-C1 lifecycle classification, Provider Reliability send/retry semantics, Snapshot Generation cadence, recovery scheduling logic, billing/payment processing (not implemented).

**Evidentiary discipline:** every governance contract traces to a demonstrated foundation contract or audit finding. Traceability in §4.4.

**Current compliance posture (honest baseline):** Merchant Value Audit documents **known violations and gaps** (e.g. PV-11 «sent» copy, PV-3 absent SAR, PV-17 intervention without action). Governance adoption does not assert full compliance — it defines the target state and verification obligations.

---

## Section 1 — Proof Governance Principles

Permanent governing principles. Ordered — earlier principles constrain later ones. Map to foundation §1.

| # | Principle | Governs | It is failing when… |
|---|-----------|---------|---------------------|
| **PG-1** | **Truth Before Claims** | No merchant claim precedes Tier 0–2 evidence | KPI, headline, or tier bullet asserts outcome truth layer does not support |
| **PG-2** | **Evidence Before Confidence** | Confidence computed from evidence chain (weakest link) | UI severity, copy tone, or AI narration implies higher certainty than evidence |
| **PG-3** | **Proof Before Presentation** | Presentation composes proof; never creates it | Dashboard/marketing treated as source of truth (R-1 violation) |
| **PG-4** | **Proof Before Intelligence** | KL / future engines compose patterns only | Insight or ranking shown without primary evidence + confidence (R-3 violation) |
| **PG-5** | **Measured Before Estimated** | Rates have denominators; insufficient data explicit | Projections, benchmarks, or bare counts presented as KPIs |
| **PG-6** | **Commercial Integrity Before Growth** | Withheld claim > inflated claim | Upsell, referral, or renewal depends on unverifiable proof |
| **PG-7** | **Unknown Remains Unknown** | Unknown is mandatory, observable state | Missing evidence rendered as success, pending-as-delivered, or zero |
| **PG-8** | **One Proof Owner Per Question** | Each merchant question has truth + presentation + governance owner (§2) | Same metric on two surfaces with divergent definitions (DR-DUP class defect) |
| **PG-9** | **Governance Before Surfacing** | New merchant proof ships only after contract + owner registered | Feature adds claim without PV contract traceability |
| **PG-10** | **Observability Is Not Optional** | Proof quality measurable internally even when not merchant-visible | Cannot audit compliance of a claim in production |

**Prime directive (ratified from foundation §1.6):**

> Every merchant-visible proof must strengthen trust through evidence — and must not silently weaken it for growth convenience.

---

## Section 2 — Proof Ownership

Every proof domain requires **three owners**. No merchant proof ships without all three named in implementation design (future) or documented here (governance).

### 2.1 Ownership model

| Role | Responsibility | Must not… |
|------|----------------|-----------|
| **Truth owner** | Tier 0–1 evidence — single engineering SoT | Be duplicated by presentation computation |
| **Presentation owner** | Merchant surface/API that displays proof — consumes truth read-only | Mint, infer, or override truth |
| **Governance owner** | PV contract compliance, confidence rules, metric registry, tier alignment | Ship features that bypass PG-9 |

**Governance owner (domain-wide):** Proof of Value domain — documented in this file; operational accountability: product + engineering lead for merchant surfaces (institutional memory ownership map to be updated on implementation).

### 2.2 Recovery Proof

| Role | Owner (today) | Notes |
|------|---------------|-------|
| **Truth** | `cartflow_purchase_truth.py` (outcomes); `RecoverySchedule` + `CartRecoveryLog` (actions); `purchase_attribution_v1.py` / `knowledge_purchase_attribution_v1.py` (attribution); `provider_reliability_truth_v1.py` (delivery disposition) | VIP lane: `vip_operational_truth_v1.py` — KL-C4 isolation |
| **Presentation** | `#carts` lifecycle + purchase labels; `#home-month` recovery highlights; `#vip` + carts banner; future Recovered Revenue KPI | **Gap:** attributed SAR not surfaced (PV-3) |
| **Governance** | Proof of Value Governance §4 (PV-2,3,11,12,13) | Cross-check Provider Reliability PR-TM-2 for delivery |

### 2.3 Understanding Proof

| Role | Owner (today) | Notes |
|------|---------------|-------|
| **Truth** | LT-C1: `customer_lifecycle_states_v1.py`; reasons: `CartRecoveryReason`; patterns: `knowledge_layer_v1.py` + `knowledge_health_v1.py`; product: `product_data/*` (foundation — merchant **Future**) | LT-C1 CI gate enforces mint |
| **Presentation** | `#carts` lifecycle block; `#home` KL + weekly reasons; `merchant_knowledge_layer.js` | Strongest proof surface: cart rows |
| **Governance** | Proof of Value Governance §4 (PV-14,15,16); LT-C1 enforcement (engineering) | KL health required below High confidence |

### 2.4 Decision Proof

| Role | Owner (today) | Notes |
|------|---------------|-------|
| **Truth** | LT-C1 `merchant_needed`, next-action fields; `cartflow_merchant_action_matrix_v1.md` (documented eligibility); future Decision Engine **not implemented** | Audit: C− decision confidence |
| **Presentation** | Lifecycle «التالي / تدخل التاجر»; archive/reopen actions; VIP merchant alert; future Daily Brief | **Gap:** normal-carts intervention without executable action (PV-17) |
| **Governance** | Proof of Value Governance §4 (PV-4,17,18); `cartflow_merchant_decision_summary_v1.md` | Daily Brief contract from Value Validation §5 |

### 2.5 Operational Proof

| Role | Owner (today) | Notes |
|------|---------------|-------|
| **Truth** | `merchant_onboarding_reality_v1.py`; `integration_health_v1.py`; `widget_configuration_trust_v1.py`; `storefront_runtime_truth_gate_v1.py`; `dashboard_read_observability_v1.py` + snapshot read model | Ops metrics: `operational_metrics_v1.py` — merchant **Future** |
| **Presentation** | `#home-setup`, `#whatsapp`, `#settings` store connection; snapshot-served dashboard APIs | **Gap:** freshness not explained to merchant |
| **Governance** | Proof of Value Governance §4 (PV-6,8); Dashboard Read Model DR-* for read freshness | Setup overstate risk documented in platform readiness |

### 2.6 Commercial Proof

| Role | Owner (today) | Notes |
|------|---------------|-------|
| **Truth** | Composite proof readiness — no single module; tier definitions: `cartflow_plans_v1.py`, `merchant_plans_catalog_v1.py` | Billing truth **Future** |
| **Presentation** | `#plans`, `#settings` subscription card; landing (`cartflow_landing.html` — no fake ROI policy) | Entitlements enforcement off by default |
| **Governance** | Proof of Value Governance §4 (PV-9); foundation §8 CI-1…CI-10; tier integrity matrix | Pro tier ahead of proof — documented |

### 2.7 Ownership contracts

| ID | Contract |
|----|----------|
| **PO-O-1** | Every new merchant-visible claim registers truth, presentation, and governance owner before ship. |
| **PO-O-2** | Presentation owner may not compute truth not available from truth owner read APIs. |
| **PO-O-3** | Governance owner rejects ship when PV contracts for the claim are **Future** without explicit **preview / partial** labelling (PV-9). |
| **PO-O-4** | Cross-domain claims declare primary proof domain + secondary only when both truth chains satisfied. |

---

## Section 3 — Proof Lifecycle

Permanent lifecycle every merchant proof must follow. Skipping a stage is a governance defect.

```
Truth          Engineering-governed Tier 0–1 evidence (Purchase, Lifecycle, Provider, …)
    ↓          Owner: engineering truth modules
Evidence     Identifiable records joinable to merchant context (recovery_key, purchase_id, …)
    ↓          Owner: truth modules + correlation discipline (PV-7)
Proof        Governed claim + confidence + proof_source + domain tag
    ↓          Owner: proof composition layer (future) — read-only over evidence
Merchant Surface   Dashboard, API, brief, report — presentation only
    ↓          Owner: presentation owners (§2)
Commercial Value   Renewal, upsell, referral, tier justification
               Owner: commercial + governance review — never bypasses Proof stage
```

### 3.1 Stage ownership rules

| Stage | May write truth? | May raise confidence? | Merchant-visible? |
|-------|------------------|----------------------|-------------------|
| **Truth** | Yes (engineering only) | N/A | Rarely direct |
| **Evidence** | Append-only / read | N/A | Internal |
| **Proof** | No | Assign per §5 | Payload fields |
| **Merchant Surface** | No | No (C-3) | Yes |
| **Commercial Value** | No | No | External copy |

### 3.2 Lifecycle contracts

| ID | Contract |
|----|----------|
| **PO-L-1** | No merchant surface may skip **Proof** stage — even «simple» copy must map to evidence or **Unknown**. |
| **PO-L-2** | Commercial Value must cite the same proof definition as merchant surface (PV-6 internal/external parity). |
| **PO-L-3** | Regression: if truth degrades, proof confidence must downgrade automatically — never freeze optimistic presentation. |

---

## Section 4 — Governance Contracts

Foundation contracts **PV-1…PV-18** elevated to **governed, testable obligations**. Each specifies **owner**, **verification**, and **merchant impact**.

**Risk class (proof defects):**

| Class | Meaning | Example |
|-------|---------|---------|
| **P0** | Active merchant deception / trust destruction | Fake recovered revenue (CI-1) |
| **P1** | Material misrepresentation | «Delivered» on acceptance only (PV-11) |
| **P2** | Decision harm / anxiety without closure | Intervention flag without action (PV-17) |
| **P3** | Integrity drift | Duplicate metric definitions (PO-O-1) |

### 4.1 Universal contracts

| ID | Contract (testable) | Owner | Verification | Merchant impact | Risk |
|----|---------------------|-------|--------------|-------------------|------|
| **PV-1** | Every merchant-visible claim includes `proof_domain` + Tier 0–2 source reference | Governance + presentation | Proof inventory audit; future API/schema gate | Trust in all surfaces | P1 |
| **PV-2** | Purchase claims require `PurchaseTruthRecord`; action claims require Recovery Truth row | Recovery truth owners | Join purchase_id / recovery_key on claim sample | Wrong win/loss narrative | P0 |
| **PV-3** | Attributed revenue fields require attribution record + confidence ≠ Unknown-only | `purchase_attribution_v1` | No merchant SAR field without attribution join; KL-C2 parity | ROI trust | P0 |
| **PV-4** | Recommendations include `confidence` + `proof_domain` | Decision presentation | Inspect KL cards + lifecycle CTAs | False urgency | P1 |
| **PV-5** | Missing evidence → `confidence=unknown`; no default success | All presentation | Negative test: undispositioned delivery → Unknown | Silent wrong decisions | P1 |
| **PV-6** | Each merchant KPI has registered owner module, denominator, refresh, stale behavior | Governance + metric owner | Metric registry §7; ops parity check | Stale/wrong numbers | P1 |
| **PV-7** | Each proof item exposes trace id (`recovery_key`, `insight_id`, `correlation_key`, …) | Presentation + proof layer | Sample trace reconstructs evidence chain | Explainability | P2 |
| **PV-8** | Presentation lifecycle/purchase labels match LT-C1 / Purchase Truth | LT-C1 + dashboard projection | Parity test vs `normal-carts` API; LT-ENF gate | Contradictory cart state | P1 |
| **PV-9** | Tier/marketing claims ⊆ provable domains for tier (foundation §8.3) | Commercial governance | Tier claim matrix review per release | Upsell deception | P0 |
| **PV-10** | Rate metrics include explicit numerator/denominator in internal definition | Metric owner | Metric contract doc + sample recompute | Misleading percentages | P1 |

### 4.2 Recovery Proof contracts

| ID | Contract (testable) | Owner | Verification | Merchant impact | Risk |
|----|---------------------|-------|--------------|-------------------|------|
| **PV-11** | UI/API MUST NOT use «delivered/وصل» unless Provider Truth delivery altitude set | Provider + presentation | Map copy keys to disposition; reconcile sample sends | WhatsApp product trust | P0 |
| **PV-12** | Recovered SAR sums only attributed purchases; VIP reported separately when mixed | Attribution + KL metrics | Recompute sum vs attribution table; VIP lane filter | Inflated ROI | P0 |
| **PV-13** | Effectiveness comparisons require min sample + window metadata or confidence ≤ Low | KL / future analytics | Cohort metadata present or card suppressed | False «what worked» | P1 |

### 4.3 Understanding Proof contracts

| ID | Contract (testable) | Owner | Verification | Merchant impact | Risk |
|----|---------------------|-------|--------------|-------------------|------|
| **PV-14** | Lifecycle explanatory fields originate from LT-C1 API fields only | LT-C1 | LT-ENF-1 + dashboard field source audit | Wrong «what happened» | P1 |
| **PV-15** | KL insights with confidence < High expose coverage/diagnosis from `/api/knowledge/health` | `knowledge_health_v1` | Health payload linked when Medium/Low/Unknown | Overconfident patterns | P1 |
| **PV-16** | Product claims require identity tier ≥ governed threshold else Unknown | Product foundation | Block product insight cards when foundation health fails | Wrong product blame | P0 |

### 4.4 Decision Proof contracts

| ID | Contract (testable) | Owner | Verification | Merchant impact | Risk |
|----|---------------------|-------|--------------|-------------------|------|
| **PV-17** | Imperative recommendations require eligible action registry entry | Decision governance | Match CTA to `merchant_action_matrix`; VIP alert exception documented | Decision anxiety (audit D) | P2 |
| **PV-18** | Daily Brief: ≤5 items; each has what/why/action; one decision each | Daily Brief owner (future) | Brief schema validation | Daily habit trust | P1 |

### 4.5 Contract traceability (audit → contract)

| Merchant Value Audit finding | Contracts | Current compliance |
|------------------------------|-----------|-------------------|
| No attributed SAR | PV-3, PV-12 | **Open** — not surfaced |
| «Sent» ≠ delivered | PV-11 | **Open** — copy risk |
| Intervention without action | PV-17 | **Open** |
| No daily brief | PV-18, PV-4 | **Open** — KL partial |
| Tier ahead of proof | PV-9 | **Open** — Pro claims |
| `#completed` overload | PV-8, PV-14 | **Partial** |
| Lifecycle block strong | PV-14 | **Largely compliant** |
| KL honest attribution internal | PV-3, PV-12 | **Compliant** internally |

### 4.6 Future enforcement candidates (not in V1 scope)

Governance defines verification; **implementation** may later add:

- CI proof-inventory gate on merchant API payloads (peer to LT-C1)  
- Tier claim linter on `merchant_plans_catalog_v1.py` marketing strings  
- KL card schema validator (confidence + health linkage)  

No enforcement ships with this document.

---

## Section 5 — Merchant Trust Rules

Governed rules for confidence, uncertainty, attribution, delivery, recommendations, and unknown state. Implements foundation §7 + §8 as operational policy.

### 5.1 Confidence governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-C-1** | Exactly one of: Confirmed / High / Medium / Low / Unknown | Schema or review checklist |
| **MT-C-2** | Confidence = f(weakest evidence link) — documented mapping (foundation §7.3) | Recompute sample |
| **MT-C-3** | AI Explanation tier cannot increase confidence (C-2) | AI output audit |
| **MT-C-4** | Presentation styling cannot imply Confirmed when ≤ Medium (C-3) | UX review against confidence |
| **MT-C-5** | Upgrade requires new evidence artifact — not copy change (C-5) | Change log tied to truth events |

### 5.2 Uncertainty governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-U-1** | Insufficient KL coverage → show insufficient-data state, not empty success | `/api/knowledge/health` diagnosis |
| **MT-U-2** | Unknown provider disposition → never «pending success» copy (C-4) | PV-11 copy audit |
| **MT-U-3** | Product identity below threshold → Unknown (PV-16) | Product-data health gate |

### 5.3 Attribution governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-A-1** | «Recovered» / attributed language requires attribution tier + window documented | Attribution module output |
| **MT-A-2** | All purchases MUST NOT count as recovery wins (CI-7; KL-C2) | KL metric parity |
| **MT-A-3** | VIP attribution isolated from normal lane (KL-C4) | Lane filter on sums |

### 5.4 Delivery governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-D-1** | Merchant-facing send status uses disposition vocabulary aligned with Provider Truth — not raw log status | PR-TM-2 alignment |
| **MT-D-2** | Delivery rate KPI requires Provider Truth denominator (PV-10) | Metric registry |

### 5.5 Recommendation governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-R-1** | Low/Unknown confidence → no imperative «do now» (C-6) | Copy lint |
| **MT-R-2** | Eligible action required for action CTAs (PV-17) | Action matrix match |
| **MT-R-3** | Optional: state inaction consequence when automation continues | Lifecycle copy audit |

### 5.6 Unknown state governance

| Rule | Requirement | Verification |
|------|-------------|--------------|
| **MT-X-1** | Unknown is listed outcome — not omitted field | Payload presence |
| **MT-X-2** | Unknown MUST NOT block display of known partial evidence elsewhere on same row | Row-level composition |

---

## Section 6 — Commercial Integrity Governance

Foundation CI-1…CI-10 elevated to **governed prohibitions**. Commercial, product, support, and marketplace channels bound equally.

### 6.1 Prohibited claims registry

| ID | Prohibition | Governance check | Risk |
|----|-------------|------------------|------|
| **CI-1** | No recovered revenue totals without PV-3 | Release review + future metric gate | P0 |
| **CI-2** | No guaranteed ROI / «pays for itself» promise | Marketing + landing review | P0 |
| **CI-3** | No «delivered» from sent/accepted alone | PV-11 | P0 |
| **CI-4** | No product loss rankings without PV-16 | Feature flag on product insights | P0 |
| **CI-5** | No AI text as standalone fact | AI pipeline requires source ids | P1 |
| **CI-6** | No hidden uncertainty below High | MT-C-* audit | P1 |
| **CI-7** | No all-purchases-as-wins | KL + dashboard purchase labelling | P0 |
| **CI-8** | No self-serve production-ready when onboarding reality false | `merchant_onboarding_reality_v1` | P1 |
| **CI-9** | No Pro/intelligence outcomes as Confirmed before Partial maturity | PV-9 tier matrix | P0 |
| **CI-10** | No referral ROI without merchant-verifiable metric | Sales playbook review | P0 |

### 6.2 Allowed pilot claims (governed whitelist)

CartFlow **may** use these without additional proof layer — each maps to **Confirmed** or documented **Partial**:

| Claim | Proof domain | Evidence |
|-------|--------------|----------|
| Captures leave reasons when widget fires | Understanding | `CartRecoveryReason` |
| Governed lifecycle state per cart | Understanding | LT-C1 |
| Recovery automation runs when configured | Recovery + Operational | `RecoverySchedule` + env |
| VIP merchant alert path exists | Recovery + Decision | VIP alert API |
| KL insights when coverage sufficient | Understanding | KL health |
| Purchase stops recovery; «تم الشراء» | Recovery + Understanding | Purchase Truth |

### 6.3 Release gate (commercial)

Before any release affecting merchant-visible copy, metrics, or tier marketing:

1. Proof impact assessment — which PV/CI contracts touched  
2. Tier matrix check (foundation §8.3)  
3. Regression on audit open items — no new P0 proof defects  
4. Documented downgrade if evidence regresses  

---

## Section 7 — Measurement Governance

Govern **proof quality** — how CartFlow measures whether governance is working. Distinct from merchant KPIs (foundation §6).

### 7.1 Proof quality dimensions

| Dimension | Definition | Owner | Target signal (internal) |
|-----------|------------|-------|--------------------------|
| **Proof coverage** | Share of merchant-visible claims with PV-1 source + domain | Governance | Trend ↑; baseline inventory from audit |
| **Confidence quality** | Share of claims where confidence matches recomputed evidence | Governance | Sample audit quarterly |
| **Merchant visibility** | Share of §6 metrics registry marked merchant-visible when eligible | Product | Per implementation phase |
| **Commercial integrity** | Count of CI violations open / release | Commercial governance | Zero P0 open at GA |
| **Contract compliance** | PV contract pass rate on sampled surfaces | Governance | Phased targets per §7.3 |

### 7.2 Metric registry governance (merchant KPIs)

Each metric in foundation §6.1 requires before merchant display:

| Field | Required |
|-------|----------|
| `metric_id` | Stable identifier |
| `proof_domain` | Primary domain |
| `truth_owner_module` | PV-6 |
| `numerator` / `denominator` | PV-10 if rate |
| `confidence_rules` | §5 mapping |
| `stale_behavior` | Unknown or last-good + label |
| `pilot_validated` | Boolean + date |

**Current registry status:** Most metrics **not merchant-visible** — governance requires registration before surfacing (PG-9).

### 7.3 Maturity model (Proof of Value domain)

Aligns with Engineering Maturity Model — proof-specific levels.

| Level | Name | Proof domain requirement |
|------:|------|--------------------------|
| **0** | Undefined | No governance |
| **1** | Working | Outcomes exist; contracts documented — **current** |
| **2** | Governed | This document adopted; owners named; release gate active |
| **3** | Measured | §7.1 dimensions reported internally |
| **4** | Enforced | Automated verification for subset of PV (e.g. PV-14 via LT-C1) |
| **5** | Institutionalized | Proof inventory in institutional memory; onboarding includes PV |
| **6** | Merchant Proven | Level 2 merchant value (foundation §10.3) sustained in pilot |

**Today:** Domain enters **Level 2 Governed** on adoption of this document. Merchant value remains **Level 1 Working** until implementation closes audit gaps.

### 7.4 Phased compliance targets (governance-only)

| Phase | Focus | Contracts |
|-------|-------|-----------|
| **P0** | Stop deception | PV-3,11,12, CI-1,3,7,9 |
| **P1** | Decision + understanding integrity | PV-4,14,15,17, PV-8 |
| **P2** | Operational + commercial completeness | PV-6,9,18, MT-D-*, freshness |
| **P3** | Product proof | PV-16 |

---

## Section 8 — Future Evolution

### 8.1 Adding proof domains

New domains (e.g. **Behavior Proof** as first-class) require:

1. Demonstrated evidence in audit — not invented  
2. Foundation V2 amendment  
3. This governance doc addendum with owners + contracts  
4. **No weakening** of PG-1…PG-10 or existing PV/CI without versioned supersession  

Existing five domains (Recovery, Understanding, Decision, Operational, Commercial) are **closed set** until formal amendment.

### 8.2 Adding contracts

- New contracts numbered **PV-19+** or **CI-11+**  
- Must include owner, verification, merchant impact, risk class  
- Trace to audit incident or foundation gap  

### 8.3 Relationship to future domains (proof strengthening only)

| Future domain | Governance requirement |
|---------------|------------------------|
| **Behavior Truth** | Complete engineering governance before MT-U / Understanding claims upgrade from Partial |
| **Merchant Understanding** | Must consume Proof metrics — not replace PV-3/PV-11 |
| **Knowledge Layer V2+** | PV-15, PG-4 unchanged |
| **Product Intelligence** | PV-16 gate mandatory |
| **Decision Engine** | PV-17, PV-18 mandatory |
| **Explainability** | PV-7 merchant-visible traces |
| **Revenue Intelligence** | PV-3, PV-13; confidence ≤ Medium unless attributed |

### 8.4 Amendment authority

| Change | Process |
|--------|---------|
| Principle (PG-*) | Foundation V2 + governance V2 + decision registry |
| Contract addition | Governance minor version + traceability |
| Contract weakening | **Forbidden** without explicit risk acceptance recorded |
| Enforcement mechanism | Separate implementation doc — must implement governance, not redefine |

### 8.5 Document hierarchy

```
Engineering Constitution (HOW truth is built)
        ↓
Proof of Value Foundation (WHAT may be claimed)
        ↓
Proof of Value Governance (THIS — HOW proof is controlled)
        ↓
Future: Proof implementation, metrics, enforcement gates
        ↓
Merchant surfaces & commercial motions
```

---

## Appendix A — Governance ↔ Foundation index

| Foundation section | Governance section |
|---------------------|-------------------|
| §1 Philosophy | §1 Principles (PG-*) |
| §2 Domains | §2 Ownership |
| §3 Hierarchy | §3 Lifecycle + R-rules via contracts |
| §4 PV-1…18 | §4 Contracts + verification |
| §7 Confidence | §5 Merchant Trust Rules |
| §8 CI-1…10 | §6 Commercial Integrity |
| §6 Metrics | §7 Measurement |
| §10 Evolution | §8 Future Evolution |

---

## Appendix B — Success criteria

| Requirement | Status |
|-------------|--------|
| Proof of Value is an official governed domain | **Yes** — peer to Provider Reliability Governance |
| Future implementation implements governance | **Required** by PG-9, §4 verification columns |
| No new merchant value invented | **Yes** — traceability to audit + foundation only |
| Merchant trust protected | **PG-7, §5, §6** |
| Documentation only | **Yes** |

**Next step (out of scope):** Proof of Value Implementation V1 — surfaces metrics and compliance mechanisms **without redefining** PV contracts.

---

## Appendix C — Current open defects (audit baseline)

Governed target state does **not** claim current full compliance. Open items to close via future implementation:

1. PV-3 / PV-12 — attributed SAR not merchant-visible  
2. PV-11 — delivery language risk on send status  
3. PV-17 — intervention without executable action  
4. PV-18 — Daily Brief not implemented  
5. PV-9 / CI-9 — Pro tier marketing ahead of proof  
6. PV-6 — merchant Operational Confidence not measured  

This list is the **implementation backlog** ordered by §7.4 P0→P3.
