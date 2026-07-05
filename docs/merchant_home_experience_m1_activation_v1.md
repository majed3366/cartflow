# CartFlow Merchant Home Experience M1 Activation V1

**Status:** Implemented  
**Date (UTC):** 2026-07-06  
**Scope:** Transport-independent activation of Merchant Home Experience on `GET /api/dashboard/summary`  
**Authority:** Follows [`merchant_experience_m1_reality_verification_v1.md`](merchant_experience_m1_reality_verification_v1.md)  
**Not in scope:** Composition, routing, wording, CSS, Product Excellence  

---

## Problem

M1 architecture was complete on the **live builder** path, but production serves summary via **snapshot read**. Pre-M1 snapshots and degraded payloads omitted `merchant_home_experience_v1`, leaving Home stuck on the static greeting shell.

---

## Solution

### Transport-independent contract

Module: `services/merchant_home_experience_activation_v1.py`

| Function | Role |
|----------|------|
| `finalize_dashboard_summary_payload()` | Single exit contract for all summary transports |
| `ensure_merchant_home_experience_on_summary()` | Attach home when missing via certified `compose_merchant_home_experience_v1` + summary context |
| `stamp_summary_contract_fields()` | Stamp `summary_contract_schema_version` |
| `build_merchant_home_transport_diagnostics()` | Operational `_merchant_home_transport` block |

**Schema version:** `merchant_home_m1_v1`

### Paths covered

| Path | Activation hook |
|------|-----------------|
| **Live builder** | `_api_json_dashboard_summary()` stamps contract; `api_dashboard_summary()` calls `finalize_dashboard_summary_payload(..., TRANSPORT_LIVE)` |
| **Snapshot read** | `build_summary_from_snapshot()` calls `finalize_dashboard_summary_payload(..., TRANSPORT_SNAPSHOT \| DEGRADED)` |
| **Snapshot HTTP** | `api_dashboard_summary()` snapshot branch re-finalizes (idempotent) |
| **Response cache** | Any future cache must store **post-finalize** payloads only (`dashboard_response_cache_v1` contract) |

Snapshot-safe compose uses **summary fields only** (brief embed, nav badges, setup name) — no hot-path DB queries during snapshot HTTP requests.

### Snapshot governance

In `write_dashboard_snapshot_guarded()` (`dashboard_snapshot_change_v1.py`):

When latest summary snapshot is **contract-stale** (missing home or schema version), next builder tick **forces WRITE** with reason `summary_contract_upgrade` — no manual rebuild required.

Read-time activation still guarantees merchant visibility **before** the upgrade write completes.

### Frontend

`merchant_dashboard_lazy.js`:

- Removed broken `#ma-daily-brief-root` fallback  
- Always calls `maApplyHomeExperience(payload || { ok: false })` — merchant-safe empty state, never silent blank  

### Observability (ops only)

Every valid summary response may include:

```json
"_merchant_home_transport": {
  "summary_source": "live|snapshot|cache|degraded",
  "cache_hit": false,
  "merchant_home_experience_attached": true,
  "home_attach_mode": "present|composed_from_summary|degraded_empty",
  "composition_version": "v1",
  "summary_contract_schema_version": "merchant_home_m1_v1",
  "snapshot_version": 0,
  "snapshot_degraded": false,
  "snapshot_stale": false
}
```

Merchants never see this block in UI — API/ops verification only.

---

## Future schema additions

1. Bump `SUMMARY_CONTRACT_SCHEMA_VERSION` when summary contract fields change materially.  
2. Extend `summary_snapshot_contract_stale()` to detect the new version.  
3. Builder auto-writes on next tick (`summary_contract_upgrade`).  
4. Read-time `finalize_dashboard_summary_payload()` hydrates missing fields until stored snapshots catch up.  

---

## Verification

Tests: `tests/test_merchant_home_experience_activation_v1.py`

---

*End of Merchant Home Experience M1 Activation V1.*
