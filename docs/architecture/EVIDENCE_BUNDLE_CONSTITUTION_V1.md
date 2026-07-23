# CartFlow Evidence Bundle Constitution V1

**Status:** Proposed for Architecture Board ratification  
**Date (UTC):** 2026-07-23  
**Type:** Constitutional design — permanent architectural authority  
**Scope:** Evidence Bundle layer — composition law only  
**Out of scope:** Implementation · refactoring · WP-ET-09 code changes · Knowledge · Business Findings · Guidance · AI · merchant UI · BFSV · Reality Validation · production cutover  

**Upstream authority:** [`EVIDENCE_TRUTH_ARCHITECTURE_V1.md`](EVIDENCE_TRUTH_ARCHITECTURE_V1.md)  
**Upstream stage law:** [`EVIDENCE_TRUTH_STAGE_REVIEW_V1.md`](../implementation/EVIDENCE_TRUTH_STAGE_REVIEW_V1.md) §19 Architectural Exit Criteria (especially EC-4)  
**Implementation blueprint:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-16, EB-1…EB-8  
**Trust law:** [`MERCHANT_TRUST_CONSTITUTION_V1.md`](../../MERCHANT_TRUST_CONSTITUTION_V1.md) (MT-1 Evidence Before Speech)  

> This Constitution does not invent a new truth layer.  
> It permanently binds the Evidence Bundle as a **composition projection** of Evidence Truth — never as an interpreter, decision engine, or independent source of merchant reality.

**STOP:** This document is governance only. It does not authorize Knowledge cutover, Findings cutover, Bundle CONSUME flags, or merchant-facing Bundle speech.

---

## 0. Primary question

### What may CartFlow assemble from governed Evidence Truth before any intelligence is allowed to speak?

**Answer:** An **Evidence Bundle** — a governed, versioned, traceable **composition** of Evidence Truth records for a defined `(store, window, as_of)`, produced only by the Evidence Bundle Composer.

```text
Raw Event
    ↓
Canonical Observation
    ↓
Evidence Truth                 ← sole producer of facts
    ↓
Evidence Bundle                ← THIS LAYER (composition only)
    ↓
Knowledge                      ← interpretation (not this layer)
    ↓
Business Finding               ← commercial meaning (not this layer)
    ↓
Guidance / Presentation        ← merchant speech (not this layer)
```

---

## 1. Purpose of Evidence Bundle

### 1.1 Sole purpose

Evidence Bundle exists for **one purpose only**:

> To compose multiple governed Evidence Truth records into a coherent, traceable, governed Bundle **without creating new truth or interpretation**.

### 1.2 What Bundle is

| Bundle is | Meaning |
|-----------|---------|
| A **composition layer** | Assembles family Evidence into one consumable projection shape |
| A **projection** | Derived from Evidence Truth; disposable relative to Evidence durability |
| A **traceability carrier** | Holds refs that preserve the explainability chain |
| A **boundary** | The only authorized path from Evidence Truth into Knowledge / Findings predicates |

### 1.3 What Bundle is NOT

| Bundle is NOT | Why |
|---------------|-----|
| Knowledge | Knowledge interprets patterns over Ready/Trusted evidence |
| Business Findings | Findings assign commercial meaning |
| Guidance | Guidance recommends or prioritizes actions |
| AI reasoning | AI may explain later; never compose truth here |
| Merchant explanation | Merchant speech is presentation after Findings/Guidance law |
| Decision engine | Bundle does not choose among hypotheses |
| Evidence Truth | Facts remain owned by family authorities |
| Raw Event store | Raw is never Bundle authority (EB-7) |

---

## 2. Constitutional principles

These principles are **permanent**. Future packages (including Composer evolution, Knowledge migration, Findings switch, and UI) must preserve them. Violation requires Architecture Board amendment of this Constitution — not silent drift.

### EB-C1 — Composition Before Interpretation

**Law:** Bundle composes. Knowledge interprets.

Bundle must **never** interpret Evidence. It may project readiness, confidence, ownership, and safe facts exactly as Evidence Truth states them. It may not assign meaning, cause, priority, or commercial narrative.

### EB-C2 — Projection Only

**Law:** Bundle is a projection of Evidence Truth.

Bundle must **never** invent new facts, fill gaps with proxies, synthesize missing family totals, or mint Evidence-like objects from Raw, Observation, metrics, or AI.

### EB-C3 — Truth Preservation

**Law:** Bundle must preserve, without modification of meaning:

| Preserved property | Requirement |
|--------------------|-------------|
| Ownership | Family owner identity remains that of Evidence Truth |
| Confidence | Bundle must not rewrite confidence grades |
| Readiness | Bundle must not rewrite readiness states |
| Provenance | Production / demo / synthetic provenance remains honest |
| Timestamps | `as_of`, observed periods, freshness metadata remain attributable |
| Evidence identity | `evidence_id` + `evidence_version` (and observation refs) remain addressable |

Projection may **omit** guidance-forbidden fields. Projection may **not** alter the semantic content of preserved truth fields.

### EB-C4 — No Fact Mutation

**Law:** Bundle must never:

- upgrade confidence  
- downgrade confidence  
- merge conflicting facts into a single “resolved” fact  
- suppress competing evidence  
- coerce Unavailable / Unknown / Insufficient into Ready / Trusted  
- coerce `visitor_total=None` into `0` or any invented quantity  

Composer may be **intentionally stricter** than a legacy dishonest loader (e.g. refuse proxy traffic). Stricter honesty is allowed. **Increased certainty without Ready Evidence is forbidden.**

### EB-C5 — Reconstructability

**Law:** Every Bundle must be reproducible from:

```text
Evidence Truth
    ↓
Observation
    ↓
Raw Event
```

No Bundle may become an independent source of truth. If Evidence Truth versions are available for the same selection key, recomposition must yield an equivalent factual projection (schema evolution governed separately). Bundle stores are **projection caches**, not authorities.

### EB-C6 — Traceability

**Law:** Every Bundle field that asserts or projects a fact must be traceable to **one or more** Evidence Truth records.

| Allowed | Forbidden |
|---------|-----------|
| Field backed by Evidence ref(s) | Orphan fields with no Evidence ref |
| Explicit Unavailable / Unknown slice when Evidence absent | Silent omission that implies completeness |
| Bundle-level visitor honesty flags derived from Visitor Evidence + authorization | Cart/recovery/product inferred as visitor |

Missing refs in strict composition → **fail closed** (build error), not silent invention.

### EB-C7 — Ownership Preservation

**Law:** Bundle owns **composition only**.

| Layer | Owns |
|-------|------|
| Evidence Truth family authorities | Facts (Visitor, Product, Cart, Recovery, Purchase, Communication, Behaviour, …) |
| Evidence Truth platform | Freshness / eligibility / confidence **stamping rules** (not family facts) |
| Evidence Bundle Composer | Projection / composition / Bundle identity / Bundle versioning |
| Knowledge / Findings / Guidance | Interpretation and speech (later; not Bundle) |

Bundle must not re-own family facts. Bundle must not override Ownership Constitution.

### EB-C8 — No Intelligence

**Law:** Bundle may never:

- explain  
- recommend  
- prioritize  
- rank  
- infer  
- predict  
- title findings  
- emit guidance, routing, or merchant-action fields  

Forbidden payload classes include (non-exhaustive): recommendation text, finding titles, UI labels as truth, ranking scores, priority, AI prompts, eligible surfaces, guidance, merchant actions.

### EB-C9 — Constitutional Boundaries

**Law:** Bundle must never:

1. **Bypass Evidence Truth** — no Raw-as-authority, no Observation-as-Findings-authority, no ad-hoc family merges outside Composer.  
2. **Feed merchant UI directly** — merchant-facing intelligence must pass through the approved architecture:

```text
Evidence Bundle → Knowledge → Business Finding → authorized Presentation / Guidance
```

3. **Become Consumable by accident** — Eligible Evidence and shadow Bundles do not imply CONSUME authorization (Truth Before Consumption / EC-7).

### EB-C10 — Fail Closed

**Law:** If required Evidence is missing, Bundle must represent that absence honestly.

| Situation | Required behaviour |
|-----------|-------------------|
| No Evidence for store/window | Fail closed — do not emit a fabricated “complete” Bundle |
| Family Evidence absent | Unavailable / Unknown family slice — **no zero-fill** |
| Visitor channel absent | Unavailable Visitor honesty — **never proxy from carts** |
| Conflicting Evidence | Preserve conflict / conflicting readiness — do not silently pick a winner |
| Demo / fixture provenance | Must never be marked production Trusted |

Absence ≠ negative proof. Completeness must never be fabricated.

### EB-C11 — Competing Evidence

**Law:** Bundle must preserve competing evidence.

Interpretation, selection among hypotheses, and commercial ranking belong to **Knowledge** (and later Findings). Bundle must not collapse multiple Ready facts into one conclusion, narrative, or “dominant cause.”

### EB-C12 — Explainability Preservation

**Law:** Bundle must retain enough provenance for future explainability.

Minimum retained chain for any merchant-facing statement that will later cite Bundle content:

```text
Business Finding
    ↓
Knowledge
    ↓
Evidence Bundle
    ↓
Evidence Truth
    ↓
Observation
    ↓
Raw Event
```

Bundle composition must not discard Evidence identity, observation refs, readiness, confidence, ownership, or provenance required for that chain.

---

## 3. Architectural guarantees

### 3.1 Forbidden forever (without Constitution amendment)

Future changes **must not**:

1. Introduce a second composition authority that bypasses Evidence Bundle Composer for Knowledge/Findings predicates.  
2. Allow Knowledge, Findings, Guidance, AI, or UI to mint Evidence or Bundle facts.  
3. Allow Bundle to read Raw Event stores as factual authority.  
4. Allow Bundle to invent visitor totals, delivery=replied, ATC=view, cart=traffic, or purchase without Purchase Evidence.  
5. Allow Bundle to upgrade readiness/confidence beyond source Evidence.  
6. Allow Bundle to suppress competing Evidence or merge conflicts into a single invented fact.  
7. Allow merchant UI to consume Bundle (or Evidence) directly as intelligence authority.  
8. Treat Bundle projection caches as durable truth superior to Evidence Truth.  
9. Enable Bundle CONSUME / Knowledge / Findings cutover without explicit Architecture authorization and gate proof (Gate C+ as required by Blueprint).  
10. Void Architectural Exit Criteria EC-1…EC-10 of Evidence Truth Stage Review V1.

### 3.2 Allowed extensions (under this Constitution)

Future work **may**:

1. Evolve Bundle **schema versions** with explicit compatibility rules (EB-5).  
2. Improve Composer selection windows, caching, and invalidation (EB-6) without changing fact ownership.  
3. Add family slices only when corresponding Evidence Truth families exist and are owned.  
4. Implement dual-read parity against legacy loaders where Composer is equal or **intentionally stricter** (never looser / more certain).  
5. Wire Knowledge / Findings to Bundle **only** behind authorized consume flags after Gate proof.  
6. Authorize Visitor Bundle fields **only** when Visitor Truth Authority Evidence is Ready/Trusted and visitor Bundle field flags are explicitly enabled.  
7. Replace disposable projection stores with durable caches — still non-authoritative relative to Evidence Truth.  
8. Strengthen runtime eligibility enforcement and import linting for EB-7.

### 3.3 Relationship to Evidence Truth

| Question | Authority |
|----------|-----------|
| What is true? | Evidence Truth |
| Who owns a family fact? | Ownership Constitution (Evidence Truth) |
| How may facts be assembled for consumers? | **This Constitution** (Evidence Bundle) |
| What does it mean commercially? | Knowledge / Findings (later) |
| What may the merchant do? | Guidance (later) |

---

## 4. Lifecycle posture

```text
Evidence Truth (Eligible / not necessarily Consumable)
        ↓
Bundle Composer (shadow or authorized consume path)
        ↓
Evidence Bundle (projection; consumable only when explicitly authorized)
        ↓
Knowledge / Findings (only after consume authorization)
```

**Permanent rules:**

- Shadow composition ≠ consumer cutover.  
- Bundle `consumable` remains false until Architecture authorizes CONSUME.  
- Eligible Evidence does not imply Bundle CONSUME.  
- Bundle CONSUME does not imply Guidance privilege.

---

## 5. Non-goals of this document

This Constitution **does not define**:

| Non-goal | Belongs to |
|----------|------------|
| Knowledge models, claims, or routing | Knowledge Layer / WP-ET-10+ |
| Business Findings families or commercial meanings | Business Findings Engine / WP-ET-11+ |
| Guidance, recommendations, or eligible actions | Guidance / Trust privilege law |
| AI reasoning, prompts, or generative explanation | Future AI governance (must not create Evidence/Bundle facts) |
| Merchant-facing intelligence, UI copy, dashboards | Presentation / Home / Brief surfaces |
| Durable SQL schemas or operational runbooks | Implementation packages |
| BFSV / Reality Validation execution | Separate gate authorization |

Implementation reports (including WP-ET-09) must **conform** to this Constitution; this document does not modify those implementations by its existence alone.

---

## 6. Conformance checklist (for future implementers)

A change is Bundle-conformant only if all of the following hold:

- [ ] Composer inputs are Evidence Truth records (or authorized test fixtures marked demo/synthetic).  
- [ ] No Raw-as-authority imports in Composer.  
- [ ] No new facts invented; missing Evidence represented as Unavailable/Unknown/fail-closed.  
- [ ] Ownership, readiness, confidence, provenance, timestamps, evidence identity preserved.  
- [ ] No confidence/readiness upgrades; no conflict suppression.  
- [ ] Every projected fact field has Evidence ref(s).  
- [ ] No explain/recommend/rank/infer/predict fields.  
- [ ] No direct merchant-UI Bundle authority.  
- [ ] Competing Evidence preserved for Knowledge.  
- [ ] Explainability chain refs retained.  
- [ ] Consume flags remain OFF unless Architecture authorizes cutover.

---

## 7. Authority and amendment

| Item | Rule |
|------|------|
| **Authority** | This document is the permanent constitutional authority for the Evidence Bundle layer |
| **Conflict** | If implementation drifts from this Constitution, Constitution wins until Board amends it |
| **Amendment** | Requires Architecture Board review; must not silently weaken EB-C1…EB-C12 |
| **Dependency** | Remains subordinate to Evidence Truth Architecture for fact ownership and Evidence production |
| **Exit Criteria** | Must preserve Evidence Truth Stage Review EC-1…EC-10 |

---

## 8. STOP

Governance document complete.

- Do **not** treat this file as authorization for WP-ET-10.  
- Do **not** enable Bundle CONSUME.  
- Do **not** connect Knowledge or Findings.  
- Do **not** modify production code or WP-ET-09 under this task.

**End of Evidence Bundle Constitution V1.**
