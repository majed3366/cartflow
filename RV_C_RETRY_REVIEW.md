# RV-C Retry Review — Reality Validation Gate C (Simulation Attach Honesty)

**Document type:** Architectural + product-truth validation gate (not engineering)  
**Status:** **Decision recorded**  
**Gate:** RV-C Retry — Simulation attach honesty  
**Investigation:** INV-002 — Merchant Identity Drift  
**Reviewed tip (UTC):** 2026-07-17 — branch `feature/inv002-rc3-fix` @ `a841157` (delivery `32157cf`)  
**Prior gate:** [`RV_C_REVIEW.md`](RV_C_REVIEW.md) — **NOT APPROVED**  
**Fix input:** [`RC3_FIX_REVIEW.md`](RC3_FIX_REVIEW.md) · [`docs/architecture/rc3_fix_session_evidence/rc3_session_evidence.json`](docs/architecture/rc3_fix_session_evidence/rc3_session_evidence.json)  
**ICT re-run (this gate):** `test_rc3_fix_composition` + `test_phase5_reality_attach` — **25 passed**

> **Mission question:** Is the platform now ready for the first truthful Merchant Reality Validation?  
> **Not this document:** Implementation, additional fixes, Merchant Reality Validation execution, INV-002 closure.

**STOP:** No implementation under this task. No Merchant Reality Validation execution.

---

## Executive Summary

### Decision

# APPROVED

### One-sentence verdict

On the reviewed tip, an **authenticated merchant session with Lab Reality Attach headers** binds **one ATTACH MQIC + one simulation QTC** and Home / Knowledge / Daily Brief / Timeline observe **the same `demo` simulation truth** (evidence: 3 carts, ≥1 timeline event); prior blockers **B1–B3 are closed**.

### Mission answer

| Question | Answer |
|----------|--------|
| Does one authenticated attached session observe Platform Authority truth? | **Yes** (Lab header walkthrough / composition path) |
| Ready for first truthful Merchant Reality Validation? | **Yes — bounded**, under the Attach-activation constraints below |
| Authorize INV-002 closure? | **No** |

### Frozen RV-C checks (Execution Architecture §6)

| Check | Result |
|-------|--------|
| Run canonical ≡ walkthrough MQIC after Attach | **PASS** — `demo` / ATTACH (`rc3_session_evidence.json`) |
| Session surfaces see sim truth (≥1 cart / non-empty) | **PASS** — Knowledge `cart_count=3` |
| Probe-`demo` alone insufficient | **PASS** — cookie session + Attach composition / HTTP |
| Write isolation (C3) under attach | **Not re-filed** — **non-blocking** for this APPROVED (Phase 3.1 historically green; Attach is read-path; re-confirm during MV) |

---

## 1. Previous Blocker Closure Matrix

| ID | Prior RV-C finding | RC-3 Fix closure | Retry verdict |
|----|--------------------|------------------|---------------|
| **B3** | Signup primary ≠ demo; Lab bind incomplete; Attach would fail-closed | `lab_session_bind_v1` owns demo; membership includes demo; **primary unchanged** (onboarding rejects system slug) | **CLOSED** |
| **B1** | Attach only in ICT; HTTP never activated | `merchant_request_identity_bind` before MQIC on Home composition, Knowledge, Brief; Timeline shares MQIC | **CLOSED** |
| **B2** | No session evidence pack | `rc3_session_evidence.json` + ICT walkthrough | **CLOSED** |

### B3 revalidation

| Check | Result | Evidence |
|-------|--------|----------|
| demo via canonical membership | **PASS** | `test_b3_lab_align_sets_membership_keeps_signup_primary` |
| signup `primary_store_id` unchanged | **PASS** | Same; Lab bind forbids primary=demo |
| onboarding system-slug protection intact | **PASS** | `resolve_merchant_onboarding_store` still rejects widget-recovery zids including `demo` |
| Attach fail-closed without valid membership | **PASS** | `attach_membership_denied` when demo ∉ membership; Lab slug forbid |

### B1 revalidation

| Check | Result | Evidence |
|-------|--------|----------|
| Attach before MQIC | **PASS** | `reality_attach_composition_v1.merchant_request_identity_bind` |
| Home / Knowledge / Brief use attached MQIC | **PASS** | Home composition + routes; ICT walkthrough |
| Timeline same MQIC | **PASS** | `test_b2_consumers_share_one_attached_mqic` |
| Attach is input only (`is_authority: false`) | **PASS** | Phase 5 + composition diagnostics |

### B2 revalidation (evidence pack)

| Check | Result | Pack field |
|-------|--------|------------|
| Simulation Run ID | **PASS** | `srs_rc3_fix_walkthrough` |
| Identity provenance ATTACH | **PASS** | `mqic.resolution_path=attach` |
| QTC simulation time | **PASS** | `mode=simulation`, `authoritative_now=2026-05-04T12:00:00+00:00` |
| Home simulation-backed | **PASS** | `home.store_slug=demo`, `ok=true` |
| Knowledge ≥3 carts | **PASS** | `cart_count=3` |
| Timeline ≥1 event | **PASS** | `timeline_evidence_events=1` |
| Brief same store / path | **PASS** | `daily_brief.store_slug=demo` |
| No signup/demo split under Attach | **PASS** | All reviewed surfaces `demo`; detach → `primary` (signup) |

---

## 2. Authority Health

| Authority | Health |
|-----------|--------|
| **Platform Identity Authority** | Sole MQIC author; ATTACH path sealed; dual-resolve fail closed |
| **Platform Time Authority** | Sole clock under Attach (`simulation` / `authority_now`) |
| **Reality Attach** | Input binder only; composed at approved points; not an authority |

---

## 3. Authenticated Session Walkthrough

```text
Session cookie (merchant auth)
        ↓
load_session_membership
  · primary = signup store (unchanged)
  · membership ⊇ { signup, demo } when Lab-owned
        ↓
Lab Attach headers
  x-cartflow-reality-attach-run-id
  x-cartflow-reality-attach-start
        ↓
merchant_request_identity_bind
  → Reality Attach → QTC SIMULATION
  → ResolveMQIC ATTACH → sealed MQIC(demo)
        ↓
Home (composition) · Knowledge (HTTP) · Daily Brief (HTTP)
  · Timeline via shared MQIC / evidence readers
        ↓
Request exit → detach
  · MQIC cleared · Attach cleared · QTC restored
  · Next unattached resolve → PRIMARY signup
```

| Assert | Result |
|--------|--------|
| Identity resolved once per attach scope | **PASS** |
| Time source bound once (QTC) | **PASS** |
| One immutable MQIC reused across consumers | **PASS** |
| No surface-local identity / time | **PASS** (reviewed surfaces) |
| Detach restores normal session path | **PASS** (`detach_path=primary`) |

---

## 4. Truth Consistency Matrix

Under **one attached session** (evidence + ICT):

| Dimension | Home | Knowledge | Daily Brief | Timeline |
|-----------|------|-----------|-------------|----------|
| Merchant identity | Session merchant | Same | Same | Same |
| Store identity | `demo` | `demo` | `demo` | `demo` |
| MQIC seal | Authority | Authority | Authority | Authority |
| Identity provenance | ATTACH | ATTACH | ATTACH | ATTACH |
| Time provenance | simulation QTC | simulation QTC | simulation QTC | simulation QTC |
| Simulation Run ID | `srs_rc3_fix_walkthrough` | Same | Same | Same |
| Evidence / data | Home ok on demo | **3 carts** | Same MQIC tenant | **≥1** recovery-truth event; activity section slug `demo` |

**Matrix verdict:** Agreement on attached truth. No signup/demo split **while Attach is active**.

---

## 5. Evidence Provenance Review

| Provenance | Present | Merchant-facing? |
|------------|---------|------------------|
| Time source (simulation QTC) | Yes | No (ops) |
| Identity source (`platform_identity_authority`) | Yes | No (`identity_authority_v1`) |
| Simulation run id | Yes | No |
| Authority owner | Yes | No |
| Evidence chain (carts / timeline events) | Yes on session path | Surfaces speak derived truth for attached tenant |

---

## 6. Failure Injection Results

| Injection | Fail-closed? | Evidence |
|-----------|--------------|----------|
| Missing / unauthorized Lab membership | **Yes** | `attach_membership_denied` / Lab slug forbid |
| Incomplete Attach inputs | **Yes** | `attach_inputs_incomplete` |
| Dual Attach | **Yes** | `attach_already_active` |
| Slug mismatch vs MQIC | **Yes** | 403 / `store_slug_mismatch` (routes + consumers) |
| Detached QTC / MQIC after scope | **Yes** | ICT detach clean |
| Stale Attach after detach | **Yes** | `peek_attach` / get_mqic None |
| Silent second truth fallback | **Not observed** on reviewed attached path | Unattached path correctly uses signup primary (labelled by absence of Attach) |

---

## 7. Merchant Honesty Assessment

| Surface | Attached session honesty |
|---------|--------------------------|
| Home | Observes attached `demo` truth via composition when Attach inputs present |
| Knowledge | HTTP session + Attach headers → 3 sim carts |
| Daily Brief | Same MQIC tenant |
| Timeline | Evidence + activity slug aligned to `demo` |

**Ruling:** Under the Lab Attach walkthrough, merchants see **attached platform truth**, not a reconstructed probe overlay and not the empty signup store.

Feature completeness is out of scope. Widget / Setup / WhatsApp are out of acceptance scope.

---

## 8. Remaining Risks

| Risk | Classification | Notes |
|------|----------------|-------|
| **`main.py` dashboard summary does not forward Attach headers** to Home composition | **Non-blocking for Lab-harness MV**; **Blocking if** first MV claims success via browser `/dashboard` summary **without** header injection or equivalent Attach activation | Wire or Lab-inject before browser-only PO Home acceptance |
| Phase 3.1 write isolation not re-filed under Attach | **Non-blocking** | Re-confirm during MV / RC-3 residual |
| Activity Timeline `while_away` items may be empty while evidence events exist | **Non-blocking** | Achievements feed-dependent; evidence reader + slug parity proven |
| Lab headers are walkthrough-scoped | **Non-blocking** | Must not ship as merchant chrome; document for Lab |
| Owned-`demo` membership special case | **Non-blocking** | Lab-only; fail-closed if not owned |
| Widget / Setup / cart KPI / auth-slug E1 | **Deferred / out of scope** | Must not be MV acceptance surfaces |
| Alias pollution on shared Lab DB | **Operational** | Evidence tests re-pin `demo` alias; Lab hygiene |

---

## 9. Decision

| Field | Value |
|-------|--------|
| **Decision** | **APPROVED** |
| **Authorizes** | **First bounded Merchant Reality Validation only** (Home / Knowledge / Daily Brief / Timeline on attached session path) |
| **Does not authorize** | INV-002 closure · Widget/Setup/WhatsApp acceptance · unrestricted browser `/dashboard` claim without Attach activation · Phase 6–8 closure narrative |

### Authorization constraints for first Merchant Reality Validation

1. Activate Reality Attach (Lab headers or equivalent) on the walkthrough session for Knowledge, Daily Brief, and Home composition.  
2. Accept only surfaces that share ATTACH MQIC + simulation QTC for `demo` (or run canonical).  
3. Do **not** accept probe-only `demo` service calls as success.  
4. Do **not** accept unattached signup-primary emptiness as “product broken” during the campaign.  
5. If PO eyes use `/dashboard` summary Home, ensure Attach inputs reach Home composition (header forward or Lab injection) before scoring Home.

### Approval record

| Role | Required |
|------|----------|
| Architecture Board | ☐ Acknowledge RV-C Retry **APPROVED** |
| Product Owner | ☐ May begin **first bounded Merchant Reality Validation** under constraints |
| Engineering Lead | ☐ Support Lab harness; no INV-002 closure |

---

## STOP

No implementation.  
No additional fixes.  
No Merchant Reality Validation execution in this task.  
No INV-002 closure.  

**RV-C Retry = APPROVED.** Await Architecture Review and Product Owner acknowledgment before starting the first bounded Merchant Reality Validation.
