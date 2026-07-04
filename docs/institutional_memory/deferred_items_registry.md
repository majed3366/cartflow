# Deferred Items Registry

**Date (UTC):** 2026-07-03  
**Purpose:** Preserve intentionally deferred architectural findings so they are not forgotten,
while preventing low-priority items from blocking active work.  
**Scope:** Institutional Memory only. No runtime, behavior, scheduler, or recovery changes.

---

## What belongs here

Findings that are **real but intentionally deferred** — investigated, understood, and consciously
not acted on now. This registry is the durable home for "we know about this; it is not urgent; here
is when to revisit." It is **not** a defect tracker and items here are **not** active blockers.

## Registry rules

Every entry MUST include:

- **Title**
- **Priority** (P0 highest … P4 lowest)
- **Category**
- **Investigation reference** (the doc/report where it was analyzed)
- **Impact** (what is and is not affected)
- **Revisit conditions** (explicit triggers to re-open)
- **Explicit decision** (why it is deferred, and what it must not block)

Priority guide: **P0** production-critical · **P1** important, schedule soon · **P2** worthwhile ·
**P3** defense-in-depth / low likelihood · **P4** cosmetic / speculative.

---

## Index

| # | Title | Priority | Category | Status |
|---|-------|----------|----------|--------|
| 1 | Reason Arm Store Scoping Defense | P3 | Defense in Depth | Deferred |
| 2 | Provider Reliability — Live Retry Activation | P1 | Reliability / Provider | Deferred |

---

## 1) Reason Arm Store Scoping Defense

| Field | Value |
|-------|-------|
| **Title** | Reason Arm Store Scoping Defense |
| **Status** | Deferred |
| **Priority** | P3 |
| **Category** | Defense in Depth |
| **Investigation reference** | `docs/recovery_dispatch_timing_investigation_v1.md` |
| **Date logged (UTC)** | 2026-07-03 |

### Description

`find_abandoned_cart_for_reason_arm()`
(`services/recovery_schedule_materialization_v1.py`) may resolve abandoned carts using
`recovery_session_id` (session_id) **without explicit `store_slug` scoping**. When the reason-POST
durable materialization path runs, a reason POST for store B can therefore discover an
`AbandonedCart` that belongs to store A if both share the same `session_id`.

Discovered during the sync-vs-async recovery dispatch timing investigation
(`docs/recovery_dispatch_timing_investigation_v1.md`).

### Investigation result

- **No production incident.**
- **No truth leak** — the resulting `recovery_key` / `RecoverySchedule` remain scoped to the
  reason-POST's own store; only the *trigger* crossed stores.
- **No scheduler issue.**
- **No dashboard issue.**
- **No Purchase Truth impact.**
- **No Session Truth impact** after the store-isolation fix
  (`docs/cartflow_session_truth_store_slug_isolation_bug_v1_report.md`).

The issue only appears under the combination of:

- the same `session_id` reused across stores,
- specific request ordering (store A's cart-event precedes store B's reason POST), and
- zero-delay test conditions (`get_recovery_delay=0`) that collapse async dispatch timing.

### Impact

| Area | Affected? |
|------|-----------|
| Production behavior | No (no evidence; real widgets rarely reuse a `session_id` across stores) |
| Truth layers (Purchase / Session) | No |
| Scheduler / recovery timing | No |
| Dashboard | No |
| Tests | Contributes to `test_demo_then_demo2_same_session_both_schedule` timing artifact only |

### Decision

**Deferred intentionally.**

This item must **NOT** block:

- Architecture Consolidation
- Operational work
- Recovery work
- Meta work

### Revisit conditions

Re-open only if:

1. Real production evidence appears.
2. Cross-store `session_id` reuse is actually observed.
3. The recovery arm architecture is redesigned (fold store scoping in as part of that work).

---

## 2) Provider Reliability — Live Retry Activation

| Field | Value |
|-------|-------|
| **Title** | Provider Reliability — Live Retry Activation (and activation-gated items) |
| **Status** | Deferred |
| **Priority** | P1 |
| **Category** | Reliability / Provider |
| **Investigation reference** | `docs/provider_reliability_activation_review_v1.md` (verdict: SAFE TO COMMIT — ACTIVATION DEFERRED); `docs/provider_reliability_governance_v1.md` §9; `docs/provider_reliability_foundation_v1_audit.md` |
| **Date logged (UTC)** | 2026-07-04 |

### Description

Provider Reliability Foundation V1 is committed as a **governed, record-only foundation**:
reconciled Provider Truth, deterministic failure disposition, a durable retry ledger
(`ProviderRetryLedger` / `services/provider_retry_ledger_v1.py`), and denominator-based
reliability metrics. **Live retry re-dispatch is intentionally OFF** (`PROVIDER_RETRY_ACTIVE`
unset) — the ledger records retry *intent* but nothing re-sends. Activating automatic
re-sends is a merchant-visible behavior change and is therefore deferred to its own future
engineering initiative.

### Investigation result

The Activation Review found **no P0/P1 defects** in the foundation and confirmed it is
behavior-neutral for merchants. The following items are gated behind future activation
(they are *not* defects in the record-only foundation):

- **Gated dispatcher** consuming `claim_due_retries` → `send_whatsapp`, honoring existing
  send idempotency + operational-control/opt-out blocks, finalizing ledger status.
- **Real-path ledger population** (currently populated only by tests / verification harness).
- **PR-11 inbound webhook authentication** (Twilio signature / Meta) — currently unauthenticated (governance §9, P1).
- **F-1 metrics window alignment** — retry_* rates take an all-time ledger numerator against a
  24h acceptance denominator (can exceed 100%); harmless while record-only, align before activation.
- **Durable provider latency sampling** (`provider_latency.sampled=false` today).
- **Meta delivery-truth ingestion** (Twilio-only today; foundation is provider-agnostic).

### Impact

| Area | Affected? |
|------|-----------|
| Production behavior (sends / recovery timing) | No — record-only; no send is added or altered |
| Merchant-visible behavior / dashboard UI | No (verified blast-radius trace of the PR-14 correlation fix) |
| Purchase Truth / Lifecycle Truth | No — decoupled, read-only reconciliation |
| Scheduler ownership | No |
| Data growth | Bounded append-only `webhook_delivered` timeline rows on delivered recovery webhooks (already governed by the timeline log growth audit) |

### Decision

**Deferred intentionally.** Foundation closed as a Governed Engineering Foundation.

Live retry activation must undergo its **own full lifecycle** — Audit → Governance →
Implementation → Activation Review → Production Validation → Closure — before any customer
re-send behavior is enabled.

This item must **NOT** block closure of Provider Reliability Foundation V1, nor other
operational / Meta / dashboard work.

### Revisit conditions

Re-open (as a new "Provider Reliability — Retry Activation" initiative) when:

1. Automatic customer re-sends on temporary failure are an explicitly approved product behavior.
2. The gated dispatcher + real-path ledger population are designed under their own governance.
3. PR-11 webhook authentication and F-1 metrics-window alignment are scheduled as activation prerequisites.
