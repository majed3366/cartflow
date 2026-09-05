# Commercial Decision Commitment V1 — Record Design

**Date (UTC):** 2026-09-05  
**Mode:** Implementation design only — **no code, no migrations, no deploy**  
**Prior art:** Lifecycle Truth Audit V1 (Option C)  
**Normative amendment:** `02_EXECUTION_TRUTH_CLOSURE_AMENDMENT.md` (overrides conflicting text below)

Evidence anchors (existing, not invented):

- COL `opportunity_id`: `col:{family}:{reason}:{store_slug}` — `services/commercial_opportunity_layer_v1/compose_v1.py`
- COL truth classes: `PRODUCTION_TRUTH_READY` / `PRODUCTION_PARTIAL` / `INSUFFICIENT` — `contract_v1.py`
- COL attach (no commitment today): `attach_v1.py` → `summary["commercial_opportunity_layer_v1"]`
- Console modes today (COL-only): `static/merchant_ui_v2_workspace.js` `consoleModeFromOpp`
- Store isolation pattern: `store_slug` on archive/schedules/findings (`models.py`)

---

## 1. Laws

| Layer | Owns | Does not own |
|-------|------|--------------|
| **COL** | Evidence readiness, opportunity objects, `opportunity_id`, measure/recheck **copy** | Action acknowledgement, execution proof, measurement windows, recheck due |
| **Commercial Commitment** | Merchant accept + execution-gated measurement + closure | Ranking, truth_class, Arabic copy generation, WON/LOST |
| **Decision Console / CDA** | Paint from COL + commitment **read model** | Any write to commitment or COL |

Do **not** persist UI modes (`actionable` / `measuring` / `recheck` / CDA arcs).

**ACTION_CHOSEN ≠ ACTION EXECUTED.** Accept never starts measurement by itself.

---

## 2. Stable identity

### 2.1 Keys

| Key | Form | Role |
|-----|------|------|
| `store_slug` | Existing merchant store slug | Isolation |
| `opportunity_key` | Exact COL `opportunity_id` at accept: `col:{family}:{reason}:{store_slug}` | Soft link (survives title/copy/UI) |
| `commitment_id` | UUID v4 (PK) | Immutable row identity |

Denormalized at accept: `opportunity_family`, `opportunity_reason`.

### 2.2 Guarantees

| Requirement | How |
|-------------|-----|
| Survives copy / Console / UI | slug + opportunity_key + commitment_id — never title text |
| Survives COL recomposition | Soft key; row remains until closed |
| No duplicate **active** commitments | Partial unique `(store_slug, opportunity_key) WHERE closed_at IS NULL` |
| Versioning | Close/supersede frees slot; new accept → new `commitment_id` |

**ACTIVE UNIQUENESS STILL SAFE:** YES — unchanged by execution/closure amendment.

---

## 3. State model (V1)

### 3.1 Persisted vs derived

| Commercial state | Persist? | Rule |
|------------------|----------|------|
| READY | **NO** | COL when no applicable open commitment |
| INSUFFICIENT_EVIDENCE | **NO** | COL empty / `INSUFFICIENT` when no open commitment |
| ACTION_CHOSEN | Facts: row + `action_chosen_at`; phase **derived** | open + `measurement_started_at IS NULL` |
| UNDER_MEASUREMENT | **NO** enum write | open + started + `now < measurement_due_at` |
| RECHECK_DUE | **NO** enum write | open + started + `now >= measurement_due_at` |
| WON / LOST / LEARNED / DISCOVERED | **Forbidden** | — |

### 3.2 Derived phase function (server) — normative

```
def derive_phase(row, now=utc_now):
    if row.closed_at is not None:
        return None
    if row.measurement_started_at is None:
        return "ACTION_CHOSEN"
    if now < row.measurement_due_at:
        return "UNDER_MEASUREMENT"
    return "RECHECK_DUE"
```

Requires: if `measurement_started_at` set then `measurement_due_at` set (same write).

### 3.3 No persisted `phase` column

Reject dual-write. Timestamps + `closed_at` are authority.

---

## 4. Minimum record fields

| Column | Type | Null | Owner / use |
|--------|------|------|-------------|
| `id` | UUID PK | NO | Commitment identity |
| `store_slug` | VARCHAR(191) | NO | Isolation |
| `opportunity_key` | VARCHAR(255) | NO | COL soft key; active uniqueness |
| `opportunity_family` | VARCHAR(64) | NO | Frozen at accept |
| `opportunity_reason` | VARCHAR(128) | NO | Frozen at accept |
| `action_chosen_at` | DATETIME(TZ) | NO | Merchant accept time |
| `action_summary` | VARCHAR(512) | NO | What was accepted (stable token preferred; not UI essay) |
| `decision_snapshot_json` | JSON | NO | Decision-time snapshot at accept (`cdc_decision_snapshot_v1`) |
| `measurement_started_at` | DATETIME(TZ) | YES | NULL until execution authority |
| `measurement_due_at` | DATETIME(TZ) | YES | Set only with start |
| `measurement_start_authority` | VARCHAR(64) | YES | `cartflow_execution` \| `merchant_execution_confirm` |
| `measurement_start_ref` | VARCHAR(191) | YES | Execution/confirm correlation |
| `baseline_snapshot_json` | JSON | YES | NULL until measurement start (`cdc_measurement_baseline_v1`) |
| `metric_key` | VARCHAR(128) | YES | Set/confirmed at measurement start |
| `baseline_metric_value` | NUMERIC | YES | Frozen at measurement start |
| `recheck_condition_frozen` | TEXT | YES | Frozen at measurement start (advisory; not auto-WON) |
| `created_at` / `updated_at` | DATETIME(TZ) | NO | Audit |
| `closed_at` | DATETIME(TZ) | YES | Ends active uniqueness |
| `close_reason` | VARCHAR(64) | YES | Required iff closed; bounded vocab |
| `close_note` | VARCHAR(200) | YES | Optional human note; not machine state |
| `superseded_by_id` | UUID FK self | YES | Chain |

### 4.1 Rejected

Persisted phase enum; separate `recheck_due_at`; outcome/WON/LOST/LEARNED; `store_id` FK; UI Arabic as SoT columns; fusing accept→measurement.

### 4.2 `close_reason` vocabulary

`merchant_cancel` | `merchant_abandon` | `opportunity_invalid` | `superseded` | `recheck_new_decision` | `store_invalidated`

Forbidden: `won`, `lost`, `learned`, `purchase`, `measurement_expired`.

---

## 5. Transition ownership

### 5.1 READY → ACTION_CHOSEN

| Aspect | Design |
|--------|--------|
| **Owner** | Merchant-authenticated `accept_opportunity` in `commercial_decision_commitment_v1` |
| **Trigger** | Explicit accept of COL opportunity — not compose, not recovery send, not purchase |
| **Write** | INSERT: `action_chosen_at`, `decision_snapshot_json`; **`measurement_started_at` remains NULL** |
| **Idempotency** | Re-accept same open key → return existing row |
| **Store isolation** | Session slug == body slug |

### 5.2 ACTION_CHOSEN → UNDER_MEASUREMENT

| Aspect | Design |
|--------|--------|
| **Owner** | Same service: `start_measurement` |
| **Trigger** | Allowed execution authority only (see amendment §A) |
| **Write** | Set `measurement_started_at`, `measurement_due_at`, authority, ref, `baseline_snapshot_json`, metric fields, `recheck_condition_frozen` |
| **Idempotency** | Second start no-op if already started |
| **Refuse** | External/unproven execution (authority C) |

### 5.3 UNDER_MEASUREMENT → RECHECK_DUE

| Aspect | Design |
|--------|--------|
| **Owner** | None — read-time derivation |
| **Trigger** | `now >= measurement_due_at` |
| **Not** | Closure; WON/LOST |

### 5.4 Closure

| Owner | Reasons |
|-------|---------|
| Merchant | `merchant_cancel`, `merchant_abandon` |
| Commitment service (explicit system APIs) | `opportunity_invalid`, `superseded`, `recheck_new_decision`, `store_invalidated` |

Never: purchase; measurement expiry alone; silent COL paint.

---

## 6. Measurement contract

| Question | Truth |
|----------|--------|
| What was accepted? | `action_summary` + `decision_snapshot_json` at accept |
| What action became active? | Only after `start_measurement` with authority A or allowlisted B |
| When did measurement start? | `measurement_started_at` |
| Measurement baseline? | `baseline_snapshot_json` frozen **at start** — not at accept |
| Window? | `[measurement_started_at, measurement_due_at)` |
| Recheck eligibility? | Clock due + still open; frozen recheck text is advisory |

No causal attribution. No WON/LOST.

Window length: `resolve_measurement_window(family)` in commitment service (not RecoverySchedule).

---

## 7. Recheck resolution (ONE rule)

**Keep the same commitment open (rule A).**

Due clock → RECHECK_DUE only. Re-read COL for evidence. Explicit close/supersede later if merchant takes a new decision version (`recheck_new_decision` / `superseded` + new accept).

---

## 8. Scheduler

**SCHEDULER_REQUIRED: NO** — RECHECK_DUE is timestamp-derived on read.

---

## 9. DB design

**Table:** `commercial_decision_commitments`

```sql
CREATE TABLE commercial_decision_commitments (
  id                          CHAR(36) PRIMARY KEY,
  store_slug                  VARCHAR(191) NOT NULL,
  opportunity_key             VARCHAR(255) NOT NULL,
  opportunity_family          VARCHAR(64)  NOT NULL,
  opportunity_reason          VARCHAR(128) NOT NULL,
  action_chosen_at            DATETIME(6)  NOT NULL,
  action_summary              VARCHAR(512) NOT NULL,
  decision_snapshot_json      JSON         NOT NULL,
  measurement_started_at      DATETIME(6)  NULL,
  measurement_due_at          DATETIME(6)  NULL,
  measurement_start_authority VARCHAR(64)  NULL,
  measurement_start_ref       VARCHAR(191) NULL,
  baseline_snapshot_json      JSON         NULL,
  metric_key                  VARCHAR(128) NULL,
  baseline_metric_value       DECIMAL(18,6) NULL,
  recheck_condition_frozen    TEXT         NULL,
  created_at                  DATETIME(6)  NOT NULL,
  updated_at                  DATETIME(6)  NOT NULL,
  closed_at                   DATETIME(6)  NULL,
  close_reason                VARCHAR(64)  NULL,
  close_note                  VARCHAR(200) NULL,
  superseded_by_id            CHAR(36)     NULL,
  CONSTRAINT fk_cdc_superseded
    FOREIGN KEY (superseded_by_id)
    REFERENCES commercial_decision_commitments(id)
);
-- UNIQUE (store_slug, opportunity_key) WHERE closed_at IS NULL
-- INDEX (store_slug, opportunity_key)
-- INDEX (store_slug, closed_at, measurement_due_at)
```

Store isolation: every query filters `store_slug = :session_store`.

---

## 10. API / service ownership

Module: `services/commercial_decision_commitment_v1/`

| Method | Behavior |
|--------|----------|
| `accept_opportunity` | ACTION_CHOSEN only; no measurement |
| `start_measurement` | Authority-gated; freezes baseline |
| `close_commitment` / `supersede_commitment` | Bounded `close_reason` |
| `reconcile_invalid_opportunity` | System close `opportunity_invalid` (explicit) |
| `derive_phase` / `attach_*` | Read model |

No `main.py` business logic.

---

## 11. Failure modes (amended)

| Failure | Behavior |
|---------|----------|
| Double accept | Idempotent open row; still ACTION_CHOSEN if not started |
| Start without authority | Refuse |
| Merchant “confirm” on non-allowlisted family | Refuse (treat as C) |
| Opportunity disappears during ACTION_CHOSEN / measurement | Stay open until explicit reconcile/close |
| Purchase | Ignored |
| Window expires | RECHECK_DUE; not closed |
| Recheck | Stay open; COL re-evaluated for display |

---

## 12. Console derivation

| Phase / COL | Mode |
|-------------|------|
| ACTION_CHOSEN | Accepted / pending execution (not watching) |
| UNDER_MEASUREMENT | Watching |
| RECHECK_DUE | Recheck |
| none + READY | Actionable |
| none + PARTIAL | Partial evidence (not lifecycle measurement) |
| none + insufficient | Insufficient |

Open commitment phase wins for that opportunity_key.

---

## 13–14. Migration / cost / checklist

Unchanged in spirit: additive table; empty = COL-only; +1 summary query; scheduler 0; scale LOW.

Checklist adds: authority allowlist tests; baseline-null-until-start; close_reason enum; recheck keeps open.

**IMPLEMENTATION AUTHORIZED: NO**  
**DEPLOY: NO**
