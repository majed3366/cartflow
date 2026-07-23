# Evidence Truth V1 — Official Stage Review Report

| Field | Value |
|-------|--------|
| **Document type** | Institutional architectural audit & stage sign-off |
| **Status** | Complete — awaiting manual Architecture Board review |
| **Date (UTC)** | 2026-07-23 |
| **Stage under review** | Evidence Truth V1 — Stages 0–5 (WP-ET-00…08 + Implementation Checkpoint V1) |
| **Prior recorded verdict** | `READY_WITH_MINOR_GAPS` (retained herein after full audit) |
| **Production code modified by this review** | **None** |
| **WP-ET-09 status after this document** | **Not started · not authorized by this document alone** |

**Governing authorities**

- [`docs/architecture/EVIDENCE_TRUTH_ARCHITECTURE_V1.md`](../architecture/EVIDENCE_TRUTH_ARCHITECTURE_V1.md)
- [`docs/architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md)
- [`docs/architecture/EVIDENCE_TRUTH_IMPLEMENTATION_CHECKPOINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_CHECKPOINT_V1.md)

**Implementation evidence**

- Package reports: `docs/implementation/WP_ET_00_FOUNDATION_SPINE.md` … `WP_ET_08_VISITOR_TRUTH_AUTHORITY.md`
- Code surface: `services/evidence_truth/`
- Authorized idle hooks: `main.py` (cart-event / conversion observation), `services/purchase_truth.py`, `services/whatsapp_delivery_truth_v1.py`, `services/recovery_truth_timeline_v1.py`, `services/product_data/product_data_line_snapshots_hook_v1.py`, `services/product_data/product_hesitation_hook_v1.py`
- Test posture cited at stage close: **80** passed across WP-ET-00…08

**Explicit non-goals of this document**

- No production behaviour change  
- No new publishers, stores, or consumers  
- No WP-ET-09 / Evidence Bundle Composer implementation  
- No BFSV resume · no Reality Validation resume · no merchant UI cutover  

---

## 1. Executive Summary

### 1.1 Purpose of the stage

Evidence Truth V1 exists to insert a **governed, owner-bound, readiness-graded fact layer** between Raw Events / Canonical Observations and all downstream interpretation (Evidence Bundle → Knowledge → Business Findings → Guidance).

Architecture mission (Architecture §1): Evidence answers only what CartFlow knows, with what confidence, as of when, for which store/subject, from which sources — and what would change that knowledge. Evidence is **not** a finding, dashboard field, or recommendation.

The stage operationalizes **Truth Before Consumption**: facts may be produced, accounted, made observable, verified, and marked eligible for later consumption — but must **not** become Consumable for Bundle / Knowledge / Findings / Guidance until a later authorized cutover.

### 1.2 Scope

This review treats the following as **one integrated architecture**:

| Package / artifact | Role in stage |
|--------------------|---------------|
| WP-ET-00 | Foundation spine (kernel, families, ownership, flags, gates) |
| WP-ET-01 | Contract kernel + type registry completion |
| WP-ET-02 | Accounting + observability stubs + Gate A harness |
| WP-ET-03 | Observation Normalizer shadow dual-write |
| WP-ET-04 | Eligibility & freshness + Observation constitutional metadata |
| Implementation Checkpoint V1 | Mid-stage architectural audit (verdict `READY_FOR_WP_ET_05`) |
| WP-ET-05 | Purchase + Communication Evidence publishers |
| WP-ET-06 | Recovery + Cart Evidence publishers |
| WP-ET-07 | Behaviour + Product Evidence publishers |
| WP-ET-08 | Visitor Truth Authority + Gate B |

Blueprint Stages covered: **0–5** (foundation through Visitor Authority). Stages 6+ (Bundle Composer, Knowledge/Findings cutover, Gates C–G) remain out of stage.

### 1.3 Overall assessment

The stage **achieves its architectural objectives** for a shadow dual-write Evidence Truth platform:

- All **seven** V1 evidence families have registered types and authoritative publishers.
- Ownership Constitution is encoded and enforced on publish paths (including Visitor closing INV-008 at the authority layer).
- Constitutional metadata, readiness vocabulary, Unavailable honesty, fail-closed validation, and **non-Consumable** lifecycle are enforced in code.
- Production remains unchanged at default flag settings; dual-write is idle and rollback is flag-based.
- Gate A (partial) and Gate B (Visitor) harnesses exist and pass in synthetic mode.

The stage does **not** yet provide a durable multi-worker production truth store, production traffic ingress for Visitor volume, or runtime enforcement of the Consumer Eligibility Matrix on Bundle/KL paths. Those are **soak / next-stage preconditions**, not reasons to redesign the family dual-write architecture.

**Official verdict retained:** `READY_WITH_MINOR_GAPS` (see §17–§18).

---

## 2. Stage Objectives

| Original objective (Architecture / Blueprint) | Achieved? | Evidence |
|-----------------------------------------------|-----------|----------|
| Establish Evidence as a first-class platform layer distinct from Observation, Knowledge, Findings, Guidance | **Yes** | Package `services/evidence_truth/`; envelope + family types; forbidden guidance payload keys |
| Single owner per evidence question (Ownership Constitution) | **Yes** | `ownership_v1.py` + publisher owner stamps; traffic folded under Visitor |
| Close INV-008 (Visitor Truth Authority before traffic enters Bundle) | **Yes at authority layer** | C-09 publisher + Gate B + proxy detection; Bundle visitor fields remain unauthorized |
| Canonical Observations as governed intermediate (C-07) | **Yes (shadow)** | Observation model/store/normalizer; dual-write flag OFF by default |
| Readiness / eligibility / freshness governance (C-03) | **Yes** | `eligibility_freshness_v1.py`; stamp on Evidence publish; Observations stay Unknown |
| Accounting & no silent loss skeleton (C-04) | **Yes (in-process)** | Ledger, reject audits, silent-loss detector |
| Observability surface stubs (C-05) | **Yes (stub)** | Admin diagnostics snapshot; freshness/coverage/latency largely stubbed |
| Seven family Evidence publishers in shadow dual-write | **Yes** | C-09…C-15 publishers behind `CARTFLOW_EVIDENCE_DUAL_WRITE` |
| Truth Before Consumption (Eligible ≠ Consumable) | **Yes** | Validator rejects `consumable=True`; eligibility matrix prohibits Bundle/KL/Findings |
| Production-safe migration (no Big Bang) | **Yes** | Flags default OFF; try/except idle hooks; legacy purchase stop retained |
| Durable, addressable Evidence surviving restart | **Partial** | Versioned identity + supersession model exist; persistence is process-local |
| Evidence Bundle composition from Evidence Truth | **Deferred** | Intentionally WP-ET-09+ |
| Knowledge / Findings consume Evidence Truth | **Deferred** | Intentionally WP-ET-10/11 |

**Objective verdict:** Stage objectives for Blueprint Stages 0–5 **are met** within the authorized shadow dual-write envelope. Durability and production Visitor ingress are acknowledged partials that do not void stage completion relative to the Blueprint’s staged migration design.

---

## 3. Work Package Summary

### WP-ET-00 — Foundation Spine

**Contribution:** Created `services/evidence_truth/` as a passive constitutional spine: readiness/confidence vocabulary, family registry, Ownership Constitution declarations, validation helpers, versioning helpers, `CARTFLOW_EVIDENCE_*` flag names (default OFF, initially unwired), Gate A–G metadata.

**Note:** Packaging variance **DEV-ET-01** — Foundation Spine pre-delivered initial C-01/C-02 surface relative to literal Blueprint WP-ET-00 text. Functionally absorbed and closed by WP-ET-01 / Checkpoint.

### WP-ET-01 — Contract Kernel + Type Registry

**Contribution:** Completed Blueprint C-01/C-02 exit: contract rule IDs (OE/EB/BK/KF/FG map), schema registry, type registration API, fail-closed publish guard, OE-2 period helper. Acyclic kernel packaging.

### WP-ET-02 — Accounting + Observability

**Contribution:** C-04 in-process ledger (raw/observation/evidence counters, rejects, ownership audits, silent-loss detector); C-05 §8 observability snapshot stubs; Gate A synthetic harness; admin diagnostics library read path. No merchant behaviour change.

### WP-ET-03 — Observation Normalizer Shadow

**Contribution:** C-07 Canonical Observation model + normalizer + in-process store; flagged dual-write (`CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE`); Consumer Eligibility Matrix (declarative); Gate A partial raw≈observation linkage; hooks on selected ingress paths (idle by default). Traffic attach deferred.

### WP-ET-04 — Eligibility & Freshness

**Contribution:** C-03 stamp library (never fabricate Ready; stale → insufficient); Observations require constitutional metadata while readiness/confidence remain unknown until Evidence publish; store enforcement.

### Implementation Checkpoint V1

**Contribution:** Mid-stage architectural audit of WP-ET-00…04; packaging variance documented; residual risks ranked; verdict **`READY_FOR_WP_ET_05`**. Confirmed no material unfinished Stage 0–2 work blocking family publishers.

### WP-ET-05 — Purchase + Communication Evidence

**Contribution:** C-13/C-14 publishers; `EvidenceTruthRecordV1` + constitutional validator; in-process Evidence version store; dual-write flag `CARTFLOW_EVIDENCE_DUAL_WRITE`; Sent ≠ Delivered; purchase terminal stop remains legacy; Gate A partial Observation→Evidence.

### WP-ET-06 — Recovery + Cart Evidence

**Contribution:** C-11/C-12 publishers; Lifecycle Truth Contract alignment for recovery stages; cart Evidence from cart observations; hooks on cart-event + recovery timeline write (idle by default); must not weaken purchase stop.

### WP-ET-07 — Behaviour + Product Evidence

**Contribution:** C-10/C-15 publishers; product signal classification (ATC/cart-line ≠ view); behaviour hesitation Evidence without cause invention; synthetic BFSV Exp 1 class check with `bfsv_resumed=false`; product/hesitation hooks.

### WP-ET-08 — Visitor Truth Authority

**Contribution:** C-09 publisher; Gate B harness; cart/recovery proxy detection; Unavailable when no channel; Bundle visitor fields unauthorized; traffic publish helper ready **without** production ingress call site.

---

## 4. Coverage Review

### 4.1 Seven V1 evidence families

| Family | Type ID | Component | Observation kind | Classification | Decision rationale |
|--------|---------|-----------|------------------|----------------|--------------------|
| Purchase | `purchase_confirmed_v1` | C-13 | `purchase` | **Implemented** | Strongest terminal family; first Evidence dual-write (WP-ET-05) |
| Communication | `message_lifecycle_v1` | C-14 | `communication` | **Implemented** | Provider delivery truth elevated without inventing reply/purchase |
| Cart | `cart_state_v1` | C-11 | `cart_event` | **Implemented** | Cart ≠ visitor proxy enforced at Visitor gate |
| Recovery | `recovery_progression_v1` | C-12 | `recovery` | **Implemented** | Lifecycle alignment; never invents purchased |
| Product | `product_interest_window_v1` | C-10 | `product_signal` | **Implemented** | ATC ≠ view classification |
| Behaviour | `hesitation_reason_v1` | C-15 | `behaviour` | **Implemented** | Captured reasons only; no confirmed-cause invention |
| Visitor | `store_visitor_window_v1` | C-09 | `traffic` | **Implemented (publisher)** / **Partial (production volume)** | Authority + Gate B complete; production traffic Raw call site missing |

### 4.2 Platform components (C-01…C-08 relevant)

| Component | Classification | Decision rationale |
|-----------|----------------|--------------------|
| C-01 Contract Kernel | **Implemented** | WP-ET-00/01 |
| C-02 Type Registry | **Implemented** | Seven types registered; publish guard |
| C-03 Eligibility & Freshness | **Implemented** | Stamp on Evidence publish |
| C-04 Accounting | **Implemented (in-process)** | Sufficient for Stage 0–5 shadow; not durable ops ledger |
| C-05 Observability | **Partially implemented** | Snapshot + stubs; not full production SRE surface |
| C-06 Raw Event Stores | **Existing (legacy)** | Not replaced; Observations reference via `raw_ref` |
| C-07 Observation Normalizer | **Implemented (shadow)** | Dual-write; process-local store |
| C-08 Provider adapters | **Existing + additive hooks** | No Big Bang rewrite |

### 4.3 Intentionally deferred

| Item | Why deferred |
|------|----------------|
| Reserved families (Attribution, Pricing, Campaign, Support) | Architecture §2 future; not V1 stage scope |
| C-16 Evidence Bundle Composer | Blueprint WP-ET-09 |
| Knowledge / Findings composer input | WP-ET-10/11 |
| Gates C–G execution / production soak | After Composer + durability |
| BFSV resume / Reality Validation | Explicitly paused by governance |
| Merchant UI / Guidance cutover | Consumable forbidden |

### 4.4 Partially implemented / missing

| Item | Classification | Explanation |
|------|----------------|-------------|
| Durable Observation/Evidence SQL (or equivalent) | **Partially implemented** | Blueprint allowed “store and/or shadow table”; implementation chose in-process stores (`max` 5000) — valid for shadow, incomplete for Architecture’s “durable” property |
| Traffic / presence Raw production attach | **Missing (attach)** | Publisher + helper exist; no durable traffic ingress owner call site found in production paths |
| Runtime Consumer Eligibility enforcement | **Partially implemented** | Matrix is declarative registry; Bundle/KL paths do not yet import Evidence (safe today) |

**Coverage conclusion:** No V1 family required by Blueprint Stages 0–5 is absent as an authority. Incomplete surfaces are persistence durability and Visitor production ingress — both documented since WP-ET-03/08 and acceptable for stage close under shadow dual-write rules.

---

## 5. Ownership Review

### 5.1 Ownership Constitution (implementation)

Source of truth: `services/evidence_truth/ownership_v1.py`.

| Evidence question | Sole owner | Primary family |
|-------------------|------------|----------------|
| `visitor_truth` | `visitor_truth_authority` | Visitor |
| `traffic_truth` | `visitor_truth_authority` | Visitor (not a parallel owner) |
| `product_view_truth` | `product_truth_authority` | Product |
| `behaviour_truth` | `behaviour_truth_authority` | Behaviour |
| `purchase_truth` | `purchase_truth_authority` | Purchase |
| `cart_truth` | `cart_truth_authority` | Cart |
| `recovery_truth` | `recovery_truth_authority` | Recovery |
| `communication_truth` | `communication_truth_authority` | Communication |
| `evidence_freshness` / `evidence_eligibility` / `evidence_confidence` | `evidence_truth_platform` | Cross-cutting (does not invent family facts) |
| `evidence_bundle_composition` | `evidence_bundle_composer` | Declared; **not implemented** (WP-ET-09) |

### 5.2 Cross-family anti-proxy controls

| Risk | Control | Location |
|------|---------|----------|
| Carts counted as traffic | Proxy detection + Gate B reject | `visitor_proxy_detection_v1`, Gate B harness |
| ATC counted as product view | Signal classification | `product_signal_classification_v1` |
| Delivered counted as replied / purchased | Lifecycle Truth Contract alignment | `lifecycle_truth_alignment_v1`, Communication/Recovery publishers |
| Guidance keys in Evidence payload | Forbidden key set | `FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1` |
| Purchase stop owned by Evidence Truth prematurely | Explicit legacy stop authority | Purchase publisher metadata |

### 5.3 Ambiguity assessment

| Topic | Ambiguity? | Assessment |
|-------|------------|------------|
| Registry dual ownership | **None** | One owner per question |
| Legacy modules still persisting Raw | **Operational, expected** | Dual-write migration: legacy persists Raw; family authorities elevate Evidence. Must not remain Findings authority after cutover (deferred) |
| Production traffic ingress owner | **Operational uncertainty** | Visitor Authority exists; which production module owns durable traffic Raw bytes is not attached — documented gap, not competing Evidence owners |

**Ownership conclusion:** Exactly one authoritative Evidence owner per family question. No overlapping Evidence authorities. Residual ambiguity is migration/ops attach, not Ownership Constitution conflict.

---

## 6. Constitutional Compliance Review

| Requirement | Status | Implementation evidence |
|-------------|--------|-------------------------|
| Ownership | **Compliant** | Owner stamped on Observation + Evidence; validator fail-closed on mismatch |
| Metadata | **Compliant** | Required: owner, family, sources, timestamp authority, confidence, readiness, accounting/observability identities, eligibility, version |
| Readiness | **Compliant** | Kernel vocabulary; C-03 stamp; Observations remain Unknown until Evidence publish |
| Fail closed | **Compliant** | Unknown types rejected; constitutional validation before store put; proxy rejects recorded |
| Unavailable semantics | **Compliant** | Visitor no-channel → `unavailable`; absence ≠ negative on Behaviour/Visitor payloads |
| Confidence integrity | **Compliant** | Grades stamped; Behaviour keeps cause confidence unknown; purchase Confirmed only when Ready rules met |
| No fabricated truth | **Compliant** | No proxy traffic; ATC ≠ view; Sent ≠ Delivered; no confirmed-cause invention; forbidden guidance keys |

**Constitutional conclusion:** Stage implementations satisfy Evidence Truth constitutional requirements for produce/account/verify/eligible paths. Consumable remains constitutionally closed.

---

## 7. Lifecycle Review

Constitutional lifecycle:

```text
Produced → Accounted → Observable → Verified → Eligible → Consumable
```

| Stage | Enforcement | Exception / nuance |
|-------|-------------|--------------------|
| **Produced** | Family publishers via `evidence_publisher_core_v1` / dual-write | No alternate production publish path found outside governed publishers |
| **Accounted** | C-04 `evidence_out` / reject audit on dual-write | Accounting ledger is process-local (ops visibility resets on restart) — not a lifecycle bypass |
| **Observable** | `observability_status=ops_visible`; merchant chrome `merchant_visible=false` | Ops-visible ≠ merchant-consumable |
| **Verified** | Envelope + constitutional metadata validation fail-closed | — |
| **Eligible** | C-03 stamp; `lifecycle_state=eligible` | Stale/channel rules applied |
| **Consumable** | **Forbidden** | `validate_evidence_constitutional_metadata_v1` rejects `consumable=True` / lifecycle `consumable` |

**Documented nuance (not a bypass):** Intermediate lifecycle labels are not persisted as separate durable transition events. A successful publish completes through **Eligible** in one governed path. Functionally the pipeline executes; the stage machine is not an append-only lifecycle event log.

**Lifecycle conclusion:** No implementation path authorizes Consumable. No silent skip of accounting/validation on the dual-write path. Intermediate-state persistence is a Minor auditability gap.

---

## 8. Explainability Readiness

### 8.1 Target future merchant statement (illustrative)

> “Product X receives high traffic but has poor conversion because delivery time is the dominant hesitation signal…”

### 8.2 Can Evidence Truth support this without redesign?

| Clause in the statement | Required upstream facts | Preserved by this stage? |
|-------------------------|-------------------------|--------------------------|
| Product X | Product Evidence / product identity on signals | **Yes** — Product family + product signal observations |
| High traffic | Visitor / traffic Evidence (sole owner) | **Yes at authority** — Visitor publisher + Unavailable honesty; **production volume attach incomplete** |
| Poor conversion | Purchase + cart/recovery context | **Yes** — Purchase/Cart/Recovery families |
| Delivery time dominant hesitation | Behaviour hesitation Evidence + Communication lifecycle (delivery ≠ sent) | **Yes** — Behaviour without inventing confirmed cause; Communication Sent≠Delivered |
| “Because” as merchant speech | Knowledge / Findings interpretation over Ready evidence | **Deferred correctly** — Evidence must not invent causal prose |
| Competing explanations | Multiple Findings over same Ready set | **Architecturally preserved** — Evidence does not collapse competitors |
| Insufficient evidence | Readiness `insufficient` / `unavailable` / Unknown Observation | **Yes** |

### 8.3 Explainability risks

1. Observation safe-payload is a **bounded field subset** (intentional). Full explainability of raw provider quirks requires durable Raw via `raw_ref`.
2. Process-local Observation/Evidence stores break historical explainability after restart/eviction if relied upon as sole store.
3. Visitor production attach must exist before “high traffic” claims can be production-true for Visitor-sourced speech.

**Explainability conclusion:** Semantic preservation is **sufficient for future explainable intelligence design**. No architectural redesign of family ownership or envelopes is required. Durable linkage and Visitor ingress are soak prerequisites before production merchant speech cutover.

---

## 9. Traceability Audit

Target chain:

```text
Business Finding
    ↓
Knowledge
    ↓
Evidence Bundle
    ↓
Evidence Truth
    ↓
Observation
    ↓
Raw Event
```

| Link | Status | Gap |
|------|--------|-----|
| Finding → Knowledge | **Deferred** | WP-ET-10/11 — expected |
| Knowledge → Bundle | **Deferred** | WP-ET-09/10 — expected |
| Bundle → Evidence Truth | **Deferred** | Composer not built — expected |
| Evidence → Observation | **Present** | `source_observations` / `EvidenceSourceRefV1.observation_ref` — in-process store |
| Observation → Raw | **Present** | `raw_ref` + `raw_kind` (digest identity, not DB FK) |
| Raw durability | **Legacy authoritative** | Shadow path does not replace Raw tables |

**Material traceability gaps**

1. Process-local Observation/Evidence stores — restart / multi-worker loses shadow chain.  
2. Store eviction at 5000 entries — oldest versions dropped.  
3. No Composer — Findings cannot yet traverse Bundle → Evidence Truth in production.  
4. Visitor traffic often never enters Observation in production (missing call site).

**Traceability conclusion:** The **identity and reference model** for Evidence→Observation→Raw is complete. **Durable end-to-end production traceability** is not yet complete. Gaps are persistence/attach/Composer — not missing family identity fields.

---

## 10. Scalability Audit

| Requirement | Assessment | Remaining concern |
|-------------|------------|-------------------|
| Bounded processing | Dual-write O(1) per ingress; soft-match capped (recent window) | Soft-match skew under rare races (Minor) |
| Append-only / governed versioning | Evidence versions supersede; no mutate-in-place (`supersedes`, `next_evidence_version_v1`) | Durable append sink missing |
| Idempotency | Observation IDs from type+`raw_ref`; publisher returns `created=False` on re-delivery of same observation into latest version | Relies on stable `raw_ref` construction |
| Rollup readiness | Types/TTL declared conceptually | No rollup jobs yet (Informational / deferred) |
| Archive readiness | Contract ready | No archive sink (High for production SaaS) |
| Hot/cold separation | Design-compatible | Implementation is all hot memory today |
| No historical full scans | Publishers do not introduce full historical recompute | Enabling dual-write without durable backend under high QPS is ops hazard |
| Merchant request isolation | Flags OFF by default; hooks try/except idle | Isolation holds at defaults |

**Scalability concerns ranked**

1. **High (soak):** In-process stores as sole Observation/Evidence persistence  
2. **High (soak):** Eviction under load if flags ON without durable sink  
3. **Medium:** Soft-match heuristics for purchase/cart association  
4. **Medium:** Dual-write ON in multi-worker without shared store  
5. **Low at defaults:** Merchant-path isolation when flags OFF  

**Scalability conclusion:** Algorithmic shape is SaaS-compatible (bounded, versioned, idempotent, no scan-based truth). Persistence topology must mature before production dual-write soak.

---

## 11. Production Safety Audit

| Check | Result | Evidence |
|-------|--------|----------|
| Production unchanged at defaults | **Pass** | Hooks no-op when flags OFF |
| Feature flags OFF by default | **Pass** | `flags_v1.py` — unknown flags fail closed to False |
| No consumer activation | **Pass** | Consumable forbidden; Bundle/KL/Findings flags unwired; eligibility matrix prohibits consumers |
| Rollback available | **Pass** | Unset dual-write flags; legacy modules remain authoritative |
| Shadow mode integrity | **Pass** | Dual-write is additive; does not replace Raw/legacy stop |
| No hidden coupling | **Pass (documented)** | Allowlisted import sites only |
| Purchase stop / Bundle visitor fields | **Pass** | Legacy stop; `CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS` OFF |
| BFSV / RV | **Pass** | Not resumed; Exp1 check synthetic only |

**Operator hazard (not a default-path defect):** Enabling `CARTFLOW_EVIDENCE_DUAL_WRITE` in multi-worker production without a durable shared store yields incomplete, non-shared shadow Evidence.

**Production safety conclusion:** Default production posture is safe. Stage may close without production cutover risk.

---

## 12. Consumer Readiness

**Question:** Is Evidence Truth mature enough to become the authoritative source for future Evidence Bundle implementation?

| Prerequisite for WP-ET-09 Composer **shadow** | Met? |
|-----------------------------------------------|------|
| Seven family publishers + type registry | **Yes** |
| Shared envelope / readiness / ownership stamps | **Yes** |
| Accounting + Gate A harnesses | **Yes** |
| Gate B Visitor ownership | **Yes** (publish path) |
| Consumable still off / dual-read only | **Yes** by design |
| Readable Evidence API for Composer | **Partial** — in-process store API; no durable query API |
| Field-level Bundle parity fixtures | **Not yet** — WP-ET-09 deliverable |
| Visitor production volume for parity | **No** — traffic call site missing |

**Assessment**

- **Mature enough** to begin Evidence Bundle Composer **shadow design/implementation** against contracts, synthetic dual-write, and in-process/test stores.  
- **Not mature enough** to claim Gate C production soak or enable Bundle consume flags without durable persistence, traffic attach, and runtime consumer guards.

This section does **not** implement Bundle and does **not** authorize WP-ET-09 by itself (see §18).

---

## 13. Remaining Minor Gaps

Classification relative to **Evidence Truth stage completeness / readiness to consider WP-ET-09**. Soak impacts are noted where stronger than stage impact.

| Gap | Class | Why this class |
|-----|-------|----------------|
| Process-local Observation/Evidence stores (max 5000) | **Minor** (stage) · **Major for Gate C soak** | Blueprint Stages 0–5 authorized shadow dual-write; Architecture “durable” property incomplete for production but not a stage redesign defect |
| Traffic Raw production call site unattached | **Minor** (stage) · **Major for Visitor production volume** | Publisher + Gate B exist; fixtures suffice for Composer design; production Visitor claims remain weak |
| Consumer Eligibility Matrix declarative only | **Minor** (stage) · **Major before any consume flag ON** | Safe while Bundle/KL do not import Evidence; must become runtime fail-closed with Composer |
| Eviction can drop oldest versions | **Minor** at flags OFF · **Major if dual-write ON without durable sink** | Default path idle; ops hazard when enabled |
| Intermediate lifecycle states not separately persisted | **Minor** | Functional pipeline OK; audit timeline weaker |
| Observation safe-payload field subset | **Minor** | Intentional; Raw via `raw_ref` |
| Soft-match purchase/cart skew heuristic | **Minor** | Documented rare mis-association risk |
| DEV-ET-01 Blueprint §11 WP-ET-00 text vs Foundation Spine | **Informational** | Doc hygiene; functionally closed |
| Freshness/coverage/latency observability stubs | **Informational** | Expected until durable timestamps feed C-05 |
| Rollup / archive jobs not built | **Informational** | Blueprint later stages |
| Gates C–G not executed | **Informational** | Correctly deferred |

**Critical:** **None.** No gap invalidates Ownership Constitution or requires redesign of the seven-family dual-write architecture.

---

## 14. Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Operators enable dual-write without durable shared store | High (ops) | Keep flags OFF; require durable store decision before any soak; document in ops runbooks |
| Visitor “high traffic” merchant claims before ingress attach | High (truth) | Keep Bundle visitor fields OFF; Gate B Unavailable when no channel; attach traffic owner before Visitor Bundle fields |
| Accidental Bundle/KL import of Evidence before runtime eligibility guards | Medium | Keep consume flags OFF; implement runtime eligibility fail-closed in WP-ET-09 Composer package |
| Soft-match mis-associates purchase/cart Observation | Low–Medium | Prefer exact `raw_ref` / observation_id; tighten heuristics before soak |
| Eviction silently drops shadow history | Medium if flags ON | Durable append store; raise/monitor store pressure; never treat in-process store as sole historical authority |
| Intermediate lifecycle not auditable as event log | Low | Optional lifecycle audit events in later hardening; not required for Composer shadow |
| DEV-ET-01 doc drift confuses future implementers | Low | Amend Blueprint §11 WP-ET-00 text (doc hygiene) |

---

## 15. Architectural Strengths

1. **Clear layer separation** — Evidence is not Observation, Knowledge, Finding, or Guidance.  
2. **Ownership Constitution encoded in code** — including Visitor Authority closing INV-008 at the authority layer.  
3. **Truth Before Consumption enforced** — Eligible without Consumable; consumer matrix prohibits premature cutover.  
4. **Fail-closed validation** — unknown types, metadata gaps, proxy inputs, and consumable lifecycle are rejected.  
5. **Family completeness for V1** — all seven Blueprint families have publishers and types.  
6. **Anti-proxy discipline** — cart≠traffic, ATC≠view, Sent≠Delivered, no cause invention.  
7. **Production-safe migration shape** — flags default OFF, idle hooks, legacy stop retained, rollback by unset.  
8. **Versioned, idempotent publish core** — supersession model and observation re-delivery handling.  
9. **Gate A / Gate B harnesses** — synthetic verification of accounting and Visitor ownership.  
10. **Explainability-preserving semantics** — sources, readiness, Unavailable, and bounded payloads leave room for competing Findings without collapsing truth.

---

## 16. Lessons Learned

1. **Shadow dual-write before consumer cutover works** — Evidence Truth can land under production without changing merchant behaviour when Consumable stays closed.  
2. **Packaging variance must be recorded early** — DEV-ET-01 (WP-ET-00 over-delivery) was harmless only because Checkpoint and WP-ET-01 closed it explicitly.  
3. **“Store and/or shadow table” needs an explicit durability milestone** — leaving process-local stores acceptable for Stages 0–5 created a clean stage close but a hard soak gate; future stages should name the durable sink package.  
4. **Authority without ingress is incomplete volume, not incomplete ownership** — Visitor Authority can be constitutionally correct while production traffic attach remains open.  
5. **Declarative eligibility is necessary but not sufficient** — registries document intent; runtime fail-closed must accompany the first Composer that can read Evidence.  
6. **Intermediate lifecycle event logs are optional for function, valuable for audit** — one-shot Eligible publish is acceptable if accounting and validation cannot be skipped.  
7. **Explainability is a retention problem as much as a semantics problem** — `raw_ref` only helps if Raw and Observation/Evidence stores remain addressable.  
8. **Gate harnesses should stay synthetic until durability exists** — green Gate A/B in-process must not be mistaken for production soak readiness.  
9. **Cross-family proxy rules must be code, not prose** — Visitor/Product/Communication/Recovery controls prevented the classic CartFlow false-equivalence failures.  
10. **Stop discipline scales** — package-by-package approval prevented Bundle/KL leakage and kept BFSV/RV paused.

---

## 17. Final Verdict

### READY_WITH_MINOR_GAPS

**Justification**

Evidence Truth V1 (WP-ET-00…08 + Checkpoint) is **architecturally complete** for Blueprint Stages 0–5 intent:

- seven-family shadow dual-write  
- constitutional ownership and metadata  
- lifecycle through Eligible with Consumable forbidden  
- Gate A/B synthetic verification  
- production-safe defaults and rollback  

Remaining gaps are **Minor/Informational relative to stage close**, with separately tracked **Major soak preconditions** (durable store, traffic attach, runtime consumer guards, eviction policy) that do **not** require architectural rework of Evidence Truth.

This is **not** `READY_FOR_NEXT_STAGE` (gaps remain).  
This is **not** `MAJOR_GAPS_FOUND` (no Critical defect; Ownership/family architecture stands).  
This is **not** `ARCHITECTURAL_REWORK_REQUIRED`.

---

## 18. Authorization

| Item | Decision |
|------|----------|
| Evidence Truth stage architectural sign-off (this audit) | **Recommended: accept with minor gaps** |
| WP-ET-09 (Evidence Bundle Composer) authorized by this document? | **No — pending manual Architecture Board review** |
| Bundle consume / Knowledge / Findings cutover | **Not authorized** |
| BFSV / Reality Validation resume | **Not authorized** |
| Production dual-write enablement | **Not authorized** by this review |

**Authorization statement**

> WP-ET-09 is **not** authorized by the mere existence of this Stage Review. Architecture must perform **manual review** of this document and issue an **explicit written authorization** before any WP-ET-09 work begins.

---

## 19. Architectural Exit Criteria

**Purpose of this section:** record the architectural truths that became **permanent** because the Evidence Truth stage (WP-ET-00…08) has been completed.

These are **constitutional outcomes** of the stage — not recommendations, not backlog ideas, and not optional guidance. Future stages (including Evidence Bundle, Knowledge, Business Findings, Guidance, and merchant surfaces) **must preserve** them. Violation requires constitutional review and Architecture Board amendment of Evidence Truth Architecture V1 — not silent drift.

**Question answered:** *What architectural truths became permanent because this stage has now been completed?*

---

### EC-1 — Sole producer of Evidence

**Permanent guarantee:** Evidence Truth is the **only** authoritative producer of Evidence.

No parallel Evidence producers may be introduced under Knowledge, Findings, Bundle composition, Guidance, dashboards, AI explanation layers, fixtures mixed as production truth, or ad-hoc metrics pipelines. Downstream layers may **compose, interpret, or present** Evidence; they may not **mint** Evidence.

---

### EC-2 — Observation origin mandatory

**Permanent guarantee:** Evidence must always originate from **governed Canonical Observations**.

Raw Events must **never** publish Evidence directly. Provider payloads, webhooks, SDK events, and replay bytes enter through Raw → Observation normalization before any Evidence Truth authority may publish.

---

### EC-3 — No direct merchant-UI consumption of Evidence

**Permanent guarantee:** Evidence must **never** be consumed directly by merchant-facing UI.

All merchant-facing intelligence must flow through the approved architecture (Evidence Bundle → Knowledge → Business Findings → authorized presentation / Guidance). UI copy, registry labels, and dashboard fields are presentation — not Evidence producers or Evidence consumers that bypass the chain.

---

### EC-4 — Evidence Bundle as sole composition layer

**Permanent guarantee:** Evidence Bundle is the **only** authorized composition layer between Evidence Truth and Knowledge / Findings.

Future composition must **not** bypass Bundle. Knowledge and Findings must not assemble family Evidence ad hoc, merge Raw/Observation into “bundle-shaped” objects, or invent composition outside the authorized Composer.

*(Bundle Composer implementation remains a later package; this exit criterion fixes the architectural rule now.)*

---

### EC-5 — Ownership Constitution permanent

**Permanent guarantee:** The Ownership Constitution is permanent.

Each Evidence family has **exactly one** authoritative owner. Traffic truth remains under Visitor Truth Authority — not a second owner. Cross-cutting platform concerns (freshness, eligibility, confidence stamping) must not invent family facts. Future owner changes require **constitutional review**.

---

### EC-6 — Visitor Truth never inferred from proxies

**Permanent guarantee:** Visitor Truth must **never again** be inferred from Cart, Recovery, or Product activity.

Visitor Truth is authoritative **only** through Visitor Truth Authority. Cart counts, recovery progress, product views, ATC, or hesitation signals are not traffic. Unavailable Visitor Evidence must remain Unavailable — not filled by proxy.

---

### EC-7 — Eligible ≠ Consumable

**Permanent guarantee:** Eligible does **not** imply Consumable.

Evidence may exist, be validated, accounted, ops-observable, and Eligible, and still remain intentionally unavailable for downstream consumption until **explicitly authorized**. Truth Before Consumption is permanent: production of Eligible Evidence is never automatic permission to cut over Bundle, Knowledge, Findings, or Guidance.

---

### EC-8 — Explainability mandatory

**Permanent guarantee:** Explainability is mandatory for merchant-facing intelligence.

Every future merchant-facing statement must remain traceable through:

```text
Business Finding
    ↓
Knowledge
    ↓
Evidence Bundle
    ↓
Evidence Truth
    ↓
Observation
    ↓
Raw Event
```

Stages may not discard the references required for this chain. Absence of evidence must remain expressible as Unknown / Insufficient / Unavailable — not invented completion.

---

### EC-9 — Competing explanations preserved

**Permanent guarantee:** Evidence must preserve competing explanations.

Evidence must **not** collapse multiple hypotheses into one conclusion. Evidence states governed facts and readiness; it does not select a single commercial narrative. Interpretation, ranking, and merchant speech belong to later architectural stages (Knowledge / Findings / Guidance) operating over Ready/Trusted Evidence without rewriting the underlying facts.

---

### EC-10 — Truth Before Intelligence mandatory

**Permanent guarantee:** Truth Before Intelligence remains mandatory.

Knowledge, Findings, Guidance, and Recommendations may **never** fabricate facts missing from Evidence Truth. AI explanation may clarify; it must not create Evidence. Where Evidence is Unavailable or Insufficient, intelligence must fail closed or declare insufficiency — not invent traffic, delivery, purchase, cause, or conversion.

---

### Exit criteria status

| ID | Guarantee | Permanence |
|----|-----------|------------|
| EC-1 | Sole Evidence producer | Constitutional — permanent |
| EC-2 | Observation origin only | Constitutional — permanent |
| EC-3 | No direct merchant-UI Evidence consume | Constitutional — permanent |
| EC-4 | Bundle sole composition layer | Constitutional — permanent |
| EC-5 | Ownership Constitution | Constitutional — permanent |
| EC-6 | Visitor never from cart/recovery/product proxy | Constitutional — permanent |
| EC-7 | Eligible ≠ Consumable | Constitutional — permanent |
| EC-8 | Full-chain explainability | Constitutional — permanent |
| EC-9 | Competing explanations preserved | Constitutional — permanent |
| EC-10 | Truth Before Intelligence | Constitutional — permanent |

These exit criteria do **not** alter the Stage Review verdict in §17, the authorization posture in §18, or any prior audit conclusion. They record what the completed stage made permanently binding for all future work.

**STOP.**

---

## Appendix A — Package closure map

| Package | Closure posture |
|---------|-----------------|
| WP-ET-00 | Closed (DEV-ET-01 packaging variance noted) |
| WP-ET-01 | Closed |
| WP-ET-02 | Closed |
| WP-ET-03 | Closed |
| WP-ET-04 | Closed |
| Checkpoint V1 | Closed — `READY_FOR_WP_ET_05` |
| WP-ET-05 | Closed |
| WP-ET-06 | Closed |
| WP-ET-07 | Closed |
| WP-ET-08 | Closed |

## Appendix B — Primary flag matrix (defaults)

| Flag | Default | Stage role |
|------|---------|------------|
| `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` | OFF | Observation shadow produce |
| `CARTFLOW_EVIDENCE_DUAL_WRITE` | OFF | Family Evidence shadow produce |
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW` | OFF | Unwired — WP-ET-09 |
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME` | OFF | Unwired — unauthorized |
| `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` | OFF | Unwired — unauthorized |
| `CARTFLOW_EVIDENCE_FINDINGS_COMPOSER_INPUT` | OFF | Unwired — unauthorized |
| `CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS` | OFF | Unauthorized |

## Appendix C — Document control

| Version | Date (UTC) | Change |
|---------|------------|--------|
| 1.0 | 2026-07-23 | Official institutional Stage Review Report for Evidence Truth V1 (WP-ET-00…08) |
| 1.1 | 2026-07-23 | Added §19 Architectural Exit Criteria (EC-1…EC-10). Verdict and prior conclusions unchanged. |

**End of official Stage Review Report.**
