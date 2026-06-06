# Purchase Truth Closure Matrix v1

**Date (UTC):** 2026-06-05  
**Scope:** Final closure proof for Purchase Truth core engine readiness (Steps 1–5).  
**Commit message:** `close purchase truth core readiness matrix`  
**Regression gate (2026-06-05):** **49 passed** across the gate suite listed below.

**No production behavior changes in this deliverable.** Documentation and verification gate only.

---

## Current Purchase Truth status

| Layer | Status |
|-------|--------|
| **Purchase Truth — core engine readiness** | **CLOSED** |
| **Lifecycle Truth Completion** | **NEXT PHASE** (not closed here) |
| **Real platform/provider pilot validation** | **Later** — not a blocker for core Purchase Truth closure |
| **Product Intelligence / attribution** | **Separate** — out of scope for this closure |
| **Full integration adapters (Zid/Salla/Shopify live)** | **Deferred** — out of scope for this closure |

Purchase Truth core engine readiness means: when durable purchase evidence exists (or is ingested and reconciled), CartFlow **stops recovery sends**, **cancels or blocks pending schedules**, and **survives cold restart** without relying on in-memory conversion flags alone.

---

## Completed verification steps (Steps 1–4)

### Step 1 — DB-only restart survival

| Field | Value |
|-------|-------|
| **Goal** | Prove purchased recovery does not resume/send after cold restart using only `purchase_truth_records`. |
| **Test file** | `tests/test_purchase_truth_db_restart_survival_v1.py` |
| **Commit** | `4737286` — `purchase truth db-only restart survival verification` |
| **Proves** | `evaluate_resume_safety` and `resume_one_schedule` read DB via `has_conversion_truth` / `has_purchase`; `purchase_completed` blocks dispatch; no WhatsApp send; `scheduled` rows marked `skipped_resume_unsafe` when resume safety fails. |
| **Production touch** | Minimal fix in `resume_one_schedule`: use `_mark_schedule_row_terminal_from_scheduled` for purchase-blocked `scheduled` rows (previously only `running` rows were finalized). |

### Step 2 — Purchase after first message blocks second message

| Field | Value |
|-------|-------|
| **Goal** | Prove Message #1 sent + durable DB purchase truth + Message #2 due → no second WhatsApp send. |
| **Test file** | `tests/test_purchase_truth_blocks_second_message_v1.py` |
| **Commit** | `5a9682c` — `purchase truth blocks second message after purchase` |
| **Proves** | `resume_one_schedule` blocks step 2 with `purchase_completed`; WhatsApp queue step 2 returns `stopped` / `stopped_converted` when memory cleared and only `PurchaseTruthRecord` exists. |
| **Production touch** | None (verification only). |

### Step 3 — Inbound purchase reply creates durable truth and blocks continuation

| Field | Value |
|-------|-------|
| **Goal** | Prove inbound WhatsApp purchase-claim reply → durable truth → lifecycle closed → no continuation send. |
| **Test file** | `tests/test_purchase_truth_inbound_reply_blocks_continuation_v1.py` |
| **Commit** | `6ed66b8` — `purchase truth inbound reply blocks continuation` |
| **Proves** | `run_inbound_whatsapp_reply_intent_hook` (same entry as `POST /webhook/whatsapp` for reply intent) on «تم الطلب», «اشتريت», «خلاص طلبت» → `ingest_purchase_truth_from_reply_claim` → `reply_purchase_claim` row + `purchase_completed` closure → Message #2 schedule cancelled → queue step 2 blocked after memory clear. |
| **Production touch** | None (verification only). |
| **Note** | `reply_purchase_claim` remains **low/medium confidence** by design; not equivalent to platform `order_paid`. |

### Step 4 — Platform/webhook purchase reconciles to active recovery

| Field | Value |
|-------|-------|
| **Goal** | Prove checkout/webhook key mismatch still closes canonical CartFlow `recovery_key`. |
| **Test file** | `tests/test_purchase_truth_platform_reconcile_blocks_recovery_v1.py` |
| **Commit** | `0b13696` — `purchase truth reconciles platform purchase to active recovery` |
| **Proves** | `build_zid_purchase_truth_payload` → `ingest_purchase_truth_payload` with checkout session drift + shared `cart_id` → `reconcile_purchase_with_active_recovery_carts` bridges to canonical abandon key (`reconcile_from=` evidence) → cart `recovered` → schedule cancelled → queue step 2 blocked after memory clear. |
| **Production touch** | None (verification only). |

---

## Supporting test corpus (pre-Step gate)

| Test file | Role |
|-----------|------|
| `tests/test_cartflow_purchase_truth_foundation_v1.py` | Durable ingest, `stop_if_purchased`, schedule cancel on `record_purchase`, DB persistence after memory reset. |
| `tests/test_purchase_truth_completion_v2.py` | Canonical facade, Zid payload build, precedence, lifecycle closure records, dashboard `has_purchase` alignment. |
| `tests/test_cartflow_session_truth_hardening_v1.py` | `has_conversion_truth` DB fallback from `purchase_truth_records`; session truth rehydration. |
| `tests/test_purchase_recovery_reconcile_v1.py` | Cart/session drift reconciliation, merchant store slug resolution, purchase-truth trace endpoint. |
| `tests/test_recovery_restart_survival.py` | Durable schedule persistence, resume safety, execution boundary (includes memory-only purchase block baseline). |
| `tests/test_purchase_lifecycle_closure_v1.py` | Lifecycle closure from reply intent and webhook chain (continuation stop). |
| `tests/test_reply_intent_handling.py` | Reply intent classification and webhook hook wiring. |

---

## Verification summary table

| Scenario | Status | Evidence | Blocking? |
|----------|--------|----------|-----------|
| Durable `purchase_truth_records` exists | **Verified** | `test_cartflow_purchase_truth_foundation_v1.py`, `test_purchase_truth_completion_v2.py` | No |
| Purchase wins over scheduled recovery (restart) | **Verified** | `test_purchase_truth_db_restart_survival_v1.py` (`4737286`) | No |
| Purchase wins after first send (Message #2) | **Verified** | `test_purchase_truth_blocks_second_message_v1.py` (`5a9682c`) | No |
| Purchase wins after inbound reply claim | **Verified** | `test_purchase_truth_inbound_reply_blocks_continuation_v1.py` (`6ed66b8`) | No |
| Platform/checkout key mismatch → canonical recovery closed | **Verified** | `test_purchase_truth_platform_reconcile_blocks_recovery_v1.py` (`0b13696`), `test_purchase_recovery_reconcile_v1.py` | No |
| DB-only restart does not resume purchased recovery | **Verified** | `test_purchase_truth_db_restart_survival_v1.py` | No |
| `has_conversion_truth` reads DB when memory cleared | **Verified** | `test_cartflow_session_truth_hardening_v1.py` | No |
| WhatsApp queue respects purchase truth before send | **Verified** | Step 2/3/4 queue assertions (`stopped` / `stopped_converted`) | No |
| Lifecycle closure records on verified ingest | **Verified** | `test_purchase_truth_completion_v2.py` | No |
| Real Zid live webhook on merchant store | **Deferred** | Code path exists (`build_zid_purchase_truth_payload` + ingest); no live pilot PASS | **No** (not core-engine blocker) |
| Real Meta/Twilio production WhatsApp delivery | **Deferred** | Mock/queue tests only | **No** (not core-engine blocker) |
| Product attribution / recovered revenue reporting | **Separate** | `services/purchase_attribution_*` — not Purchase Truth closure | **No** |
| Lifecycle dashboard display consistency | **Next phase** | Lifecycle Truth Completion | **No** (for Purchase Truth closure) |
| Full Zid/Salla/Shopify integration adapters | **Deferred** | `integrations/` — not part of Steps 1–5 | **No** |
| `recovery_key` widget vs checkout always aligned | **Partially mitigated** | Reconciliation by `cart_id` / session; identity audits remain | **No** (reconcile path verified) |

---

## Remaining non-blocking limitations

These are **explicitly NOT blockers** for marking Purchase Truth core engine readiness **CLOSED**:

1. **Live Zid webhook pilot** — Production HTTP route and merchant-specific payload shapes need operator pilot confirmation; unit/facade tests cover ingest + reconcile logic.
2. **Live WhatsApp provider pilot** — Send path tested via mock queue and patched `send_whatsapp`; production Meta/Twilio credentials and delivery receipts not re-certified here.
3. **Product Intelligence / attribution** — Purchase truth closure does not certify recovered-revenue causality or merchant reporting accuracy.
4. **`reply_purchase_claim` confidence** — Customer reply claims remain lower confidence than `order_paid`; policy unchanged by Steps 1–5.
5. **End-to-end HTTP webhook TestClient slowness** — Some full `TestClient` webhook tests are slow in shared SQLite dev environments; Step 3 uses `run_inbound_whatsapp_reply_intent_hook` (production hook entry) with equivalent coverage.
6. **Dashboard row classification edge cases** — Merchant dashboard purchased vs pending display moves to **Lifecycle Truth Completion**.

---

## Deferred to Lifecycle Truth Completion

- Unified lifecycle display labels (Arabic/English) across dashboard, ops, and merchant views.
- Cross-module precedence presentation (purchase vs reply vs return vs delay) in UI copy.
- VIP / manual-handling lifecycle alignment audits.
- Closure record ↔ dashboard phase_key consistency audits.
- Scenario B/C completion matrices from `docs/cartflow_lifecycle_truth_completion_audit_v1.md`.

**Lifecycle Truth Completion is NOT marked closed by this document.**

---

## Deferred to real platform integration testing

- Live Zid `order.paid` webhook on connected merchant stores.
- Platform integration gateway HTTP routes under production auth.
- Salla / Shopify adapter purchase ingest (not in scope).
- OAuth / token refresh and webhook signature verification pilots.
- Cross-store identity drift under real checkout redirects.

---

## Final regression gate (Step 5)

**Command run (2026-06-05):**

```text
pytest tests/test_purchase_truth_db_restart_survival_v1.py \
      tests/test_purchase_truth_blocks_second_message_v1.py \
      tests/test_purchase_truth_inbound_reply_blocks_continuation_v1.py \
      tests/test_purchase_truth_platform_reconcile_blocks_recovery_v1.py \
      tests/test_purchase_truth_completion_v2.py \
      tests/test_cartflow_purchase_truth_foundation_v1.py \
      tests/test_cartflow_session_truth_hardening_v1.py \
      tests/test_purchase_recovery_reconcile_v1.py \
      tests/test_recovery_restart_survival.py -q
```

**Result:** **49 passed**, 0 failed.

---

## Final closure decision

**Purchase Truth core engine readiness = CLOSED**

Closure is justified because all operational risks targeted in Steps 1–4 now have explicit PASS evidence:

- Durable purchase truth exists and survives memory clear.
- Purchase wins over scheduled recovery after restart.
- Purchase wins after first WhatsApp send (no Message #2).
- Purchase wins after inbound reply purchase claim (durable ingest).
- Platform/checkout session drift can reconcile to canonical active `recovery_key`.
- Pending schedules are cancelled or send paths return purchase-blocked terminal outcomes.

**Lifecycle Truth Completion = NEXT PHASE**

**Real platform/provider pilot validation = later, not a blocker for core Purchase Truth closure.**

---

## Key production paths (reference)

| Path | Module / entry |
|------|----------------|
| Durable ingest | `services/cartflow_purchase_truth.record_purchase` |
| Canonical facade | `services/purchase_truth.ingest_purchase_truth` / `ingest_purchase_truth_payload` |
| Reply claim ingest | `services/purchase_truth.ingest_purchase_truth_from_reply_claim` |
| Zid payload builder | `services/zid_webhook_purchase_v2.build_zid_purchase_truth_payload` |
| Active cart reconcile | `main.reconcile_purchase_with_active_recovery_carts` |
| Session truth read | `services/cartflow_session_truth.has_conversion_truth` |
| Resume safety | `services/recovery_restart_survival.evaluate_resume_safety` |
| Send gate | `services/cartflow_purchase_truth.stop_if_purchased`, `services/whatsapp_queue._is_converted` |
| Inbound reply hook | `services/reply_intent_handling.run_inbound_whatsapp_reply_intent_hook` |

---

*Prior audit docs remain historical context: `docs/cartflow_purchase_truth_audit_v1.md`, `docs/cartflow_purchase_truth_completion_v2.md`. This matrix supersedes their **closure verdict** for core engine readiness as of 2026-06-05.*
