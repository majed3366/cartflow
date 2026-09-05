# Commercial Decision Lifecycle Truth Audit V1 — Reuse Matrix

**Date (UTC):** 2026-09-05  
**Companion:** `00_EXISTING_LIFECYCLE_INVENTORY.md`  

Marks: **REUSE** · **PARTIAL** · **NO** · **DANGEROUS TO REUSE**

Commercial decision needs (columns):

| Abbrev | Need |
|--------|------|
| ID | Stable identity across discover→outcome |
| SP | State persistence |
| TH | Transition history |
| SCH | Scheduler trigger |
| MW | Measurement window |
| RO | Reopen |
| OC | Outcome (commercial) |
| LN | Learning memory |
| SI | Store isolation |
| AU | Auditability |

---

## Matrix

| Existing system | ID | SP | TH | SCH | MW | RO | OC | LN | SI | AU |
|-----------------|----|----|----|-----|----|----|----|----|----|-----|
| MerchantCartLifecycleArchive | NO | PARTIAL | PARTIAL | NO | NO | REUSE* | NO | NO | REUSE | PARTIAL |
| RecoverySchedule | NO | DANGEROUS | PARTIAL | DANGEROUS | DANGEROUS | NO | NO | NO | REUSE | PARTIAL |
| PurchaseTruth / Closure | NO | NO | PARTIAL | PARTIAL | PARTIAL† | NO | DANGEROUS‡ | NO | REUSE | REUSE |
| PurchaseAttribution (derived) | NO | NO | NO | NO | PARTIAL† | NO | DANGEROUS‡ | NO | REUSE | PARTIAL |
| CustomerLifecycleStatesV1 | NO | NO | NO | NO | DANGEROUS | PARTIAL | NO | NO | REUSE | NO |
| RecoveryTruthTimeline | NO | NO | REUSE* | NO | NO | NO | NO | NO | REUSE | REUSE |
| Followup / Delivery / Logs | NO | NO | PARTIAL | NO | NO | NO | NO | NO | REUSE | PARTIAL |
| BusinessFindings + BFL | PARTIAL | PARTIAL | PARTIAL | NO | PARTIAL | PARTIAL | NO | PARTIAL§ | REUSE | REUSE |
| DCE decision cards | PARTIAL | NO | NO | NO | NO | NO | NO | NO | REUSE | NO |
| Merchant Decision Registry | PARTIAL | NO | NO | NO | NO | NO | NO | NO | — | NO |
| Cart Workspace shadow | PARTIAL | NO | PARTIAL | NO | NO | PARTIAL | NO | NO | REUSE | NO |
| OGL | PARTIAL | NO | NO | NO | NO | NO | NO | NO | REUSE | NO |
| COL (compose + opportunity_id) | PARTIAL | NO | NO | NO | NO | NO | NO | NO | REUSE | NO |
| COL sessionStorage focus | NO | NO | NO | NO | NO | NO | NO | NO | — | NO |
| CDA / Decision Console modes | NO | NO | NO | NO | NO | NO | NO | NO | — | NO |
| Product metric/trend values | NO | NO | NO | NO | PARTIAL | NO | NO | NO | REUSE | PARTIAL |
| RRV / sim missions | NO | NO | NO | NO | NO | NO | NO | NO | — | NO |

\* Pattern reuse only (archive reopen semantics; timeline append-only), not the same domain object.  
† Attribution / delay windows ≠ commercial post-action measurement.  
‡ Cart recovery purchase ≠ commercial decision WON.  
§ Finding `resolved` / supersede is finding memory, not merchant-action LEARNED.

---

## Directly reusable (patterns / isolation / evidence — not wholesale state machines)

- **Store isolation** conventions (`store_slug` / `recovery_key` patterns)
- **COL `opportunity_id` compositional key** as *candidate soft identity* (not commitment)
- **BFL `advance_state` + unique finding_id + fingerprint** as *lifecycle machinery patterns*
- **Timeline append-only audit pattern** for future transition history
- **PurchaseTruth / Closure** as *evidence inputs* to future outcome evaluation (not as WON)
- **Reason counts / product metrics** as *observable signals* for measure_ar evaluation

## Partially reusable

- Business Findings status vocabulary (`insufficient_evidence`, `confirmed`, …) — adjacent commercial language
- OGL/COL recheck/measure **copy contracts** — presentation already exists
- Decision Console modes — must remain **derived from truth**, never become SoT

## Do-not-reuse / dangerous

- RecoverySchedule statuses as commercial measurement
- CustomerLifecycle `waiting_*` as `under_measurement`
- CDA arcs as persisted lifecycle
- Cart archive reopen as commercial reopen
- Purchase completed as commercial WON
- Cart Workspace in-memory decisions as production SoT
- Simulation / RRV missions on production path

---

## Commercial candidate state mapping (Phase 5)

| Candidate | Existing representation | Reuse directly | Derive safely | Needs new persisted truth | Transition owner candidate | Risks |
|-----------|-------------------------|----------------|---------------|---------------------------|----------------------------|-------|
| DISCOVERED | Soft: first COL primary appear / finding detected | NO | PARTIAL (compose presence) | Optional | Compose / none | Duplicate “discovered” every render |
| READY | COL `PRODUCTION_TRUTH_READY` | YES (as evidence class) | YES | NO for class itself | COL compose | Not a commitment |
| ACTION_CHOSEN | CDA paint only | NO | NO | **YES** | Merchant action API (new) | Without persist, Console lies after refresh |
| UNDER_MEASUREMENT | CDA / Console `measuring` from PARTIAL **or** paint | NO | ONLY if ACTION_CHOSEN+window exist | YES (or derive from commitment) | Commitment writer + clock | Confusing PARTIAL≠measuring-after-action |
| RECHECK_DUE | CDA default / Console recheck mode / `recheck_ar` copy | NO | ONLY if window/end condition persisted | YES (or derive) | Scheduler or on-read evaluate | Time-based without owner |
| WON | None commercial; purchase/closure exist | NO | NO | YES + attribution | Outcome evaluator | False victory from unrelated purchase |
| LOST | None | NO | NO | YES + attribution | Outcome evaluator | Same |
| LEARNED | None (finding resolve ≠ lesson) | NO | NO | YES | Intelligence consumer | Premature memory poisoning |
| INSUFFICIENT_EVIDENCE | COL `INSUFFICIENT` / empty; OGL abstain; finding status | YES (as gate) | YES | NO | COL / truth gate | Keep as **refusal**, not lifecycle mid-state |

---

## Minimum extension options (Phase 9)

### OPTION A — Reuse findings/BFL + minimal commitment fields on finding

**Idea:** When merchant acts on a COL opportunity aligned to a finding, stamp fields on `business_findings` (or linked row): `action_chosen_at`, `baseline_json`, `measure_until`.

| Dimension | Assessment |
|-----------|------------|
| Duplication | Medium — COL id ≠ finding_id always |
| Coupling | **High** — BFL becomes merchant-action machine |
| Migration | Medium |
| Scheduler | Low–medium (measure_until scan) |
| DB growth | Low |
| Query cost | Low if indexed by store+finding |
| Store isolation | OK |
| Observability | Partial |
| Reversibility | Hard (pollutes findings) |
| Console compatibility | OK if derived modes read new fields |
| Scale 500→10k | OK if narrow indexes |
| **Verdict** | Risky coupling — **not preferred** |

### OPTION B — Derive commercial state from timeline/events + COL only

**Idea:** No new table; infer action/measure/recheck from existing events.

| Dimension | Assessment |
|-----------|------------|
| Duplication | Low |
| Coupling | High interpretive debt |
| Migration | None |
| Scheduler | None unless added later |
| **Truth gap** | **Cannot** — no action acknowledgement / baseline events today |
| **Verdict** | **Insufficient** until events exist; inventing meaning from recovery timeline is **DANGEROUS** |

### OPTION C — Narrow `commercial_decision_lifecycle` (or commitment) record

**Idea:** One small persisted object per active commercial commitment:

- `store_slug`
- `opportunity_key` (COL-style `col:family:reason:store`)
- `state` (minimal enum)
- `action_chosen_at`, `baseline_snapshot_json`, `measure_until`
- `closed_at` / optional outcome later
- unique current open commitment per `(store_slug, opportunity_key)`

| Dimension | Assessment |
|-----------|------------|
| Duplication | Low if COL remains derive-only |
| Coupling | Low–medium (COL key soft-link) |
| Migration | Additive table only |
| Scheduler | Optional due scan for RECHECK_DUE |
| DB growth | Low (1 open row per issue) |
| Query cost | O(1) by store+key |
| Store isolation | Explicit |
| Observability | Clear |
| Reversibility | High (drop table / ignore) |
| Console compatibility | Best — modes derive from commitment+COL |
| Scale | Good |
| **Verdict** | **Preferred** when implementation is someday authorized |

---

## Recommendation (Phase 10) — ONE

### WHAT TO REUSE

- COL compose + truth gate as **evidence readiness** (`READY` / `PARTIAL` / `INSUFFICIENT`)
- COL `opportunity_id` as **soft opportunity key** (not sole authority after action)
- BFL patterns (unique id, advance_state legality, store isolation) as **engineering patterns only**
- Purchase/closure/timeline/metrics as **measurement inputs**, not outcome labels
- Decision Console / CDA as **presentation** always derived from truth

### WHAT NOT TO REUSE

- RecoverySchedule / customer lifecycle waiting as commercial measurement
- CDA arcs / Console modes as SoT
- Cart archive reopen as commercial reopen
- Purchase completed as WON
- In-memory cart workspace decisions
- Simulation missions

### MINIMUM NEW TRUTH REQUIRED (when authorized later)

A **narrow persisted commercial decision commitment** (Option C): action acknowledgement + baseline snapshot + measurement window + state for open commitments. Optional append-only transition events.

### WHO OWNS TRANSITIONS (future)

- **Evidence readiness:** COL compose (unchanged)
- **Action chosen:** merchant-authenticated write API (explicit)
- **Under measurement / recheck due:** derived from commitment timestamps + optional scheduler due job
- **Outcome / learned:** deferred until attribution contract exists

### WHICH STATES SHOULD EXIST IN V1 (if built later)

| State | Role |
|-------|------|
| `INSUFFICIENT_EVIDENCE` | Derived (COL empty / gate) — already real |
| `READY` | Derived (COL READY) — already real |
| `ACTION_CHOSEN` | Persisted commitment required |
| `UNDER_MEASUREMENT` | Derived from open commitment + window open |
| `RECHECK_DUE` | Derived from window end / recheck predicate |

### WHICH STATES SHOULD NOT EXIST YET

| State | Why |
|-------|-----|
| `DISCOVERED` | Redundant with READY/PARTIAL appear; no durable need |
| `WON` | No commercial action attribution |
| `LOST` | Same |
| `LEARNED` | No decision memory store / no safe intelligence consumer contract |

### SCHEDULER / DB / QUERY / SCALE (if Option C later)

- Scheduler: **LOW–MEDIUM** (optional due scan)
- DB: **LOW**
- Query: O(1) keyed read on dashboard attach
- Scale risk: **LOW** if one open commitment per opportunity key

**IMPLEMENTATION AUTHORIZED: NO**  
**DEPLOY: NO**
