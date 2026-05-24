# CartFlow Lifecycle Truth v1 — real log scenarios

**Module:** `services/cartflow_lifecycle_truth.py` (shadow mode)  
**Evaluator:** `evaluate_lifecycle_truth()`  
**Shadow log:** `[LIFECYCLE TRUTH MISMATCH]` when legacy intelligence label ≠ canonical

Precedence in code: **purchase > reply > return > waiting > send**

---

## Scenario A — Purchase truth chain (production grep order)

Observed log sequence from `docs/audit_lifecycle_truth_completion_v1.md` / `test_audit_10`:

```text
[PURCHASE DETECTED] recovery_key=demo:s-audit-truth store_slug=demo session_id=s-audit-truth ...
[PURCHASE TRUTH] ... verified=true
[PURCHASE LIFECYCLE CLOSED] ... terminal_state=closed_purchase future_recovery_allowed=false
[PURCHASE STOP] recovery_key=demo:s-audit-truth schedules_cancelled=0 first_record=True
```

**Canonical:** `purchased` — `terminal=true` — merchant: «تم الشراء — أوقفنا المتابعة»

---

## Scenario B — Sent then converted (valid timeline)

From `docs/cartflow_lifecycle_truth_audit_v1.md` §7 — not a conflict:

```text
CartRecoveryLog: mock_sent (step 1)
CartRecoveryLog: stopped_converted (tail step)
```

**Inputs:** `log_statuses={mock_sent, stopped_converted}`, `latest_log_status=stopped_converted`  
**Canonical:** `purchased` (purchase tier beats send)

---

## Scenario C — Customer replied (follow-up suppress)

From `main.py` recovery path / audit matrix row 3:

```text
[LIFECYCLE DECISION] behavior=customer_replied decision=HANDOFF action=handoff_continuation
CartRecoveryLog.status=skipped_followup_customer_replied
```

**Canonical:** `replied` — «تفاعل العميل مع الرسالة — لن نرسل متابعة تلقائية الآن»

**Shadow note:** intelligence may still say `returned` if `returned=True` is passed with `replied=True` (old return-before-reply) → expect `[LIFECYCLE TRUTH MISMATCH] legacy_canonical=returned canonical_canonical=replied`.

---

## Scenario D — Returned to site (anti-spam)

Audit row 1 / `returned_to_site` durable log:

```text
[LIFECYCLE DECISION] behavior=returned_to_site decision=STOP action=no_send
CartRecoveryLog.status=returned_to_site
```

**Canonical:** `returned` — «عاد العميل — لن نزعجه حالياً»

---

## Scenario E — Delay not elapsed

Audit row 7:

```text
[LIFECYCLE DECISION] behavior=delay_waiting decision=WAIT action=wait_schedule
[DELAY BLOCKED] skipping send
CartRecoveryLog.status=skipped_delay_gate
```

**Canonical:** `waiting` — «بانتظار الوقت المناسب»

---

## Scenario F — WhatsApp failed

From `CartRecoveryLog` inventory:

```text
CartRecoveryLog.status=whatsapp_failed
```

**Canonical:** `failed` (when no purchase/reply/return)

---

## Scenario G — VIP manual

```text
CartRecoveryLog.status=vip_manual_handling
```

**Canonical:** `vip_manual` — «يتم التعامل مع هذه السلة يدوياً»

---

## Scenario H — Schedule cancelled after purchase stop

`RecoverySchedule.status=cancelled`, `last_error` contains `purchase_truth_stop`:

**Canonical:** `cancelled` if purchase tier not already matched; usually absorbed by `purchased` when truth row exists.

---

## Operator grep (shadow)

```text
[LIFECYCLE TRUTH MISMATCH]
[LIFECYCLE DECISION]
[PURCHASE TRUTH]
[PURCHASE LIFECYCLE CLOSED]
```
