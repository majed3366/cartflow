# Governance Registry — Institutional Memory V1

**Date (UTC):** 2026-07-03  
**Purpose:** Principles that survive personnel changes. When in doubt, these rules override convenience.

---

## G-001: Truth Before Intelligence

**Statement:** Durable facts (purchase, lifecycle, send proof) must be correct and closed before any intelligence layer (hesitation scoring, recommendations, knowledge layer) influences merchant-facing decisions.

**Implications:**
- Do not infer purchase from behavioral signals alone.
- Product purchase mappings are analytics-tier until explicitly promoted.
- Classifier and purchase truth gates precede movement copy and badges.

**Violations to watch:** ML or heuristic lifecycle replacing LT-C1; dashboard labels driven by cold-tier mappings.

**Reference:** `docs/cartflow_decision_confidence_audit_v1.md`, decision registry D-010

---

## G-002: One Source Of Truth

**Statement:** Each merchant-facing question has exactly one owning module and one durable store (see ownership map).

**Implications:**
- Purchase → `purchase_truth_records`
- Lifecycle label → `classify_customer_lifecycle_state_v1()`
- Dashboard rows → latest snapshot + hot slice
- Counters → `dashboard_counter_totals_v1`
- Movement presentation → movement visibility service (shadow)

**Violations to watch:** Duplicate lifecycle logic in routes; badge counts from page window; timeline status shown as lifecycle without classifier.

**Reference:** `docs/institutional_memory/ownership_map.md`, `docs/lifecycle_truth_contract.md`

---

## G-003: Archive Before Delete

**Statement:** Historical rows are not destroyed without an archived copy or documented retention policy.

**Implications:**
- Dashboard snapshots: hot table + `dashboard_snapshots_archive`
- Timeline and recovery logs: append-only; growth measured before any retention change
- Migrations that drop data require explicit governance sign-off and backup plan

**Violations to watch:** `DELETE FROM dashboard_snapshots` without archive; truncating logs to “fix” counters.

**Reference:** `docs/data_accumulation_governance_v1.md`, `docs/dashboard_snapshot_archive_v1_report.md`

---

## G-004: Runtime Isolation

**Statement:** Long-running scheduler work must not share the API process or connection pool.

**Implications:**
- `CARTFLOW_PROCESS_ROLE=api` — HTTP handlers only; no due scanner, no snapshot builder loop, no archive loop
- `CARTFLOW_PROCESS_ROLE=scheduler` — background loops; no public merchant traffic
- Delay dispatch and resume-on-startup belong on scheduler

**Violations to watch:** Enabling scanner on API for “quick fix”; increasing pool size instead of splitting roles.

**Reference:** `docs/incident_pool_exhaustion_postmortem_v1.md`, `docs/railway_api_scheduler_deployment_v1.md`

---

## G-005: No Event Lost

**Statement:** Recovery and lifecycle transitions that matter to merchants must leave an append-only audit trail.

**Implications:**
- `recovery_truth_timeline_events` for proven transitions
- `cart_recovery_logs` for send attempts and outcomes
- Idempotent writers — duplicate events worse than missing only when deduped correctly

**Violations to watch:** Updating log rows in place to “correct” history; skipping timeline write on send success.

**Reference:** `docs/timeline_log_growth_audit_v1.md`, decision registry D-009

---

## G-006: Growth Must Be Measured

**Statement:** Any append-only or high-churn table must have measured row counts, growth rate, and risk tier before retention or archive policy changes.

**Implications:**
- Use `GET /dev/data-growth-measurement` and domain audits (timeline, snapshots)
- Phase governance: measure → archive design → scheduler activation → verify
- LOW risk today does not mean skip measurement tomorrow

**Violations to watch:** New event tables without growth probe; archive disabled silently in prod.

**Reference:** `docs/data_accumulation_governance_v1.md`, `docs/timeline_log_growth_audit_v1.md`

---

## G-010: Execution Governance (Work Packages)

**Statement:** High and Critical Investigations execute only through controlled Work Packages. No WP advances automatically; Architecture approval, evidence, and rollback verification are mandatory between WPs. `main.py` remains composition-only. Reality Validation remains the final acceptance gate where blueprints require it.

**Implications:**
- Lifecycle: Architecture → Investigation → Root Cause Confirmed → Implementation Architecture → Execution Blueprint → WP → Evidence Review → Architecture Approval → … → Reality Replay → Verification → Close.
- Every WP uses the Work Package Template before coding and the Review Template before approval.
- Any reviewer may stop on architecture drift, improper `main.py` growth, or Time/Reality/Identity/Merchant contract breakage.

**Violations to watch:** Skipping approval between WPs; coding on `main`; closing WPs without evidence; expanding `main.py` with business/time logic.

**Reference:** `docs/governance/execution/EXECUTION_GOVERNANCE_FRAMEWORK_V1.md`

---

## G-011: Identity Foundation Before Knowledge

**Statement:** Every knowledge domain must complete Identity Investigation and Identity Foundation (canonical identity, SoT, snapshot, projection, authenticity) before Truth Validation, Knowledge Layer, or Commercial Intelligence work. Merchant surfaces must never fabricate identity — only real identity or explicitly unresolved.

**Implications:**
- Architectural order: Domain → Identity Investigation → Identity Foundation → Truth Validation → Knowledge → Commercial Intelligence → Merchant Surface
- No fixture-backed merchant knowledge; no silent loader degrade into placeholders
- Simulator must obey production identity rules (display names + snapshot path)
- Product Identity is the first mapped domain — readiness BLOCKED until authenticity/loader/projection/sim gaps close
- Commercial Knowledge Expansion resumes only after domain readiness = READY (approved)

**Violations to watch:** Shipping product findings from `demo_rich_fixture_v1`; Home naming «منتج X»; Knowledge work starting without Foundation map; “temporary” placeholder labels on production paths.

**Reference:** `IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`, `IDENTITY_FOUNDATION_CONTRACT_V1.md`, `IDENTITY_AUTHENTICITY_RULES_V1.md`, `IDENTITY_READINESS_CHECKLIST_V1.md`, `PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`, `PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md`

---

## Extended governance (operational)

| Principle | Summary |
|-----------|---------|
| **Production verification** | Scheduler/build changes require deploy verification scripts and log markers (`[SCHEDULER BUILD INFO]`, archive config). |
| **Parity before trust** | Snapshot builder must match live builder semantics; parity guards block silent drift. |
| **Degraded mode explicit** | Turning off snapshot mode is a conscious degradation, not default prod behavior. |
| **Merchant copy honesty** | Labels must reflect classifier truth, not aspirational product language. |
| **Pilot readiness** | Stabilization exit criteria and operational contracts gate feature expansion. |

**Reference:** `docs/cartflow_stabilization_exit_criteria_v1.md`, `docs/cartflow_operational_contracts_v1.md`, `docs/cartflow_deployment_governance_v1.md`

---

## Governance change process

1. Document problem in decision registry (or failure registry if incident-driven).
2. Update ownership map if SoT shifts.
3. Run targeted audit; update architecture audit baseline status.
4. Production verify before marking CLOSED.
5. Append `docs/SYSTEM_SUMMARY.md` §10 on substantive changes.
