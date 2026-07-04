# Provider Reliability Activation Review V1

**Type:** Activation-safety review (read-only) · **Reviewed:** Provider Reliability Implementation V1
**Governance:** [`provider_reliability_governance_v1.md`](provider_reliability_governance_v1.md) · **Audit:** [`provider_reliability_foundation_v1_audit.md`](provider_reliability_foundation_v1_audit.md) · **Implementation:** [`provider_reliability_implementation_v1.md`](provider_reliability_implementation_v1.md)
**Constitution stage:** §4 Lifecycle — pre-commit / pre-activation gate. No new implementation, no behavior change, no live activation.

---

## Verdict

> ## **SAFE TO COMMIT — ACTIVATION DEFERRED**

The implementation is **additive, default-safe, and behavior-neutral for merchants**.
Live retry re-dispatch remains OFF (`PROVIDER_RETRY_ACTIVE` unset) and must stay
record-only until the activation prerequisites in §7 are met. One non-blocking metrics
coherence caveat (F-1) should be corrected **before** live activation, not before commit.

Provider Reliability Foundation can be **closed as a governed, record-only foundation**
(maturity: truth/classification/metrics = Level 3 Measured; durable retry infra = Level 2
Governed pending activation).

---

## Evidence base

- **Diff (tracked files):** only 4, all purely additive — `models.py` (+47, new `ProviderRetryLedger`), `schema_widget.py` (+9, self-creating schema), `services/operational_metrics_v1.py` (+55, read-only block + contracts), `services/whatsapp_send.py` (**+1**, PR-14 correlation). New modules/tests/docs are net-new files. **No** scheduler, dashboard, Purchase-Truth, Lifecycle-Truth, or recovery-flow file was modified.
- **Tests:** `tests/test_provider_reliability_v1.py` — **19/19 pass**.
- **Harness:** `scripts/_provider_reliability_verify_v1.py` — **21/21 checks PASS**.
- **Operational block:** `metrics.provider_reliability` renders with `null` rates at zero denominator, no PII, `retry_live_dispatch_active=false`.
- **Blast-radius trace:** consumers of `WhatsAppDeliveryTruth.recovery_key`, `webhook_delivered`, and the movement shadow were read directly (citations below).

---

## Review Area 1 — Provider Truth Correctness ✅ PASS

`services/provider_reliability_truth_v1.reconcile_provider_truth`:

| Check | Result | Evidence |
|-------|--------|----------|
| Acceptance is not delivery | ✅ | acceptance sets `accepted` only; `delivered` untouched |
| Provider/customer delivery not inferred | ✅ | delivery altitude set **only** from `WhatsAppDeliveryTruth.truth_level` (`_delivery_truth_altitude`) |
| Terminal outcome explicit | ✅ | `failed` set only from `whatsapp_failed`/`failed_final`/`failed_delivery`; sets `altitude=terminal`, `terminal_outcome=failed` |
| accepted-without-delivery → `accepted_awaiting_delivery` | ✅ | reconcile returns `altitude=acceptance`, `delivered=False`, `reason=accepted_awaiting_delivery` (harness §2) |
| Purchase Truth decoupled | ✅ | read-only; no PurchaseTruthRecord import/write |
| Lifecycle Truth decoupled | ✅ | reads `CartRecoveryLog.status`; performs no lifecycle mutation |

No cross-altitude inference exists anywhere in the reconciliation path.

## Review Area 2 — Correlation Integrity ✅ PASS

| Check | Result | Evidence |
|-------|--------|----------|
| Send path persists `recovery_key` | ✅ | `whatsapp_send.py:557` passes `recovery_key=(rk or "")` into `record_provider_acceptance_from_send` |
| Delivery webhooks reconcile to timeline | ✅ | `ingest_twilio_status_callback` fires `STATUS_WEBHOOK_DELIVERED` for delivered w/ non-empty key (`whatsapp_delivery_truth_v1.py:428`) |
| No orphan delivery events for normal sends | ✅ | timeline bridge is **gated on non-empty `recovery_key`** — empty-key (non-recovery) sends never emit timeline events |
| Works Twilio today / Meta later | ✅ (foundation) | ledger + truth keyed on `correlation_key`+`provider` (provider-agnostic). Meta delivery ingestion not yet wired (governance §9, deferred) |
| No duplicate correlation keys | ✅ | `ProviderRetryLedger` `UniqueConstraint(correlation_key, provider, step)`; delivery truth unique by `message_sid`, `recovery_key` intentionally non-unique (many SIDs per recovery); reconcile takes latest by id |

## Review Area 3 — Retry Ledger Safety ✅ PASS

| Check | Result | Evidence |
|-------|--------|----------|
| Retry records durable | ✅ | `ProviderRetryLedger` (DB); survives session close/reopen (harness "survives session restart") |
| Retry budget enforced | ✅ | `attempt >= max_attempts` → `exhausted` (test `test_retry_schedules_and_exhausts_within_budget`) |
| Retry-After respected | ✅ | `next_attempt_at = now + max(backoff, Retry-After)`; harness delta = 120s |
| Retry claims atomic | ✅ | `claim_due_retries` conditional `UPDATE ... WHERE status=pending AND claimed_at IS NULL` |
| Restart-safe | ✅ | claim reads only DB state; no process memory (harness single-dispatch after restart) |
| Exhaustion terminal + observable | ✅ | `status=exhausted`, no `next_attempt_at`; surfaced in `retry_queue.exhausted` + `retry_exhaustion_rate` |
| Idempotency prevents duplicate sends | ✅ | repeat success = single row; claim returns each due row exactly once |
| Live re-dispatch OFF | ✅ | `retry_active()` default False; ledger records intent only, never sends |

## Review Area 4 — Failure Disposition Safety ✅ PASS

`resolve_failure_disposition(...)` is a **total function**: any input not in the governed
map falls through to `unknown` (never silent, never implicit success). All five axes are
covered and verified deterministically (9 taxonomy checks in the harness, plus unit tests):
retry (rate_limit / unavailable / timeout), terminal (rejected / auth / template / sandbox /
not_configured), non_provider (empty_message / invalid_phone / converted / opt-out),
suppressed (duplicate), unknown (unclassified / `unknown_provider_failure`).
Unknown is recorded as an observable ledger status; it does **not** succeed.

## Review Area 5 — Metrics Correctness ✅ PASS (1 caveat, F-1)

| Check | Result | Evidence |
|-------|--------|----------|
| Denominator-based | ✅ | every rate = numerator/denominator; denominators exposed explicitly |
| Raw counts not KPIs | ✅ | counts live under `denominators`/`retry_queue`, never as the headline rate |
| Zero denominator safe | ✅ | `_pct` returns `None` when denominator 0 (verified live block) |
| Appears in operational metrics | ✅ | `metrics.provider_reliability` + 4 metric-contract entries |
| No PII exposed | ✅ | block contains only rates/counts/health/availability/latency — no phone/session/cart |

**F-1 (P2, non-blocking, fix before live activation):** the retry rates
(`retry_rate`, `retry_success_rate`, `retry_exhaustion_rate`) take their **numerator from
the all-time ledger** but their **denominator from a 24h `CartRecoveryLog` window**. When
the ledger is populated across activation this can produce rates >100% (harness showed
`retry_rate=400%`). Harmless today (ledger is empty in production — record-only), but before
live activation the ledger query should be bounded to the same window (or use
ledger-internal denominators). Acceptance/delivery/unknown rates are already coherent
(same-source windowed).

## Review Area 6 — Behavior Neutrality ✅ PASS (one intended, merchant-neutral delta)

**Fully unchanged:** new sends (none), retry dispatch (OFF), scheduler ownership,
dashboard UI, Purchase Truth, Lifecycle Truth, recovery timing, recovery scheduling
semantics. Diff proves no restricted file was modified.

**One intended behavior delta — the PR-14 correlation fix — verified merchant-neutral.**
Persisting `recovery_key` re-activates the previously-dead delivery→timeline bridge. Full
blast-radius trace:

| Potential consumer | Effect of the fix | Merchant-visible? |
|--------------------|-------------------|-------------------|
| `merchant_cart_row_classifier` / lifecycle bucket | keys on `provider_send_proven` = `provider_queued`/`provider_sent` **only**; `webhook_delivered` not in `_PROVIDER_SEND_STATUSES` | **No** |
| Customer movement snapshot (`_shadow_movement_from_timeline`) | `timeline_status_to_movement_event('webhook_delivered')` → `None` ⇒ **total no-op**; module is shadow, "does not affect dashboard, lifecycle" | **No** |
| `purchase_attribution_v1` | takes `recovery_key` as input param; delivery-truth use is a `_future` hook returning `False` today | **No** |
| `vip_operational_truth_v1` | reads delivery truth by `message_sid` on the separate VIP-merchant-alert lane | **No** |
| `recovery_truth_timeline_events` (append) | +1 append-only `webhook_delivered` row per delivered recovery message; consumed only by `/dev/*` diagnostics | **No** (dev/admin only) |
| `WhatsAppDeliveryTruth.recovery_key` | now populated (was NULL); read only by dev diagnostics + `_future` hook | **No** |

Net delta: internal delivery truth becomes accurate; bounded append-only growth on
delivered recovery webhooks (≤1 row/message; already governed by the timeline log growth
audit). **No merchant dashboard, lifecycle, recovery, or purchase-truth behavior changes.**

## Review Area 7 — Activation Readiness

1. **Is the foundation safe to commit?** — **Yes.** Additive, default-safe, tested; the only behavior delta (PR-14) is verified merchant-neutral.
2. **Is live retry activation safe today?** — **No.** No dispatcher consumes `claim_due_retries` to actually re-send; activating would introduce new customer sends and requires the prerequisites below.
3. **What is required before activation?**
   - A gated dispatcher that consumes `claim_due_retries` → `send_whatsapp`, honoring existing send idempotency + operational-control/opt-out blocks, and finalizes ledger status.
   - Ledger population from the real send failure path (currently populated only by tests/harness).
   - **PR-11** inbound webhook authentication (Twilio signature / Meta) — currently unauthenticated (governance §9 P1).
   - **F-1** metrics window alignment for retry rates.
   - Durable provider latency sampling (`provider_latency.sampled=false` today).
   - Explicit sign-off that automatic re-sends are a desired merchant-visible behavior.
4. **What should remain record-only?** — The entire retry ledger (`record_send_outcome`, `claim_due_retries`) and `PROVIDER_RETRY_ACTIVE`=off, until §7.3 is complete. Truth reconciliation, disposition mapping, and metrics remain read-only permanently.
5. **Production verification required after commit** (read-only, no activation):
   - Confirm `provider_retry_ledger` table auto-creates (schema hook) with zero rows.
   - Confirm `metrics.provider_reliability` renders in `/dev/operational-metrics` with real acceptance/delivery denominators and `retry_live_dispatch_active=false`.
   - Confirm delivery webhooks now correlate (spot-check `/dev/recovery-truth?recovery_key=` shows `webhook_delivered` for a delivered recovery) and merchant dashboard status/counts are unchanged.

---

## Required checks — results

| Check | Result |
|-------|--------|
| Provider reliability tests | ✅ 19/19 |
| Verification harness | ✅ 21/21 |
| Operational metrics provider block | ✅ present, `null` at zero denominator, no PII |
| Correlation path | ✅ acceptance→webhook→delivered on same `recovery_key` |
| Retry ledger idempotency | ✅ single row on repeat success |
| Restart-safety simulation | ✅ ledger survives session close; claim once |
| No duplicate-send simulation | ✅ due retry claimed exactly once |
| Live retry OFF check | ✅ `retry_active()=False`, `retry_live_dispatch_active=false` |
| Restricted systems untouched | ✅ diff = 4 additive tracked files; no scheduler/dashboard/truth files |

---

## Findings summary

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| F-1 | P2 | Retry rates mix all-time ledger numerator with windowed acceptance denominator (can exceed 100%) | Align ledger query to metrics window **before live activation**; harmless while record-only |
| F-2 | P3 | PR-14 appends `webhook_delivered` timeline rows on delivered recovery webhooks (bounded append-only growth) | None — already governed by timeline log growth audit; monitor |
| F-3 | Info | Meta delivery ingestion / webhook auth not wired | Deferred to governance §9 activation phases |

No P0 or P1 findings. Nothing blocks commit.
