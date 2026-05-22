# Lifecycle Truth Completion v1 — Audit Report

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit of lifecycle decision layers before new behavior.  
**Commit:** `audit: verify lifecycle truth completion v1`

No changes to WhatsApp send, delays, queue/worker, RecoverySchedule, Purchase Truth, Reply Intent, Continuation, dashboard, widget, or runtime lifecycle behavior.

---

## Architecture (three decision surfaces)

| Layer | Module | Role |
|-------|--------|------|
| **A — Recovery lifecycle intelligence** | `services/lifecycle_intelligence.py` | Boolean evidence → `[LIFECYCLE DECISION]` / `[LIFECYCLE ACTION]` (observation + gates in `main._observe_lifecycle_intelligence_decision`) |
| **B — Reply intent (WhatsApp text)** | `services/reply_intent_handling.py` | Inbound reply → `[REPLY INTENT]` → `decision` + `action` (PURCHASE/STOP/PRICE/DELIVERY/UNKNOWN) |
| **C — Purchase truth (evidence)** | `services/purchase_truth.py` | `purchase_completed` / `order_paid` / events → `[PURCHASE TRUTH]` → `[PURCHASE LIFECYCLE CLOSED]` |

Terminal closure (`terminal_state=closed_purchase`, `future_recovery_allowed=false`) is enforced in **`services/purchase_lifecycle_closure.py`**, invoked from Purchase Truth and reply PURCHASE paths — not from layer A alone.

**Note:** There is no `decision=CLOSED` enum in layer A. “Close” is expressed as `decision=STOP` + `action=close_lifecycle` or Purchase Truth logs.

---

## Lifecycle matrix

| # | Behavior / trigger | Expected (product) | Observed (code) | Verified | PASS |
|---|------------------|--------------------|-----------------|----------|------|
| 1 | `returned_to_site` | `decision=STOP`, `action=no_send` | `decide_lifecycle_recovery(returned=True)` → STOP, `no_send` | `test_lifecycle_intelligence`, `test_audit_01`, propagation tests | **PASS** |
| 2 | `purchase_completed` (recovery flag) | `CLOSED` / close, `future_recovery_allowed=false` | Layer A: STOP + `close_lifecycle`. Layer C: `[PURCHASE TRUTH]` + `[PURCHASE LIFECYCLE CLOSED]` + block flags | `test_audit_02`, `test_purchase_truth_*` | **PASS** (CLOSED = layer C + action hint, not a separate A enum) |
| 3 | `customer_replied` (generic) | HANDOFF or STOP by intent | Layer A: **HANDOFF** + `handoff_continuation`. Recovery seq: **STOP follow-up** (`skipped_followup_customer_replied`) + `[RECOVERY AUTOMATION STOPPED]` | `test_audit_03`, `main` ~6645 | **PASS** (HANDOFF at observe; execution suppresses send) |
| 4 | `customer_replied` STOP (`لا أريد`) | `decision=STOP` | Reply intent: STOP + `stop_recovery` | `test_audit_04`, `test_reply_intent_handling` | **PASS** |
| 5 | `customer_replied` PURCHASE (`تم الطلب`) | `decision=CLOSE` | Reply intent: **STOP** + `close_lifecycle` → `record_purchase_lifecycle_closure` | `test_audit_05`, webhook closure tests | **PASS** (CLOSE = STOP + close_lifecycle + closure logs) |
| 6 | `ignored` | `decision=CONTINUE`, `next_step=attempt_N` | CONTINUE, `attempt_{n+1}`, `proceed_recovery` | `test_audit_06` | **PASS** |
| 7 | `delay_waiting` | `decision=WAIT` | WAIT, `wait_schedule`, behavior `delay_waiting` | `test_audit_07`, `main` ~7065 `delay_pending=True` | **PASS** |
| 8 | `unknown` | `decision=FALLBACK` | FALLBACK, `reason_then_delay` | `test_audit_08` | **PASS** |
| 9 | `checkout_started` | WAIT or temporary suppress | **Not in lifecycle intelligence.** Widget: `suppress_when_checkout_started` blocks triggers only | `test_audit_09` | **PARTIAL** — widget only |
| 10 | Purchase truth event | `[PURCHASE TRUTH]` → `[PURCHASE LIFECYCLE CLOSED]` | `ingest_purchase_truth_payload` logs both; recovery blocked via `block_recovery_if_purchase_lifecycle_closed` | `test_audit_10`, `test_purchase_truth_lifecycle_v1` | **PASS** |

Automated proof: `pytest tests/test_lifecycle_truth_completion_audit_v1.py`

---

## Final summary table

| Lifecycle state | Expected | Observed | PASS / FAIL | Risk | Priority |
|-----------------|----------|----------|-------------|------|----------|
| returned_to_site | STOP, no_send | STOP, no_send | **PASS** | Low | — |
| purchase_completed (intel) | Close lifecycle | STOP + close_lifecycle action | **PASS** | Low | — |
| purchase_completed (truth) | TRUTH + CLOSED + block recovery | Implemented | **PASS** | Low | — |
| customer_replied (generic) | HANDOFF / STOP | HANDOFF observe + follow-up suppress | **PASS** | Medium — two log lines | P2 |
| customer_replied STOP | STOP | STOP + stop_recovery | **PASS** | Low | — |
| customer_replied PURCHASE | CLOSE | STOP + close_lifecycle + closure | **PASS** | Medium — dual classifiers (`recovery_reply_intent=other`) | P2 |
| ignored | CONTINUE, attempt_N | CONTINUE, attempt_{n+1} | **PASS** | Low | — |
| delay_waiting | WAIT | WAIT | **PASS** | Low | — |
| unknown | FALLBACK | FALLBACK | **PASS** | Low | — |
| checkout_started | WAIT / suppress | Widget suppress only | **PARTIAL** | Medium — no unified lifecycle log | **P1** |
| purchase truth chain | TRUTH → CLOSED → BLOCK | Verified in tests | **PASS** | Low | — |

---

## Gaps

### Closed gaps ✅

- Returned-to-site → STOP / no_send (intelligence + anti-spam).
- Purchase evidence → Purchase Truth → terminal closed_purchase + recovery block.
- Reply PURCHASE / STOP → reply intent decisions + lifecycle closure hooks.
- Ignored → CONTINUE with `next_step`.
- Delay not elapsed → WAIT.
- No signal → FALLBACK / reason_then_delay.
- Idempotent closure logs (`[PURCHASE LIFECYCLE CLOSED]` / `ALREADY CLOSED`).

### Remaining gaps 🟡

- **`checkout_started`** has no `behavior=` in lifecycle intelligence; only widget trigger suppression.
- **`customer_replied`** logs HANDOFF in `[LIFECYCLE DECISION]` but recovery path uses follow-up **suppress** (STOP-like), not continuation handoff — naming mismatch for operators.
- **Reply PURCHASE** uses `decision=STOP` in `[REPLY INTENT]`, not a literal `CLOSED` label (closure proof is `[PURCHASE LIFECYCLE CLOSED]`).
- **Dual classifiers:** `[RECOVERY REPLY INTENT] intent=other` vs reply/continuation PURCHASE for `تم الطلب` (documented in propagation tests).

### Dangerous gaps 🔴

- None identified for **blocking** wrong sends when purchase truth or conversion flags are set, provided deploy includes Purchase Truth + closure v1 (`effb1cb`+).
- **Operational risk:** operators grep only `[LIFECYCLE DECISION]` and miss `[PURCHASE TRUTH]` / `[PURCHASE LIFECYCLE CLOSED]` on evidence-only purchase (no WhatsApp “تم الطلب”).

---

## Recommendations (future work — out of scope for this audit)

1. Add `checkout_started` to lifecycle observation (WAIT + `suppress_widget`) or document as widget-only permanently.
2. Align `customer_replied` log decision with execution (HANDOFF vs STOP) or add `extra=intent=` on observe when reply intent already ran.
3. Single operator runbook: grep order `[PURCHASE TRUTH]`, `[PURCHASE LIFECYCLE CLOSED]`, `[REPLY INTENT]`, `[LIFECYCLE DECISION]`, `[RECOVERY BLOCKED]`.

---

## Code references

- Decision table: `services/lifecycle_intelligence.py` → `decide_lifecycle_recovery()`
- Observe hook: `main.py` → `_observe_lifecycle_intelligence_decision()`
- Reply intent: `services/reply_intent_handling.py` → `lifecycle_decision_for_reply_intent()`
- Purchase truth: `services/purchase_truth.py` → `ingest_purchase_truth_payload()`
- Terminal closure: `services/purchase_lifecycle_closure.py` → `record_purchase_lifecycle_closure()`
