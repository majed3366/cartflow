# CartFlow Session Truth Audit v1

**Date (UTC):** 2026-05-23  
**Scope:** Read-only audit of in-process recovery session flags in `main.py`.  
**Related:** `docs/cartflow_lifecycle_alias_map.md`, `docs/cartflow_lifecycle_truth_audit_v1.md`

**Flags under review:**

```text
_session_recovery_sent: dict[str, bool] = {}
_session_recovery_converted: dict[str, bool] = {}
```

Declared: `main.py` L2247–2248 (comment L2241: per `recovery_key`, per worker process).

---

## 1. Executive answers

| Question | Answer (evidence-based) |
|----------|-------------------------|
| **1. Cache only or decision source?** | **Both.** They are an in-process cache **and** a live decision source on hot paths—not a read-through cache that always falls back to DB. |
| **2. Lost on restart?** | **Yes** — dicts are module globals; empty after process restart. |
| **3. Rebuild path?** | **Partial.** See §4 — purchase has durable `purchase_truth_records`; send/converted memory is **not** automatically rehydrated into these dicts on startup. |
| **4. Risk** | **MEDIUM–HIGH** (single process: **MEDIUM**; multi-worker / restart: **HIGH**). |

---

## 2. Flag definitions

### 2.1 `_session_recovery_converted`

| Property | Detail |
|----------|--------|
| **Type** | `dict[str, bool]` keyed by `recovery_key` (`store_slug:session_id`) |
| **Reader** | `_is_user_converted(recovery_key)` → `bool(_session_recovery_converted.get(recovery_key))` (`main.py` L5232–5234) |
| **Writers** | `_mark_user_converted_for_payload`, `_mark_session_converted` (fallback after failed ingest), `cartflow_purchase_truth._mark_session_converted`, `purchase_lifecycle_closure._sync_main_session_terminal_flags` (`main.py` L5248–5272; `purchase_lifecycle_closure.py` L147–149) |
| **Lock** | `_recovery_session_lock` (`threading.RLock`, L2261) |

**Important:** Successful conversion paths call `ingest_purchase_truth_payload` first, which persists DB **and** sets this dict via `cartflow_purchase_truth.record_purchase` → `_mark_session_converted`.

### 2.2 `_session_recovery_sent`

| Property | Detail |
|----------|--------|
| **Type** | `dict[str, bool]` keyed by `recovery_key` |
| **Reader** | `_session_recovery_sent.get(recovery_key)` before scheduling (`main.py` L8540–8555) |
| **Writers** | After successful send completion (`main.py` L7913, L7984), VIP handoff (`L5228`), other send paths (`L5066`, `L5129`); also set with converted in `_sync_main_session_terminal_flags` (`purchase_lifecycle_closure.py` L149) |
| **Lock** | `_recovery_session_lock` |

**Not read by** `_is_user_converted` or `has_purchase`.

---

## 3. Question 1 — Cache only or decision source?

### Verdict: **Decision source (in-process), not DB-backed cache**

Evidence that code **branches on these dicts directly**:

| Behavior | Mechanism | Evidence |
|----------|-----------|----------|
| Skip re-schedule when “already sent” | `if _session_recovery_sent.get(recovery_key):` → `recovery_state: "sent"` | `main.py` L8540–8555 |
| Stop recovery sequence (purchase) | `if _is_user_converted(recovery_key):` → log `stopped_converted` | `main.py` L6796–6817, L7301+, L7891+ |
| Lifecycle intelligence observe | `purchased=bool(_is_user_converted(recovery_key))` | `main.py` L7157, L7208, L7564 |
| Purchase lifecycle closed check | `is_purchase_lifecycle_closed` → `_closed_keys` **or** `_is_user_converted` | `purchase_lifecycle_closure.py` L102–112 |
| Resume safety (durable schedule) | `if _is_user_converted(rk): return False, "purchase_completed"` | `recovery_restart_survival.py` L1265–1278 |
| WhatsApp queue | `_is_user_converted(key)` | `whatsapp_queue.py` L92–94 |
| Platform gateway | `_is_user_converted(rk)` | `platform_integration_gateway.py` L247–253 |

**Durable parallel (purchase only):**

| Mechanism | Reads DB? | Evidence |
|-----------|-----------|----------|
| `stop_if_purchased` → `has_purchase` | **Yes** (`purchase_truth_records` + memory mirror) | `cartflow_purchase_truth.py` L169–188, `main.py` L6548–6555 |
| `_is_user_converted` | **No** — memory only | `main.py` L5232–5234 |

So: **purchase stop is dual-path** — durable truth via `has_purchase` at sequence wake; many other gates still use `_is_user_converted` only.

**Attribution** uses memory as hint: `purchase_attribution_v1` reads `_session_recovery_sent.get(rk)` (`L651–654`) but also DB/logs elsewhere in same module.

---

## 4. Question 2 — Lost on restart?

### Verdict: **Yes**

- Dicts are initialized empty at import (`main.py` L2247–2248).
- No startup hook rehydrates them from `CartRecoveryLog` or `purchase_truth_records` (grep: no assignment to `_session_recovery_converted` except writers/tests).
- Tests explicitly `.clear()` both dicts in teardown (`test_recovery_isolation.py`, `test_purchase_truth_lifecycle_v1.py`, etc.).

---

## 5. Question 3 — Rebuild paths (after restart)

| Truth | Rebuild into session dict? | Alternative durable / log path |
|-------|----------------------------|--------------------------------|
| **Purchased** | **No** auto-rehydrate into `_session_recovery_converted` | **`purchase_truth_records`** via `has_purchase()` / `stop_if_purchased()` (`cartflow_purchase_truth`); `CartRecoveryLog.status=stopped_converted`; `ingest_purchase_truth_payload` on new conversion event |
| **Purchase lifecycle closed** | **No** — `_closed_keys` also memory (`purchase_lifecycle_closure.py` L23–24) | Same as above + `stop_if_purchased` at wake |
| **Sent** | **No** auto-rehydrate into `_session_recovery_sent` | **`_cart_recovery_log_has_successful_send_for_step`** queries `CartRecoveryLog` for `mock_sent`/`sent_real` (`main.py` L3430–3453); used in `evaluate_resume_safety` L1286–1289 |
| **Schedule claim** | **No** — `_session_recovery_started` also memory (`_try_claim_recovery_session` L5759–5767) | `RecoverySchedule` rows + duplicate guards |

### Gap (documented, not fixed)

After restart, **`_is_user_converted(rk)` is false** even when `purchase_truth_records` has a row, until:

- A new conversion/purchase ingest runs, or
- Tests/dev code set the dict manually.

**Mitigation already in production path:** `_run_recovery_sequence_after_cart_abandoned_impl` calls **`stop_if_purchased` first** (DB-backed) before `block_recovery_if_purchase_lifecycle_closed` (memory-heavy) — `main.py` L6547–6568.

**Remaining gap:** `evaluate_resume_safety` checks `_is_user_converted` **before** `has_purchase` — `recovery_restart_survival.py` L1265 — so durable schedule resume may not see purchase until something sets memory or another layer blocks send.

---

## 6. Question 4 — Who uses each flag?

### `_session_recovery_converted`

| Consumer | Role |
|----------|------|
| `_is_user_converted` | Central boolean for “purchase completed” in recovery sequence |
| `purchase_lifecycle_closure.is_purchase_lifecycle_closed` | Terminal closure check (with `_closed_keys`) |
| `lifecycle_intelligence` observe hooks | `purchased=True` when converted |
| `recovery_restart_survival.evaluate_resume_safety` | Block resume with `purchase_completed` |
| `whatsapp_queue` | Block send when converted |
| `platform_integration_gateway` | Skip routing when converted |
| `cartflow_purchase_truth._mark_session_converted` | Writer after durable record |

### `_session_recovery_sent`

| Consumer | Role |
|----------|------|
| Pre-schedule cart abandon handler | If set → skip schedule, API `recovery_state=sent` (`main.py` L8541) |
| Post-send paths | Set `True` after successful WhatsApp recovery message |
| `purchase_lifecycle_closure._sync_main_session_terminal_flags` | Also sets sent when purchase closes |
| `purchase_attribution_v1` | `memory_sent` hint (not sole source) |

### Related session dicts (context, not in scope but same risk class)

`main.py` L2242–2257 also defines: `_session_recovery_started`, `_session_recovery_logged`, `_session_recovery_returned`, `_session_recovery_send_count`, multi-slot keys, etc. Same process-local semantics.

---

## 7. Risk assessment

### `_session_recovery_converted` — **MEDIUM** (single worker) / **HIGH** (restart / multi-worker)

| Factor | Level | Rationale |
|--------|-------|-----------|
| Purchase stop without memory | **LOW** on wake path | `stop_if_purchased` uses DB (`cartflow_purchase_truth`) |
| Gates using only `_is_user_converted` | **MEDIUM** | False negative after restart until re-ingest |
| Multi-worker | **HIGH** | Each worker has separate dict; `cartflow_queue_readiness.py` L183–186 documents this |
| Operator confusion | **MEDIUM** | Purchase truth logs vs empty converted flag |

### `_session_recovery_sent` — **MEDIUM** (single worker) / **HIGH** (restart)

| Factor | Level | Rationale |
|--------|-------|-----------|
| Pre-schedule check L8541 | **HIGH** on restart | Memory false → may allow re-schedule despite `mock_sent` in DB |
| Send dedup in sequence | **LOWER** | `_cart_recovery_log_has_successful_send_for_step` used in several gates |
| Multi-worker | **HIGH** | Same as converted |

### Combined operational risk: **MEDIUM–HIGH**

Documented prior art: `services/cartflow_queue_readiness.py` L183–186 — *"In-memory session flags … are process-local; multiple workers need DB-backed or distributed claims."*

---

## 8. Recommendations (future Lifecycle Truth — docs only)

1. Treat **`purchase_truth_records`** as authoritative for `purchased`; treat `_session_recovery_converted` as **accelerator**, not source of truth.
2. Treat **`CartRecoveryLog` (`mock_sent`/`sent_real`)** as authoritative for `sent`; treat `_session_recovery_sent` as **schedule fast-path only**.
3. On read, prefer: `has_purchase(rk) OR _is_user_converted(rk)` and `log_has_sent OR _session_recovery_sent` (future unified helper — **not implemented in v1**).
4. Rehydrate session dicts on startup from DB **only if** product requires zero false negatives after deploy restart.

---

## 9. Evidence index (grep anchors)

```text
main.py                          L2241–2248  declarations
main.py                          L5232–5274  converted read/write
main.py                          L8540–8555  sent read (schedule)
main.py                          L6547–6555  stop_if_purchased (DB) before closure
purchase_lifecycle_closure.py    L102–149   closure ↔ converted/sent
cartflow_purchase_truth.py       L213–218   writer converted
recovery_restart_survival.py     L1265–1289 resume safety
cartflow_queue_readiness.py      L183–186   multi-worker note
tests/operational/diagnostics.py L28–32     dict lengths (ops)
```

---

## 10. Verification checklist

- [ ] Confirm deploy topology (single uvicorn vs multiple workers).
- [ ] After restart + existing `purchase_truth_records` row, spot-check: `stop_if_purchased` vs `_is_user_converted`.
- [ ] After restart + existing `mock_sent` log, spot-check: re-abandon scheduling vs `_cart_recovery_log_has_successful_send_for_step`.

**No code was changed in this audit.**
