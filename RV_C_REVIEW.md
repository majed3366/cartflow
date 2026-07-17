# RV-C Review — Reality Validation Gate C (Simulation Attach Honesty)

**Document type:** Architectural + product-truth validation gate (not engineering)  
**Status:** **Decision recorded**  
**Gate:** RV-C — Simulation attach honesty  
**Investigation:** INV-002 — Merchant Identity Drift  
**Reviewed tip (UTC):** 2026-07-17 — branch `feature/inv002-phase5` @ `7ef1fe3` (Phase 5 delivery `592c62e`)  
**Upstream:** [`INV_002_EXECUTION_ARCHITECTURE.md`](INV_002_EXECUTION_ARCHITECTURE.md) §6 · [`Phase5_REVIEW.md`](Phase5_REVIEW.md) · [`RV_B_REVIEW.md`](RV_B_REVIEW.md) · Identity Authority Architecture V1  

| Prerequisite | Status |
|--------------|--------|
| WP-1…WP-6 (Phase 1–4 critical surfaces) | Done |
| RV-B APPROVED | Done |
| Phase 5 Reality Attach delivered | Done (`reality_attach_v1`) |
| Merchant Reality Validation | **Not started** (blocked by this gate) |

> **Mission question:** Does a merchant session observe exactly the same truth that exists inside the Platform Authorities?  
> **Not this document:** Production code, Merchant Reality Validation execution, INV-002 closure, Widget/Setup/WhatsApp/Recommendations/Providers review.

**STOP:** No implementation under this task. No Merchant Reality Validation execution.

---

## Executive Summary

### Decision

# NOT APPROVED

### One-sentence verdict

**Authority-chain Attach is contractually sound when activated**, but a **merchant HTTP session still does not activate Reality Attach**, and **no session-path RC-3 evidence** shows Home / Knowledge / Daily Brief / Timeline rendering simulation truth under attached MQIC + QTC — therefore Merchant Reality Validation would **not yet be truthful**.

### Frozen RV-C checks (Execution Architecture §6)

| Check | Result |
|-------|--------|
| Small Reality (or equivalent) run’s canonical store ≡ walkthrough MQIC after Attach | **CONDITIONAL PASS** — true inside `reality_attach_scope` / ICT-20; **not demonstrated on merchant HTTP walkthrough** |
| Session merchant surfaces see sim truth for that store under correct QTC (≥1 cart / non-empty honest state) | **FAIL** — no session-path evidence pack; ICT proves MQIC/QTC bind only |
| Hardcoded `demo` service probe **alone** is insufficient | **PASS** (rule upheld; probes correctly rejected as acceptance) |
| Write isolation to declared canonical still green (C3) | **NOT RE-PROVEN under Attach session** — Phase 3.1 suite exists historically; not part of an attached walkthrough pack |

### Mission answer

| Question | Answer |
|----------|--------|
| Do Platform Authorities hold one coherent attached truth when Attach runs? | **Yes** (ICT + Phase 5 contracts) |
| Does a **merchant session** observe that truth today? | **No** — Attach is not composed into the merchant request path |
| Would first Merchant Reality Validation be truthful now? | **No** |

---

## 1. Authority Health

### Platform Identity Authority

| Field | Assessment |
|-------|------------|
| Owner | `platform_identity_authority` only (IA-4) |
| MQIC | Sealed, immutable; dual-resolve fail closed |
| Session entry | Phase 3 `resolve_mqic_from_session` |
| Attach path | `ResolutionPath.ATTACH` when `simulation_run_id` + `simulation_canonical_store_id` supplied and membership-authorized |
| Phase 5 merge | `build_session_resolve_input` overlays active attach inputs via `peek_attach_resolve_inputs` |
| Cardinality | One successful bind per request scope |

**Health when Attach active (tests):** PASS — MQIC.store_slug / canonical ≡ declaration; provenance includes ATTACH path.

**Health on merchant HTTP without Attach:** PASS for RV-B one-store story on primary/session store — but that store is **not** the simulation truth store (INV-002 RCA shape).

### Platform Time Authority

| Field | Assessment |
|-------|------------|
| Owner | `platform_time_authority` / Query Time Context |
| Attach bind | `SimulationClockProvider` via `activate_query_time_context(SIMULATION)` |
| Merchant `now` | `authority_now()` under attached QTC |
| Detach | Restores ambient (ICT detach clean) |

**Health when Attach active (tests):** PASS.  
**Health on merchant HTTP without Attach:** Production / ambient SystemClock — correct for production, **not** simulation as-of.

### Reality Attach

| Field | Assessment |
|-------|------------|
| Role | Input binder only (`is_authority: false`) |
| API | `reality_attach_scope` / `reality_attach_declaration_scope` |
| Wired into `main.py` | **No** |
| Wired into Home / KL / Brief / Timeline composition | **No** |
| Call sites outside ICT | **None found** |

**Architectural correctness of the binder:** PASS.  
**Product activation for merchant session:** **FAIL** (blocking).

---

## 2. Session Walkthrough

Intended attached walkthrough (Execution Architecture / mission):

```text
Session start
  → MQIC resolve once (Phase 3)
  → Simulation Attach (Phase 5)
  → Authorities updated (IA ATTACH + TA SIMULATION)
  → Home / Knowledge / Daily Brief / Timeline render
  → No surface invents truth
```

### Observed walkthrough capability at reviewed tip

| Step | Merchant HTTP session today | Under ICT `reality_attach_scope` |
|------|----------------------------|-----------------------------------|
| Session starts | Yes (cookies / auth) | Synthetic membership snapshot |
| MQIC resolved once | Yes (Phase 3 on migrated surfaces) | Yes |
| Simulation attached | **No** — no composition calls Attach | Yes |
| Authorities updated for sim | **No** — primary/session MQIC; ambient/production QTC unless other scopes | Yes (ATTACH + SIMULATION) |
| Home / KL / Brief / Timeline render | Yes, for **session** store | Consumers share attached MQIC (ensure_* tests) |
| Surface-local truth | No on migrated paths (RV-B) | No |

### Walkthrough verdict

**Incomplete.** The authority chain for an attached session is proven in isolation. The **merchant session path never enters that chain**, so the walkthrough required by RV-C cannot be claimed.

---

## 3. Truth Consistency Matrix

Scope: Home · Knowledge · Daily Brief · Timeline · Attached simulation session.

| Dimension | Authorities (when Attach active) | Surfaces (when Attach active, tests) | Merchant HTTP session (no Attach) | Consistent? |
|-----------|----------------------------------|--------------------------------------|-----------------------------------|-------------|
| Merchant identity | MQIC.merchant_id | Same MQIC | Session merchant | N/A vs sim |
| Store identity | Run canonical / `demo` | Same `store_slug` | Primary/session (often signup) | **Split vs Lab sim store** |
| Simulation time | QTC SIMULATION + `authority_now` | Time-aware consumers use TA when QTC active | Wall / production context | **Split** |
| Timeline evidence | Keyed by MQIC slug | MQIC-gated readers | Session store (often empty) | **Split vs sim** |
| Knowledge evidence | Keyed by MQIC slug + windows | Same | Session store windows | **Split vs sim** |
| Activity summary (Home) | Composed from MQIC tenants | Same MQIC nested bind | Session store | **Split vs sim** |
| Stale authority | Detach clears MQIC/QTC (ICT) | N/A | N/A | Attach detach OK in tests |
| Contradictions across four surfaces | None under one MQIC | None (ICT consumer share) | Four agree with each other on **wrong** store vs sim | Intra-session OK; **vs Authorities’ sim truth NO** |

**Matrix verdict:** Surfaces remain mutually consistent (RV-B). They are **not** consistent with **attached simulation truth** on the merchant session path.

---

## 4. Evidence Provenance Review

| Provenance field | Present when Attach active? | Merchant-facing? | Session walkthrough evidence? |
|------------------|----------------------------|------------------|-------------------------------|
| Time source (`simulation` / QTC mode) | Yes (`attach_diagnostics`, QTC) | No (ops) | Tests only |
| Identity source (`platform_identity_authority`) | Yes | No (ops `identity_authority_v1`) | Tests + migrated surface ops fields |
| Simulation run id | Yes on MQIC + QTC | No | Tests only |
| Authority owner | Yes | No | Yes (architecture) |
| Evidence chain (carts → KL → Brief → Timeline) | Architecturally via MQIC + TA | Surfaces speak derived truth | **No attached session pack with ≥1 cart** |

Traceability **design** is adequate. Traceability **proof on a merchant attached session** is missing.

---

## 5. Failure Injection Results

Analyzed against Phase 5 ICT + architecture (no new code; no production mutation).

| Injection | Expected | Observed / evidence | Fail-closed? |
|-----------|----------|---------------------|--------------|
| Split truth (attach store ≠ membership) | Reject | `attach_membership_denied` ICT-21 | **Yes** |
| Detached MQIC mid-attach dual bind | DualResolveViolation | ICT second bind | **Yes** |
| Detached clock after scope exit | Ambient restored | `test_attach_removed_cleanly` | **Yes** |
| Legacy identity path on migrated surfaces | Forbidden | RV-B inventory still holds | **Yes** (reviewed scope) |
| Provider identity as tenant | Forbidden | Consumers use `mqic.store_slug` | **Yes** (reviewed scope) |
| Stale attach after detach | No peek inputs / no MQIC | ICT detach | **Yes** |
| Simulation detachment | Lifecycle DETACHED | ICT | **Yes** |
| Slug mismatch declaration vs membership store | Reject | `attach_slug_mismatch` | **Yes** |
| Dual attach | Reject | `attach_already_active` | **Yes** |
| **Merchant session without Attach while Lab data on `demo`** | Should not claim RV-C success | **Still the default path** | N/A — **this is the product failure mode under review** |

Failure injection for the **binder** is green. The **missing activation** is itself the residual failure: silent empty merchant experience vs rich Lab probe.

---

## 6. Merchant Honesty Assessment

| Surface | Honest representation of Authority state when Attach active? | Honest on merchant HTTP today? |
|---------|---------------------------------------------------------------|--------------------------------|
| Home | Yes (MQIC + nested Brief/KL/Timeline) | Honest for **unattached** session store — **not** sim truth |
| Knowledge | Yes | Same |
| Daily Brief | Yes | Same |
| Timeline | Yes | Same |

**Honesty ruling:** Surfaces do not invent a second presentation layer. They faithfully render whatever MQIC/QTC the request bound. Because Attach is never bound on merchant HTTP, merchants still see **actual platform truth for the wrong store relative to simulation** — which is exactly INV-002’s dishonest validation trap if PO eyes proceed now.

Reconstructed presentation? **No.** Wrong tenant relative to sim? **Yes, without Attach activation.**

---

## 7. Remaining Risks

| Risk | Rating | Notes |
|------|--------|-------|
| False-green Merchant Reality Validation if started now | **Critical** | Would re-learn Checkpoint V2 / RCA |
| Attach API unused at edge | **High** | Composition WP / Lab harness required before RV-C re-attempt |
| Membership: merchant ∉ run canonical | **High** | Attach correctly fail-closes; walkthrough must authorize membership first |
| E1 auth-slug pointer vs MQIC after future Attach | **Medium** | RV-B constraint; must keep coherent when Attach is composed |
| Write isolation under attached session | **Medium** | Re-run Phase 3.1 class under Attach before RV-C APPROVED |
| Widget/Setup/cart KPI escape | **Out of scope** | Must not be used as RV-C or first MV acceptance |

---

## 8. Decision

| Field | Value |
|-------|--------|
| **Decision** | **NOT APPROVED** |
| **Authorizes Merchant Reality Validation?** | **No** |
| **Authorizes further product implementation in this task?** | **No** (governance only) |

### Blocking issues

1. **B1 — No merchant-session Attach composition**  
   `reality_attach_scope` / declaration scope are invoked only from `tests/identity_authority/test_phase5_reality_attach.py`. Home composition, Knowledge/Brief routes, Timeline, and `main.py` do not activate Attach. A merchant session therefore cannot observe attached Authority state.

2. **B2 — ICT-22 / RC-3 session-path evidence missing**  
   No evidence that session-rendered Home / Knowledge / Daily Brief / Timeline show simulation truth (≥1 cart / non-empty honest state) under attached MQIC + simulation QTC. Phase 5 ICT proves bind contracts, not merchant-visible sim content on the session path.

3. **B3 — Walkthrough preconditions not demonstrated**  
   Authorized membership of the merchant principal on the run’s canonical store **plus** Attach activation for the request is required. Default signup-session shape (INV-002 RCA) still yields empty surfaces while Lab truth remains on `demo`.

### Non-blocking residuals (do not alone decide NOT APPROVED, but must accompany re-attempt)

- C3 write-isolation suite not re-filed under an attached session pack  
- Phase 2 global middleware still absent (opt-in bind remains acceptable if Attach is composed on the reviewed surfaces)  
- Widget / Setup / WhatsApp remain out of acceptance scope  

### What would make RV-C APPROVED (guidance only — not authorizing work here)

1. Compose Reality Attach into the **merchant session walkthrough path** for reviewed surfaces (Authority inputs only; no surface-local identity).  
2. File RC-3 evidence: same session — MQIC canonical ≡ Small Reality (or equivalent) run store; QTC simulation; Home/KL/Brief/Timeline non-empty honest agreement; correlation ids; **not** probe-only.  
3. Re-confirm write isolation under that attached session.  
4. Re-run this gate.

### Approval record

| Role | Required |
|------|----------|
| Architecture Board | ☐ Acknowledge RV-C **NOT APPROVED** + blocking issues |
| Engineering Lead | ☐ May open a composition / evidence WP only after normal authorization — **not** Merchant Reality Validation |
| Product Owner | ☐ **Do not** begin first Merchant Reality Validation until RV-C is APPROVED |

---

## STOP

No Merchant Reality Validation execution.  
No implementation.  
No INV-002 closure.  

**RV-C = NOT APPROVED.** Await Product Owner acknowledgment that Merchant Reality Validation must not start. Await Architecture acknowledgment before authorizing the next Work Package that closes B1–B3.
