# Snapshot Generation Optimization v1

**Program:** CartFlow Operational Governance — Snapshot Phase (implementation)
**Date (UTC):** 2026-07-04
**Status:** Implemented. Behavior-neutral for merchants; generation cost reduced.
**Implements:** `docs/snapshot_generation_governance_v1.md` (SG-1, SG-2, SG-4, SG-5, SG-6, SG-7, SG-9, SG-10).
**Basis:** `docs/dashboard_snapshot_generation_audit_v1.md` (why growth happened), Platform risk **P0-2** (`docs/production_reality_validation_v1.md`).
**Non-goals:** dashboard redesign, snapshot-shape redesign, merchant-visible behavior change, scheduler-ownership change, archive-policy change, event-emitter wiring (SG-1 fully event-driven remains future work — see §8).

---

## 1. Objective

Stop generating snapshot rows that carry no new information. Before this change the
background builder rewrote all ~6 snapshot types for every eligible store on a fixed
~45s rotation via an **append-only** writer with **no data-change comparison** — ~42k
rows/day of which 99.66% were immediately superseded (audit v1). This change makes
generation **follow meaningful change** while preserving identical merchant reads and
freshness.

Generation now happens only when the content a merchant would read actually changed;
otherwise the existing latest row is either left untouched (still fresh) or refreshed
in place (no new row).

---

## 2. What changed (code)

| Area | Module | Change |
|---|---|---|
| Semantic fingerprint + policy + gate | `services/dashboard_snapshot_change_v1.py` (new) | SG-6 fingerprint, SG-5 per-type policy, SG-1/2/7 `write_dashboard_snapshot_guarded`. |
| In-place freshness touch + write primitive | `services/dashboard_snapshot_v1.py` | Added `touch_dashboard_snapshot_freshness`; `upsert_dashboard_snapshot` gains `generation_reason` (SG-4). Raw append behavior unchanged for direct callers. |
| Generation metrics | `services/dashboard_snapshot_generation_metrics_v1.py` (new) | SG-4 in-process counters + report. |
| Builder routing + SG-9 | `services/dashboard_snapshot_builder_v1.py` | All 6 writes route through the guarded writer; `dashboard_cards` skipped when `summary` is fully unchanged (derived, SG-9); tick logs write-reduction. |
| Metrics exposure | `services/operational_metrics_v1.py` | `collect_snapshot_generation_metrics()` + `metrics.snapshot_generation` block + metric contracts. |
| Tests | `tests/test_dashboard_snapshot_change_v1.py` (new) | Fingerprint, skip/touch/write, volatile-only, read-neutrality, metrics, policy. |

The **single production generation path** is now
`dashboard_snapshot_change_v1.write_dashboard_snapshot_guarded`, used by the builder
(the only production generator). `upsert_dashboard_snapshot` remains the low-level
append primitive, used by the guarded writer for real inserts and reserved for
tests / migrations / backfill.

---

## 3. Semantic fingerprint (SG-6)

`semantic_snapshot_fingerprint(payload, snapshot_type)` = SHA-256 of the canonical
JSON projection of the payload with **volatile keys removed recursively** and keys
sorted. Equal fingerprint ⇔ the merchant read returns the same content.

### 3.1 Excluded volatile keys (`VOLATILE_SNAPSHOT_KEYS`)

Verified field-by-field against the six builder payloads:

| Key | Where | Why volatile |
|---|---|---|
| `merchant_counter_generated_at` | summary, normal_carts (top-level) | per-build `datetime.now()` |
| `counter_generated_at` | inside `merchant_counter_health` | per-build `datetime.now()` |
| `counter_snapshot_age_seconds` | inside `merchant_counter_health` | recomputed against now |
| `merchant_time_relative_ar` | normal_carts rows | relative "X ago" vs now |
| `merchant_followup_next_line_ar` | normal_carts rows | live countdown "next message in {eta}" |
| `generated_at`, `snapshot_generated_at`, `measured_at`, `server_time`, `as_of`, `as_of_iso`, `now_iso`, `now_utc`, `data_freshness_seconds`, `age_seconds`, `seconds_ago`, `uptime_seconds`, `elapsed_ms`, `duration_ms` | generic metadata | generation/measurement metadata |

### 3.2 Deliberately KEPT (absolute — change only on real events)

`merchant_last_seen_display` (formats absolute `last_seen_at`), `next_attempt_due_at`
(absolute schedule time — a reschedule changes it), `connected_at_ar`,
`widget_last_seen_at_ar`, `merchant_ar_date_header` (changes once per day — a legitimate
time-bucket rollover, SG-7). Keeping these guarantees a genuine change (customer
returns, phone added, reschedule, connection change, day rollover) still triggers a
write. The relative *display* of a due time is excluded, but its absolute driver
(`next_attempt_due_at`) is kept — so a reschedule writes, a mere countdown tick does not.

Changing this exclusion set is a governed decision (SG-12) recorded in
`docs/snapshot_generation_governance_v1.md` §4.3.

---

## 4. Generation decision (SG-1 / SG-2 / SG-7)

Per `(store, type)`, given a freshly-built candidate payload:

| Condition | Decision | Reason | New row? |
|---|---|---|---|
| Gate disabled for type | WRITE | `gate_disabled` | yes |
| No previous latest row | WRITE | `first_build` | yes |
| Fingerprint differs | WRITE | `content_change` | yes |
| Identical **and** latest row stale (`expires_at` passed) | TOUCH | `failsafe_touch` | **no** — freshness refreshed in place |
| Identical **and** latest row still fresh | SKIP | `identical_skip` | **no** — nothing written |

**Read-neutrality:** reads always fetch the latest row per `(store_slug, snapshot_type)`
and see identical content. A SKIP leaves the fresh latest row untouched; a TOUCH advances
`generated_at`/`expires_at` on that same row (read-equivalent to having re-appended an
identical row, minus the growth and version churn).

**Scheduler is now a safety mechanism (SG-1 / SG-7):** a builder tick triggers a *check*
(build + fingerprint compare), never a *write by itself*. Elapsed time alone can only
produce a freshness TOUCH of an already-stale, still-identical row — never a new version.

---

## 5. Per-type policy (SG-5 / SG-11) + derived coupling (SG-9)

`SnapshotGenerationPolicy` per type (mirrors governance §3): importance, trigger mode,
`change_gate_enabled`, `freshness_touch_enabled`, `max_staleness_s`, `failsafe_age_s`,
and `derived_from`. Independently configurable; env kill-switches make it reversible:

- `CARTFLOW_SNAPSHOT_CHANGE_GATE` — global on/off.
- `CARTFLOW_SNAPSHOT_CHANGE_GATE_<TYPE>` — per type (e.g. `..._NORMAL_CARTS`).

Precedence: per-type env > global env > policy default (enabled).

**SG-9:** `dashboard_cards` declares `derived_from = summary`. When a tick fully SKIPs
`summary` (unchanged + fresh), the builder does not independently build/write
`dashboard_cards`; when `summary` writes or is touched, `dashboard_cards` runs through its
own gate. `dashboard_cards` is never generated on its own clock.

---

## 6. Metrics (SG-4)

`services/dashboard_snapshot_generation_metrics_v1.py` records every decision and exposes
`snapshot_generation_metrics_report()`:

| Metric | Meaning |
|---|---|
| `writes_executed` / `rows_written` | new snapshot rows appended (real generation) |
| `writes_avoided` / `rows_avoided` | identical rewrites eliminated (skip + touch) |
| `touches` / `skips` | in-place freshness refreshes / no-write skips |
| `change_detection_checks` | decisions where the gate compared fingerprints |
| `change_detection_hit_rate_pct` | % of checks where content was identical (avoidable) |
| `snapshot_skip_rate_pct` | % of all decisions that wrote nothing at all |
| `write_reduction_pct` | rows eliminated vs the append-every-tick baseline |
| `average_write_reduction` | rows avoided per decision |
| `by_type`, `by_reason` | per-type and per-reason breakdown |

Exposed read-only under `metrics.snapshot_generation` in
`build_operational_metrics_report()`, and per-tick in the builder log line
`[DASHBOARD SNAPSHOT BUILDER TICK] ... rows_written=.. rows_avoided=.. write_reduction_pct=..`.

---

## 7. Verification

- `tests/test_dashboard_snapshot_change_v1.py` (16 tests): identical/volatile-only
  payloads produce equal fingerprints (no write); real content/absolute-timestamp
  changes produce different fingerprints (write); first build writes; identical+fresh
  skips (row count and version unchanged); identical+stale touches in place (no new row,
  `expires_at` advanced, version unchanged); gate-disabled always writes; **read-neutrality
  after skip** (latest row returns identical content); metrics reflect reduction.
- `tests/test_dashboard_builder_parity_v1.py` still passes, incl.
  `test_live_and_snapshot_builder_rows_match` — the builder still produces correct rows
  through the guarded writer (**preserved correctness**).
- Existing snapshot/loop suites pass. Six unrelated failures in the wider suite were
  confirmed pre-existing/environmental by re-running them against baseline with this
  change stashed (failsafe reason-string drift, a dev-route allowlist assertion, and
  shared-DB/timing artifacts) — none introduced here.

**Preserved:** Purchase Truth, Lifecycle Truth, dashboard UI, merchant-visible behavior,
scheduler ownership, archive policy, recovery flow. Latest-row read contract unchanged
(SG-3). No migration (fingerprints are recomputed from the stored payload — no schema
column added).

---

## 8. Deferred / future (does not block closure)

- **SG-1 fully event-driven generation:** emit §4.1 change signals (lifecycle/purchase/
  reply/cart-event/settings) to trigger targeted rebuilds. The SG-2 fingerprint gate
  already collapses any bursts to one write per real change, so this is an efficiency/
  latency improvement, not a correctness gap.
- **SG-2 static enforcement gate** (LT-C1-style "no time-only write path / gate present").
- **§5.5 append→touch note:** the in-place freshness TOUCH is a deliberate, documented
  evolution of the append-only invariant (Data-Growth C-DATA-6) — recorded under SG-12 in
  `docs/snapshot_generation_governance_v1.md`.
