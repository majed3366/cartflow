# Operational Maturity v1 — Audit Report

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit of operational **detect → explain → alert → control → verify recovery** readiness.  
**Commit:** `audit: verify operational maturity v1`

No changes to lifecycle, queue, Purchase Truth, recovery execution, WhatsApp send, or widget.

**Companion docs:** `docs/cartflow_admin_operational_control.md`, `docs/cartflow_admin_operational_guidance.md`, `docs/cartflow_runtime_health.md`, `docs/admin_dashboard_human_understanding_validation.md`

---

## Control loop model

```text
detect  → explain → alert → control → verify recovery
   │         │        │        │            │
   │         │        │        │            └─ admin_verification_layer, dev /verify endpoints
   │         │        │        └─ read-only actions; /admin/control placeholder (no kill yet)
   │         │        └─ timeline, anomalies, risk emoji; /admin/alerts placeholder
   │         └─ risk_summary, impact, quick_answers, guidance
   └─ health buffers, runtime snapshot, per-store trust
```

---

## Operational capability matrix

| # | Capability | Exists? | Verified? | Gap? | PASS |
|---|------------|---------|-----------|------|------|
| 1 | **Health visibility** | Yes — `build_admin_operational_health_readonly`, `/admin/operational-health`, `build_runtime_health_snapshot` | `test_admin_operational_control`, `test_admin_operational_health`, audit tests | No single external APM export wired | **PASS** |
| 2 | **Alert visibility** | Partial — in-process anomalies + timeline; `/admin/alerts` **placeholder** | Anomaly counters + timeline in control v2 tests | No paging/Slack/email; VIP merchant alerts separate | **PARTIAL** |
| 3 | **Risk explanation** | Yes — `admin_risk_summary`, `admin_impact_layer`, `quick_answers` | `test_risk_detected_on_pool_timeout` | Arabic-only; capped store scan | **PASS** |
| 4 | **Recommended action** | Yes — `admin_actions_layer`, `derive_admin_operational_guidance`, actionable items on `/admin/operations` | Control v2 module tests | Actions are **navigation/guidance**, not one-click remediation | **PASS** (guidance) |
| 5 | **Verify fix** | Yes — `admin_verification_layer` (in-process recovery when issue clears) | `test_verification_after_issue_clears` | Process-local only; lost on full restart | **PARTIAL** |
| 6 | **Safe stop / kill switch** | Partial — recovery **gates** (return, purchase, delay); **no** admin kill API | Recovery logs `[RECOVERY AUTOMATION STOPPED]`; `/admin/control` stub | **No platform kill switch** in admin UI | **FAIL** (admin kill) / **PASS** (recovery gates) |
| 7 | **Manual retry** | Partial — dev verify: `GET /dev/recovery-restart-survival-verify?action=scan`, load tests | `test_dev_verify_endpoint_inspect`, restart survival tests | No authenticated “retry this session” in admin | **PARTIAL** |
| 8 | **Runtime status** | Yes — `/dev/production-readiness`, runtime health snapshot, DB pool card, scanner health | `test_cartflow_runtime_health`, ops health probe | Production route gated; not merchant-facing | **PASS** (ops) |
| 9 | **Store-level visibility** | Yes — `build_admin_operational_summary_readonly` trust buckets per store | `test_cartflow_admin_operational_summary` | Capped scan (`_MAX_STORES_TO_SCORE`); `/admin/stores` placeholder | **PARTIAL** |
| 10 | **Historical evidence** | Yes — ring buffers (cart-event, pool, bg errors), timeline, `CartRecoveryLog`, load-test snapshots on health page | Timeline + verification deque tests | Retention in-memory only (bounded deques) | **PARTIAL** |

**Automated audit:** `pytest tests/test_operational_maturity_audit_v1.py -q`

---

## Detect → explain → alert → control → verify (recovery)

| Stage | What works today | Evidence |
|-------|------------------|----------|
| **Detect** | Slow `cart-event`, pool timeout, bg task errors, anomaly symbols, platform category, per-store trust | `record_*` hooks, `emit_anomaly`, health page cards |
| **Explain** | Risk level emoji, problem_ar, why_ar, impact tier, quick_answers (healthy? failing? who? what to do?) | `admin_risk_summary`, `admin_impact_layer` |
| **Alert** | Timeline severity lines; risk_detected headline; structured logs opt-in (`CARTFLOW_STRUCTURED_HEALTH_LOG`) | `admin_operational_timeline`; not centralized alerts UI |
| **Control** | Read-only recommended actions + admin load tests (dry_run default); env flags (`CARTFLOW_RECOVERY_RESUME_ON_STARTUP`, etc.) | `POST /admin/ops/load-test/*`; no kill switch |
| **Verify recovery** | Verification layer when signals clear; dev recovery verify endpoints; restart survival inspect/scan | `admin_verification_layer`; `/dev/recovery-restart-survival-verify` |

---

## Final summary

| Capability | Expected | Observed | PASS / FAIL | Risk | Priority |
|------------|----------|----------|-------------|------|----------|
| Health visibility | Ops see system + recovery wiring health | Operational health page + runtime snapshot | **PASS** | Low | — |
| Alert visibility | Central alerts | Timeline + anomalies; alerts page stub | **PARTIAL** | Medium — ops may miss signals without visiting health page | P2 |
| Risk explanation | Plain-language risk | AR risk/impact/quick answers | **PASS** | Low | — |
| Recommended action | What to do next | Action layer + guidance (read-only links) | **PASS** | Low | — |
| Verify fix | Confirm issue cleared | In-process verification deque | **PARTIAL** | Medium — not durable across restart | P2 |
| Safe stop / kill switch | Emergency stop customer impact | Recovery anti-spam only; admin control stub | **FAIL** (admin) | **High** for incident response without SSH | **P1** |
| Manual retry | Re-run recovery safely | Dev scan + boundary execute | **PARTIAL** | Medium | P2 |
| Runtime status | Prod vs dev, deps, pool | production-readiness report | **PASS** (ops) | Low | — |
| Store-level visibility | Per-store readiness | Trust buckets in summary | **PARTIAL** | Medium — list UIs incomplete | P2 |
| Historical evidence | Audit trail | Logs + bounded buffers + DB logs | **PARTIAL** | Medium — no long-term metrics store | P2 |

---

## Gaps

### Closed gaps ✅

- Internal **operational health center** (`/admin/operational-health`) with v2 modules: risk, impact, actions, verification, timeline, revenue protection.
- **Platform + per-store** trust scoring (`build_admin_operational_summary_readonly`).
- **Runtime health** anomaly buffer and symbolic types (duplicate send, provider failure, etc.).
- **Detect** hooks on cart-event finish, pool timeout, background errors.
- **Explain** via quick_answers and Arabic operational copy.
- **Admin auth** for ops pages and load tests (`CARTFLOW_ADMIN_PASSWORD`).
- **Dev verification** family for recovery (restart survival, delay, duplicate, production-readiness).
- **Load / failure simulation** harnesses under `/admin/ops/load-test/*` (dry_run default).

### Remaining gaps 🟡

- **`/admin/control`** and **`/admin/alerts`** are placeholders (“قريباً”).
- **No external alerting** (PagerDuty, Slack, email) from operational summary.
- **Verification layer** is in-process; full process restart clears recovery history.
- **Historical evidence** bounded to ring buffers — not a metrics TSDB.
- **Store list / paused stores** admin routes not built.
- **Sentry/APM** documented as future consumer only.

### Dangerous gaps 🔴

- **No admin kill switch** — incidents require env/config/SSH or code deploy to stop customer-facing recovery at platform level.
- **Multi-process ops:** verification and anomaly buffers are **per process** — load-balanced API may show split brain on health page without sticky sessions or external store.
- **Dev routes in production** partially gated — ops must confirm `ENV` + `PRODUCTION_MODE` + `no_dev_in_production` before deploy (`/dev/production-readiness` checklist).

---

## Deploy & real verification

### Deploy checklist (ops)

| Step | Check | PASS if |
|------|-------|---------|
| 1 | `CARTFLOW_ADMIN_PASSWORD` set | Can log in to `/admin/operations` |
| 2 | `GET /dev/production-readiness` (or internal equivalent) | Critical env present; dev routes blocked in prod |
| 3 | Open `/admin/operational-health` | Hero verdict + component cards render |
| 4 | Trigger slow cart-event or pool stress in staging | Risk_detected or warning tier appears |
| 5 | Clear condition | Verification layer shows recovery (in same process) |
| 6 | `GET /dev/recovery-restart-survival-verify?action=inspect` | `recovery_schedules` persistence visible |
| 7 | Run `POST /admin/ops/load-test/failure-scenarios` (auth) | Summary on health page; no customer WA when dry_run=true |

### Overall PASS criteria

- Operator can answer within 60s on health page: **healthy?** **what failed?** **who affected?** **what to do?** **did it recover?**
- Recovery verify dev endpoints respond on staging.
- No requirement for kill switch PASS until `/admin/control` is implemented (documented **FAIL**).

### Overall FAIL criteria

- Health page errors blank for all modules.
- Pool/timeout signals never appear under known stress.
- Production deploy with default `SECRET_KEY` or missing `DATABASE_URL` per production-readiness.

---

## Code map

| Capability | Primary module / route |
|------------|-------------------------|
| Health + control v2 | `services/admin_operational_control/`, `services/admin_operational_health.py` |
| Platform summary | `services/cartflow_admin_operational_summary.py` |
| Guidance / actions | `services/cartflow_admin_operational_guidance.py`, `cartflow_admin_action_guidance.py` |
| Runtime anomalies | `services/cartflow_runtime_health.py` |
| Admin UI | `routes/admin_operations.py`, `templates/admin_operational_health.html` |
| Load / failure tests | `routes/admin_ops.py`, `services/admin_*_load_test.py` |
| Recovery verify | `main.py` `/dev/recovery-*-verify`, `/dev/recovery-restart-survival-verify` |
| Production gate | `services/cartflow_production_readiness.py`, `GET /dev/production-readiness` |

---

## Recommendations (future — out of scope)

1. Implement `/admin/control` kill switch (env-backed, audited, no schedule mutation).
2. Wire `build_admin_operational_control_readonly` to Slack/webhook on `risk_level >= 2`.
3. Persist verification recoveries + timeline to DB or Redis for multi-worker.
4. Complete `/admin/stores` with per-store drill-down from trust buckets.
5. Export health snapshot to Sentry/Datadog as optional consumer.
