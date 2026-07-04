# Provider Reliability Implementation V1

**Status:** Implemented (foundation) · **Classification:** Provider Reliability domain — Stage-3 Implementation
**Governs under:** [`provider_reliability_governance_v1.md`](provider_reliability_governance_v1.md) (authoritative) · Evidence: [`provider_reliability_foundation_v1_audit.md`](provider_reliability_foundation_v1_audit.md)
**Engineering Constitution stage:** §4 Lifecycle — *Implementation* (implements approved governance; does not decide reliability behavior)

---

## 1. Objective

Implement Provider Reliability Governance V1 so provider behavior becomes
**deterministic, observable, durable, and measurable** — without redesigning the
provider architecture, Recovery, or Purchase Truth, and **without changing
merchant-visible behavior**.

The implementation is **additive and default-safe**, matching the codebase idiom used
by `whatsapp_delivery_truth_v1` (additive truth foundation that does not change
recovery/queue/attribution decisions). It builds the contract-compliant reliability
foundation and wires the read-only/observability surfaces immediately; **live retry
re-dispatch is gated OFF by default** (`PROVIDER_RETRY_ACTIVE`) because activating
automatic re-sends is a merchant-visible behavior change reserved for a later,
explicitly-approved activation step (governance §9 phasing).

---

## 2. What was added (files)

| File | Role | Governance |
|------|------|-----------|
| `services/provider_reliability_truth_v1.py` | **Phase 1 + 3** — reconciled Provider Truth model (4 altitudes, no cross-altitude inference) + deterministic failure disposition mapping | §2 PR-1/2/5; §3 PR-7/9 |
| `services/provider_retry_ledger_v1.py` | **Phase 2** — durable, restart-safe, budget-aware, `Retry-After`-compliant, idempotent retry ledger (record-only by default) | §4 PR-4, PR-RT-1..9 |
| `services/provider_reliability_metrics_v1.py` | **Phase 4 + 5** — operational visibility read-model + denominator-based metrics | §6; §7 PR-10 |
| `models.py` → `ProviderRetryLedger` | Durable system-of-record table (one row per `correlation_key`+provider+step) | PR-4, PR-RT-5 |
| `schema_widget.py` → `ensure_provider_retry_ledger_schema` | Self-creating schema (mirrors delivery-truth pattern; no Alembic-only step) | — |
| `services/whatsapp_send.py` (1 line) | **Phase 1 correctness fix (PR-14)** — persist `recovery_key` at acceptance so delivery truth links back | §2 PR-14, PR-2 |
| `services/operational_metrics_v1.py` | Exposes `metrics.provider_reliability` + metric-contract registry entries | §7 |
| `tests/test_provider_reliability_v1.py` | 19 tests across all phases | §Verification |
| `scripts/_provider_reliability_verify_v1.py` | End-to-end verification harness (21 checks) | §Verification |

**No changes to:** Purchase Truth, Lifecycle Truth, dashboard UI, merchant-visible
behavior, snapshot generation, scheduler ownership, recovery scheduling semantics.

---

## 3. Phase 1 — Provider Truth Foundation (§2)

### Four altitudes, one owner each, no inference
`reconcile_provider_truth(correlation_key)` reconciles the **existing** stores into one
authoritative disposition:

```
Acceptance          ← CartRecoveryLog.status  (sent_real | mock_sent)
Provider Delivery   ← WhatsAppDeliveryTruth.truth_level (sent_to_network)
Customer Delivery   ← WhatsAppDeliveryTruth.truth_level (delivered_to_customer | read_by_customer)
Terminal Outcome    ← either store (whatsapp_failed | failed_final | failed_delivery)
```

- **Acceptance never implies delivery (PR-1/PR-2).** A row that is `accepted` with no
  delivery evidence resolves to `altitude=acceptance`, `delivered=False`,
  `reason=accepted_awaiting_delivery`. Delivery is set **only** by delivery evidence.
- **One reconciled owner (PR-5).** Reconciliation is the single authority; it reads the
  underlying stores but never mutates Purchase Truth or Lifecycle Truth.
- **Read-only.** No writes to truth stores.

### PR-14 correlation fix (the one live correctness change)
The audit found the delivery→timeline bridge dead because `send_whatsapp()` recorded
provider acceptance **without** the `recovery_key` (`whatsapp_send.py:550`). Governance
PR-14 mandates correlation persisted at send. The fix passes `recovery_key=(rk or "")`
into `record_provider_acceptance_from_send(...)`. Consequence: delivery/read webhooks
now link back to their recovery, so `reconcile_provider_truth` and the existing
delivery→timeline bridge observe real delivery evidence (additive observability; no
dashboard UI or merchant change).

---

## 4. Phase 3 — Deterministic failure classification (§3)

`resolve_failure_disposition(...)` maps **every** provider outcome to exactly one axis,
building on the existing `cartflow_provider_readiness.classify_provider_failure`:

| Failure class / signal | Disposition |
|------------------------|-------------|
| `provider_rate_limited`, `provider_unavailable`, `provider_timeout` | **retry** |
| `provider_rejected_message`, `template_not_approved`, `sandbox_recipient_not_joined`, `provider_auth_failed`, `provider_not_configured` | **terminal** |
| `empty_message`, `invalid_phone`, converted / opt-out markers | **non_provider** |
| duplicate marker | **suppressed** |
| anything unclassified / `unknown_provider_failure` | **unknown** (observable, never silent — PR-6) |

Precedence: internal marker → non-provider error string → provider failure class. No
implicit behavior; unknown is a first-class, observable state.

---

## 5. Phase 2 — Durable retry ledger (§4)

`ProviderRetryLedger` is the durable **system of record** for retry intent. The
foundation is **record-only**: recording a retryable failure schedules the next attempt
in the DB but **never re-dispatches** while `PROVIDER_RETRY_ACTIVE` is off (default), so
no send is added or altered.

`record_send_outcome(...)` behavior by disposition:

- **retry** → increment `attempt`; if `attempt >= max_attempts` → `status=exhausted`
  (terminal + observable, PR-RT-3); else `status=pending` with
  `next_attempt_at = now + max(exponential_backoff(attempt), Retry-After)` and
  `retry_after_until` recorded (PR-8 / PR-RT-7).
- **terminal / suppressed / non_provider** → recorded with the matching terminal status;
  no retry scheduled (PR-RT-9: only retryable outcomes retry).
- **unknown** → `status=unknown`, observable, awaits reconciliation (PR-6).
- **success** → `status=succeeded`, idempotent (repeat = no-op single row, PR-RT-8).

Durable-queue operations (process-memory-free, PR-4/PR-RT-5):

- `claim_due_retries()` — atomically stamps `claimed_at` so a due retry is claimed
  **exactly once** across restarts/workers (no duplicate sends). Returns row snapshots;
  **does not send** (that is the future gated dispatcher).
- `cancel_retry()` — cancels open retries on conversion / opt-out (PR-RT-4).
- Budget/backoff via env: `PROVIDER_RETRY_MAX_ATTEMPTS` (3), `PROVIDER_RETRY_BACKOFF_SECONDS`
  (60), `PROVIDER_RETRY_BACKOFF_MAX_SECONDS` (3600).

`Retry-After` parsing accepts integer-seconds or HTTP-date.

---

## 6. Phase 4 + 5 — Visibility & denominator metrics (§6, §7)

`build_provider_reliability_report(window_hours=24)` is a read-only reconciliation of
CartRecoveryLog (acceptance) + WhatsAppDeliveryTruth (delivery) + ProviderRetryLedger
(retries) + provider readiness. It is surfaced under
`operational_metrics_v1 → metrics.provider_reliability`.

**Rates are denominator-based (PR-10)** — `None` when the denominator is 0; raw counts
are exposed only as `denominators`, never as the KPI:

| Metric | Numerator / Denominator |
|--------|--------------------------|
| `acceptance_rate` | accepted / attempted (accepted+failed) |
| `delivery_rate` | delivered / accepted |
| `retry_rate` | retried / attempted |
| `retry_success_rate` | succeeded-after-retry / retried |
| `retry_exhaustion_rate` | exhausted / retried |
| `unknown_state_rate` | (accepted − delivered − delivery_failed) / accepted |
| `provider_availability` | readiness (point-in-time) |
| `provider_latency` | `{sampled: false, ceiling_seconds}` — honestly not yet durably sampled (audit §6.2) |

Visibility block includes `retry_queue` (pending / due_backlog / exhausted / cancelled /
unknown) and `provider_health`. Metric names are registered in
`operational_metrics_v1.list_metric_contracts()`.

---

## 7. Verification (Phase 6)

`tests/test_provider_reliability_v1.py` — **19 tests, all passing**:
disposition determinism; acceptance≠delivery; delivery-only-from-evidence; terminal
failure; missing-key; retry schedule/exhaustion; Retry-After honored; success
idempotency; single-dispatch claim; cancellation; terminal-never-retries;
denominator-based metrics (with/without data).

`scripts/_provider_reliability_verify_v1.py` — **21/21 checks, PASS**, demonstrating
against a throwaway DB:

- restart safety & retry persistence (row survives session close/reopen)
- Retry-After compliance (≥120s floor honored)
- idempotency (repeat success = single row) and no-duplicate-dispatch (claim once)
- delivery truth integrity + correlation integrity (acceptance→webhook→delivered on the
  **same** `recovery_key`)
- no silent failure (every ledger row carries an observable status)
- denominator-based metrics; **live dispatch OFF** (`retry_live_dispatch_active=False`)

**Pre-existing, unrelated failures** (confirmed by stash-revert): `test_operational_metrics_v1::test_allowlisted_in_production_dev_routes`
(dev-route allowlist in `main.py`), `test_whatsapp_delivery_truth_v1::…test_send_passes_status_callback`
(patches a non-existent `services.whatsapp_send.Client`). Neither is touched by this work.

---

## 8. Governance contract coverage

| Contract | Where satisfied |
|----------|-----------------|
| PR-1 acceptance ≠ delivery | reconcile (no inference) + metrics keep rates separate |
| PR-2 delivery never inferred | delivery altitude only from delivery evidence |
| PR-3 terminal failures observable | ledger `terminal`/`exhausted` statuses + metrics |
| PR-4 retries durable | `ProviderRetryLedger` (DB), `claim_due_retries` restart-safe |
| PR-5 one reconciled owner | `reconcile_provider_truth` is the single authority |
| PR-6 unknown observable | `DISPOSITION_UNKNOWN` + ledger `unknown` + `unknown_state_rate` |
| PR-7 no silent temporary failure | temporary → `retry` disposition recorded durably |
| PR-8 provider backoff authoritative | `Retry-After` parsed and used as the floor |
| PR-9 every failure classified+owned | deterministic disposition map (total function) |
| PR-10 metrics have denominators | all rates over explicit denominators, `None` when 0 |
| PR-14 correlation mandatory at send | `recovery_key` persisted at acceptance |
| PR-5/PR-13 provider-agnostic | keyed on `correlation_key`+`provider`; Twilio today, Meta inherits |

**Deferred to explicit activation (governance §9, not this phase):** PR-11 webhook
authentication (touches routes); live retry re-dispatch loop (merchant-visible behavior —
gated by `PROVIDER_RETRY_ACTIVE`); durable latency sampling.

---

## 9. Maturity

Provider Reliability moves from **Level 1 (Working)** to **Level 3 (Measured)** for the
truth/classification/metrics surfaces (governed contracts + denominator metrics + tests),
with durable retry infrastructure in place at **Level 2 (Governed)** pending live
activation. Future providers (Meta, others) inherit this foundation rather than
implementing their own reliability behavior.
