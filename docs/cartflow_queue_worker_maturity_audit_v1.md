# CartFlow Queue / Worker Maturity Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only operational audit — delayed recovery under restart, duplicate dispatch, multi-worker, and load.  
**Commit message:** `docs: add queue worker maturity audit v1`  
**Related:** `docs/cartflow_queue_worker_readiness.md`, `docs/audit_queue_worker_maturity_v1.md`, `docs/cartflow_session_truth_audit.md`

**No runtime changes** in this deliverable. Evidence is from code paths and existing tests (`tests/test_recovery_restart_survival.py`, `tests/test_recovery_execution_boundary.py`, `tests/test_queue_worker_maturity_audit_v1.py`, `tests/test_cartflow_queue_readiness_verification.py`).

---

## Executive answer

> **Will recovery remain correct under multiple workers, restarts, and higher load?**

| Deployment shape | Verdict |
|------------------|---------|
| **1 process**, restart OK, moderate delayed volume | **Likely safe** — durable `RecoverySchedule` + DB claim + WA idempotency + purchase stop + stale `running` repair cover the main failure modes. |
| **Process restart** (same host, new PID) | **Likely safe** — resume scan + future rearm + session truth / purchase truth DB fallbacks; in-memory guards re-built or bypassed via DB. |
| **2+ Uvicorn/API workers** on same DB without ops discipline | **Unsafe beyond ~1 active scheduler** — pre-delay guards (`_try_claim_recovery_session`, `_session_recovery_started`) are **process-local**; each worker runs **startup resume scan** by default; dual asyncio delay + DB due scanner can race until claim/idempotency wins. |
| **100 stores × ~10 concurrent due recoveries** (single worker) | **Likely safe** with tuning (`max_dispatch=25`, scanner interval, `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS`). |
| **1000+ due rows / minute** without a dedicated queue worker | **Unsafe** — no distributed job lease, no back-pressure queue; asyncio tasks + HTTP process CPU bound. |

**Practical line:** Current system is **production-viable for single-worker (or effectively single-scheduler) CartFlow** with the reliability stack shipped through session truth + purchase truth + restart survival. It is **not yet a horizontally scaled multi-worker recovery engine** without configuration and a future dedicated worker/queue.

---

## Part 1 — Execution ownership map

| Component | Owner module / entry | Claim / coordination | Idempotency | Risk |
|-----------|----------------------|----------------------|-------------|------|
| **RecoverySchedule (durable row)** | `models.RecoverySchedule`; `services/recovery_restart_survival.persist_recovery_schedule_durable` | Natural key: `recovery_key` + `step` + `multi_slot_index` (lookup in `_schedule_row_lookup`, L344–368) | Upsert/update row; terminal set `_TERMINAL` (L37–49) blocks re-claim | **Low** for persistence; **Medium** if two writers race before claim |
| **Delayed execution (live path)** | `services/recovery_delay_dispatcher.dispatch_recovery_schedule` → `await asyncio.sleep` → `execute_recovery_schedule` | In-process only until boundary | Same row: `claim_recovery_schedule_execution` before send path | **Medium** — lost on crash until resume/scan |
| **Delayed execution (DB boundary)** | `services/recovery_execution_boundary.execute_recovery_schedule` | `claim_recovery_schedule_execution` (`scheduled`→`running`, SQL update count=1, L456–483) | Terminal skip if already terminal; stale repair at entry (L99–116) | **Low** per row |
| **Restart resume (due)** | `recovery_restart_survival.run_recovery_resume_scan_async` → `resume_one_schedule` | Claim then `asyncio.create_task(execute_recovery_schedule)` (L1344–1366) | `evaluate_resume_safety` + claim | **Low** with claim |
| **Restart rearm (future due)** | `rearm_one_future_scheduled_recovery` + `spawn_recovery_schedule_dispatch` | Per-process `_future_rearm_spawned` (L111–112, L168–180) | One rearm per PID per `schedule_id` | **Medium** multi-worker — each PID may rearm |
| **Startup orchestration** | `main._startup_whatsapp_queue` (L861–911): resume scan + optional DB due loop + WA queue worker | Env: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` (default on, L1377–1381) | `max_dispatch=25` per startup | **High** if N workers all scan |
| **DB due scanner (manual/loop)** | `services/recovery_db_due_scanner.scan_due_recovery_schedules` | Same claim via `execute_recovery_schedule`; optional loop `recovery_db_due_scanner_loop` (`CARTFLOW_DB_DUE_SCANNER_ENABLED`, default **false**) | Stale repair first; `evaluate_resume_safety` | **Medium** — third path to due rows |
| **Schedule claim (DB)** | `claim_recovery_schedule_execution` | Atomic `UPDATE … WHERE status='scheduled'` | `claim_race_lost`, `already_running`, `already_terminal` (L415–483) | **Low** |
| **Session schedule claim (memory)** | `main._try_claim_recovery_session` (L5777–5784) | `_session_recovery_started[recovery_key]` under `_recovery_session_lock` | **Process-only** — no cross-worker | **High** multi-worker |
| **Duplicate guard (memory)** | `services/cartflow_duplicate_guard` | Signatures + counters; `note_recovery_schedule_duplicate` | In-process TTL maps | **High** cross-process |
| **Inflight send TTL** | `try_begin_outbound_whatsapp_inflight` (default **6s** TTL, L210–260) | `recovery_key:step:{n}` monotonic expiry | Blocks overlapping coroutines **same process** | **PARTIAL** |
| **WA send idempotency (DB)** | `services/recovery_whatsapp_idempotency` | Query `CartRecoveryLog` for `mock_sent`/`sent_real`/`queued` per step | Survives restart/worker (module docstring L2) | **Low** |
| **Resume safety** | `evaluate_resume_safety` (L1239–1317) | No claim — preflight | Blocks: purchase (`_is_user_converted`), return, `already_sent` log, template disabled | **Low** |
| **Stale `running` repair** | `repair_stale_running_recovery_schedules` (default **600s**, L55, L575–579) | Age on `updated_at`; evidence from logs | `failed_resume_stale` or `completed` / `skipped_duplicate` (L752–809) | **Low** ops tuning |
| **Purchase stop** | `cartflow_purchase_truth.stop_if_purchased` | Cancels schedules; durable `purchase_truth_records` | Session truth hardening reads DB on miss | **Low** |
| **Sent truth (schedule skip)** | `cartflow_session_truth.has_sent_truth` at schedule time (`main` ~L8541) | DB log fallback | Complements memory `_session_recovery_sent` | **Low** post-hardening |
| **WhatsApp queue worker** | `services/whatsapp_queue` + `start_whatsapp_queue_worker` at startup | **Separate** from normal recovery delay path | Retry/backoff for queued WA jobs — not the cart-abandon asyncio chain | N/A for recovery delay |

---

## Part 2 — Multi-worker reality audit

Assume **worker A** and **worker B** share one database (typical multi-Uvicorn).

| Question | Safeguard | YES / PARTIAL / NO | Evidence |
|----------|-----------|-------------------|----------|
| **Can both send?** | DB claim + WA idempotency + inflight TTL | **PARTIAL** | Second `execute_recovery_schedule` gets `already_running` or `claim_race_lost` (L427–483). Second provider call blocked by `check_whatsapp_recovery_send_idempotency` if first log row exists. **Gap:** two workers can each accept `cart_abandoned` and pass `_try_claim_recovery_session` on different processes (L5777–5784), creating **two asyncio delay tasks** for same session until schedule/claim converges. |
| **Can both resume?** | Startup `run_recovery_resume_scan_async` on **each** worker | **PARTIAL** | Both scan due rows (L1394–1425). First claim wins; second `resume_one_schedule` → `duplicate_resume_claim` (L1352–1358). **Wasted work**, not necessarily double send. |
| **Can both mark terminal?** | `finalize_recovery_schedule_durable` + `_TERMINAL` + `_PROTECTED_TERMINAL_NO_DOWNGRADE` | **PARTIAL** | Terminal rows not re-claimed (L416–425). Concurrent finalize possible but status should converge to terminal. |
| **Can both bypass duplicate guard?** | Memory guard vs DB | **YES** (cross-process) | `cartflow_duplicate_guard` and `_session_recovery_started` are **not** shared (module L25–28, `main` L5777). `cartflow_queue_readiness.py` L183–186 documents multi-worker memory risk. |

**Multi-worker ops minimum (not code — deployment):**

- Run **one** recovery scheduler role per DB (single worker **or** `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` on all but one instance).
- Enable `CARTFLOW_DB_DUE_SCANNER_ENABLED` on **at most one** instance if used.
- Do **not** scale HTTP workers for recovery volume without a future dedicated queue consumer.

---

## Part 3 — Queue absence audit

There is **no Redis/Celery/RQ recovery job queue**. Current behavior:

| Mechanism | Role | Limitation |
|-----------|------|------------|
| **`asyncio.sleep`** | Holds delay until `due_at` in live process (`recovery_delay_dispatcher`) | Dies on process exit; relies on DB row + resume/rearm |
| **`RecoverySchedule` rows** | Durable `due_at`, `status`, `context_json` | Not a queue — polled by startup scan / optional DB scanner |
| **Restart scans** | `run_recovery_resume_scan_async` + `repair_stale_running_recovery_schedules` | Cap `max_dispatch=25`; not full table scan for all due at once |
| **Memory locks** | `_recovery_session_lock`, `_session_recovery_started`, duplicate guard inflight | **Single process** |
| **DB rows** | `recovery_schedules`, `cart_recovery_logs`, `purchase_truth_records` | Coordination via claim + log idempotency, not lease queue |
| **Duplicate guards** | HTTP burst throttle, schedule duplicate notes | Cross-worker weak |

**Implication:** Recovery is **“durable schedule + in-process timer + periodic poll”**, not **“at-least-once job queue with worker lease”**.

---

## Part 4 — Failure scenarios

| Scenario | Protection | Status | Evidence |
|----------|------------|--------|----------|
| **Restart before `due_at`** | Future rearm preserves `due_at`; no early execute | **YES** | `rearm_one_future_scheduled_recovery` L124–166; tests `test_future_scheduled_rearms_dispatcher_without_early_execute` |
| **Restart after `due_at`** | Resume scan → claim → execute | **YES** | `resume_one_schedule` L1320–1368; `test_scenario_a_due_after_restart_discoverable` |
| **Restart during send** | WA idempotency + inflight TTL; stale repair if stuck `running` | **PARTIAL** | Idempotency before provider; stale repair after 600s with log evidence |
| **Worker crash after send** | `CartRecoveryLog` + schedule finalize → `completed` | **YES** | `map_cart_recovery_log_status_to_schedule_terminal` L505–520; stale repair promotes send evidence |
| **Provider timeout** | `whatsapp_failed` log; schedule terminal; queue retries on **separate** WA queue path | **PARTIAL** | Recovery inline path logs failure; retry policy depends on path |
| **Duplicate wake** (abandon burst) | Memory claim + cart event throttle + DB claim | **PARTIAL** | `_try_claim_recovery_session`; `should_process_cart_event_burst`; `claim_race_lost` |
| **DB slow** | SQLAlchemy errors → rollback; claim returns `claim_db_error` | **PARTIAL** | L494–502; may delay dispatch, not silently duplicate |
| **Schedule stuck `running`** | `repair_stale_running_recovery_schedules` on startup scan / due scanner | **YES** | L813–876; `CARTFLOW_RECOVERY_RUNNING_STALE_SECONDS` |
| **Multi-worker startup** | Each runs resume scan (default on) | **NO** (without ops) | `main` L884–886 every worker |
| **Partial send failures** | Failed status; idempotency does not block retry on `whatsapp_failed` | **PARTIAL** | `_IDEMPOTENCY_BLOCK_STATUSES` excludes failures (`recovery_whatsapp_idempotency` L15–20) |

---

## Part 5 — Existing safeguards inventory (production today)

| Safeguard | What it protects | Module / hook |
|-----------|------------------|---------------|
| **Restart survival** | Lost asyncio task after crash | `recovery_restart_survival` |
| **DB claim `scheduled→running`** | Double execute on same schedule row | `claim_recovery_schedule_execution` |
| **Execution boundary** | Single entry for worker-ready execute | `recovery_execution_boundary.execute_recovery_schedule` |
| **Resume safety** | Resume only if purchase/return/sent/template gates pass | `evaluate_resume_safety` |
| **Stale running repair** | Orphan `running` rows | `repair_stale_running_recovery_schedules` |
| **Purchase stop** | Post-purchase recovery halt | `cartflow_purchase_truth.stop_if_purchased` |
| **Purchase / session truth** | Restart/multi-worker conversion & sent hints | `cartflow_session_truth`, `has_purchase` |
| **WA idempotency** | Double provider send per step | `recovery_whatsapp_idempotency` |
| **Duplicate guard** | In-process spam / inflight overlap | `cartflow_duplicate_guard` |
| **Terminal schedule states** | Re-run blocked | `_TERMINAL` in `recovery_restart_survival` |
| **Lifecycle shadow** | Observability only | `cartflow_lifecycle_truth` (no execution change) |
| **DB due scanner (optional)** | Picks up orphan `scheduled` past `due_at` | `recovery_db_due_scanner` (env-gated) |

---

## Part 6 — Risks, gaps, priorities

### Active protections (strengths)

1. **Durable schedule + atomic claim** — strongest multi-instance primitive today.  
2. **Evidence-based stale repair** — reduces infinite `running`.  
3. **DB-backed send idempotency** — last-line defense against double WhatsApp.  
4. **Purchase truth + session truth** — stop/resume decisions survive restart.  

### Gaps (ordered)

| Priority | Gap | Impact |
|----------|-----|--------|
| **P1** | Pre-delay **memory** claims (`_try_claim_recovery_session`, sent/started dicts) | Duplicate **tasks** across workers before DB row exists |
| **P1** | **Every** API worker runs startup resume scan by default | Duplicate dispatch attempts; load amplification |
| **P2** | Dual driver: asyncio sleep **and** DB scanner **and** resume | Race until claim; ops complexity |
| **P2** | No distributed lease / queue ack | Cannot safely scale to many workers |
| **P3** | `max_dispatch=25` caps | Large due backlogs drain slowly |
| **P3** | Phone cache `recovery_session_phone` process-local | Worker B may miss phone until DB resolve |

### Recommended future priorities (no implementation in v1)

1. **Dedicated recovery scheduler process** (or single leader election) — one resume/due consumer per DB.  
2. **Real queue** (Redis stream / Celery) with visibility timeout and ack after `execute_recovery_schedule` success.  
3. **Move pre-delay claim to DB** (e.g. insert `scheduled` before `create_task`, reject duplicate upsert).  
4. **Ops defaults:** document `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0` for horizontal API replicas.  
5. **Load test:** N due rows, M workers, measure duplicate `[WA IDEMPOTENCY HIT]` and `claim_race_lost` rates.

---

## Verification references

```bash
python -m pytest tests/test_queue_worker_maturity_audit_v1.py tests/test_recovery_restart_survival.py tests/test_cartflow_queue_readiness_verification.py tests/test_recovery_execution_boundary.py -q
```

Manual ops grep:

```text
[RECOVERY CLAIMED]
[RECOVERY CLAIM SKIPPED]
[WA IDEMPOTENCY HIT]
[RECOVERY STALE DETECTED]
[PURCHASE STOP]
[CARTFLOW DUPLICATE]
```

---

## Document control

| Item | Value |
|------|--------|
| Runtime changes | **None** |
| New endpoints / tables | **None** |
| Authoritative execution entry (future workers) | `execute_recovery_schedule(schedule_id=…)` |
