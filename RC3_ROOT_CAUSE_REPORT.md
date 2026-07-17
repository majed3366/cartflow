# RC-3 Root Cause Report — Why Merchant Session Misses Attached Truth

**Document type:** Root-cause investigation (not engineering)  
**Status:** **Decision recorded**  
**Investigation:** INV-002 — Merchant Identity Drift  
**Trigger:** [`RV_C_REVIEW.md`](RV_C_REVIEW.md) — **NOT APPROVED**  
**Reviewed tip (UTC):** 2026-07-17 — branch `feature/inv002-phase5` @ `820a837`  
**Upstream:** Phase 5 Attach · RV-B · INV-002 RCA · Execution Architecture §6 (RV-C / RC-3)

> **Mission:** Determine why a real merchant HTTP session does not observe the same attached truth as Platform Authorities, and produce a **minimal corrective plan**.  
> **Not this document:** Implementation, Attach expansion, consumer rewrites, Authority redesign, Merchant Reality Validation, RV-C retry.

**STOP:** No implementation under this task.

---

## Executive Summary

### Verdict

# READY FOR RC3 FIX

RV-C failed for three **known, localized** causes — not because Time Authority, Identity Authority, or Reality Attach are architecturally wrong.

| Blocker | One-line root cause |
|---------|---------------------|
| **B1** | Phase 5 delivered Attach as a **library API**; merchant HTTP composition **never calls it** before Phase 3 MQIC bind. |
| **B2** | RC-3 evidence requires an attached **session path**; without B1 (+ B3), that path cannot exist, so no pack was filed. |
| **B3** | Lab “bind demo” never puts `demo` on the Phase 3 membership/primary path; signup store ≠ sim tenant; Attach would fail-closed even if composed. |

### Mission answer

A merchant HTTP session observes Platform Authority truth for whatever MQIC/QTC that request binds. Today that bind is **unattached primary/session identity** (signup store) under ambient/production time. Attached simulation truth exists only when `reality_attach_scope` runs — **only in ICT tests**.

### Recommendation

Authorize a **minimal RC-3 Fix Work Package** that (in order) closes **B3 → B1 → B2**, then re-run **RV-C**. Do **not** reopen the broader INV-002 investigation.

---

## 1. Root Cause Matrix

| ID | Observed | Expected | Architectural owner | Root cause | Minimal corrective action |
|----|----------|----------|---------------------|------------|---------------------------|
| **B1** | `reality_attach_scope` only in ICT; Home/KL/Brief HTTP never enter Attach | Merchant walkthrough request activates Attach **inputs**, then Authorities | Composition root (not Authorities, not consumers) | Phase 5 deliberately left `main.py` / Home / routes untouched; no composition call site | Add thin composition before Phase 3 bind on walkthrough path |
| **B2** | No session pack with ≥1 cart under attached MQIC+QTC | RC-3 / ICT-22 session evidence for Home+KL+Brief+Timeline | Evidence / Lab harness (after B1+B3) | Evidence is a consequence of missing path, not a separate product defect | File minimum evidence set once composition+membership work |
| **B3** | Signup primary store empty; sim on `demo`; Lab sets `demo.merchant_user_id` only | One canonical path: session membership includes run store; Attach can authorize | Session & membership (Phase 3 inputs) + Lab bind | `_signup_and_bind_demo` never sets `primary_store_id`; Phase 3 membership = `{primary}` only | Lab/session membership alignment so run canonical ∈ membership (and active/primary for walkthrough) |

---

## 2. Execution Path Diagram

### 2.1 Current merchant HTTP path (RV-C failure)

```text
Merchant cookie
      │
      ▼
resolve_merchant_onboarding_store ──▶ Store = primary_store_id (signup slug)
      │
      ▼
load_session_membership
      │  membership = { signup canonical only }
      │  demo NOT in membership
      ▼
bind_mqic_* / resolve_mqic_from_session
      │  NO reality_attach_scope
      │  path = PRIMARY | SESSION (not ATTACH)
      │  QTC = ambient / production (unless unrelated scope)
      ▼
Home / Knowledge / Daily Brief / Timeline
      │  consume mqic.store_slug = signup
      ▼
Empty / activation  ≠  sim truth on demo
```

### 2.2 ICT-only attached path (architecturally correct, not merchant HTTP)

```text
Synthetic SessionMembershipSnapshot (includes demo)
      │
      ▼
reality_attach_scope(run_id, demo canonical, SimulationClock)
      ├─▶ Time Authority  SIMULATION QTC
      └─▶ Identity Authority  ATTACH MQIC
      ▼
ensure_* consumers share one MQIC
      ▼
ICT green — never exercised by /dashboard or /api/... session routes
```

### 2.3 Legal composition entry (B1 — where Attach must enter)

Attach must remain an **input binder**, not a second authority.

```text
HTTP request (cookies) + optional walkthrough attach declaration
      │
      ▼
【 COMPOSITION ROOT — legal Attach entry 】
   1. load_session_membership(cookies)     ← Phase 3 inputs
   2. IF walkthrough attach authorized:
        register Attach inputs / reality_attach_* scope
        (simulation_run_id, canonical, clock/as-of)
      │  FORBIDDEN: resolve store_slug here
      │  FORBIDDEN: invent MQIC outside Authority
      │  FORBIDDEN: bypass Time Authority
      ▼
   3. bind_mqic_for_* / resolve_mqic_from_session
        ← Phase 3 merges peek_attach_resolve_inputs → ATTACH
      ▼
   4. Home / KL / Brief / Timeline consume MQIC only
```

**Exact call sites that must gain composition (minimal set for RV-C surfaces):**

| Surface path | Current bind | Legal Attach entry (before bind) |
|--------------|--------------|----------------------------------|
| Home (summary → `build_merchant_home_experience_api_payload`) | `bind_mqic_for_dashboard_home(cookies=…)` in `merchant_home_composition_v1.py` | Immediately **before** that bind (or shared helper used by it) |
| Knowledge HTTP | `bind_mqic_from_merchant_session` in `routes/knowledge.py` | Same helper before bind |
| Daily Brief HTTP | `bind_mqic_for_daily_brief` in `routes/daily_brief.py` | Same helper before bind |
| Timeline | Nested under Home MQIC (WP-6) | Covered if Home composition attaches first |

**Not legal:** global middleware that *owns* identity/time; `main.py` business rules; surface-local `demo` seals (`mqic_from_caller_store_slug` as walkthrough success).

---

## 3. Blocker deep-dives

### B1 — Merchant-session Reality Attach composition

| Field | Detail |
|-------|--------|
| **Observed behaviour** | Grep: `reality_attach_scope` / `reality_attach_declaration_scope` only under `tests/identity_authority/test_phase5_reality_attach.py`. Home composition binds MQIC from cookies with no Attach. `main.py` has zero Attach references. |
| **Expected behaviour** | Walkthrough/lab merchant request activates Attach inputs, then Phase 3/Authority bind yields ATTACH MQIC + simulation QTC for that request. |
| **Architectural owner** | Request composition root (thin helper). Attach module already exists; Authorities already accept inputs. |
| **Root cause** | Phase 5 success criteria were **binder + ICT**, explicitly **no consumer / main.py wiring**. RV-C requires the **session path**; Phase 5 did not deliver it. |
| **Evidence** | `Phase5_REVIEW.md` “Files intentionally untouched”; `RV_C_REVIEW.md` B1; codebase call-site inventory. |
| **Affected execution path** | `/dashboard` summary Home payload; Knowledge/Brief API routes; any walkthrough that opens those surfaces. |
| **Why prior gates missed it** | RV-B asked “one MQIC across surfaces,” not “Attach on HTTP.” Phase 5 asked “Attach library correct,” not “merchant HTTP activates Attach.” RV-C is the first gate that requires both. |
| **Minimal corrective action** | One shared composition helper: membership → (optional) Attach activate → existing `resolve_mqic_from_session` / bind. Wire only Home + Knowledge + Brief entrypoints. No consumer truth rewrite. |

### B2 — Missing RC-3 session-path evidence

| Field | Detail |
|-------|--------|
| **Observed behaviour** | No artefact proving same merchant session: MQIC ≡ run canonical, QTC simulation, Home/KL/Brief/Timeline non-empty agreement. |
| **Expected behaviour** | RC-3 / ICT-22 pack: session path ≥1 cart (or equivalent honest non-empty), correlation ids, not probe-only. |
| **Architectural owner** | Lab / evidence harness (depends on B1+B3). |
| **Root cause** | Evidence cannot be collected until the session path can Attach with authorized membership. Absence is **downstream of B1+B3**, not an independent Authority failure. |
| **Evidence** | Execution Architecture §6 RV-C; `RV_C_REVIEW.md` B2; Phase 5 ICT lacks HTTP session + DB sim content asserts. |
| **Affected execution path** | RV-C re-attempt; first Merchant Reality Validation authorization. |
| **Why prior gates missed it** | Phase 5 ICT intentionally synthetic; Checkpoint V2 used `demo` probes (now correctly rejected). |
| **Minimal corrective action** | After B3+B1: one Lab/scripted session walkthrough → JSON+screenshots under agreed evidence path (see §5). |

**Can Home / Knowledge / Daily Brief / Timeline demonstrate attached sim truth in one session?**

| Surface | Capable once B1+B3 true? | Notes |
|---------|--------------------------|-------|
| Home | **Yes** | Nested Brief + Knowledge + Timeline already share one MQIC |
| Knowledge | **Yes** | Session bind + `mqic.store_slug` |
| Daily Brief | **Yes** | Same |
| Timeline | **Yes** | Under Home MQIC (WP-6) |

Minimum evidence set for RV-C (B2 deliverable):

1. `simulation_run_id`, correlation id, cookie/session id (redacted)  
2. MQIC dump: `store_slug`, `canonical_store_id`, `resolution_path=attach`, `simulation_run_id`  
3. QTC dump: mode=`simulation`, `simulation_run_id`, `authoritative_now`  
4. Same request/session: Home payload identity diagnostics + non-empty honest signal (≥1 cart or KL cart_count≥1)  
5. Knowledge + Brief + Timeline identity fields equal to MQIC  
6. Explicit note: **not** standalone `build_knowledge_report("demo")` probe  
7. Optional: Phase 3.1 write-isolation green under attach (residual)

### B3 — Signup → demo membership divergence

| Field | Detail |
|-------|--------|
| **Observed behaviour** | Signup creates Store A + `MerchantUser.primary_store_id=A`. Lab `_signup_and_bind_demo` sets `demo.merchant_user_id=user` and attempts nonexistent `user.store_id`; **does not** set `primary_store_id` to demo. Phase 3 `membership_store_ids = {primary only}`. |
| **Expected behaviour** | For attached walkthrough: merchant membership includes run canonical (`demo`); Phase 3/Attach can resolve ATTACH to that store without inventing a second channel. |
| **Architectural owner** | Session & membership inputs (Phase 3) + Lab bind script (composition of inputs). Not Attach-as-authority. |
| **Root cause** | **Two identities, one cookie:** account linked loosely to `demo` via `merchant_user_id`, but **session tenant** remains signup primary. Attach requires membership of the sim store → would `attach_membership_denied` if composed today against real cookies. |
| **Evidence** | `scripts/reality_validation_lab_v1_small.py` `_signup_and_bind_demo` L334–370; `session_membership_v1._membership_from_primary`; INV-002_REVIEW RCA; Checkpoint `merchant_store_scoping`. |
| **Affected execution path** | Every session resolve after Lab signup; Attach authorization; RV-C honesty. |
| **Why prior gates missed it** | INV-002 RCA documented it; Identity WPs unified **speech path** on whatever primary is — they did not fix Lab bind. Phase 5 Attach correctly fail-closes unauthorized stores (makes B3 visible as a hard gate). |
| **Minimal corrective action** | Align Lab/walkthrough inputs so run canonical ∈ membership and is the attach target (e.g. set `primary_store_id` to demo **or** expand membership snapshot to include demo for authorized review — Board chooses one minimal policy). Do **not** teach surfaces to seal probe `demo` while session primary remains signup. |

#### B3 — Do identities share one canonical path?

| Identity artefact | Path today | Same as sim `demo`? |
|-------------------|------------|---------------------|
| Merchant signup store | `primary_store_id` → signup `zid_store_id` | **No** |
| Lab bind | `demo.merchant_user_id` only | Ownership hint only |
| Phase 3 membership | `{ primary }` | **Signup only** |
| MQIC (HTTP) | PRIMARY/SESSION from membership | **Signup** |
| Simulation writes | SRS → `demo` | **demo** |
| Attach (if activated with real membership) | Requires demo ∈ membership | **Would fail closed** |

**Divergence point:** Lab bind / primary store assignment — **before** Attach and **before** MQIC. Not inside Time Authority. Not inside consumer presentation.

---

## 4. Evidence (inventory)

| Source | Supports |
|--------|----------|
| `RV_C_REVIEW.md` | B1–B3 blockers; NOT APPROVED |
| `Phase5_REVIEW.md` | Attach binder correct; consumers/`main.py` intentionally untouched |
| `tests/identity_authority/test_phase5_reality_attach.py` | Sole Attach call sites |
| `services/merchant_home_composition_v1.py` ~L367 | Home bind without Attach |
| `routes/knowledge.py` / `routes/daily_brief.py` | Separate HTTP binds without Attach |
| `session_membership_v1._membership_from_primary` | Single-store membership = primary |
| `scripts/reality_validation_lab_v1_small.py` `_signup_and_bind_demo` | Incomplete demo bind |
| `docs/investigations/INV-002_REVIEW.md` | Original RCA (signup ≠ demo) |
| Checkpoint V2 `merchant_store_scoping` | demo_carts=27 vs signup carts=0 |

---

## 5. Corrective Plan

### B3 — Membership / Lab bind alignment

| Field | Plan |
|-------|------|
| **Minimal implementation** | Lab/walkthrough: ensure merchant session membership includes simulation canonical (`demo` for current Lab). Prefer setting `MerchantUser.primary_store_id` to demo store **or** Board-approved Phase 3 membership expansion for review-only — one path, fail-closed if unauthorized. |
| **Owner** | Engineering (Lab bind + Phase 3 input alignment) under Architecture constraints |
| **Rollback boundary** | Revert Lab bind / membership input change; production merchants without Attach unchanged |
| **Identity impact** | Session MQIC can legally ATTACH to run store; no second MQIC author |
| **Time Authority impact** | None directly |
| **Merchant-facing impact** | Walkthrough session tenant becomes sim store (labelled via Attach provenance ops-side); must not silent-remap production merchants |
| **Operational impact** | Lab scripts stop claiming “bound” when primary still signup |
| **Testing required** | Membership includes demo; unauthorized attach still denied; production signup path regression |

### B1 — Composition root Attach activation

| Field | Plan |
|-------|------|
| **Minimal implementation** | Shared helper used by Home composition + Knowledge/Brief routes: if walkthrough Attach declaration present/authorized → `reality_attach_scope` or declaration scope **then** existing Phase 3 bind. Attach supplies inputs only. |
| **Owner** | Engineering (composition) |
| **Rollback boundary** | Remove helper wiring; Attach library remains; production unattached path intact |
| **Identity impact** | MQIC path becomes ATTACH when declaration active; still Authority-sealed |
| **Time Authority impact** | QTC SIMULATION when Attach binds time; still TA-owned |
| **Merchant-facing impact** | None until declaration active; when active, surfaces show sim tenant truth |
| **Operational impact** | `attach_diagnostics` / `identity_authority_v1` on walkthrough requests |
| **Testing required** | ICT: HTTP-or-composition test that cookies+declaration → ATTACH MQIC; dual-resolve still fail closed; no `main.py` ResolveMQIC logic |

### B2 — Session evidence pack

| Field | Plan |
|-------|------|
| **Minimal implementation** | Scripted attached session against Small Reality (or equivalent) → evidence JSON + screenshots (Home; KL/Brief/Timeline identity equality; ≥1 cart class signal) |
| **Owner** | Engineering + Lab evidence |
| **Rollback boundary** | Evidence artefacts only |
| **Identity / Time impact** | None (observation) |
| **Merchant-facing impact** | None |
| **Operational impact** | RV-C re-attempt package |
| **Testing required** | Checklist in §3 B2 minimum evidence set; Phase 3.1 under attach recommended |

---

## 6. Implementation Order

```text
1) B3  Membership / Lab bind alignment
        ↓  (Attach can authorize run store)
2) B1  Composition root activates Attach before Phase 3 bind
        ↓  (HTTP session can enter attached Authority chain)
3) B2  File RC-3 session evidence pack
        ↓
4) Re-run RV-C  (separate gate task — not authorized here)
```

**Dependency rule:** B2 must not start as a “probe campaign.” B1 without B3 yields fail-closed empty attach. B3 without B1 leaves session on demo primary **or** multi-member without ATTACH/QTC — insufficient for full RV-C (time + attach provenance) if only primary is flipped without Attach; for Lab honesty, **B3+B1 together** are the minimal truthful pair; B2 proves it.

---

## 7. Risk Analysis

| Risk | If ignored | If over-built |
|------|------------|---------------|
| Compose Attach in `main.py` as business logic | ICT-40 / composition-only breach | Prefer thin service helper |
| Seal `demo` via `mqic_from_caller_store_slug` for PO eyes | False green (RV-B E4) | Forbidden as acceptance |
| Expand membership for all merchants to all stores | Tenant leak | Lab/walkthrough-scoped only |
| Skip B3 and only Attach | `attach_membership_denied` | Must fix inputs first |
| Skip evidence (B2) and claim RV-C | Gate fraud | Always file RC-3 pack |
| Modify Home/KL/Brief/Timeline truth logic | Scope creep / G-IA-1 risk | Consumers stay MQIC consumers |

---

## 8. Decision

| Field | Value |
|-------|--------|
| **Recommendation** | **READY FOR RC3 FIX** |
| **Reopen INV-002 investigation?** | **No** — causes are identified and scoped to B1–B3 |
| **Authorize implementation in this task?** | **No** |
| **Authorize RV-C retry in this task?** | **No** |
| **Authorize Merchant Reality Validation?** | **No** |

### Approval record

| Role | Required |
|------|----------|
| Architecture Board | ☐ Acknowledge RC-3 findings + READY FOR RC3 FIX |
| Product Owner | ☐ Acknowledge Merchant Reality Validation remains blocked until RV-C APPROVED |
| Engineering Lead | ☐ May open RC-3 Fix WP (B3→B1→B2) after normal authorization |

---

## STOP

No implementation.  
No RV-C retry.  
No Merchant Reality Validation.  

Await Architecture Review and Product Owner approval before opening the RC-3 Fix Work Package.
