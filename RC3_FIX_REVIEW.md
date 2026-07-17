# INV-002 RC-3 Fix Review — Membership · Composition · Session Evidence

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package | RC-3 Fix (B3 → B1 → B2) |
| Branch | `feature/inv002-rc3-fix` |
| Delivery commit | 32157cf (32157cfc…) |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-17 |

---

## Executive Summary

RC-3 Fix closes the three RV-C blockers without rewriting consumers or making Reality Attach an authority:

1. **B3** — Lab bind links `demo.merchant_user_id` and Phase 3 membership includes `demo` while **signup `primary_store_id` stays intact** (onboarding rejects system slug `demo`).
2. **B1** — `merchant_request_identity_bind` activates Reality Attach **before** MQIC bind on Home composition, Knowledge, and Daily Brief (Timeline via shared MQIC).
3. **B2** — Authenticated session evidence pack shows Home / Knowledge / Brief / Timeline on `demo` under ATTACH MQIC + simulation QTC with non-empty carts.

**STOP:** RV-C retry and Merchant Reality Validation are **not** executed in this WP.

---

## Branch / Commit

| Field | Value |
|-------|--------|
| **Branch** | `feature/inv002-rc3-fix` |
| **Base** | `feature/inv002-phase5` @ `973b4c2` |
| **Delivery commit** | 32157cf |
| **RC-3 + Phase 5 tests** | **25 passed** (`test_rc3_fix_composition` + `test_phase5_reality_attach`) |
| **`main.py` impact** | **None** |

---

## Files created

| Path |
|------|
| `services/identity_authority/lab_session_bind_v1.py` |
| `services/identity_authority/reality_attach_composition_v1.py` |
| `tests/identity_authority/test_rc3_fix_composition.py` |
| `docs/architecture/rc3_fix_session_evidence/rc3_session_evidence.json` |
| `RC3_FIX_REVIEW.md` |

## Files modified

| Path | Change |
|------|--------|
| `services/identity_authority/session_membership_v1.py` | Include owned Lab `demo` in membership |
| `services/identity_authority/__init__.py` | Export RC-3 APIs; `__version__ = "8"` |
| `services/merchant_home_composition_v1.py` | Composition bind via `merchant_request_identity_bind` |
| `routes/knowledge.py` | Attach headers before bind |
| `routes/daily_brief.py` | Attach headers before bind |
| `scripts/reality_validation_lab_v1_small.py` | Use Lab bind helper (B3) |
| `docs/SYSTEM_SUMMARY.md` | §10 |
| `docs/investigations/INV-002.md` | Status |

## Files intentionally untouched

| Path | Reason |
|------|--------|
| `main.py` | No wiring required; Home uses composition helper; routes self-contained |
| Consumer truth builders (KL/Brief/Timeline logic) | Consume MQIC only |
| Widget / Setup / WhatsApp / Recommendations | Out of scope |
| Platform Time / Identity Authority cores | Inputs only |

---

## B3 result

| Check | Result |
|-------|--------|
| Lab bind sets demo ownership | **PASS** |
| Signup primary unchanged | **PASS** (required — onboarding rejects `demo`) |
| Membership includes demo when owned | **PASS** |
| Unauthorized slug fail closed | **PASS** |
| Normal signup without Lab bind | **PASS** |

---

## B1 result

| Check | Result |
|-------|--------|
| Attach before bind (composition) | **PASS** |
| Home / Knowledge / Brief wired | **PASS** |
| Timeline via shared MQIC | **PASS** |
| QTC simulation clock | **PASS** |
| One MQIC / clean detach | **PASS** |
| Dual attach fail closed | **PASS** |
| Attach is not an authority | **PASS** |

**Lab headers:** `x-cartflow-reality-attach-run-id`, `x-cartflow-reality-attach-start`

---

## B2 evidence

Artefact: `docs/architecture/rc3_fix_session_evidence/rc3_session_evidence.json`

| Field | Value |
|-------|--------|
| simulation_run_id | `srs_rc3_fix_walkthrough` |
| store_slug | `demo` |
| MQIC path | `attach` |
| QTC | `simulation` @ 2026-05-04T12:00:00+00:00 |
| Knowledge cart_count | **3** |
| Timeline evidence events | **1** |
| Activity timeline store | `demo` |
| Home / Brief store | `demo` |
| Detach path | `primary` (signup; not ATTACH) |
| Verdict | **PASS** |

---

## Authority chain / MQIC / QTC / Membership

```text
Lab bind → demo ∈ membership (primary = signup)
     ↓
merchant_request_identity_bind + Attach headers
     ↓
Time Authority SIMULATION + Identity Authority ATTACH → MQIC(demo)
     ↓
Home / Knowledge / Brief / Timeline consume MQIC
     ↓
Detach → primary signup MQIC, no sim QTC
```

---

## Fail-closed / contract tests

Covered in `test_rc3_fix_composition.py`: membership alignment, normal path, attach activation, shared MQIC, QTC clock, dual attach, unauthorized Lab slug, incomplete inputs, detach, deterministic replay, HTTP Knowledge/Brief + Home compose walkthrough.

---

## Impact

| Dimension | Impact |
|-----------|--------|
| Query | One optional owned-demo lookup in `load_session_membership` (same Store table; no new query class) |
| I/O | None (no provider) |
| Latency | Negligible |
| Scheduler / Pool | None |
| `main.py` | Untouched |
| Merchant UX | Unchanged when Attach headers absent |

---

## Architectural debt

| Removed | Introduced |
|---------|------------|
| Lab bind that set ownership without membership | Lab headers are walkthrough-scoped (document; not merchant chrome) |
| Attach library unused on HTTP | Membership special-case for owned `demo` (Lab-only; documented) |

---

## Rollback boundary

Revert RC-3 Fix commit(s). Phase 5 Attach library remains. Production unattached sessions unchanged.

---

## Recommendation for RV-C retry

**Ready to re-run RV-C** after Architecture + PO acknowledgment. Evidence pack + composition path address B1–B3. Do **not** start Merchant Reality Validation until RV-C is **APPROVED**.

---

## STOP

No RV-C execution in this WP.  
No Merchant Reality Validation.  
No INV-002 closure.  
Await Architecture Review and Product Owner acknowledgment.
