# Commercial Decision Commitment V1 — Design Amendment

**Date (UTC):** 2026-09-05  
**Type:** Execution truth + closure ownership corrections  
**Base design:** `01_COMMITMENT_RECORD_DESIGN.md` (direction approved; this amendment is normative where it conflicts)  
**Implementation:** NOT AUTHORIZED · **Deploy:** NO  

---

## A. ACTION_CHOSEN ≠ ACTION EXECUTED

### Law

| Term | Means | Does not mean |
|------|--------|----------------|
| **ACTION_CHOSEN** | Merchant accepted / committed to the proposed action | Action executed; measurement started; outcome known |
| **Measurement start** | Authoritative evidence that the action became **active** | Merchant intent alone; external claim without proof |

### Timestamps

| Field | Set when | Remains NULL when |
|-------|----------|-------------------|
| `action_chosen_at` | Accept write succeeds | — |
| `measurement_started_at` | `start_measurement` succeeds under allowed authority | Accept; retries of accept; external action without proof |
| `measurement_due_at` | Together with `measurement_started_at` only | Accept; any time measurement has not started |

**ACTION_CHOSEN MUST NOT automatically start measurement.**  
Prior design text that fused accept + measurement start is **revoked**.

### Measurement-start evidence (allowed authorities)

| Code | Evidence | Starts measurement? |
|------|----------|---------------------|
| **A** `cartflow_execution` | CartFlow itself executed the action and recorded **execution success** (same service/transaction or verified execution receipt id) | **YES** |
| **B** `merchant_execution_confirm` | Merchant explicit confirmation that they executed **and** product semantics for that family/action treat confirmation as authoritative execution evidence (allowlist in commitment contract) | **YES only if allowlisted** |
| **C** *(none)* | External / offline action with no CartFlow execution proof and no allowlisted confirmation | **NO** — stay ACTION_CHOSEN |

Do not fabricate execution truth. Unknown authority → refuse `start_measurement` (4xx).

Persisted on start (minimum):

- `measurement_start_authority` — `cartflow_execution` | `merchant_execution_confirm`
- `measurement_start_ref` — optional opaque correlation (execution id / confirm token), VARCHAR(191) NULL

---

## B. Derived phases (exact)

```
open := closed_at IS NULL

ACTION_CHOSEN:
  open AND action_chosen_at IS NOT NULL AND measurement_started_at IS NULL

UNDER_MEASUREMENT:
  open AND measurement_started_at IS NOT NULL AND now < measurement_due_at

RECHECK_DUE:
  open AND measurement_started_at IS NOT NULL AND now >= measurement_due_at

READY / INSUFFICIENT:
  COL-derived only when no applicable active commitment
  (or commitment closed → fall back to COL)
```

`measurement_due_at` is required whenever `measurement_started_at` is set (same write).

---

## C. Closure ownership

### Who may set `closed_at`

| Owner | Via | Allowed reasons |
|-------|-----|-----------------|
| **Merchant** (authenticated) | `close_commitment` | `merchant_cancel`, `merchant_abandon` |
| **Commitment service** (system transition, no `main.py` logic) | `close_commitment` / `supersede_commitment` inside service | `opportunity_invalid`, `superseded`, `recheck_new_decision`, `store_invalidated` |

**Not owners:** RecoverySchedule, purchase-truth, COL compose alone, Console, scheduler clock.

### What must not close

| Event | Effect on commitment |
|-------|----------------------|
| Purchase / cart recovery | **No automatic closure** |
| Measurement window expiry (`now >= measurement_due_at`) | Phase → **RECHECK_DUE** only; **not** closure |
| COL recompose / rank change alone | **No** silent close |

### When system may close

| Reason | Trigger (explicit) |
|--------|---------------------|
| `opportunity_invalid` | Reconcile: COL no longer exposes `opportunity_key` **and** service `reconcile_invalid_opportunity` invoked (not every dashboard paint) |
| `superseded` | New accept requires freeing slot after prior close in same transaction, or explicit supersede API |
| `recheck_new_decision` | Merchant accepts a **materially new** decision version after RECHECK_DUE (close then insert) |
| `store_invalidated` | Store disconnect / permanent tenant invalidation path already used elsewhere |

---

## D. `close_reason` vocabulary (required in V1)

Bounded enum — **no free-text as state semantics**. Optional `close_note` capped ≤200 chars for human audit only (not machine state).

| Value | Meaning |
|-------|---------|
| `merchant_cancel` | Merchant cancels commitment before/during lifecycle |
| `merchant_abandon` | Explicit abandonment |
| `opportunity_invalid` | Opportunity invalid / disappeared (reconcile) |
| `superseded` | Replaced by another commitment chain |
| `recheck_new_decision` | After recheck, merchant commits to a new decision version |
| `store_invalidated` | Store disconnect / permanent invalidation |

Forbidden as close reasons: `won`, `lost`, `learned`, `purchase`, `measurement_expired`.

---

## E. Recheck without WON/LOST — ONE rule

**Chosen: A — keep the same commitment open.**

When phase becomes RECHECK_DUE:

1. Do **not** mark success/failure.
2. Do **not** auto-close.
3. Do **not** auto-create a new commitment.
4. Console/Workspace re-reads **current COL evidence** for context; commitment phase remains RECHECK_DUE until an **explicit** close/supersede write.
5. If merchant chooses a new decision version: close with `recheck_new_decision` or `superseded`, then `accept` a new row (frees active uniqueness). That is a **later write**, not the due-clock resolution.

Reject B/C as automatic due-time behavior (they invent resolution). B remains available only as explicit merchant/system write after recheck.

---

## F. Baseline timing

| Snapshot | Freeze point | Purpose |
|----------|--------------|---------|
| **Decision-time** `decision_snapshot_json` | At **accept** (`ACTION_CHOSEN`) | What was accepted (opportunity identity, proposed action tokens, truth_class at accept) — **not** the measurement baseline |
| **Measurement baseline** `baseline_snapshot_json` | At **measurement start** only | Frozen metrics/signals for the measurement window |

**Preferred principle (normative):** baseline belongs to measurement start.

At accept:

- `baseline_snapshot_json` = NULL  
- `baseline_metric_value` = NULL  
- `metric_key` may be **proposed** at accept (nullable until start) or set at start  
- `decision_snapshot_json` NOT NULL (versioned, small)

At `start_measurement`:

- Freeze `baseline_snapshot_json` + `baseline_metric_value` + ensure `metric_key`  
- Set `measurement_started_at` / `measurement_due_at`  
- Freeze `recheck_condition_frozen` from COL/OGL at **start** (or copy from decision snapshot if unchanged — prefer refresh at start)

Do not conflate decision-time and measurement baseline.

---

## G. JSON contracts

### `decision_snapshot_json` (accept)

| Rule | Value |
|------|--------|
| `schema_version` | `"cdc_decision_snapshot_v1"` |
| Allowed fields | `opportunity_key`, `opportunity_family`, `opportunity_reason`, `truth_class`, `action_code` (stable token if any), `proposed_metric_key`, `signal_counts` (bounded map of named scalars), `accepted_at` |
| Forbidden | UI Arabic body as SoT, unbounded event arrays, HTML, CDA arcs, full COL package dump |
| Max payload | ≤ 4 KiB serialized |

### `baseline_snapshot_json` (measurement start)

| Rule | Value |
|------|--------|
| `schema_version` | `"cdc_measurement_baseline_v1"` |
| Allowed fields | `metric_key`, `metric_value`, `metric_unit` (optional), `signal_counts` (≤16 keys), `opportunity_key`, `truth_class_at_start`, `window_days`, `started_at` |
| Forbidden | Arbitrary history, UI-formatted strings as truth, recovery timeline dumps |
| Max payload | ≤ 4 KiB serialized |

Unknown keys: reject or strip at write (fail closed on schema_version mismatch).

---

## H. Field amendments (delta vs base design)

| Change | Detail |
|--------|--------|
| Revoke | Accept fused with measurement start |
| Add | `measurement_start_authority`, `measurement_start_ref` |
| Add | `decision_snapshot_json` NOT NULL at accept |
| Change | `baseline_snapshot_json` NULL until measurement start |
| Change | `recheck_condition_frozen` NULL until measurement start (or set at start only) |
| Keep | Active uniqueness; `close_reason` required when `closed_at` set |
| Keep | Scheduler NOT required |

---

## I. Console derivation (amended)

| Commitment phase | Console mode |
|------------------|--------------|
| ACTION_CHOSEN | Action **accepted / pending execution** — not watching |
| UNDER_MEASUREMENT | Watching |
| RECHECK_DUE | Recheck / reopen |
| none + COL READY | Actionable |
| none + COL PARTIAL | Partial evidence paint (not lifecycle measurement) |
| none + insufficient | Insufficient |

Commitment phase still wins over COL when open for that opportunity_key.

---

**IMPLEMENTATION AUTHORIZED: NO**  
**DEPLOY: NO**
