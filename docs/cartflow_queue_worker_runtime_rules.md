# CartFlow — Queue / Worker Runtime Rules v1

**Status:** Operational guardrails (env + logs). No recovery queue implementation yet.  
**Related:** `docs/cartflow_queue_worker_maturity_audit_v1.md`, `services/recovery_scheduler_guardrails.py`

---

## Rule: one recovery scheduler owner per database

Until a real job queue with distributed lease/ack exists:

> **Only ONE process** should own recovery **resume scan** and **future-due re-arm** on startup.

All other API replicas must **not** run the startup resume scan.

---

## Environment variable

| Variable | Scheduler owner | API replicas (horizontal scale) |
|----------|-----------------|----------------------------------|
| `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` | **`1`** or unset (default) | **`0`** |

### Values

| Value | Resume scan on startup |
|-------|-------------------------|
| Unset | **Enabled** (`reason=default`) — safe for current single-worker production |
| `1`, `true`, `yes`, `on` | **Enabled** |
| `0`, `false`, `no`, `off` | **Disabled** |

### Startup logs (every process)

```text
[RECOVERY SCHEDULER OWNER]
enabled=true|false
reason=default|env
CARTFLOW_RECOVERY_RESUME_ON_STARTUP=(unset)|<value>
```

When **enabled**:

```text
[RECOVERY WORKER MODE]
mode=single_scheduler_expected
warning=do_not_enable_on_multiple_api_workers
```

Warnings do **not** block startup — they surface unsafe multi-worker configuration.

---

## Deployment patterns

### Single server / one Uvicorn worker (today)

- Leave env **unset** or set `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`.
- One process runs resume scan + in-process `asyncio` delay tasks.
- **No behavior change** from guardrails v1.

### Multiple Uvicorn workers on one host (unsafe without split)

- **Wrong:** four workers, all with resume enabled → four startup scans, duplicate re-arm attempts, wasted claim races.
- **Right:** one worker with `=1`, other workers with `=0`.
- Or run **one** dedicated CartFlow instance as scheduler owner and scale HTTP elsewhere with `=0`.

### Future dedicated scheduler service

- Scheduler service: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`
- Stateless API fleet: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`
- Optional: `CARTFLOW_DB_DUE_SCANNER_ENABLED=true` on **scheduler only** (see `recovery_db_due_scanner_loop.py`)

---

## What this does **not** fix

- In-memory `_try_claim_recovery_session` remains per-process — guardrails only address **startup resume scan** ownership.
- `asyncio.sleep` delay tasks still run on the process that handled `cart_abandoned`.
- DB claim + WhatsApp idempotency still provide last-line duplicate-send protection.

---

## Scaling misconception

**More Uvicorn workers ≠ more recovery capacity.**

Extra workers increase HTTP throughput but can **duplicate** recovery scheduling work unless resume ownership is split as above.

For load targets (100+ stores, 1000+ due rows), plan a **dedicated queue/worker** phase — see maturity audit recommended priorities.

---

## Verification

```bash
python -m pytest tests/test_recovery_scheduler_guardrails_v1.py -q
```

After deploy, confirm logs on boot:

- Owner process: `[RECOVERY SCHEDULER OWNER] enabled=true`
- API replicas: `enabled=false` and no `[RECOVERY RESUME SCAN]` from startup scan
