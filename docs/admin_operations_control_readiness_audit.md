# Admin Operations Center — Control Readiness Audit

**Date (UTC):** 2026-06-01  
**Scope:** Read-only audit of operational signals vs. controllable actions. No behavior, UX, recovery, WhatsApp, onboarding, or Identity Contract changes.  
**Commit:** `ops: admin control readiness audit`

**Companion docs:** `docs/audit_operational_maturity_v1.md`, `docs/operational_control_v1.md`, `docs/cartflow_runtime_health.md`, `docs/cartflow_admin_support_diagnostics_v1.md`, `docs/cartflow_admin_operational_control.md`

---

## Executive summary

CartFlow already exposes **strong diagnostic visibility** through four admin surfaces and a **targeted pause/resume control plane** (`operational_control_v1`). Most signals are **observe-only** by design: they depend on in-process buffers, bounded store scans, or truth layers (Purchase Truth, lifecycle guards) that must not be overridden from admin UI.

**Before adding health scores, bulk repair, or merchant-facing controls**, the mature path is:

1. Promote **existing** pause gates (`/admin/control`) into ops-center workflows (links, not new logic).
2. Add **admin-authenticated wrappers** around proven internal repair paths (stale-running repair, resume scan) with **dry-run / inspect defaults**.
3. Keep lifecycle, cart rows, schedule deletion, and direct DB repair **admin-invisible forever**.

---

## SECTION A — Current operational visibility

### A.1 Admin surfaces

| Surface | Route | Auth | Role |
|---------|-------|------|------|
| Operations Center | `GET /admin/operations` (+ lazy `/section/investigation`, `/section/analytics`) | Admin session | Alerts, top risks, timeline, trends, store/recovery aggregates |
| Operational health | `GET /admin/operational-health` | Admin session | Risk/impact/actions/verification/timeline layers; issue cards |
| Operational control | `GET /admin/control`, `POST …/apply`, `POST …/resume` | Admin session | **Existing mutating pause gates** |
| Support diagnostics | `GET /admin/support-diagnostics/ui`, `GET /admin/support-diagnostics` | Admin session | Per-session/recovery_key investigation |
| DB due scanner API | `GET /api/admin/db-due-scanner-health` | Admin session | Scanner loop metrics card |
| Load / failure simulation | `POST /admin/ops/load-test/*` | Admin session | Synthetic traffic (default `dry_run_whatsapp=true`) |
| Public health | `GET /health`, `GET /health/scheduler` | None | LB probe; scheduler overdue/stale counts |
| Dev JSON (non-prod / allowlisted) | `/dev/admin-operational-summary`, `/dev/production-readiness`, `/dev/recovery-health`, `/dev/purchase-truth-*`, `/dev/lifecycle-truth-check`, `/dev/recovery-restart-survival-verify` | Dev gate | Deep probes for operators |

**Placeholders (visibility only, no signals):** `/admin/alerts`, `/admin/stores*`, `/admin/reports/*`, `/admin/system/*` → `admin_placeholder.html`.

**Merchant-facing (not admin):** `GET /dashboard/normal-carts/operations` embeds runtime health snapshot; dashboard build logs `[CARTFLOW DIAGNOSTIC] runtime_conflict`.

---

### A.2 Signal inventory by domain

#### Runtime anomalies (`cartflow_runtime_health.py`, in-process buffer ≤200)

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `duplicate_send_attempt` | `cartflow_duplicate_guard` | Anomaly buffer, degradation flags, optional `[CARTFLOW ANOMALY]` log | **Diagnostic Only** |
| `send_after_return` | Pre-send diag, duplicate guard | Same | **Diagnostic Only** |
| `send_after_conversion` | Pre-send diag | Same | **Diagnostic Only** |
| `identity_merge_blocked` | Duplicate guard, session consistency | `identity_conflict_detected`, trust degradation | **Diagnostic Only** |
| `missing_customer_phone` | Symbol defined | Buffer counts | **Diagnostic Only** |
| `provider_send_failure` | Send paths | WhatsApp card, `whatsapp_failure` issue | **Future Actionable** (pause WA exists; reconnect N/A) |
| `impossible_state_transition` | `cartflow_lifecycle_guard` | Lifecycle diagnostics, pressure flags | **Diagnostic Only** |
| `dashboard_payload_conflict` | Duplicate guard / observability | Dashboard pressure flag | **Diagnostic Only** |
| `duplicate_active_recovery` / `duplicate_behavioral_merge` | Duplicate guard | Guard counters | **Diagnostic Only** |

#### Duplicate prevention (`cartflow_duplicate_guard`)

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `duplicate_prevention_runtime_ok` | Inflight keys < 50k | Runtime health, production readiness, trust score | **Diagnostic Only** |
| `duplicate_send_blocked_recently` | Block in last 300s | `degradation_flags.duplicate_guard_pressure` | **Diagnostic Only** |
| Guard counters | In-process | `anomaly_visibility.duplicate_guard_counters` | **Diagnostic Only** |

#### Lifecycle consistency (`cartflow_lifecycle_guard`)

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `lifecycle_runtime_ok` | Invalid transitions bounded | Runtime health, store trust | **Diagnostic Only** |
| `lifecycle_conflict_detected` | Recent conflicts | Summary `repeated_lifecycle_pressure` | **Diagnostic Only** |
| `invalid_transition_recently` | Last 300s | Admin runtime summary | **Diagnostic Only** |
| Dashboard conflict: `recovered_cart_with_send_success_log` | `detect_recovery_runtime_conflicts` | Merchant dashboard build logs | **Diagnostic Only** |
| Dashboard conflict: `identity_trust_failed_with_send_success_log` | Same | Same | **Diagnostic Only** |
| Dashboard conflict: `anti_spam_skip_without_behavioral_return` | Same | Same | **Diagnostic Only** |

#### Session / behavioral consistency (`cartflow_session_consistency`)

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `session_runtime_consistent` | No recent drift | Trust signals | **Diagnostic Only** |
| `stale_state_detected` | Behavioral/frontend lag | Trust warning, action guidance | **Diagnostic Only** |
| `runtime_state_drift_detected` | Dashboard vs canonical | Runtime health, merchant ops dashboard | **Diagnostic Only** |
| `behavioral_state_consistent` | Stale window check | Trust signals | **Diagnostic Only** |

#### Provider / WhatsApp

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| Twilio env configured | `_twilio_env_snapshot` | Provider runtime card | **Diagnostic Only** |
| `whatsapp_provider_ready` | Observability snapshot | Runtime health | **Diagnostic Only** |
| Provider readiness mode/failure_class | `cartflow_provider_readiness` | Summary, production readiness | **Future Actionable** (config is env/ops, not in-app reconnect) |
| `recent_send_failures_24h` | DB `CartRecoveryLog` | WhatsApp card, `whatsapp_failure` issue | **Actionable** (pause WA; investigate) |
| Merchant WA production level | `whatsapp_production_reality_v2` | Operational health WhatsApp card | **Diagnostic Only** |
| `provider_instability` (potential) | Configured but unstable | Operational control issue (potential tier) | **Future Actionable** |

#### Store / onboarding readiness

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `onboarding_ready` / blocked / completion % | `cartflow_onboarding_readiness` | Runtime health, per-store rows | **Future Actionable** (re-run check = read-only refresh) |
| Store trust score (0–100) + bucket | `cartflow_admin_operational_summary` | Store rows, legacy summary | **Diagnostic Only** |
| Phone coverage gap | Stores with carts, no phone | Summary hints | **Diagnostic Only** |
| `platform_admin_category` | Aggregate mapper | Ops center platform card | **Diagnostic Only** |

**Operations Center alert kinds** (`admin_operations_center_v1.py`):

| Alert kind | Trigger | Severity | Class |
|------------|---------|----------|-------|
| `stale_recovery` | Overdue scheduled or stale `running` (>600s) | Critical | **Future Actionable** (repair scan exists internally) |
| `failed_recovery` | Terminal failure statuses | High | **Diagnostic Only** (no safe auto-retry) |
| `whatsapp_missing` | Provider not ready | High | **Future Actionable** (merchant completes setup) |
| `store_needs_setup` | Onboarding not ready | Medium | **Future Actionable** (guidance only) |
| `no_cart_events` | No carts in 7 days | Low | **Diagnostic Only** |

#### Queue / worker / scheduler

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| Process role, resume/due-scanner enabled | `recovery_process_role_v1` | `/health/scheduler`, ops scheduler card | **Diagnostic Only** |
| `overdue_scheduled_count`, `running_stale_count` | DB queries | Scheduler health, stale alerts | **Future Actionable** |
| Schedule status aggregates | `RecoverySchedule` group-by | Ops center recovery summary | **Diagnostic Only** |
| Resume/claim/execution heartbeats | `recovery_health_v1` | `/dev/recovery-health`, logs | **Diagnostic Only** |
| `stuck_running_detected` | Running > threshold | Recovery health snapshot | **Future Actionable** |
| DB due scanner loop metrics | `db_due_scanner_health` | Admin API + health card | **Diagnostic Only** |
| Queue readiness summary | `cartflow_queue_readiness` | Tests/docs only | **Diagnostic Only** (not wired to admin HTML) |
| Platform schedule paused | `operational_control_v1` | `/admin/control` | **Actionable** (already implemented) |

**Internal automatic repair (not admin-exposed):** `repair_stale_running_recovery_schedules` on startup/due scan (`recovery_restart_survival.py`).

#### DB pressure

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| QueuePool timeout | SQLAlchemy listener | DB pool card, `db_pool_timeout` issue | **Diagnostic Only** |
| Pool checked_out / size / overflow | `_pool_snapshot_safe` | DB pool card | **Diagnostic Only** |
| Per-request SQL audit | `db_request_audit` (env) | Logs only | **Diagnostic Only** |
| Hot-path query audit | `dashboard_hot_path_query_audit_v1` | Logs/tests | **Diagnostic Only** |
| Slow cart-event (≥2500ms) | `record_cart_event_finish_sample` | Cart-event card, `cart_event_slow` issue | **Diagnostic Only** |

#### Purchase truth & return-to-site

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `has_purchase(recovery_key)` | `cartflow_purchase_truth` | Support diagnostics | **Diagnostic Only** |
| Purchase truth ingest | Webhook / conversion paths | Logs, dev endpoints | **Diagnostic Only** |
| `recovery_stopped_purchase` | Schedule cancelled + purchase truth | Support diagnostics | **Diagnostic Only** |
| Lifecycle closure records | `lifecycle_closure_records_v1` | Support diagnostics, audits | **Diagnostic Only** |
| Return-to-site / behavioral return | Recovery engine | Logs, session consistency | **Diagnostic Only** |

#### Identity mismatches

| Signal | Detection | Visibility | Class |
|--------|-----------|------------|-------|
| `identity_resolution_ok` | Observability flat snapshot | Runtime health | **Diagnostic Only** |
| Journey identity shadow (Phase 0) | `journey_identity_resolver_v1` | Shadow logs only | **Diagnostic Only** |
| Store slug vs platform id drift | Audits / connection layer | Docs, not admin tile | **Diagnostic Only** |

#### Operational control issues (`admin_operational_control/signals.py`)

| Issue code | Tier | Class |
|------------|------|-------|
| `cart_event_slow` | actual | **Diagnostic Only** |
| `db_pool_timeout` | actual | **Diagnostic Only** |
| `background_task_failure` | actual | **Diagnostic Only** |
| `whatsapp_failure` | actual | **Actionable** (pause WA) |
| `provider_instability` | potential | **Future Actionable** |
| `recovery_runtime_down` | actual | **Future Actionable** (resume scan) |
| `runtime_degraded` | potential | **Diagnostic Only** |
| `sandbox_mode` | potential | **Diagnostic Only** |

#### Support diagnostic issue types (`admin_support_diagnostics_v1.py`)

`missing_input`, `delivered_to_customer`, `read_by_customer`, `recovery_waiting_delay`, `provider_not_ready`, `store_not_ready`, `activation_not_complete`, `cart_not_visible`, `missing_phone`, `missing_reason`, `whatsapp_failed`, `schedule_{status}`, `no_recovery_activity`, `recovery_stopped_purchase`, log-status variants — all **Diagnostic Only** (session-scoped investigation, no mutating repair).

#### Production readiness (`cartflow_production_readiness.py`)

Composes env checks + operational signals + admin summary. Dev: `GET /dev/production-readiness`. **Diagnostic Only.**

---

### A.3 Existing controls (already shipped)

| Control | Effect | Scope | Rollback |
|---------|--------|-------|----------|
| `pause_wa` | Blocks new WhatsApp sends | Platform | `POST /admin/control/resume` |
| `pause_scheduling` | Blocks new `RecoverySchedule` rows | Platform | Resume |
| `pause_store` | Blocks sends/scheduling for slug | Per store | Resume or remove slug |
| `pause_reason` | Blocks by reason tag | Per reason | Resume |
| `pause_continuation` | Blocks auto-reply continuation | Platform | Resume |
| `pause_provider` | Provider-level block | Platform | Resume |
| Dry-run apply | Logs `[CONTROL DRY RUN]`, no state change | — | N/A |

**Limits:** In-process state (per worker; lost on restart). No automatic duration expiry. Not merchant-facing.

---

## SECTION B — Control readiness matrix

| Signal | Current detection | Current visibility | Control candidate | Risk | Recommended scope | Readiness class |
|--------|-------------------|------------------|-------------------|------|-------------------|-----------------|
| WhatsApp send failures (24h) | DB `CartRecoveryLog` | Ops center, health issue `whatsapp_failure` | **Pause WA** (exists) | Low | Admin | **Actionable** |
| Platform schedule creation paused | `operational_control_v1` | `/admin/control` | **Pause/resume scheduling** (exists) | Low | Admin | **Actionable** |
| Per-store recovery impact | Pause store set | `/admin/control` | **Pause store** (exists) | Low–Med | Admin | **Actionable** |
| Stale `running` schedules | DB age + scheduler health | Alert `stale_recovery`, `/health/scheduler` | **Run stale repair scan** (dry-run default) | Med | Admin | **Future Actionable** |
| Recovery runtime down | Readiness flags | Issue `recovery_runtime_down` | **Recovery resume inspect/scan** (admin-auth dev parity) | Med | Admin | **Future Actionable** |
| Overdue scheduled count | DB query | Scheduler card | **Trigger due scan** (inspect-only first) | Med | Internal | **Future Actionable** |
| Provider not configured | Env + readiness | `provider_instability`, `whatsapp_missing` | Reconnect provider | High (misconfig) | Ops/env | **Diagnostic Only** |
| Onboarding incomplete | `cartflow_onboarding_readiness` | Alert `store_needs_setup` | Re-run readiness check (read-only refresh) | Low | Admin | **Future Actionable** |
| Duplicate send blocked | In-process guard | Degradation flags | None — by design | — | Internal | **Diagnostic Only** |
| Lifecycle conflict | Lifecycle guard | Pressure flags, logs | None | Critical if exposed | Internal | **Diagnostic Only** |
| Identity merge blocked | Duplicate guard | Anomaly buffer | None | Critical | Internal | **Diagnostic Only** |
| Dashboard payload conflict | Observability | Merchant ops logs | None | High | Internal | **Diagnostic Only** |
| Purchase truth stop | Purchase truth + schedule | Support diagnostics | None | Critical | Internal | **Diagnostic Only** |
| DB pool timeout | Pool listener | Health card | Scale/restart (infra) | Med | Ops/Internal | **Diagnostic Only** |
| Slow cart-event | Finish sample deque | Health card | Profile/hot-path (dev) | Low | Internal | **Diagnostic Only** |
| Sandbox mode active | Onboarding aggregate | Issue `sandbox_mode` | Toggle production env | High | Ops | **Diagnostic Only** |
| Trust score degraded | Per-store scan | Store rows | None | Med | Admin view only | **Diagnostic Only** |
| No cart events 7d | AbandonedCart query | Ops alert | Widget install checklist (guidance) | Low | Merchant docs | **Diagnostic Only** |
| Failed recovery terminal | Schedule status | Ops alert | Manual merchant retry only | High | Merchant | **Diagnostic Only** |
| Background task failure | In-process counter | Health issue | Restart worker / investigate logs | Med | Ops | **Diagnostic Only** |
| Anomaly buffer overflow | Ring buffer cap | Truncated preview | None | — | Internal | **Diagnostic Only** |
| Load test / failure sim | Admin POST | Health page display | Run simulation (exists, dry_run default) | Low | Admin | **Actionable** (diagnostic tool) |

---

## SECTION C — Dangerous controls (never expose directly)

These actions must **not** appear as admin or merchant one-click controls. Investigation may link to logs/dev tools; mutation stays code-reviewed and automated only.

| Forbidden control | Why |
|-------------------|-----|
| Delete or bulk-cancel `RecoverySchedule` rows | Loses durable recovery intent; bypasses anti-spam and purchase-truth stops |
| Rewrite lifecycle state on `AbandonedCart` | Breaks Purchase Truth, dashboard truth, and merchant KPIs |
| Bulk modify / merge cart rows | Identity Contract and recovery_key integrity |
| Force-send WhatsApp bypassing guards | Duplicate send, send-after-return/conversion/purchase |
| Clear Purchase Truth or lifecycle closure records | Financial/recovery audit trail |
| Direct SQL / ORM “repair” from admin UI | Unbounded blast radius; no rollback |
| Override duplicate guard or lifecycle guard flags | Silent customer harm |
| Reset merchant OAuth tokens from admin | Security; merchant must reconnect |
| Platform-wide “delete all pending recoveries” | Irreversible revenue impact |
| Merchant-facing kill switches | Wrong audience; use admin pause + merchant settings separately |
| Health score that auto-triggers mutations | Score must remain advisory until verified |
| Cross-store bulk pause without explicit slug list | Collateral damage |
| Replay/recreate schedules for arbitrary sessions without guards | Duplicate sends |

**Automatic internal repairs that must stay internal:** `repair_stale_running_recovery_schedules` (evidence-gated), purchase-truth ingest, lifecycle closure — only promote to admin with **dry-run + inspect + audit event** wrappers.

---

## SECTION D — Recommended Phase 1 controls (3–5)

Selection: high ops value, low risk, easy rollback, builds on **proven** code paths. Does **not** duplicate existing pause gates; adds **admin-authenticated operational triggers** and **workflow promotion**.

### 1. Stale running schedule repair scan (Admin)

| Field | Value |
|-------|-------|
| **Signal** | `stale_recovery`, `running_stale_count`, `stuck_running_detected` |
| **Proposed control** | `POST /api/admin/recovery/stale-repair` with `dry_run=true` default; calls existing `repair_stale_running_recovery_schedules` |
| **Risk** | Medium (mutates schedule status when not dry-run) |
| **Rollback** | Schedules move to evidence-gated terminal states; no delete; re-run inspect |
| **Permissions** | Admin session only |
| **Scope** | Admin |

### 2. Recovery resume scan — inspect then scan (Admin)

| Field | Value |
|-------|-------|
| **Signal** | `recovery_runtime_down`, overdue schedules, post-restart gap |
| **Proposed control** | Admin-auth mirror of `GET /dev/recovery-restart-survival-verify?action=inspect|scan` |
| **Risk** | Medium for `scan` (may claim/send); Low for `inspect` |
| **Rollback** | Pause scheduling + pause WA; scan is idempotent with existing guards |
| **Permissions** | Admin session only |
| **Scope** | Admin |

### 3. One-click operational pause from health issue (Admin)

| Field | Value |
|-------|-------|
| **Signal** | `whatsapp_failure`, incident response |
| **Proposed control** | POST to existing `/admin/control/apply` with `pause_wa` + reason — **wire health issue card to control API** (no new gate logic) |
| **Risk** | Low |
| **Rollback** | `POST /admin/control/resume` |
| **Permissions** | Admin session only |
| **Scope** | Admin |

### 4. On-demand operational snapshot export (Admin)

| Field | Value |
|-------|-------|
| **Signal** | Incident response, support handoff |
| **Proposed control** | `GET /api/admin/operational-snapshot` → JSON bundle (runtime health + admin summary + scheduler health + control state) |
| **Risk** | Low (read-only; redact secrets) |
| **Rollback** | N/A |
| **Permissions** | Admin session only |
| **Scope** | Admin / Internal |

### 5. Re-run store readiness evaluation (Admin)

| Field | Value |
|-------|-------|
| **Signal** | `store_needs_setup`, trust bucket degraded |
| **Proposed control** | `GET /api/admin/store-readiness?store_slug=` → fresh `evaluate_onboarding_readiness` snapshot (no writes) |
| **Risk** | Low |
| **Rollback** | N/A |
| **Permissions** | Admin session only |
| **Scope** | Admin |

**Explicitly deferred from Phase 1:** health scores, merchant-facing controls, lifecycle/cart repair, schedule deletion, Identity Contract actions, Zid OAuth repair (blocked on partner approval).

---

## SECTION E — Roadmap

### Phase 0 (current — no new implementation)

- Use `/admin/operations` + `/admin/operational-health` + `/admin/support-diagnostics` for investigation.
- Use `/admin/control` pause/resume during incidents.
- Use dev probes where allowlisted; do not expose dev routes to merchants.

### Phase 1 (recommended next — 3–5 controls above)

- Admin-auth stale repair + resume scan with dry-run/inspect defaults.
- Health issue → existing pause API wiring (admin only).
- Read-only snapshot export + per-store readiness refresh.

**Exit criteria:** Each control has audit event, dry-run path, documented rollback, and tests mirroring dev verify behavior.

### Phase 2 — Hardening before broader controls

- **Durable control state** (Redis/DB) so pauses survive restart and multi-worker deploys.
- **Automatic pause expiry** from `duration` metadata on control apply.
- Promote queue readiness summary into ops center HTML.
- Central alerts channel (Slack/webhook) from existing timeline — still no new alert *types*.

### Phase 3 — Future actionable (safeguards required)

- Per-session “retry recovery” with full guard chain (duplicate, purchase, return, delay).
- Provider readiness wizard links (not in-app credential mutation).
- Health score (advisory only, no auto-mutation).
- Merchant-visible “connection status refresh” for Zid OAuth (after partner approval unblocks callback).

### Phase 4 — Never

- Lifecycle rewrite, bulk cart repair, schedule deletion UI, Purchase Truth override, merchant kill switches.

---

## Appendix — Detection → visibility quick map

```text
Detectors (guards, DB, heartbeats, env)
    → cartflow_runtime_health.build_runtime_health_snapshot()
    → cartflow_admin_operational_summary.build_admin_operational_summary_readonly()
    → admin_operational_health.build_admin_operational_health_readonly()
    → admin_operations_center_v1 (alerts, trends)
    → Admin UI + support diagnostics API

Mutations (today): operational_control_v1 gates only
Mutations (internal): repair_stale_running_recovery_schedules, purchase truth ingest
```

**Observability env flags:** `CARTFLOW_STRUCTURED_HEALTH_LOG=1`, `CARTFLOW_OBSERVABILITY_MODE=basic|debug`, `CARTFLOW_RECOVERY_RESUME_ON_STARTUP=1`.

**Known gaps (audit):** Anomaly buffer per-process; `/admin/alerts` placeholder; no external APM export; control state not durable across workers; Zid OAuth blocked on partner review (ops external).
