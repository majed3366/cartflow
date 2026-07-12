# Cart Workspace Implementation Constitution V1

**Status:** Governing implementation law  
**Date (UTC):** 2026-07-12  
**Nature:** Non-negotiable engineering rules that preserve approved Product Foundation, Architecture, and Engineering Specification during implementation.  
**Not:** a coding style guide, tutorial, Figma brief, or Product amendment.

---

## Constitutional Authority

This constitution **inherits** authority from:

| Authority | Document |
|-----------|----------|
| Product law | [`cart_workspace_constitution_v2.md`](../product/cart_workspace_constitution_v2.md) and Governance Pack peers |
| Architecture | [`cart_workspace_architecture_review_v1.md`](cart_workspace_architecture_review_v1.md) |
| Engineering Specification | [`cart_workspace_engineering_specification_v1.md`](cart_workspace_engineering_specification_v1.md) |

**Derivation:** Product → Architecture → Engineering Specification → **Implementation Constitution** → Code.

**Forbidden reverse:** Implementation may never redefine Product, Architecture, or Engineering Specification.

---

## Permanent Implementation Principle

> **Implementation translates Engineering Specification. It never redesigns Product or Architecture.**

Architecture translates Product Truth.  
Engineering Specification translates Architecture exactly once.  
Implementation executes that Specification under this Constitution.

Any conflict is resolved upward — never by silent code discretion.

---

# Engineering Constitution

## Part 1 — Implementation Principle

| ID | Rule |
|----|------|
| **IC-1** | Implementation translates Engineering Specification only. |
| **IC-2** | Implementation must not invent Product behavior. |
| **IC-3** | Implementation must not invent Architecture planes, ownership, or admission semantics. |
| **IC-4** | When Specification is silent on a Product OQ (OQ-1, OQ-2, OQ-4 / T4, T6, T12), Implementation exposes hooks only — it must not invent policy. |
| **IC-5** | “It works” is not constitutional sufficiency. Correctness under this Constitution is required. |

---

## Part 2 — Product Integrity

Implementation must **never** change:

| Protected domain | Examples of forbidden silent change |
|------------------|-------------------------------------|
| **Ownership** | Dual-axis holders; T1–T12 meaning; Override as mode not owner |
| **Admission** | Binary Admit/Reject; R01–R20 outcomes; fail-closed default |
| **Decision identity** | One open Decision → one card; fingerprint stability; no DOM identity |
| **Operational behavior** | Lifecycle WL-*; Calm Recovery; no mysterious disappear/duplicate/oscillation |
| **Attention hierarchy** | A → B → C → D → E |
| **Calm Recovery** | Post-Action ownership return meaning; Quiet as success |
| **Zone semantics** | A Override; B Decisions; C reassurance; D compact outcomes; E rare health |
| **Card semantics** | One Decision; Explain Before Asking; one primary Action |

**IC-P1:** Any requested behavioral change must return to **Product Governance**. Implementation PRs are not a Product venue.

---

## Part 3 — Architectural Integrity

Implementation must preserve Architecture Review planes and sole owners:

| Plane | Must remain | Must never absorb |
|-------|-------------|-------------------|
| **P0 Truth** | Recovery / purchase / provider / evidence peers | Cards, zones, CSS |
| **P1 Ownership** | Single transition authority | UI; visual ordering; Admit invention |
| **P2 Admission** | Single compiled gate | Frontend state; markdown reasoning; history-scan Admit |
| **P3 Projection** | Merchant-facing operational read model | Ownership/Admit mutation |
| **P4 Rendering** | Paint + interaction dispatch only | Business logic; zone membership; Admit |

| ID | Rule |
|----|------|
| **IC-A1** | P0–P4 separation is non-negotiable. |
| **IC-A2** | One owner per rule — no duplicate Admit, Ownership, or Projection logic in API, scheduler, frontend, jobs, or renderer. |
| **IC-A3** | Rendering = paint only. |
| **IC-A4** | Projection = merchant truth view of already-governed state — not a second truth mint. |
| **IC-A5** | Admission = single gate for Workspace attention. |
| **IC-A6** | Ownership = single write authority for dual axes + Override mode + journey phase. |
| **IC-A7** | No shortcut that collapses planes for convenience. |

---

## Part 4 — Module Integrity

| ID | Rule |
|----|------|
| **IC-M1** | Every module owns **exactly one** responsibility (per Engineering Specification module map). |
| **IC-M2** | Modules communicate only through **approved contracts** (`cart_workspace_contracts_v1`). |
| **IC-M3** | No hidden dependencies (side-channel globals, undocumented imports of peer internals for business rules). |
| **IC-M4** | No circular ownership (import direction follows Spec Part 18). |
| **IC-M5** | No duplicated business rules across modules, `main.py`, scheduler, or static JS. |
| **IC-M6** | `main.py` / route files = composition and wiring only — not Admit, Ownership, or Projection logic. |
| **IC-M7** | Existing peer modules (e.g. `merchant_decision_layer_v1`) may supply Proof inputs; they must not create Workspace cards or re-Admit. |

---

# Feature Flag Constitution

## Part 5 — Feature Flag Governance

**Flag:** `CARTFLOW_CART_WORKSPACE_V1`

| ID | Rule |
|----|------|
| **IC-F1** | Default **OFF** in all environments until explicit rollout approval. |
| **IC-F2** | Shadow before replacement (M1–M3 before merchant-visible M4+). |
| **IC-F3** | Parity before rollout (desktop/mobile entity set; Quiet/Admit scenarios). |
| **IC-F4** | Rollback by flag — turning OFF restores prior carts surface without data destruction. |
| **IC-F5** | No destructive migration tied to flag enablement. |
| **IC-F6** | Flag-gated code paths must not leak Workspace business truth into the legacy surface when OFF. |
| **IC-F7** | Optional shadow flag (if used) remains default OFF and write-safe (logs/metrics only unless Spec says otherwise). |

---

# Runtime Constitution

## Part 6 — Runtime Integrity

| ID | Rule |
|----|------|
| **IC-R1** | Runtime is **deterministic**: same ownership + admission inputs → same outcomes. |
| **IC-R2** | Queries are **bounded**: Workspace hot paths use open Decisions, current ownership, bounded projection, compact rollups. |
| **IC-R3** | No duplicated evaluation (refresh/poll/scheduler must not re-Admit same fingerprint). |
| **IC-R4** | No frontend business logic (no R0x, no T*, no ownership classification in JS). |
| **IC-R5** | No hot-path historical scans (timelines, all carts, unbounded events, full message history). |
| **IC-R6** | **Stable identity**: `decision_id` survives refresh, viewport, restart; DOM is never canonical. |
| **IC-R7** | **Idempotency**: duplicate webhooks, repeated observations, and replayed commands do not oscillate ownership or duplicate cards. |
| **IC-R8** | Governance documents are never interpreted on the request hot path — compiled rules only. |
| **IC-R9** | Fail closed for new merchant Decisions when Proof/Admit is insufficient or compiler fails. |
| **IC-R10** | Last-good projection may be retained under uncertainty; never blank-repaint away known open Decisions. |

---

# Testing Constitution

## Part 7 — Testing Constitution

Every implementation increment must include evidence appropriate to its scope:

| Layer | Required when |
|-------|----------------|
| **Unit tests** | Module logic changes (ownership, admission, identity, commands) |
| **Contract tests** | Envelope/field/invariant changes |
| **Projection tests** | Zone membership, Quiet, ordering, card fields |
| **Parity tests** | Desktop/mobile entity set; shadow vs expected governance outcomes |
| **Production validation** | Before enabling for real merchants (M5+) |
| **Product approval** | Before rollout / surface retirement (M6–M7) |

| ID | Rule |
|----|------|
| **IC-T1** | No implementation is complete without evidence. |
| **IC-T2** | Screenshots alone do not prove Ownership, Admission, or identity rules. |
| **IC-T3** | Deferred OQ hooks must be tested as **non-inventing** (reserved / rejected invent paths). |
| **IC-T4** | Query-bound / hot-path tests must fail if history scans reappear on Workspace GET. |

---

# Change Governance

## Part 8 — Change Governance

No Pull Request may:

| Forbidden PR content | Required path instead |
|----------------------|----------------------|
| Redefine product behavior | Product Governance |
| Redefine ownership | Product + Architecture amendment |
| Redefine admission | Product + Admission Matrix governance |
| Redefine projection semantics | Architecture + Engineering Spec amendment |
| Redefine rendering responsibilities (give P4 business logic) | Architecture Review |

**IC-C1:** If such a change is needed, **return to Product Governance** (and Architecture as required). Do not “fix forward” in code.

**IC-C2:** Spec clarifications that do not change Product outcomes may amend Engineering Specification via Architecture Review — still not silently in a feature PR.

---

## Part 9 — Temporary Code Policy

Temporary code is allowed **only if** all of the following hold:

| Requirement | Mandatory |
|-------------|-----------|
| Explicitly documented (comment + changelog/issue link) | Yes |
| Linked to an issue / tracked item | Yes |
| Has an owner | Yes |
| Has a removal condition | Yes |
| Has a target removal milestone | Yes |

| ID | Rule |
|----|------|
| **IC-TMP1** | No permanent temporary code. |
| **IC-TMP2** | Temporary bypass of feature flag, plane separation, or fail-closed Admit is **forbidden**. |
| **IC-TMP3** | Shadow/debug logging must not mint merchant-visible truth. |

---

# Performance Constitution

## Part 10 — Performance Constitution

Implementation must satisfy:

| ID | Principle |
|----|-----------|
| **IC-PERF1** | **Growth ≠ Slowdown** — historical accumulation must not slow Decision-facing paths. |
| **IC-PERF2** | **Archive Before Delete** — history exits L2 via governed archive; no silent destructive cleanup as “optimization.” |
| **IC-PERF3** | **Rollups Before Recompute** — Zone D from compact rollups, not full recomputation of history on GET. |
| **IC-PERF4** | **Query Cost Visible** — expensive paths must be measurable and reviewable. |
| **IC-PERF5** | **Hot Path Independent of History** — open Decisions + ownership + bounded projection only. |

**IC-PERF6:** Performance optimizations must **preserve** architectural integrity. Faster + unconstitutional = rejected.

---

# Operational Integrity

## Part 11 — Operational Integrity

Implementation must **never**:

| Forbidden | Why |
|-----------|-----|
| Fabricate merchant truth | Truth authorities remain P0 peers |
| Fabricate calm | Quiet only when no admitted Decisions |
| Fabricate completion | Zone D from completion truth / rollups only |
| Fabricate delivery | No false provider delivery claims (handoff eligibility honesty) |
| Silently discard actions | Persist, idempotent retry, or explicit fail |
| Silently change ownership | Only `ownership` transition authority + audited gates |

**IC-O1:** Operational truth is constitutional. Convenience UX that lies is a Product violation, not a polish choice.

---

# Code Review Constitution

## Part 12 — Code Review Constitution

### PR Review Checklist

Every Pull Request touching Cart Workspace **must** answer:

| # | Question | Fail if unclear |
|---|----------|-----------------|
| 1 | Which **Product** principle does this implement? | Yes |
| 2 | Which **Architecture** rule / plane does this satisfy? | Yes |
| 3 | Which **Engineering module** owns it? | Yes |
| 4 | Does it **duplicate** existing logic (Admit/Ownership/Projection/JS)? | Yes — must be No or justified removal of duplicate |
| 5 | Does it preserve **runtime simplicity** (compiled rules, no governance I/O)? | Yes |
| 6 | Does it preserve **deterministic** behavior? | Yes |
| 7 | Does it preserve **feature-flag** safety (default OFF, no destructive migrate)? | Yes |
| 8 | Does it invent **OQ-1/2/4** policy? | Yes — must be No |
| 9 | Are **tests/evidence** included for the increment? | Yes |

**IC-PR1:** If any answer is unclear, the PR is **not ready**.

**IC-PR2:** Reviewers enforce plane boundaries more strictly than stylistic preferences.

---

# Production Readiness

## Part 13 — Production Readiness

### Production Readiness Checklist

Every implementation wave ends only after:

| Gate | Required |
|------|----------|
| Automated tests pass | Yes |
| Production validation succeeds (scope-appropriate) | Yes |
| Parity confirmed (entity set / governance scenarios) | Yes |
| Product review completed | Yes (for merchant-visible enablement) |
| Approval recorded (changelog / release note / ratification note) | Yes |
| Feature flag plan explicit (who enables, rollback) | Yes |

| ID | Rule |
|----|------|
| **IC-PROD1** | Never merge solely because “the code works.” |
| **IC-PROD2** | Merge because implementation remains **constitutionally correct**. |
| **IC-PROD3** | Merchant rollout (M6) and legacy retirement (M7) require recorded Product approval. |

---

# Amendment Rules

## Part 14 — Amendment Rules

This Implementation Constitution may evolve **only** through:

1. **Proposal** — written change with rationale and affected IC-* ids  
2. **Architecture Review** — confirm planes/owners still hold  
3. **Product impact assessment** — confirm no silent Product redefine  
4. **Ratification** — explicit version bump (V1.1+) and SYSTEM_SUMMARY changelog  

| ID | Rule |
|----|------|
| **IC-AMD1** | No silent implementation philosophy changes. |
| **IC-AMD2** | Bugfixes that restore Spec compliance do not require Constitution amendment. |
| **IC-AMD3** | Spec gaps discovered in implementation return to Engineering Specification / Product — not ad-hoc Constitution bypass. |

---

## Compliance summary (for implementers)

A future developer implements Cart Workspace by:

1. Reading Engineering Specification for *what to build*  
2. Obeying this Constitution for *what must never be violated*  
3. Leaving Product/Architecture decisions to governance  

They must **not** independently redesign ownership, admission, zones, attention, Calm Recovery, or plane boundaries.

---

## Derivation gate

| Stage | Status |
|-------|--------|
| Product Foundation | Inherited (read-only) |
| Architecture Review V1 | Inherited (Verdict A) |
| Engineering Specification V1 | Inherited (Verdict A) |
| **Implementation Constitution V1** | **Governing — this document** |
| Implementation waves | Must comply; flag default OFF |

---

## Change log

| Version | Change |
|---------|--------|
| **V1** | Full Implementation Constitution: IC-* rules across product/architecture/module/flag/runtime/testing/change/temporary/performance/operational/PR/production; checklists; amendment process. |

---

**End of Cart Workspace Implementation Constitution V1.**
