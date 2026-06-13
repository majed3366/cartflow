# Lifecycle Authority Recovery v1 Report

**Date (UTC):** 2026-06-13  
**Scope:** Establish `customer_lifecycle_state` / `classify_customer_lifecycle_state_v1` as the sole merchant-facing lifecycle authority.

---

## Summary

CartFlow now routes merchant-facing lifecycle display through **one authority**:

| Authority | Role after recovery |
|-----------|---------------------|
| `customer_lifecycle_state` | **Sole lifecycle label, bucket, archive UX, counters** |
| `classify_customer_lifecycle_state_v1` | **Producer** |
| `vip_lifecycle_status` (DB column) | **Evidence only** → `vip_lifecycle_status_evidence` |
| `phase_key` / `coarse` | **Evidence only** (`lifecycle_evidence_*` on rows) |
| `merchant_followup_*_ar` | **Display derivatives** synced from lifecycle fields |
| `merchantLifecycleCompact` (JS) | **Removed from merchant lifecycle path** — unavailable fallback only |
| Messages page | **Lifecycle attached** per `recovery_key` via classifier |

Evidence sources (timeline, purchase truth, schedules, behavioral, logs) still feed classification; they do not own merchant lifecycle labels.

---

## Implementation map

### Core module

- `services/lifecycle_authority_recovery_v1.py`
  - `attach_merchant_row_lifecycle_authority` — attach + follow-up sync + finalize
  - `sync_merchant_followup_clarity_from_lifecycle` — no independent schedule authority
  - `sync_vip_legacy_display_from_lifecycle` — VIP template fields as derivatives
  - `lifecycle_authority_active_count` / `lifecycle_authority_waiting_count` — summary badges
  - `enrich_message_history_rows_with_lifecycle` — messages page lifecycle

### Classifier (`customer_lifecycle_states_v1.py`)

- Added `vip_lifecycle_status_evidence` parameter
- VIP lane: `converted` → `completed`, `closed` → `archived`, active VIP → `needs_intervention` with contacted/abandoned copy
- Removed blanket `_needs_intervention(is_vip_lane=True)` — VIP handled explicitly before normal intervention rules

### Surfaces converted

| Surface | Change |
|---------|--------|
| Normal Carts row build (`main.py`) | Follow-up clarity → `sync_merchant_followup_clarity_from_lifecycle` |
| Summary counters (`_normal_carts_dashboard_stats`) | `lifecycle_authority_active_count` / `waiting_count` |
| VIP batch API (`vip_dashboard_batch_v1.py`) | `attach_merchant_row_lifecycle_authority` on each row |
| VIP legacy cards (`_vip_dashboard_cart_alert_dict_from_group`) | Lifecycle attach + smart actions from lifecycle |
| Messages API | `enrich_message_history_rows_with_lifecycle` |
| Dashboard JS | No `merchantLifecycleCompact` fallback; `merchantNextLineShort` uses lifecycle label |
| Smart actions | VIP contacted inference from lifecycle label + evidence |

### Preserved (evidence, not authority)

- `CartRecoveryLog`, `RecoverySchedule`, `cf_behavioral`, purchase truth, timeline ingest
- `vip_lifecycle_status` column updates on merchant VIP actions (feeds evidence on next read)

---

## Verification matrix (required areas)

| Area | Authority after recovery | Verified locally |
|------|--------------------------|------------------|
| Return Detection | `customer_lifecycle_state` (`return_to_site`, `waiting_purchase_window`) | classifier tests |
| Reply Detection | `customer_lifecycle_state` (`customer_reply`, `customer_engaged`) | classifier tests |
| Purchase Detection | `customer_lifecycle_state` (`completed`) | classifier + VIP converted |
| VIP Display | `customer_lifecycle_label_ar` + legacy VIP fields synced | VIP attach test |
| Messages Display | `customer_lifecycle_state` on message rows | enrich function |
| Archive Display | `customer_lifecycle_state` (`archived`) | attach tests |
| Summary Counters | `lifecycle_authority_active_count` | unit test |
| Next Action | Lifecycle label in JS; smart actions use lifecycle evidence | JS + smart_actions |

---

## Tests

- `tests/test_lifecycle_authority_recovery_v1.py` — 9 cases (new)
- Existing lifecycle suites: **38 passed** in combined run
- Verify script: `scripts/lifecycle_authority_recovery_verify_v1.py`

---

## Files touched

- `services/lifecycle_authority_recovery_v1.py` (new)
- `services/customer_lifecycle_states_v1.py`
- `services/vip_dashboard_batch_v1.py`
- `services/merchant_followup_clarity_v1.py` (docstring)
- `services/smart_actions.py`
- `main.py`
- `static/merchant_dashboard_lazy.js`
- `tests/test_lifecycle_authority_recovery_v1.py` (new)
- `scripts/lifecycle_authority_recovery_verify_v1.py` (new)

---

## Post-deploy note

Production dashboard API parity requires deploy + authenticated gate run. Local verification **PASS** (see Production Verification Report).
