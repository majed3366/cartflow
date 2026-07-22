# Merchant Experience Capability Gap Register

**Status:** Active entry point for the next architectural chapter  
**Date (UTC):** 2026-07-22  
**Authority:** Merchant Experience Hardening V1 (MEH)  
**Rule:** Every unresolved merchant-experience issue that cannot be fixed inside the current stack must appear here. No guessing. No hidden feature work.

---

## Purpose

Prove the natural limit of the current architecture:

```text
Truth → Evidence → CIS → Knowledge → Guidance → Surface Composition → MEIF → Pages
```

Category A issues are fixed in MEH without new layers.  
Category B issues are documented here as Capability Gaps.

---

## Gaps

### CG-MEH-01 — Time-aligned Knowledge vs wall-clock merchant reads

| Field | Value |
|-------|-------|
| Status | **CLOSED by TABF V1** — `resolve_bound_as_of_v1`; probe `/dev/time-authority` |
| Findings | MEV1-H03, MEV1-K03 |
| Required future capability | Time Authority consumer binding for all merchant Knowledge/Home reads |
| Architectural reason | Knowledge/Home evaluate wall-clock windows while Reality history may sit elsewhere; MEIF can show as_of/window cues only |
| Why existing stack cannot solve | Forbidden to redesign Time Authority or rewrite Knowledge Foundation in MEH |

### CG-MEH-02 — Operational Truth as Surface Composition input

| Field | Value |
|-------|-------|
| Findings | MEV1-D02, MEV1-C02, MEV1-S02 |
| Required future capability | Governed Operational Truth / Merchant Operational State as first-class SCF inputs |
| Architectural reason | SCF V1 consumes Presentation + Knowledge only; empty-states cannot see durable carts/WA at compose time |
| Why existing stack cannot solve | Forbidden to expand SCF inputs in MEH; MEIF may suppress false empty-states at the bridge only |

### CG-MEH-03 — Durable cart list projection / identity-time window

| Field | Value |
|-------|-------|
| Findings | MEV1-C01, MEV1-C03 (queue materialization) |
| Required future capability | Cart list projection that materializes durable AbandonedCart rows into merchant queue |
| Architectural reason | `normal-carts` can be empty while AbandonedCart rows exist |
| Why existing stack cannot solve | MEIF can forbid false please-wait and show ops counts; cannot invent a queue |

### CG-MEH-04 — Communication follow-up operations projection

| Field | Value |
|-------|-------|
| Findings | MEV1-M02 |
| Required future capability | Communication ops projection (follow-up queue) distinct from Settings WhatsApp |
| Architectural reason | Mock sends/schedules are durable facts; no governed follow-up work queue exists |
| Why existing stack cannot solve | MEIF can show activity facts; cannot create a follow-up queue |

### CG-MEH-05 — Operationally useful Commercial Guidance product policy

| Field | Value |
|-------|-------|
| Findings | MEV1-G01, MEV1-G03 (engine/policy portion) |
| Required future capability | Guidance eligibility/registry policy for actionable ops guidance with merchant confidence |
| Architectural reason | Monitor-only guidance may be technically correct yet operationally unhelpful |
| Why existing stack cannot solve | Forbidden to add Guidance engines/eligibility in MEH; MEIF may demote/label confusing monitor guidance only |

### CG-MEH-06 — Setup lifecycle vs lived Reality history

| Field | Value |
|-------|-------|
| Findings | MEV1-H04 (lifecycle ownership) |
| Required future capability | Setup/activation lifecycle that yields to durable operational history |
| Architectural reason | Onboarding remaining_setup can remain after Reality history exists |
| Why existing stack cannot solve | MEIF suppresses setup theatre when durable carts exist (presentation); cannot rewrite setup ownership |

---

## Next chapter entry

The next architectural chapter should begin by selecting one or more of these gaps — typically **CG-MEH-02** (Operational Truth → SCF) and/or **CG-MEH-01** (Time Authority consumer binding) — as the highest-leverage unlocks for merchant truthfulness beyond the MEH ceiling (~85–90).
