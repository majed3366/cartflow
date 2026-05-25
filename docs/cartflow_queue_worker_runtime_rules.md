# CartFlow — Queue / Worker Runtime Rules v1

**Status:** Operational guardrails (env + logs + health). No recovery queue implementation yet.  
**Related:** `docs/cartflow_queue_worker_maturity_audit_v1.md`, `services/recovery_scheduler_guardrails.py`, `GET /dev/recovery-health`

---

## Rule: only ONE process may own recovery resume scheduling

Until a real job queue with distributed lease/ack exists:

> **Exactly one** CartFlow process per database should run the startup **resume scan** and **future-due re-arm**.

All horizontal API replicas must set resume to **disabled**.

---

## Environment variable

| Role | `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` |
|------|--------------------------------------|
| **Scheduler owner** (single dedicated process or lone server) | **`1`** or **unset** (default = enabled) |
| **API replicas** (stateless horizontal scale) | **`0`** |

### Values

| Value | Resume scan on startup |
|-------|-------------------------|
| Unset | **Enabled** (`reason=default`) — safe for current single-worker production |
| `1`, `true`, `yes`, `on` | **Enabled** |
| `0`, `false`, `no`, `off` | **Disabled** — scan skipped (`reason=resume_on_startup_disabled`) |

---

## Startup logs (every process)

```text
[RECOVERY SCHEDULER OWNER]
enabled=true|false
reason=default|env
process_id=<pid>
instance=<hostname or CARTFLOW_INSTANCE_ID>
CARTFLOW_RECOVERY_RESUME_ON_STARTUP=(unset)|<value>
```

When **enabled** (scheduler owner):

```text
[RECOVERY WORKER MODE]
single_scheduler_expected=true
```

When **enabled** and the fleet looks multi-worker or production-scale:

```text
[RECOVERY SCHEDULER RISK]
risk=multi_worker_resume
action=set_CARTFLOW_RECOVERY_RESUME_ON_STARTUP_0_on_api_replicas
detail=WEB_CONCURRENCY=4
```

Warnings do **not** block startup — they surface unsafe configuration.

### Multi-worker signals (heuristic)

- `WEB_CONCURRENCY` > 1
- `UVICORN_WORKERS` > 1
- `CARTFLOW_UVICORN_WORKERS` > 1
- `WORKERS` > 1

---

## Deployment patterns

### Single server / one Uvicorn worker (today)

- Leave env **unset** or `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`.
- One process runs resume scan + in-process `asyncio` delay tasks.
- **No recovery send behavior change** from guardrails v1.

### Multiple Uvicorn workers or API replicas (required split)

- **Wrong:** four workers, all with resume enabled → four startup scans, duplicate re-arm attempts, wasted claim races.
- **Right:**
  - **One** scheduler owner: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1` (or unset)
  - **All other replicas:** `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`

Example (conceptual):

| Process | Env |
|---------|-----|
| `cartflow-scheduler` (1 instance) | unset or `1` |
| `cartflow-api` replica 1–N | `0` |

### Future dedicated scheduler service

- Scheduler service: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`
- Stateless API fleet: `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=0`
- Optional: `CARTFLOW_DB_DUE_SCANNER_ENABLED=true` on **scheduler only** (`recovery_db_due_scanner_loop.py`)

---

## Health endpoint (no log access required)

`GET /dev/recovery-health` — allowed in production (`main._DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`).

Top-level fields for ops:

| Field | Meaning |
|-------|---------|
| `scheduler_owner_mode` | `owner` or `api_replica` |
| `resume_on_startup_enabled` | Same as env guardrail |
| `last_resume` | Last resume scan heartbeat (this process or fleet if shared DB) |
| `pending_due` | Count of `scheduled` rows with `due_at <= now` |
| `stuck_running` | `running` rows older than threshold |
| `scheduler_detail` | Full owner config + `process_id` / `instance` / risk hints |

---

## What this does **not** fix

- In-memory `_try_claim_recovery_session` remains per-process — guardrails only address **startup resume scan** ownership.
- `asyncio.sleep` delay tasks still run on the process that handled `cart_abandoned`.
- DB claim + WhatsApp idempotency still provide last-line duplicate-send protection.

---

## Scaling misconception

**More Uvicorn workers ≠ more recovery capacity.**

Extra workers increase HTTP throughput but can **duplicate** recovery scheduling work unless resume ownership is split as above.

---

## Verification

```bash
python -m pytest tests/test_recovery_scheduler_guardrails_v1.py -q
curl -sS https://<host>/dev/recovery-health
```

After deploy:

- **Owner** process: `[RECOVERY SCHEDULER OWNER] enabled=true`, `[RECOVERY WORKER MODE] single_scheduler_expected=true`
- **API replicas:** `enabled=false`, no startup `[RECOVERY RESUME SCAN]` dispatch
- Health: `scheduler_owner_mode` matches role per instance
