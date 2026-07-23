# CartFlow Evidence Truth Implementation Blueprint V1

**Status:** Proposed for Architecture + Engineering ratification  
**Date (UTC):** 2026-07-23  
**Type:** Implementation blueprint — approved architectural preparation  
**Authority (upstream):** [`EVIDENCE_TRUTH_ARCHITECTURE_V1.md`](EVIDENCE_TRUTH_ARCHITECTURE_V1.md)  
**Scope:** Remove implementation ambiguity so multiple engineers produce functionally equivalent Evidence Truth behaviour  
**Out of scope:** Production code · refactoring · feature work · BFSV resume · Reality Validation execution · UI redesign  

**Authoritative inputs:**

| Input | Role in this blueprint |
|-------|------------------------|
| Evidence Truth Architecture V1 | Constitutional law — not renegotiated here |
| Evidence Pipeline Scientific Validation Phase 0 | Confirmed: Raw traffic + ProductSignalEvents persist; EvidenceBundle never receives traffic truth; Visitor Truth has no owner; Evidence→Bundle contract missing |
| BFSV Experiment 0 | Baseline pipeline observation inventory (ingress → persistence) |
| BFSV Experiment 1 | Confirmed composition gap (persisted signals ≠ Bundle consumption) |
| Existing production architecture | Purchase/Recovery/Lifecycle/Delivery/Product Foundation/KL/Findings/Widget/WhatsApp as physical sources |

> **This is not an implementation task.**  
> After approval, engineering may open Work Packages (§11). Until then: **STOP**.

**Hard freezes while blueprint is pending / during early packages:**

- No production Evidence Truth code merge without Stage gates (§3 / §9)  
- No BFSV Experiment 2+  
- No Reality Validation resume for Evidence Truth acceptance until Gate G is authorized  
- No cart-as-traffic proxy  
- No Business Findings / Knowledge “fix” that invents visitor or product-view truth  

---

## 0. Blueprint intent

### What must be introduced

1. Evidence Truth Platform spine (contracts, readiness, accounting, observability).  
2. Canonical Observation Normalizer.  
3. Family Evidence Authorities (new Visitor; wrapped/elevated existing truths).  
4. Evidence Bundle Composer (consumption-only projection).  
5. Dual-write / dual-read migration machinery + feature flags.  
6. Gate suite A–G with non-skip policy.

### What remains unchanged (until a named stage says otherwise)

1. Purchase Truth terminal stop semantics.  
2. Recovery scheduling / WhatsApp send paths.  
3. Widget / cart-event ingress behaviour (except additive observation hooks).  
4. Merchant Evidence Registry presentation labels (labels ≠ truth).  
5. Knowledge Routing eligibility/priority rules (routing never mints evidence).  
6. Business Findings family evaluators’ commercial meanings (only their evidence predicates migrate to Bundle Composer).  
7. Identity Authority (MQIC) and Time Authority (QTC) — Evidence consumes them; does not replace them.

### Success definition for the blueprint

Implementation can begin **without new architectural decisions**. Remaining choices are engineering (table names, queue tech, flag keys) inside the contracts below.

---

## SECTION 1 — Evidence Truth Components

Classification legend:

| Tag | Meaning |
|-----|---------|
| **NEW** | Does not exist; must be introduced |
| **EXISTING** | Remains; may be consumed as source |
| **MODIFIED** | Exists; must change behaviour/contract to conform |
| **DEPRECATED** | Must be retired after cutover (not deleted in Stage 1) |

---

### 1.1 Evidence Truth Platform (cross-cutting)

#### C-01 Evidence Contract Kernel

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Shared types: readiness enum, confidence grade, freshness metadata, evidence record envelope, schema_version |
| **Responsibility** | Single vocabulary for OE/EB/BK/KF/FG; reject illegal states |
| **Owner** | Evidence Truth Platform |
| **Inputs** | Architecture §2.0 / §6 |
| **Outputs** | Typed envelopes used by all authorities + Composer |
| **Persistence** | None (library); versions documented in schema registry |
| **Consumers** | All Evidence components |
| **Producer contracts** | N/A (definitional) |
| **Consumer contracts** | All producers must emit kernel-valid records |

#### C-02 Evidence Type Registry (technical)

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Catalog of `evidence_family` + `evidence_type` + schema + dedupe key + TTL + owner module |
| **Responsibility** | Prevent undeclared evidence types; one meaning per field |
| **Owner** | Evidence Truth Platform |
| **Inputs** | Family authority registrations |
| **Outputs** | Registry lookup / validation API |
| **Persistence** | Version-controlled registry (code or config — engineering choice); not merchant DB labels |
| **Consumers** | Authorities, Composer, observability |
| **Producer contracts** | Types registered before first publish |
| **Consumer contracts** | Reject unknown types (fail closed in prod publish path) |

**Distinct from** EXISTING Merchant Evidence Registry (`merchant_evidence_registry_v1`) — presentation labels only (**EXISTING**, unchanged meaning).

#### C-03 Evidence Eligibility & Freshness Engine

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Apply platform readiness/freshness/confidence rules to family candidates |
| **Responsibility** | OE-5; stale→Insufficient/Unavailable; never fabricate Ready |
| **Owner** | Evidence Truth Platform |
| **Inputs** | Candidate evidence + family predicates + TTLs |
| **Outputs** | Readiness + confidence + freshness stamps |
| **Persistence** | Policy config; results stamped on evidence versions |
| **Consumers** | Family authorities (call-in), Composer (read stamps) |
| **Producer / consumer contracts** | Families supply predicates; platform supplies vocabulary |

#### C-04 Evidence Accounting & No-Silent-Loss Auditor

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Count Raw → Observation → Evidence → Bundle projection; detect drops |
| **Responsibility** | ET-9; every drop audited or classified Unavailable |
| **Owner** | Evidence Truth Platform / Ops |
| **Inputs** | Stage counters, reject reasons, lag metrics |
| **Outputs** | Accounting ledger / admin diagnostics |
| **Persistence** | Derived metrics store or append-only audit log |
| **Consumers** | Gate A, ops, rollback verification |
| **Contracts** | Publish path increments; rejects emit reason codes |

#### C-05 Evidence Observability Surface

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Expose health/freshness/coverage/latency/volume/violations (§8) |
| **Responsibility** | Per-stage diagnostics; no merchant chrome claims |
| **Owner** | Evidence Truth Platform |
| **Inputs** | Accounting + authority metrics |
| **Outputs** | Admin/ops read API or structured logs |
| **Persistence** | Ephemeral aggregates + retained audit samples |
| **Consumers** | Gates, on-call, migration dashboards |

---

### 1.2 Ingress & observation

#### C-06 Raw Event Stores (physical ingress)

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** |
| **Purpose** | Persist ingress faithfully (cart-events, traffic, ProductSignalEvents, WA webhooks, etc.) |
| **Responsibility** | Durability + provenance; not readiness |
| **Owner** | Existing ingress modules / adapters |
| **Inputs** | Widget, SDKs, providers, WhatsApp |
| **Outputs** | Raw rows |
| **Persistence** | Canonical operational tables (unchanged ownership) |
| **Consumers** | Observation Normalizer (read) |
| **Contracts** | No silent delete; adapters remain Raw-only |

#### C-07 Observation Normalizer

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** |
| **Purpose** | Provider-neutral Canonical Observations |
| **Responsibility** | Map Raw → observation_type + subject + observed_at + source channel + MQIC-compatible store |
| **Owner** | Evidence Truth Platform (Ingress Observation) |
| **Inputs** | Raw Event refs |
| **Outputs** | Canonical Observation records |
| **Persistence** | Canonical observation store (new) and/or dual-write shadow table |
| **Consumers** | Family authorities |
| **Producer contracts** | Fail closed on identity mismatch; never invent subjects |
| **Consumer contracts** | Authorities read observations only (not Raw as authority) |

#### C-08 Provider / Channel Adapters

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** (MODIFIED only where additive observation hooks required) |
| **Purpose** | Zid/Salla/Shopify/Widget/WhatsApp/Browser SDK/Mobile SDK → Raw |
| **Responsibility** | Alias mapping; never publish Evidence |
| **Owner** | Provider/channel teams under Identity alias rules |
| **Inputs** | External payloads |
| **Outputs** | Raw Events |
| **Persistence** | Existing |
| **Consumers** | Observation Normalizer |
| **Contracts** | Additive hooks only in migration stages; behaviour freeze otherwise |

---

### 1.3 Family Evidence Authorities

#### C-09 Visitor Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** (closes INV-008) |
| **Purpose** | Sole owner of Visitor/Traffic Truth |
| **Responsibility** | Observations → Visitor Evidence; never cart proxies |
| **Owner** | Visitor Truth Authority |
| **Inputs** | Visit/session/presence observations |
| **Outputs** | Visitor Evidence versions + readiness |
| **Persistence** | Canonical visitor evidence (+ optional rollups) |
| **Consumers** | Bundle Composer only (for visitor fields) |
| **Producer contracts** | OE-*; Unavailable when channel absent |
| **Consumer contracts** | EB-3: `has_visitor_truth` only if readiness ≥ Ready |

#### C-10 Product Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** semantic owner; **EXISTING** sources (`product_data/*`, ProductSignalEvents, cart line snapshots, catalog) |
| **Purpose** | Product view / interest / catalog evidence |
| **Responsibility** | Elevate ProductSignalEvents from “persisted signal” to governed Product Evidence |
| **Owner** | Product Truth Authority |
| **Inputs** | Product observations |
| **Outputs** | Product Evidence; `has_product_views` readiness |
| **Persistence** | Canonical product evidence; sources remain |
| **Consumers** | Bundle Composer |
| **Contracts** | Views Ready only from view evidence — ATC is not a view |

#### C-11 Cart Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (elevate from AbandonedCart / cart-event paths) |
| **Purpose** | Cart composition, active/abandon, no-phone inputs |
| **Responsibility** | Cart Evidence publication; identity via recovery_key / session rules |
| **Owner** | Cart Truth Authority |
| **Inputs** | Cart observations |
| **Outputs** | Cart Evidence |
| **Persistence** | Evidence versions + existing cart tables as sources |
| **Consumers** | Bundle Composer; Recovery correlation |
| **Contracts** | Identity conflict → fail closed with Identity Authority |

#### C-12 Recovery Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (elevate `recovery_truth_timeline_v1`, lifecycle truth) |
| **Purpose** | Recovery progression evidence aligned to Lifecycle Truth Contract |
| **Responsibility** | Timeline-backed Ready states; sent ≠ delivered |
| **Owner** | Recovery Truth Authority |
| **Inputs** | Recovery/timeline observations |
| **Outputs** | Recovery Evidence |
| **Persistence** | Evidence versions; timeline remains source of progression proof |
| **Consumers** | Bundle Composer; Proof Surface (presentation) |
| **Contracts** | Must not weaken terminal purchase stop |

#### C-13 Purchase Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (elevate `purchase_truth` / `PurchaseTruthRecord`) |
| **Purpose** | Proven purchase/conversion evidence |
| **Responsibility** | Terminal conversion authority; Evidence wrap without semantic change |
| **Owner** | Purchase Truth Authority |
| **Inputs** | Conversion/order observations |
| **Outputs** | Purchase Evidence |
| **Persistence** | Existing purchase truth + evidence versions |
| **Consumers** | Bundle Composer; recovery stop; Findings |
| **Contracts** | Corrections via superseding versions only |

#### C-14 Communication Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (elevate WhatsApp delivery truth / send logs) |
| **Purpose** | Message accepted / delivered / failed / replied |
| **Responsibility** | Channel-neutral communication evidence |
| **Owner** | Communication Truth Authority |
| **Inputs** | Provider send + webhook observations |
| **Outputs** | Communication Evidence |
| **Persistence** | Evidence versions + existing delivery truth |
| **Consumers** | Bundle Composer |
| **Contracts** | Delivery claims require delivery evidence |

#### C-15 Behaviour Truth Authority

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (elevate reason capture, hesitation mappings, widget interaction facts) |
| **Purpose** | Hesitation, reasons, returns behaviour, widget interaction evidence |
| **Responsibility** | Behaviour Evidence; widget_shown Unavailable until impression events exist |
| **Owner** | Behaviour Truth Authority |
| **Inputs** | Widget/SDK behaviour observations |
| **Outputs** | Behaviour Evidence |
| **Persistence** | Evidence versions + existing reason/hesitation tables |
| **Consumers** | Bundle Composer |
| **Contracts** | No confirmed-cause invention |

---

### 1.4 Consumption chain

#### C-16 Evidence Bundle Composer

| Field | Definition |
|-------|------------|
| **Tag** | **NEW** (replaces authority role of today’s loader) |
| **Purpose** | Project Evidence → EvidenceBundle for `(store, window, as_of)` |
| **Responsibility** | EB-1…EB-8; cache optional; never Raw-as-authority |
| **Owner** | Evidence Bundle Composer |
| **Inputs** | Published Evidence + MQIC + QTC |
| **Outputs** | Versioned EvidenceBundle DTO |
| **Persistence** | Projection / cache only (disposable) |
| **Consumers** | Knowledge loaders, Business Findings, future Guidance predicates |
| **Producer contracts** | Families publish first |
| **Consumer contracts** | Consumers treat Bundle as sole factual input for findings/knowledge predicates |

#### C-17 Legacy EvidenceBundle Loader

| Field | Definition |
|-------|------------|
| **Tag** | **DEPRECATED** (after Stage 4–5 cutover); **EXISTING** until then |
| **Purpose** | Today’s `load_evidence_bundle_from_db_v1` / fixtures |
| **Responsibility** | Interim production stability; dual-read baseline |
| **Owner** | Business Findings evidence module (interim) |
| **Inputs** | Operational tables / fixtures |
| **Outputs** | Legacy Bundle |
| **Persistence** | None (read path) |
| **Consumers** | Findings (until switch) |
| **Contracts** | Must keep `visitor_total=None` / `has_visitor_truth=False` until Visitor Authority Ready — **no proxy** |
| **Deprecation rule** | Removed only after Gate C + consumer flags off legacy |

#### C-18 Knowledge Loaders / Knowledge Layer

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (consume Composer / evidence refs; no new truth) |
| **Purpose** | Knowledge States / insights |
| **Responsibility** | BK-1…BK-5 |
| **Owner** | Knowledge producers |
| **Inputs** | EvidenceBundle / evidence refs |
| **Outputs** | Knowledge with claim-level evidence_id |
| **Persistence** | Existing KL paths + producer metadata |
| **Consumers** | Routing, Home, Brief (as today) |
| **Contracts** | No write to Evidence |

#### C-19 Business Findings Engine

| Field | Definition |
|-------|------------|
| **Tag** | **MODIFIED** (input source switches to Composer; evaluators stable) |
| **Purpose** | Commercial findings |
| **Responsibility** | KF-1…KF-5 |
| **Owner** | Business Findings Engine |
| **Inputs** | EvidenceBundle from Composer |
| **Outputs** | BusinessFindingV1 |
| **Persistence** | Existing run/package (lifecycle store still future) |
| **Consumers** | Guidance / Home candidates / Review Lab |
| **Contracts** | Insufficient evidence remains valid |

#### C-20 Guidance / Decision / Home composition

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** → **FUTURE INTEGRATION** for Evidence-native predicates |
| **Purpose** | Merchant next steps / attention |
| **Responsibility** | FG-1…FG-4; Trust MT-* |
| **Owner** | Decision / Guidance / surface composers |
| **Inputs** | Findings / decisions / routed knowledge |
| **Outputs** | Guidance items |
| **Persistence** | Existing decision/brief stores |
| **Consumers** | Surfaces |
| **Contracts** | No Evidence writes; no Raw reads for speech |

#### C-21 Merchant Evidence Registry + Claim Evidence

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** |
| **Purpose** | Merchant Arabic labels + claim→evidence_id mapping |
| **Responsibility** | Presentation only |
| **Owner** | Presentation architecture |
| **Inputs** | insight_key / tier0 keys |
| **Outputs** | Labels on API payloads |
| **Persistence** | Code registry |
| **Consumers** | KL UI, Proof Surface |
| **Contracts** | Must map to Evidence Truth families when new types activate; does not create truth |

#### C-22 Proof Surface

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** |
| **Purpose** | Merchant-visible proof composition |
| **Responsibility** | Read existing truths; later may read Evidence refs |
| **Owner** | Presentation |
| **Inputs** | Purchase/Lifecycle/Recovery/Provider truths |
| **Outputs** | `merchant_proof_surface_v1` |
| **Persistence** | None |
| **Consumers** | Cart rows |
| **Contracts** | Future Integration — optional evidence_refs; no truth ownership |

#### C-23 Knowledge Routing

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** |
| **Purpose** | Eligibility / priority / lifetime / visibility |
| **Responsibility** | Route published knowledge — never mint Evidence |
| **Owner** | Knowledge Routing |
| **Inputs** | Producer items |
| **Outputs** | Routed knowledge |
| **Persistence** | Ephemeral routing output |
| **Consumers** | Daily Brief, future surfaces |
| **Contracts** | Future Integration only if evidence readiness metadata is exposed on producers |

#### C-24 Reality Simulator / Reality Validation / BFSV harnesses

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING** harnesses; **FUTURE INTEGRATION** for Evidence pipeline |
| **Purpose** | Generate/replay governed history; validate pipeline |
| **Responsibility** | Emit Raw/Observations with simulation provenance — not parallel truth |
| **Owner** | Simulator / Validation programs |
| **Inputs** | Scenarios / clocks |
| **Outputs** | Raw events into same pipeline |
| **Persistence** | Sim-scoped |
| **Consumers** | Same authorities |
| **Contracts** | **Do not resume** until Gates F/G authorized; blueprint defines gates only |

#### C-25 Dashboard / Snapshots / Archive / Rollups

| Field | Definition |
|-------|------------|
| **Tag** | **EXISTING**; Archive/Rollups **FUTURE INTEGRATION** for Evidence-native rollups |
| **Purpose** | Merchant ops surfaces; hot-path read models; archival |
| **Responsibility** | Consume existing read models until Evidence rollups exist |
| **Owner** | Dashboard / snapshot / archive modules |
| **Inputs** | Current truth/read models |
| **Outputs** | UI / snapshots |
| **Persistence** | Snapshots disposable; archive durable |
| **Contracts** | No Change for core cart ops until Stage packages explicitly integrate |

---

### 1.4.1 Component summary matrix

| ID | Component | Tag |
|----|-----------|-----|
| C-01 | Evidence Contract Kernel | NEW |
| C-02 | Evidence Type Registry (technical) | NEW |
| C-03 | Eligibility & Freshness Engine | NEW |
| C-04 | Evidence Accounting Auditor | NEW |
| C-05 | Observability Surface | NEW |
| C-06 | Raw Event Stores | EXISTING |
| C-07 | Observation Normalizer | NEW |
| C-08 | Provider/Channel Adapters | EXISTING (+ additive MODIFIED) |
| C-09 | Visitor Truth Authority | NEW |
| C-10 | Product Truth Authority | NEW owner / EXISTING sources |
| C-11 | Cart Truth Authority | MODIFIED |
| C-12 | Recovery Truth Authority | MODIFIED |
| C-13 | Purchase Truth Authority | MODIFIED |
| C-14 | Communication Truth Authority | MODIFIED |
| C-15 | Behaviour Truth Authority | MODIFIED |
| C-16 | Evidence Bundle Composer | NEW |
| C-17 | Legacy EvidenceBundle Loader | DEPRECATED (deferred) |
| C-18 | Knowledge Layer | MODIFIED |
| C-19 | Business Findings Engine | MODIFIED |
| C-20 | Guidance / Decision / Home | EXISTING → FUTURE INTEGRATION |
| C-21 | Merchant Evidence Registry | EXISTING |
| C-22 | Proof Surface | EXISTING → FUTURE INTEGRATION |
| C-23 | Knowledge Routing | EXISTING |
| C-24 | Simulator / RV / BFSV | FUTURE INTEGRATION (gated) |
| C-25 | Dashboard / Snapshots / Archive | EXISTING / FUTURE INTEGRATION |

---

## SECTION 2 — Implementation Dependency Graph

### 2.1 Normative DAG (no cycles)

Identity Authority (MQIC) and Time Authority (QTC) are hard upstream inputs — they do not depend on Evidence Truth.

```text
Identity Authority (MQIC) ──┐
Time Authority (QTC) ───────┼──► Evidence Contract Kernel (C-01)
                            │              │
Raw Event Stores (C-06) ────┤              ▼
Provider Adapters (C-08) ───┘    Evidence Type Registry (C-02)
                                           │
                                           ▼
                                 Observation Normalizer (C-07)
                                           │
        ┌──────────────┬──────────┬────────┼──────────┬──────────────┐
        ▼              ▼          ▼        ▼          ▼              ▼
   Purchase(C-13) Comm(C-14) Recovery(C-12) Cart(C-11) Behaviour(C-15) Product(C-10)
        │              │          │        │          │              │
        └──────────────┴──────────┴────┬───┴──────────┴──────┐       │
                                       │                     │       │
                                       │         Visitor Truth Authority (C-09)
                                       │                     │       │
                                       ▼                     ▼       ▼
                            Eligibility & Freshness (C-03) ◄─┴───────┘
                                       │
                                       ▼
                      Evidence Accounting (C-04) + Observability (C-05)
                                       │
                                       ▼
                            Evidence Bundle Composer (C-16)
                                       │
                  ┌────────────────────┼────────────────────┐
                  ▼                    ▼                    ▼
           Knowledge (C-18)   Business Findings (C-19)   Legacy Loader (C-17 shadow)
                  │                    │
                  ▼                    ▼
           Knowledge Routing    Guidance / Home (C-20)
                  │
                  ▼
           Surfaces (Dashboard, Brief, …)
```

### 2.2 Exact implementation order (packages)

| Order | Component | May start only after |
|------:|-----------|----------------------|
| 1 | C-01 Contract Kernel | Architecture + this blueprint approved |
| 2 | C-02 Type Registry | C-01 |
| 3 | C-04 Accounting (skeleton) + C-05 Observability stubs | C-01 |
| 4 | C-07 Observation Normalizer (shadow dual-write) | C-01, C-02, C-06 |
| 5 | C-03 Eligibility & Freshness | C-01, C-02 |
| 6 | C-13 Purchase Evidence publisher wrap | C-07, C-03 |
| 7 | C-14 Communication Evidence publisher wrap | C-07, C-03 |
| 8 | C-12 Recovery Evidence publisher wrap | C-07, C-03, C-13 (terminal interaction rules) |
| 9 | C-11 Cart Evidence publisher wrap | C-07, C-03 |
| 10 | C-15 Behaviour Evidence publisher wrap | C-07, C-03 |
| 11 | C-10 Product Evidence publisher | C-07, C-03 (+ ProductSignalEvent observations) |
| 12 | C-09 Visitor Truth Authority | C-07, C-03 (**ownership early; Bundle consumption late**) |
| 13 | C-16 Bundle Composer (shadow dual-read) | All family publishers that will be compared + C-04 |
| 14 | C-18 Knowledge loader adaptation | C-16 Gate C partial |
| 15 | C-19 Business Findings input switch | C-16 Gate C + Gate E prep |
| 16 | Deprecate C-17 legacy loader authority | Gates C–E green |
| 17 | C-20 / C-22 / C-23 / C-25 integrations | After consumer stability |
| 18 | C-24 BFSV/RV (execution) | Gates A–E green + explicit authorization (Gate F/G) |

### 2.3 Cycle prevention rules

1. Authorities never import Bundle Composer.  
2. Composer never imports Knowledge or Findings.  
3. Knowledge/Findings never import Raw stores as authority.  
4. Visitor Authority never imports Cart counters.  
5. Observability is sink-only (no publish side effects).  
6. Merchant Evidence Registry never imported by authorities for truth decisions.

---

## SECTION 3 — Migration Plan

**Design goal:** Independently deployable stages; production stable after each; merchant certainty never increases without readiness upgrade.

### Stage 0 — Freeze & instrumentation prep (deployable docs + flags)

| | |
|--|--|
| **Introduce** | Feature flags skeleton; logging conventions; blueprint ratification |
| **Unchanged** | All production behaviour |
| **Exit** | Flags default **off**; no consumer reads Evidence Truth |
| **Rollback** | N/A (docs/flags only) |

### Stage 1 — Platform spine

| | |
|--|--|
| **Introduce** | C-01, C-02, C-04 skeleton, C-05 stubs |
| **Unchanged** | Ingress, Bundle loader, KL, Findings |
| **Exit** | Unit tests for readiness enum + registry validation; admin counters exist (zero traffic) |
| **Rollback** | Disable modules; no data migrations required |

### Stage 2 — Observation Normalizer (shadow dual-write)

| | |
|--|--|
| **Introduce** | C-07 writes Canonical Observations **alongside** existing Raw persistence for selected event types (start: purchase, communication, cart-event, product signals, traffic if present) |
| **Unchanged** | All readers still use legacy paths |
| **Exit** | Accounting: Raw count ≈ Observation count within tolerance; identity fail-closed proven |
| **Rollback** | Stop observation writes; Raw path untouched |

### Stage 3 — Strong-family Evidence dual-write (Purchase → Communication → Recovery → Cart)

| | |
|--|--|
| **Introduce** | C-13, C-14, C-12, C-11 publish Evidence versions from observations; **no consumer switch** |
| **Unchanged** | Bundle loader, KL, Findings, recovery stop (still driven by existing Purchase Truth) |
| **Exit** | Evidence versions exist; Gate A accounting green for these families; purchase terminal parity tests pass |
| **Rollback** | Stop Evidence publishers; existing truth modules remain authoritative |

### Stage 4 — Behaviour + Product Evidence dual-write

| | |
|--|--|
| **Introduce** | C-15, C-10 publishers; ProductSignalEvents → Observations → Product Evidence |
| **Unchanged** | Bundle still sets `has_product_views=False` until Composer switch |
| **Exit** | Product evidence volume matches signal persistence (BFSV Exp 1 class check); no ATC-as-view |
| **Rollback** | Disable publishers |

### Stage 5 — Visitor Truth Authority dual-write

| | |
|--|--|
| **Introduce** | C-09 publishes Visitor Evidence from traffic/presence observations |
| **Unchanged** | Bundle `visitor_total` remains Unavailable/None for consumers (**critical**) |
| **Exit** | Visitor ownership live; Gate B (authority publish) green; still **not** consumed |
| **Rollback** | Disable Visitor publisher; consumers unchanged |

### Stage 6 — Bundle Composer shadow dual-read

| | |
|--|--|
| **Introduce** | C-16 builds Bundle from Evidence; compare to C-17 legacy Bundle field-by-field |
| **Unchanged** | Production consumers still use legacy Bundle |
| **Exit** | Gate C parity report: equal or intentionally stricter (never looser/more certain); diffs explained |
| **Rollback** | Disable Composer; legacy only |

### Stage 7 — EvidenceBundle consumer switch (flagged)

| | |
|--|--|
| **Introduce** | Findings (+ optionally KL metrics path) read Composer when flag on |
| **Unchanged** | Flag off → legacy; merchant speech must not gain certainty |
| **Exit** | Gate D (Knowledge) + Gate E (Findings) parity; Review Lab deterministic |
| **Rollback** | Flag off immediately |

**Optimal switch order inside Stage 7 (substeps, each deployable):**

1. Non-visitor Bundle fields (purchase/recovery/communication/cart/behaviour)  
2. Product view flags only when Product Evidence Ready  
3. Visitor fields last — only when Visitor Evidence Ready **and** Gate B+C visitor slice green  

### Stage 8 — Remove legacy Bundle authority path

| | |
|--|--|
| **Introduce** | Composer-only factual path for Findings/KL predicates |
| **Deprecated** | C-17 authority role (fixtures remain for demo provenance) |
| **Exit** | No production code path treats Raw tables as Findings authority |
| **Rollback** | Re-enable Stage 7 flag dual-read (retain legacy code one release) |

### Stage 9 — Downstream integrations (optional, separate)

| | |
|--|--|
| **Introduce** | Proof Surface evidence_refs; Routing readiness metadata; Dashboard/Archive Evidence rollups as needed |
| **Unchanged** | Core cart ops if not in package scope |
| **Exit** | Per-subsystem compatibility matrix row moves to No Change or complete Migration |

### Stage 10 — Validation authorization (not auto-start)

| | |
|--|--|
| **Define only here** | Gate F (BFSV Exp 1 replay) + Gate G (Reality Validation) |
| **Execution** | Requires explicit Architecture + Product authorization **after** Stages 1–8 |
| **This blueprint does not resume BFSV or RV** | |

### Why this order (vs naive “Visitor first → Bundle switch”)

1. Scientific validation shows **persistence works** but **composition fails** — fix accounting + Composer contracts before trusting visitor consumption.  
2. Purchase/Communication wraps protect terminal money paths before touching visitor.  
3. Visitor Authority is introduced **before** Bundle consumption (ownership ≠ cutover).  
4. Dual-read proves parity before any merchant-visible change.  
5. Each stage is flag-safe and independently deployable.

---

## SECTION 4 — Compatibility Matrix

| Subsystem | Status | Notes |
|-----------|--------|-------|
| **Dashboard** (carts/home chrome) | **No Change** (Stages 0–8) | Future Integration for Evidence rollups/refs only |
| **Knowledge** | **Migration Required** | BK conformance; input via Composer/evidence refs; no Raw authority |
| **Business Findings** | **Migration Required** | Switch Bundle source; keep evaluator meanings; KF-3 enforced |
| **Guidance** / Decision / Attention | **Future Integration** | Consumes findings/decisions; FG rules; no Evidence writes |
| **Widget** | **Adapter Required** | Additive observation emission; no Evidence publish; behaviour freeze otherwise |
| **WhatsApp** | **Adapter Required** | Webhooks → Observations; Communication Authority owns Evidence |
| **Purchase Truth** | **Migration Required** (wrap) | Semantics unchanged; Evidence publisher dual-write then compose |
| **Recovery Truth / Timeline** | **Migration Required** (wrap) | Same |
| **Provider Delivery Truth** | **Migration Required** (wrap → Communication) | Sent ≠ delivered preserved |
| **Product Foundation / ProductSignalEvents** | **Migration Required** | Signals become sources under Product Truth Authority |
| **Cart / AbandonedCart paths** | **Migration Required** (wrap → Cart Authority) | |
| **Merchant Evidence Registry** | **No Change** (labels) | Future Integration: map new evidence types to labels when activated |
| **Proof Surface** | **Future Integration** | Optional evidence_refs |
| **Knowledge Routing** | **No Change** | Future Integration if readiness metadata routed |
| **Daily Brief / Home composition** | **No Change** initially | Future Integration via Findings/Knowledge only |
| **Reality Validation** | **Future Integration** | Gate G — do not resume in this blueprint execution |
| **Simulator** | **Adapter Required** (later) | Must emit Raw/Observations with sim provenance into same pipeline |
| **BFSV harness** | **Future Integration** | Gate F — paused; define only |
| **Rollups** | **Future Integration** | Family-owned derived evidence types |
| **Archive** | **No Change** / **Future Integration** | Immutable evidence versions are archive-friendly; no rewrite of archive UX required for Stages 1–8 |
| **Snapshots** | **No Change** | Disposable read models; rebuild after bulk replay when Gate G runs |
| **Identity / Time Authorities** | **No Change** | Hard dependencies — not modified by Evidence Truth |

---

## SECTION 5 — Contract Implementation Map

### 5.1 OE — Observation → Evidence

| Rule | Producer | Consumer | Validation point | Failure behaviour |
|------|----------|----------|------------------|-------------------|
| OE-1 sources[] | Family Authority | Composer, Accounting | Publish validator | Reject publish; audit `missing_sources` |
| OE-2 period containment | Family Authority | Registry tests | Publish validator | Reject / Conflicting |
| OE-3 dedupe | Family Authority | Accounting | Dedupe key uniqueness | Idempotent ack; `duplicate_suppressed` |
| OE-4 out-of-order | Family Authority + buffer | Accounting | Sequence tests | Reorder or supersede; never drop |
| OE-5 readiness | C-03 + Authority | Composer | Enum conformance | Invalid enum → reject |
| OE-6 identity | Authority + MQIC | All | Identity gate | Fail closed; no publish |
| OE-7 no guidance text | Authority | Static/CI lint | Schema forbid fields | Reject |

### 5.2 EB — Evidence → EvidenceBundle

| Rule | Producer | Consumer | Validation point | Failure behaviour |
|------|----------|----------|------------------|-------------------|
| EB-1 projection only | C-16 Composer | KL, Findings | Gate C parity | Fail Composer build; do not invent |
| EB-2 no zero-fill | Composer | Findings | Field policy tests | Emit Unavailable/Unknown slice |
| EB-3 has_* flags | Composer | Findings/KL | Gate B/C | Flags false unless readiness ≥ Ready |
| EB-4 evidence_refs | Composer | Explainability | Bundle schema tests | Missing refs → build error in strict mode |
| EB-5 schema_version | Composer | Consumers | Compat matrix | Reject incompatible major |
| EB-6 cache invalidation | Composer | Ops | Version bump tests | Stale cache discard |
| EB-7 no Raw authority | Composer | CI import linter | Arch tests | Build fail if Raw import in Composer |
| EB-8 demo provenance | Fixture builder | Review Lab | Provenance field | Demo never marked production Trusted |

### 5.3 BK — EvidenceBundle → Knowledge

| Rule | Producer | Consumer | Validation point | Failure behaviour |
|------|----------|----------|------------------|-------------------|
| BK-1 required families | Knowledge producer | Routing/UI | Claim schema | Claim blocked if undeclared |
| BK-2 readiness gate | Knowledge producer | Surfaces | Gate D | Unknown/Insufficient confidence |
| BK-3 claim evidence_id | Claim mapper + Registry | UI | Claim tests | Fallback only via declared map |
| BK-4 no Evidence write | Knowledge | CI | Import/arch tests | Fail CI |
| BK-5 routing after produce | Routing | Brief | Existing KR tests | No routing without producer item |

### 5.4 KF — Knowledge/Bundle → Business Findings

| Rule | Producer | Consumer | Validation point | Failure behaviour |
|------|----------|----------|------------------|-------------------|
| KF-1 Bundle predicates | Findings Engine | Guidance/Lab | Gate E | Skip finding / insufficient |
| KF-2 insufficient valid | Findings Engine | Lab | Deterministic fixtures | Emit insufficient finding |
| KF-3 visitor None ≠ 0 | Findings Engine | Lab | Explicit unit tests | Hard fail if coerced |
| KF-4 one meaning | Findings families | Product | Contract tests | Dedupe/rank rules |
| KF-5 explainability | Findings Engine | Lab/UI | Package schema | Reject package without summary/refs |

### 5.5 FG — Findings → Guidance

| Rule | Producer | Consumer | Validation point | Failure behaviour |
|------|----------|----------|------------------|-------------------|
| FG-1 finding required | Guidance/Decision | Surfaces | Decision governance | Silence (MT-3) |
| FG-2 trust privilege | Guidance | Home/Brief | Trust ladder checks | Withhold |
| FG-3 no upstream mutate | Guidance | CI | Arch tests | Fail CI |
| FG-4 surfaces consume routed | Composers | UI | KR readiness | No ad-hoc Raw reads |

---

## SECTION 6 — Persistence Blueprint

### 6.1 Persistence classes

| Class | Definition | Retention |
|-------|------------|-----------|
| **Canonical storage** | Authoritative durable records | Long-lived; immutable versions |
| **Derived storage** | Recomputable from canonical | Rebuildable |
| **Projection** | Query-shaped DTO materialization | Disposable |
| **Rollup** | Window aggregates owned by family | Rebuildable; versioned |
| **Snapshot** | Hot-path read model (dashboard) | Disposable |
| **Cache** | Composer/bundle cache | TTL / version invalidation |
| **Ephemeral** | In-flight buffers, worker memory | Lost on restart → must be recoverable from canonical/Raw |

### 6.2 Per-family persistence map

| Family | Canonical | Derived | Projection | Rollup | Snapshot | Cache | Ephemeral |
|--------|-----------|---------|------------|--------|----------|-------|-----------|
| **Visitor** | Visitor Evidence versions; visit observations | Session uniques | Bundle `visitor_*` | Daily/weekly visitor counts | Optional store health cards (later) | Composer slice | Reorder buffer |
| **Product** | Product Evidence; observations from signals/lines | Interest scores | Bundle `products`, `has_product_views` | Top-N products | Product foundation health (existing may remain) | Composer slice | Hook buffers |
| **Cart** | Cart Evidence; AbandonedCart remains source-of-record for ops | Active counts | Bundle cart fields | Cart volume rollups | Dashboard snapshots (existing) | Composer | Cart-event in-flight |
| **Recovery** | Recovery Evidence; timeline events canonical for progression | Lifecycle projection | Bundle movement/recovery | Recovery funnel rollups | Row snapshots | Composer | Schedule workers |
| **Purchase** | PurchaseTruthRecord + Purchase Evidence versions | Attribution (existing derived) | Bundle purchase fields | Purchase rollups | — | Composer | Conversion ingest |
| **Communication** | Communication Evidence; delivery truth rows | Delivery rates | Bundle `wa_*` | Send/fail rollups | — | Composer | Webhook buffer |
| **Behaviour** | Behaviour Evidence; reason/hesitation tables | Distributions | Bundle hesitation/widget fields | Reason rollups | — | Composer | Widget POST buffer |

### 6.3 Cross-cutting persistence

| Concern | Class | Rule |
|---------|-------|------|
| Canonical Observations | Canonical | Required for OE-1 traceability |
| Evidence versions | Canonical immutable | Supersede only |
| Accounting ledger | Derived / append-only audit | Gate A |
| Bundle | Projection (+ optional Cache) | Never canonical |
| Demo fixtures | Ephemeral/derived with provenance | Not production Trusted |
| Archive | Canonical Evidence versions eligible | No silent purge |
| Schema registry | Version-controlled config | Dual-read on breaking change |

### 6.4 Explicit non-goals for Stages 1–8

- New merchant-facing DB tables for Findings lifecycle (still future).  
- Replacing AbandonedCart as operational cart store.  
- Moving WhatsApp send execution into Evidence Truth.

---

## SECTION 7 — Failure Handling

**Prime directive:** No silent evidence loss.

| Failure | Blueprint handling |
|---------|-------------------|
| **Late evidence** | Accept; supersede or append version; invalidate Composer cache; audit `late_arrival`; recompute affected rollups |
| **Duplicate evidence** | Idempotent dedupe key; ack without double count; audit `duplicate_suppressed` |
| **Conflicting evidence** | Readiness=Conflicting; block Ready for claim; keep both observation refs; typed reconciliation job; never arbitrary pick |
| **Schema evolution** | Additive default; breaking → `schema_version` bump + dual-read window + Gate C re-run |
| **Provider evolution** | Adapter maps new payload → same observation types; new types require registry entry before publish |
| **Replay** | Provenance=`replay`/`simulation`; deterministic IDs; cannot clobber production Trusted without explicit supersession policy |
| **Partial failure** | Per-family publish isolation; Bundle slice Unavailable for failed family; other families still project |
| **Worker restart** | Ephemeral buffers rebuilt from Raw/Observations; at-least-once publish with idempotent keys |
| **Idempotency** | `(store, evidence_type, subject, window_key, content_hash)` publish identity |
| **Missing ownership** | Registry rejects unowned types; Gate A fails open deploy if unknown owner detected in prod publish path |
| **Composer failure** | Consumers stay on legacy until Stage 8; after Stage 8 fail closed to insufficient/unavailable package — never Raw fallback |

### 7.1 Rejected evidence reason codes (minimum set)

`missing_sources` · `identity_mismatch` · `unknown_type` · `schema_invalid` · `duplicate_suppressed` · `conflict_unresolved` · `stale_forbidden_for_live` · `guidance_field_forbidden` · `owner_missing`

Every reject increments Accounting.

---

## SECTION 8 — Observability Blueprint

Every stage (Raw, Observation, Evidence publish, Bundle compose, Knowledge load, Findings run) exposes:

| Signal | Definition |
|--------|------------|
| **health** | Up / degraded / down per component |
| **freshness** | Age of newest observation/evidence per family/store |
| **coverage** | % stores/windows with Ready vs Unavailable/Insufficient |
| **latency** | Raw→Observation, Observation→Evidence, Evidence→Bundle p50/p95 |
| **volume** | Counts in/out per stage |
| **contract violations** | OE/EB/BK/KF/FG break counters |
| **rejected evidence** | By reason code |
| **missing ownership** | Publishes attempted without registry owner |
| **Evidence accounting** | Invariants: `in >= out + rejected + in_flight`; lag alerts |

### 8.1 Required dashboards / log channels (ops, not merchant)

1. Evidence Pipeline Health  
2. Family Readiness Map  
3. Bundle Parity Diff (Stage 6–7)  
4. Silent-Loss Detector  
5. Visitor Authority Status (explicit Unavailable vs Ready)

### 8.2 Alert classes

| Class | Trigger |
|-------|---------|
| P0 | Silent-loss detector trip; identity fail-open attempt; visitor proxy detection |
| P1 | Conflict rate spike; Composer/legacy parity breach while flag on |
| P2 | Freshness SLA breach; high duplicate rate |

---

## SECTION 9 — Reality Validation Gates

**Policy: no gate may be skipped.** Gates are sequential for acceptance; earlier gates may re-run after later changes.

| Gate | Name | Proves | Required before |
|------|------|--------|-----------------|
| **A** | Evidence accounting | Raw→Observation→Evidence counts reconcile; rejects audited; no silent loss | Any consumer flag on |
| **B** | Visitor Truth | Visitor Authority sole owner; carts never proxy; Unavailable honest when no channel | Visitor Bundle fields enabled |
| **C** | EvidenceBundle parity | Composer ≡ legacy where legacy was honest; Composer stricter allowed; never more certain without Ready | Findings/KL switch |
| **D** | Knowledge parity | Same claims/confidence class under Composer input; BK-2 holds | Declaring Knowledge migration done |
| **E** | Business Finding parity | Deterministic findings match fixtures + KF-3; Review Lab stable | Declaring Findings migration done |
| **F** | BFSV Experiment 1 replay | Persisted signals produce governed Evidence and Bundle slices without composition gap | Full pipeline acceptance (**authorization required; not started by this blueprint**) |
| **G** | Reality Validation | Sim/production-class walkthrough under MQIC+QTC+Evidence | Production “Evidence Truth complete” claim (**authorization required; not started by this blueprint**) |

### 9.1 Gate artifacts (each gate)

- Written report path under `docs/architecture/` (or investigations)  
- Metrics export / accounting snapshot  
- Pass/fail checklist signed by Architecture  
- Explicit **Do Not Proceed** list if amber  

### 9.2 Freeze during gates

Failing Gate A–E blocks Stage progression.  
Gate F/G blocked until Architecture + Product explicitly open them — **this document does not open them**.

---

## SECTION 10 — Rollback Strategy

### 10.1 Principles

1. **Flags first** — consumer switches revert in minutes.  
2. **Canonical Evidence retained** — rollback does not delete Evidence versions.  
3. **Knowledge/Findings historical outputs** remain explainable via provenance (`loaded_from`, evidence_refs, schema_version).  
4. **No Raw rewrite** during rollback.  
5. **Historical consistency** — as-of queries use evidence versions valid at that time; supersession preserved.

### 10.2 Rollback matrix

| Stage | Rollback action | Preserves Evidence | Preserves Knowledge/Findings history | Production stability |
|-------|-----------------|--------------------|--------------------------------------|----------------------|
| 1 Spine | Disable modules | N/A | N/A | Yes |
| 2 Observations | Stop dual-write | Observations optional purge only if unused | N/A | Yes — Raw intact |
| 3–5 Evidence dual-write | Stop publishers | **Keep** versions | N/A | Yes — legacy readers |
| 6 Composer shadow | Disable Composer jobs | Keep Evidence | N/A | Yes |
| 7 Consumer switch | Flag off → legacy Bundle | Keep Evidence | Prior packages keep refs | Yes |
| 8 Legacy removal | Revert deploy to Stage 7 dual-read build | Keep Evidence | Yes | Yes |
| Post F/G | Disable sim/replay injectors | Keep production Evidence | Yes | Yes |

### 10.3 Forbidden rollback behaviours

- Deleting Evidence to “clean” diffs  
- Re-enabling cart-as-traffic  
- Silent Raw fallback inside Composer after Stage 8  
- Changing past Finding meanings without new run provenance  

---

## SECTION 11 — Execution Packages

Each package is a manageable engineering scope. **No production code in this blueprint task.**

### WP-ET-00 — Blueprint & flag skeleton

| | |
|--|--|
| **Objective** | Ratify blueprint; add flag names/docs only |
| **Dependencies** | Architecture V1 approved |
| **Expected output** | Flag matrix; owner assignments; gate owners |
| **Verification** | Review sign-off |
| **Rollback point** | Docs-only |

### WP-ET-01 — Contract Kernel + Type Registry

| | |
|--|--|
| **Objective** | C-01, C-02 |
| **Dependencies** | WP-ET-00 |
| **Expected output** | Shared types + registry; unit tests |
| **Verification** | Enum/schema tests |
| **Rollback point** | Stage 1 |

### WP-ET-02 — Accounting + Observability stubs

| | |
|--|--|
| **Objective** | C-04, C-05 skeletons; Gate A harness |
| **Dependencies** | WP-ET-01 |
| **Expected output** | Counters/reason codes; admin read path |
| **Verification** | Synthetic increment tests |
| **Rollback point** | Stage 1 |

### WP-ET-03 — Observation Normalizer shadow

| | |
|--|--|
| **Objective** | C-07 dual-write for priority Raw types |
| **Dependencies** | WP-ET-01, WP-ET-02 |
| **Expected output** | Observation store + accounting linkage |
| **Verification** | Gate A partial (Raw≈Observation) |
| **Rollback point** | Stage 2 |

### WP-ET-04 — Eligibility & Freshness Engine

| | |
|--|--|
| **Objective** | C-03 |
| **Dependencies** | WP-ET-01 |
| **Expected output** | Readiness stamping library |
| **Verification** | Transition rule tests (§6 Architecture) |
| **Rollback point** | Stage 1/3 |

### WP-ET-05 — Purchase + Communication Evidence publishers

| | |
|--|--|
| **Objective** | C-13, C-14 dual-write |
| **Dependencies** | WP-ET-03, WP-ET-04 |
| **Expected output** | Evidence versions; terminal parity |
| **Verification** | Purchase stop + delivery≠sent tests |
| **Rollback point** | Stage 3 |

### WP-ET-06 — Recovery + Cart Evidence publishers

| | |
|--|--|
| **Objective** | C-12, C-11 dual-write |
| **Dependencies** | WP-ET-05 |
| **Expected output** | Recovery/Cart Evidence |
| **Verification** | Lifecycle Truth Contract alignment tests |
| **Rollback point** | Stage 3 |

### WP-ET-07 — Behaviour + Product Evidence publishers

| | |
|--|--|
| **Objective** | C-15, C-10 |
| **Dependencies** | WP-ET-03, WP-ET-04 |
| **Expected output** | Behaviour/Product Evidence; signal accounting |
| **Verification** | BFSV Exp 1 class check (persist→evidence); no ATC-as-view |
| **Rollback point** | Stage 4 |

### WP-ET-08 — Visitor Truth Authority

| | |
|--|--|
| **Objective** | C-09 dual-write; Gate B |
| **Dependencies** | WP-ET-03, WP-ET-04 |
| **Expected output** | Visitor Evidence; Unavailable when no channel |
| **Verification** | Gate B; proxy-detection tests |
| **Rollback point** | Stage 5 |

### WP-ET-09 — Bundle Composer shadow + Gate C

| | |
|--|--|
| **Objective** | C-16 dual-read parity |
| **Dependencies** | WP-ET-05…08, WP-ET-02 |
| **Expected output** | Parity report; Composer DTO |
| **Verification** | Gate C |
| **Rollback point** | Stage 6 |

### WP-ET-10 — Knowledge consumer migration + Gate D

| | |
|--|--|
| **Objective** | C-18 BK conformance behind flag |
| **Dependencies** | WP-ET-09 / Gate C |
| **Expected output** | KL path via Composer |
| **Verification** | Gate D |
| **Rollback point** | Stage 7 flag |

### WP-ET-11 — Business Findings switch + Gate E

| | |
|--|--|
| **Objective** | C-19 input switch; KF-3 hard tests |
| **Dependencies** | WP-ET-09 / Gate C; WP-ET-10 recommended |
| **Expected output** | Findings from Composer |
| **Verification** | Gate E + Review Lab |
| **Rollback point** | Stage 7 flag |

### WP-ET-12 — Legacy loader deprecation

| | |
|--|--|
| **Objective** | Remove C-17 authority role |
| **Dependencies** | Gates C–E green for one soak period |
| **Expected output** | Composer-only factual path |
| **Verification** | Import linter; no Raw authority in Findings |
| **Rollback point** | Stage 8 (keep prior release dual-read) |

### WP-ET-13 — Gate F/G authorization packages (separate)

| | |
|--|--|
| **Objective** | Execute BFSV Exp 1 replay + Reality Validation under Evidence Truth |
| **Dependencies** | WP-ET-12 + explicit Architecture/Product auth |
| **Expected output** | Gate F/G reports |
| **Verification** | §9 artifacts |
| **Rollback point** | Disable injectors; production flags unchanged |
| **Note** | **Not opened by this blueprint** |

Package size rule: if a WP exceeds ~1–2 engineer-weeks of focused work, split along family boundaries (already done above).

---

## SECTION 12 — Readiness Review

### 12.1 Architecture readiness

| Item | Status |
|------|--------|
| Evidence Truth Architecture V1 | Available — constitutional input |
| Ownership uniqueness | Specified (Visitor gap closed in design) |
| Contracts OE/EB/BK/KF/FG | Mapped to validation points |
| Circular dependency risk | Mitigated by DAG + import rules |
| **Verdict** | **Ready for blueprint ratification** |

### 12.2 Engineering readiness

| Item | Status |
|------|--------|
| Physical sources exist (Raw, signals, purchase, timeline) | Yes (Phase 0 / Exp 0–1 baseline) |
| Bundle Composer target DTO | Exists as legacy shape — adapt, don’t invent merchant fields casually |
| Flag/rollback patterns in repo | Established elsewhere; reuse |
| Open decisions remaining | Storage table names, queue vs sync normalizer — **engineering only** |
| **Verdict** | **Ready to open WP-ET-00…01 after blueprint approval** |

### 12.3 Operational readiness

| Item | Status |
|------|--------|
| Observability blueprint | Specified |
| Silent-loss auditor | Specified (must ship WP-ET-02 before consumer flags) |
| On-call runbooks | **Not written** — required before Stage 7 |
| **Verdict** | **Conditionally ready** — runbooks blocking for Stage 7 |

### 12.4 Testing readiness

| Item | Status |
|------|--------|
| Gate A–E definitions | Specified |
| Fixture/demo provenance rules | Specified |
| BFSV/RV execution | **Paused** — Gate F/G defined but not authorized |
| **Verdict** | **Ready for Stages 1–6 tests; F/G later** |

### 12.5 Reality Validation readiness

| Item | Status |
|------|--------|
| Simulator as same-pipeline emitter | Required; not yet Evidence-integrated |
| Gate G | Defined; **do not resume** until authorized |
| **Verdict** | **Not ready to execute** — by design |

### 12.6 Overall implementation risk

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidental visitor proxy during Findings switch | **High** | Gate B + KF-3 + proxy detector P0 |
| Bundle parity illusions (zeros vs Unavailable) | **High** | Gate C strict field policy |
| Dual-write load / DB growth | **Medium** | Bounded windows; accounting cost metrics |
| Scope creep into Home/UI | **Medium** | Compatibility matrix No Change until Stage 9 |
| Premature BFSV/RV | **Medium** | Hard freeze; WP-ET-13 auth gate |
| Purchase terminal regression | **High** | WP-ET-05 parity tests; wrap-not-rewrite |

**Overall risk rating for starting WP-ET-00…04 after approval:** **Medium** — manageable if gates are non-skippable and Stage 7 remains flag-guarded.

---

## 13. STOP

**Deliverable:** `docs/architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`

**Await:** Blueprint approval.

**Do not:**

- begin production implementation  
- resume BFSV  
- resume Reality Validation  
- modify EvidenceBundle loaders, Knowledge, or Business Findings in this phase  

---

*End of Evidence Truth Implementation Blueprint V1.*
