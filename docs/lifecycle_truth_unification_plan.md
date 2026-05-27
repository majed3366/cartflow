# CartFlow Lifecycle Truth Unification Plan (Phase 1)

**Date (UTC):** 2026-05-27  
**Scope:** Planning only. **No runtime changes**, no cleanup, no deletion.  
**Objective:** Make `customer_lifecycle_state` the single authoritative source for dashboard meaning.

---

## PART 1 — Inventory (where lifecycle-like state is computed)

Legend: authoritative means "should decide visible business truth for merchant dashboard."

| File | Function / area | State(s) computed | Authoritative? |
|---|---|---|---|
| `services/customer_lifecycle_states_v1.py` | `classify_customer_lifecycle_state_v1` | `waiting_first_send`, `waiting_customer_reply`, `customer_reply`, `customer_engaged`, `return_to_site`, `waiting_next_scheduled`, `needs_intervention`, `completed`, `archived`, `active` | **yes** (target owner) |
| `services/customer_lifecycle_states_v1.py` | `attach_customer_lifecycle_state_v1` | Writes `customer_lifecycle_state`, `customer_lifecycle_label_ar`, `customer_lifecycle_status_row_class`, `customer_lifecycle_dashboard_action`, `customer_lifecycle_is_archived_visual` | **yes** (target owner) |
| `services/merchant_cart_row_classifier.py` | `classify_merchant_cart_row` | `primary_bucket` = `waiting/sent/needs_followup/customer_reply/customer_engaged/return_to_site/recovered/no_phone`; writes `merchant_cart_bucket`, `merchant_status_label_ar`, `merchant_cart_visible_tabs` | **no** (derived in Phase 1) |
| `services/merchant_cart_row_classifier.py` | `_return_to_site_truth`, `_sent_truth`, `_customer_engagement_truth` | Return/sent/reply/engaged truth branches | **no** (derived evidence consumers) |
| `services/merchant_cart_row_classifier.py` | `merchant_cart_filter_counts_from_rows`, `merchant_nav_badge_waiting_count` | Dashboard filter counts | **no** (derived in Phase 1 from lifecycle state) |
| `services/merchant_recovery_lifecycle_truth.py` | `build_merchant_recovery_lifecycle_truth` + `attach_merchant_recovery_lifecycle_truth` | Additional lifecycle-like status strings (`returned_to_site`, `message_sent`, etc.) and explanation fields | **no** (read-only enrichment) |
| `services/recovery_truth_timeline_v1.py` | `provider_send_proven`, `customer_reply_proven`, `continuation_started_proven` | Evidence for sent/reply/engaged | **no** (evidence only) |
| `services/cartflow_session_truth.py` | `has_sent_truth`, `has_conversion_truth` | Cache-first sent/conversion gate checks | **no** (optimization only) |
| `services/merchant_cart_lifecycle_archive_v1.py` | `is_merchant_archived` / archive/reopen functions | Archive persistence state | **no** (evidence for lifecycle owner) |
| `services/cartflow_purchase_truth.py` | `has_purchase` and ingest functions | Purchase truth | **no** (evidence for lifecycle owner) |
| `main.py` | `_build_merchant_normal_cart_row_payload` | Executes three layers in parallel: classifier + merchant_recovery_lifecycle_truth + lifecycle v1 | **mixed (currently ambiguous)** |
| `main.py` | `_api_json_dashboard_normal_carts` | Counts and badges from classifier-derived fields (`merchant_cart_primary_bucket`, `merchant_cart_bucket`) | **no** (should be derived from lifecycle state) |
| `static/merchant_dashboard_lazy.js` | `cartLifecycleStatusLabel` / `cartLifecycleStatusClass` | Chip display chooses lifecycle first, fallback classifier | **no** (renderer only) |
| `static/merchant_dashboard_lazy.js` | table row render + filters (`data-ma-filter`, `merchant_cart_bucket`) | Tab grouping/count rendering from classifier fields | **no** (renderer only) |

### Focused inventory for requested states

| Requested state | Computed in | Current source type |
|---|---|---|
| waiting | lifecycle v1 + classifier | parallel decision |
| sent | lifecycle v1 + classifier + timeline evidence | parallel decision |
| reply | lifecycle v1 + classifier + timeline evidence | parallel decision |
| return | lifecycle v1 + classifier + behavioral/log evidence | parallel decision |
| archive | lifecycle v1 + archive table + client visual helper | mixed overlay/terminal semantics |
| purchase | lifecycle v1 + classifier + purchase truth | parallel decision |

---

## PART 2 — Truth ownership (target contract)

### Single owner

`customer_lifecycle_state` is the **only authoritative truth** for merchant-facing lifecycle semantics.

### Ownership matrix

| Concern | Owner in Phase 1 |
|---|---|
| Dashboard chip text/style | `customer_lifecycle_state` (via lifecycle v1 fields) |
| Dashboard tab bucket | **derived from `customer_lifecycle_state` only** |
| Dashboard counts/badges | **derived from `customer_lifecycle_state` only** |
| Archive grouping/row placement | `customer_lifecycle_state == archived` only |
| Merchant explanation block | lifecycle v1 explanation fields only |

### Non-owners

| Component | Role after unification |
|---|---|
| Classifier (`merchant_cart_row_classifier`) | **Derived compatibility adapter** (non-authoritative) |
| Timeline (`recovery_truth_timeline_v1`) | **Evidence store** only |
| Cache (`cartflow_session_truth`, `_session_recovery_*`) | **Optimization/gating** only |
| `merchant_recovery_lifecycle_truth` | **Supplemental diagnostics copy** only |

---

## PART 3 — Parallel decisions outside lifecycle owner

No deletions in this phase. Marking action type only.

### A) SAFE REMOVE (later cleanup PR)

1. UI fallbacks that can contradict lifecycle owner:
   - `merchant_dashboard_lazy.js`: `cartLifecycleStatusLabel()` fallback to `merchant_status_label_ar`.
2. Redundant visual class fallback:
   - `merchant_dashboard_lazy.js`: `cartLifecycleStatusClass()` fallback to `merchant_status_row_class`.
3. Count derivation from legacy tab arrays once lifecycle-tab mapping exists:
   - `merchant_cart_visible_tabs` dependency in counting/filter helpers.

### B) REPLACE (Phase 1 implementation target)

1. `main._api_json_dashboard_normal_carts` bucket counts:
   - Replace `merchant_cart_primary_bucket`/`merchant_cart_bucket` counting with lifecycle-state mapping.
2. Filter badge waiting count:
   - Replace classifier filter check with lifecycle-state mapped waiting set.
3. Table row filter attributes (`data-ma-filter`, `data-ma-primary-bucket`):
   - Replace with `data-ma-lifecycle-state` and a single lifecycle→tab mapper.
4. "Return chip vs Sent tab" split:
   - Replace `PRIMARY_RETURN_TO_SITE -> UI_FILTER_SENT` with lifecycle-owned tab mapping.
5. Archive grouping:
   - Replace mixed checks (`customer_lifecycle_is_archived_visual` OR state) with canonical `state == archived`.

### C) KEEP (read-only evidence / required compatibility)

1. Timeline proofs:
   - `provider_send_proven`, `customer_reply_proven`, `continuation_started_proven`.
2. Purchase evidence:
   - `has_purchase` truth path.
3. Archive persistence:
   - `merchant_cart_lifecycle_archive_v1` table and API.
4. Classifier module:
   - Keep as compatibility layer during migration, but marked non-authoritative.
5. Session truth cache:
   - Keep for execution optimization; no dashboard ownership.

---

## PART 4 — Acceptance model (one recovery_key, one truth)

For any row representing one lifecycle:

`Dashboard tab`  
= derived from `customer_lifecycle_state`  
= `Chip` from lifecycle label  
= `Explanation` from lifecycle explanation fields  
= `Count` from lifecycle-state aggregation  
= `Archive behavior` from lifecycle state/action.

### Canonical lifecycle -> tab mapping (proposed plan-level contract)

| `customer_lifecycle_state` | Tab |
|---|---|
| `waiting_first_send`, `active` | waiting |
| `waiting_customer_reply`, `waiting_next_scheduled`, `return_to_site` | sent |
| `customer_reply`, `customer_engaged`, `needs_intervention` | attention |
| `completed` | recovered |
| `archived` | archived (or all-with-archived slice per UI policy) |

> Note: exact tab names in UI can stay as-is; mapping source must be lifecycle-only.

### Impossible states (must fail validation)

| Impossible combination | Why invalid |
|---|---|
| Sent + Returned (as two simultaneous authoritative states) | Returned is its own lifecycle state, not a parallel flag |
| Archived + Waiting | Archived is terminal operational state |
| Reply + No reply | Timeline proof is binary for reply at a point-in-time state |
| Return + Engaged | Engaged requires reply+continuation; return-only cannot be engaged |

### Validation rule (plan)

At API payload build time for normal carts, enforce:
1. Exactly one `customer_lifecycle_state`.
2. Tab key generated from that one state.
3. Counts generated from tab/state mapping only.
4. Archive action determined only by lifecycle state/action fields.
5. Any conflicting legacy fields are treated informational, never deciding.

---

## Implementation boundary (this document only)

- This is a **documentation plan** for Phase 1 unification.
- No runtime behavior changed in this task.
- No files deleted or refactored in this task.

