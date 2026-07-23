# CartFlow Evidence Truth Architecture V1

**Status:** Proposed for Architecture + Product ratification  
**Date (UTC):** 2026-07-23  
**Type:** Constitutional design — architectural authority  
**Scope:** Permanent Evidence Truth platform layer — architecture only  
**Out of scope:** Implementation · refactoring · wiring · loaders · Business Findings changes · Knowledge changes · BFSV continuation · schema migrations · UI  

**Governing product law:** [`MERCHANT_TRUST_CONSTITUTION_V1.md`](../../MERCHANT_TRUST_CONSTITUTION_V1.md) (MT-1 Evidence Before Speech)  
**Commercial proof law:** [`docs/proof_of_value_foundation_v1.md`](../proof_of_value_foundation_v1.md), [`docs/proof_of_value_governance_v1.md`](../proof_of_value_governance_v1.md)  
**Sibling authorities:** Identity Authority Architecture V1 (*which store*), Time Authority (*as of when*), Knowledge Routing Foundation V1 (*where knowledge may appear*)  
**Related investigations:** INV-008 Visitor Truth Coverage Gap (no architectural owner today)  

> This is not a plan to repair today’s EvidenceBundle loaders.  
> This is the Evidence Truth model that must remain correct for Demo, Reality Simulator, Production, Zid, Salla, Shopify, Widget, WhatsApp, Browser SDK, Mobile SDK, historical replay, and every future knowledge consumer.

**Scientific validation baseline (accepted facts — not repair targets):**

| Fact | Implication for this constitution |
|------|-----------------------------------|
| Raw traffic persists correctly | Persistence ≠ Evidence Truth |
| ProductSignalEvents persist correctly | Signal persistence ≠ governed evidence |
| EvidenceBundle never receives traffic truth | Composition gap confirms missing Evidence → Bundle contract |
| Visitor Truth has no architectural owner | Ownership Constitution must assign exactly one owner |
| Evidence Truth → EvidenceBundle contract does not exist | This document defines it |
| BFSV Experiment 2 is intentionally paused | No BFSV work until this architecture is ratified |

**STOP:** Await architectural approval. Do not begin implementation. Do not resume BFSV.

---

## 0. Primary question

### What is the single authoritative layer that transforms canonical merchant observations into governed evidence that all future platform knowledge may safely consume?

**Answer:** **Evidence Truth** — a first-class platform layer that:

1. Owns the meaning of each evidence family (Visitor, Product, Cart, Recovery, Purchase, Communication, Behaviour, …).  
2. Emits **immutable, versioned, confidence-graded, freshness-scoped evidence records**.  
3. Exposes those records **only** through a governed **Evidence → EvidenceBundle** consumption contract.  
4. Never invents knowledge, findings, or guidance.

```text
Raw Event
    ↓
Canonical Observation          ← provider-neutral “what was observed”
    ↓
Evidence Truth                 ← THIS LAYER (governed proof facts)
    ↓
EvidenceBundle                 ← consumption projection only
    ↓
Knowledge                      ← patterns / understanding states
    ↓
Business Finding               ← commercial meaning
    ↓
Guidance                       ← what the merchant may do next
```

Surfaces, Knowledge Layer, Business Findings Engine, Daily Brief, Home, and future AI **must not** invent Evidence Truth. They consume EvidenceBundle (or later routed knowledge derived from it).

---

## 1. Evidence Truth Mission

### 1.1 What is Evidence?

**Evidence** is a **governed, durable, provider-neutral fact** that CartFlow asserts about merchant reality after observation has been validated, normalized, and assigned an owner.

Evidence answers only:

> **What does CartFlow know, with what confidence, as of when, for which store/subject, from which sources — and what would change that knowledge?**

| Property | Definition |
|----------|------------|
| **Governed** | Produced only by the Evidence Truth owner for that family |
| **Durable** | Survives process restart; addressable by stable evidence identity |
| **Provider-neutral** | Same meaning whether source was Zid, Widget, WhatsApp webhook, or replay |
| **Confidence-graded** | Carries an explicit readiness/confidence state (see §6) |
| **Freshness-scoped** | Declares observation window and staleness rules |
| **Versioned** | Schema + semantic version; evolution is explicit |
| **Traceable** | Points back to Canonical Observation(s) and/or Raw Event refs |
| **Immutable** | Once published for a `(evidence_id, evidence_version)`, content does not mutate; supersession creates a new version |

Evidence is **not** a dashboard field, not a finding title, and not a recommendation.

### 1.2 What is NOT Evidence?

| Not Evidence | Why |
|--------------|-----|
| Raw webhook / HTTP payload | Unvalidated, provider-shaped, may be duplicate or partial |
| Canonical Observation alone | Normalized fact of receipt — not yet readiness-governed for consumption |
| Aggregate KPI without owner | Metrics may *display* evidence; they do not *define* it |
| Knowledge insight / pattern | Interpretation over evidence |
| Business Finding | Commercial meaning of patterns |
| Guidance / recommendation | Privileged speech after findings (Trust MT-6) |
| UI copy / registry label | Presentation of evidence identity — not the evidence itself |
| Fixture / demo seed | Valid only when explicitly marked `provenance=demo` and never mixed as production truth |
| “Unavailable” filled with proxy (e.g. carts as traffic) | Forbidden — invents evidence |
| AI-generated assertion | May explain; never creates Evidence Truth |

### 1.3 Permanent vocabulary — six distinct stages

| Term | Question answered | May invent meaning? |
|------|-------------------|---------------------|
| **Raw Event** | What bytes / payload arrived? | No — transport/persistence only |
| **Observation** | What was canonically observed (provider-neutral)? | No — normalization only |
| **Evidence** | What governed fact may consumers safely use? | No — validation + readiness only |
| **Knowledge State** | What patterns / understanding does CartFlow hold? | Yes — but only over Ready/Trusted evidence |
| **Business Finding** | What does that mean commercially for the merchant? | Yes — deterministic commercial meaning |
| **Guidance** | What may CartFlow recommend or prioritize next? | Yes — only after findings + Trust rules |

#### Raw Event

- Ingress artifact: cart-event body, product signal row, WhatsApp webhook, SDK beacon, provider order webhook, replay envelope.  
- May be incomplete, out of order, duplicated, or provider-specific.  
- **Owner:** Ingress / adapter that persisted it.  
- **Must never** be read directly by Knowledge, Findings, or Guidance for merchant speech.

#### Observation (Canonical Observation)

- Provider-neutral record: subject, observed_at, observation_type, store identity (MQIC-compatible), source channel, raw refs.  
- Answers “we observed X at T for subject S.”  
- **Does not** assert readiness for findings.  
- Multiple observations may support one Evidence record.

#### Evidence (Evidence Truth record)

- Governed assertion with readiness, confidence, freshness, version, owner, and observation refs.  
- Answers “CartFlow may treat Y as known under state Z.”  
- **Single meaning per field** (see §9).

#### Knowledge State

- Platform understanding derived from one or more Evidence records (and prior knowledge).  
- Examples: hesitation distribution stability, recovery bottleneck pattern, product interest cluster.  
- **Must declare evidence dependencies.** If required evidence is not Ready/Trusted, Knowledge State is Unknown/Insufficient — never guessed.

#### Business Finding

- Deterministic commercial conclusion (Business Findings Engine contract).  
- Consumes **EvidenceBundle** (projection of Evidence Truth), never Raw Events.  
- Insufficient evidence is a valid finding outcome — not a loader bug to paper over.

#### Guidance

- Merchant-facing next step, attention item, or recommendation.  
- Downstream of Findings (and Decision / Explanation / Routing as applicable).  
- Subject to Merchant Trust Constitution: silence preferred over invention.

### 1.4 Mission statement

> **Evidence Truth transforms canonical merchant observations into governed evidence that all future platform knowledge can safely consume — without inventing meaning, without silent loss, and without provider-shaped leaks.**

---

## 2. Canonical Evidence Model

Evidence Truth organizes reality into **evidence families**. Families are namespaces of ownership and lifecycle — not separate products and not analytics engines.

V1 canonical families (expandable without breaking this constitution):

| Family | Primary question |
|--------|------------------|
| **Visitor Evidence** | Who visited / how much storefront presence occurred? |
| **Product Evidence** | What product interest, view, and catalog facts occurred? |
| **Cart Evidence** | What cart composition and abandon/active states occurred? |
| **Recovery Evidence** | What recovery lifecycle progression occurred? |
| **Purchase Evidence** | What purchase / conversion facts are proven? |
| **Communication Evidence** | What message send / delivery / reply facts occurred? |
| **Behaviour Evidence** | What hesitation, reason, return, and interaction facts occurred? |

Future families (reserved — not required for V1 implementation): Attribution Evidence, Pricing Evidence, Campaign Evidence, Support Evidence. Addition requires Ownership Constitution update (§4) before any consumer may depend on them.

### 2.0 Common record shape (normative)

Every Evidence Truth record **must** be expressible with at least:

| Field | Meaning |
|-------|---------|
| `evidence_family` | One of the families above |
| `evidence_type` | Stable subtype within family (one meaning) |
| `evidence_id` | Stable logical identity (family + type + subject + window key) |
| `evidence_version` | Monotonic version for this `evidence_id` |
| `canonical_store_id` / `store_slug` | From Identity Authority / MQIC — never ad-hoc |
| `subject` | Cart, session, product, visitor, message, store, … |
| `observed_period` | Inclusive start / exclusive end (or point-in-time) |
| `as_of` | Time Authority / QTC compatibility stamp |
| `readiness` | §6 state |
| `confidence` | Grade compatible with Proof of Value §7 |
| `freshness` | Age + TTL / stale threshold metadata |
| `sources[]` | Observation refs + channel provenance |
| `schema_version` | Contract version of this record shape |
| `supersedes` | Prior `evidence_version` if any |
| `integrity` | Checksum / content hash for immutability verification |

**Forbidden on Evidence records:** recommendation text, finding titles, UI labels, ranking scores, AI prompts, surface eligibility (that is Knowledge Routing).

### 2.1 Visitor Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Visitor Truth Authority** (new architectural owner under Evidence Truth — closes INV-008 gap) |
| **Lifecycle** | Raw visit/session/presence events → Observations (`store_visit`, `session_start`, …) → Visitor Evidence aggregates / subject facts → Ready when eligibility rules pass → Bundle field `visitor_*` only from this owner |
| **Source(s)** | Widget / Browser SDK presence, storefront beacons, provider traffic webhooks (if any), Mobile SDK, historical replay of the same observation types |
| **Confidence** | Unknown until owner publishes; never inferred from cart counts |
| **Freshness** | Windowed counts stale per declared TTL; point visits immutable once published |
| **Versioning** | `visitor_evidence` schema; bump on meaning change of visitor definition |

**Hard rule:** Carts, abandoned carts, or recovery rows **must never** proxy Visitor Evidence.

### 2.2 Product Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Product Truth Authority** (Evidence Truth family owner; today’s ProductSignalEvents are *sources*, not the authority) |
| **Lifecycle** | Product signals / catalog hooks → Observations → Product Evidence (views, interest, cart-line presence) → Ready for Bundle `products` / view flags |
| **Source(s)** | ProductSignalEvents, cart line snapshots, catalog sync, Widget PDP hooks, provider product webhooks, replay |
| **Confidence** | Per product subject; `has_product_views` only when view evidence is Ready |
| **Freshness** | Signal windows; catalog facts may have longer TTL than view counts |
| **Versioning** | `product_evidence` schema; product_id identity must be provider-neutral alias → canonical product key |

### 2.3 Cart Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Cart Truth Authority** (session/cart persistence + abandon identity; correlates via `recovery_key` rules in source-of-truth map) |
| **Lifecycle** | Cart-event Raw → Observations → Cart Evidence (active, value, items, no-phone, VIP lane inputs) → Bundle cart fields |
| **Source(s)** | `POST /api/cart-event`, provider cart webhooks, test-widget, SDK cart APIs, replay |
| **Confidence** | High when durable cart row + identity coherent; Unknown on identity conflict (fail closed with Identity Authority) |
| **Freshness** | Live carts short TTL for “active”; historical cart facts immutable after terminal purchase/archive overlay |
| **Versioning** | `cart_evidence` schema; identity changes require new observation chain, not silent rewrite |

### 2.4 Recovery Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Recovery Truth Authority** (timeline + lifecycle truth modules conceptually under this family) |
| **Lifecycle** | Schedule/send/return/reply events → Observations → Recovery Evidence aligned with Lifecycle Truth Contract states → Bundle recovery/movement fields |
| **Source(s)** | Recovery schedules, recovery logs, recovery truth timeline, return-to-site signals, archive overlay |
| **Confidence** | Progression requires timeline proof where Lifecycle Truth Contract demands it (e.g. sent ≠ delivered) |
| **Freshness** | Event facts immutable; open-lifecycle “current state” is a versioned projection |
| **Versioning** | `recovery_evidence` schema; state vocabulary locked to Lifecycle Truth Contract |

### 2.5 Purchase Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Purchase Truth Authority** (existing purchase truth conceptual owner — elevated into Evidence Truth family) |
| **Lifecycle** | Conversion / order webhooks → Observations → Purchase Evidence → terminal stop authority for recovery → Bundle purchase fields |
| **Source(s)** | Conversion API, provider order webhooks, purchase truth records, replay |
| **Confidence** | Confirmed only when Purchase Truth eligibility passes; never “assumed purchased” from cart disappearance |
| **Freshness** | Purchase facts are point-in-time immutable; corrections via superseding version + audit |
| **Versioning** | `purchase_evidence` schema; reconciles with recovery stop rules |

### 2.6 Communication Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Communication Truth Authority** (WhatsApp / provider delivery truth + template send proof) |
| **Lifecycle** | Provider queued/sent/delivered/failed + inbound reply → Observations → Communication Evidence → Bundle `wa_*` / message fields |
| **Source(s)** | Twilio/Meta send paths, delivery webhooks, inbound reply webhooks, WhatsApp delivery truth, merchant alert sends |
| **Confidence** | **Sent ≠ Delivered** (Proof of Value). Delivery claims require delivery evidence |
| **Freshness** | Delivery updates may arrive late — late evidence rules (§8) apply; no silent drop |
| **Versioning** | `communication_evidence` schema; channel-agnostic types (`message_accepted`, `message_delivered`, `customer_replied`) |

### 2.7 Behaviour Evidence

| Aspect | Definition |
|--------|------------|
| **Owner** | **Behaviour Truth Authority** (hesitation, reason capture, return behaviour, widget interaction facts) |
| **Lifecycle** | Widget/SDK reason & interaction Raw → Observations → Behaviour Evidence → Bundle hesitation / widget / return behaviour fields |
| **Source(s)** | Widget reason capture, phone capture, hesitation hooks, return-without-purchase observations, Browser/Mobile SDK behaviour events |
| **Confidence** | Reason evidence High when durable reason record exists; interaction counts need eligibility thresholds |
| **Freshness** | Reason tags stable per session; distributions are windowed and versioned |
| **Versioning** | `behaviour_evidence` schema; reason taxonomy changes require explicit migration notes |

### 2.8 Cross-family rules

1. **One fact → one primary family.** Secondary refs allowed; dual ownership forbidden.  
2. **Correlation** across families uses Identity Authority subjects (`recovery_key`, canonical product id, visitor id) — Evidence Truth does not invent identity.  
3. **Commerce Signals** (if used) sit **after** Evidence and may only reference Evidence — they never replace Evidence Truth (see `commerce_signals_foundation_v1.md`).  
4. **Merchant Evidence Registry** maps `evidence_id` → merchant labels for presentation. Registry is **not** Evidence Truth; it must not invent new truth.

---

## 3. Evidence Lifecycle

```text
Raw Event
    ↓
Canonical Observation
    ↓
Evidence Truth
    ↓
EvidenceBundle
    ↓
Knowledge
    ↓
Business Finding
    ↓
Guidance
```

### 3.1 Stage responsibilities

| Stage | Responsibility | Writes | Must not |
|-------|----------------|--------|----------|
| **Raw Event** | Persist ingress faithfully with provenance | Raw store | Interpret, drop silently, rewrite history without audit |
| **Canonical Observation** | Normalize to provider-neutral observation types | Observation store | Assert readiness, confidence for findings, merchant speech |
| **Evidence Truth** | Validate, dedupe, order, grade, version, publish evidence | Evidence store (immutable versions) | Create findings, guidance, surface layout |
| **EvidenceBundle** | Project store-scoped evidence for a query window into a consumption DTO | Ephemeral / cached projection only | Own truth, invent missing fields, query raw tables ad hoc as authority |
| **Knowledge** | Derive understanding / patterns from Bundle (or evidence refs) | Knowledge states | Backfill missing evidence with proxies |
| **Business Finding** | Emit commercial findings from Bundle | Finding records | Read Raw Events or bypass readiness |
| **Guidance** | Recommend / prioritize actions under Trust + Decision rules | Guidance / decisions / routed items | Speak without finding+evidence support |

### 3.2 Contracts between stages (summary)

Detailed field contracts are in §5. Lifecycle invariants:

1. **Forward-only meaning:** Each stage may only *restrict* or *project* meaning from the previous — never invent upstream facts.  
2. **Fail closed on identity/time:** Missing MQIC or QTC → no merchant-grade Evidence publication for that request/run.  
3. **Readiness monotonicity for a version:** A published version’s readiness may be superseded by a **new version**, not silently edited.  
4. **Bundle is not a source:** If Bundle and Evidence Truth disagree, Evidence Truth wins; Bundle is rebuilt.  
5. **Knowledge/Findings/Guidance never write Evidence.**

### 3.3 EvidenceBundle role (constitutional clarification)

Today’s `EvidenceBundle` (Business Findings evidence module) is a **pragmatic aggregation DTO**. Under this architecture it becomes:

> **EvidenceBundle = consumption-only projection of Evidence Truth for a `(store, window, as_of)` query.**

It is **not** the Evidence Truth store. It **must not** load Raw Events as authority. Fields such as `visitor_total`, `has_visitor_truth`, `has_product_views` are **Bundle projections** of Visitor/Product Evidence readiness — not inventable flags.

### 3.4 Relationship to Proof / Decision / Routing

Proof of Value pipeline (Truth → Evidence → Proof → Decision → Surface) remains valid. Mapping:

| PoV / Routing term | Evidence Truth Architecture term |
|--------------------|----------------------------------|
| Truth (Tier 0) | Family authorities inside Evidence Truth |
| Evidence | Evidence Truth records |
| Proof / Proof Surface | Presentation composition over Evidence (and registry labels) |
| Knowledge item | Knowledge State (+ producer metadata) |
| Decision / Guidance | Guidance stage (Decision Foundation / Governance) |
| Knowledge Routing | After Knowledge/Findings/Guidance — never creates evidence |

---

## 4. Ownership Constitution

**Law:** Every evidence question has **exactly one owner**. If two modules disagree, the named owner wins. Surfaces never own evidence questions.

### 4.1 Ownership table

| Evidence question | Single owner | Notes |
|-------------------|--------------|-------|
| **Visitor Truth** | Visitor Truth Authority | Closes INV-008; no other module may define visitor totals |
| **Product View Truth** | Product Truth Authority | ProductSignalEvents are sources under this owner |
| **Traffic Truth** | Visitor Truth Authority | “Traffic” is a Visitor Evidence concern; not a parallel owner |
| **Behaviour Truth** | Behaviour Truth Authority | Hesitation, reasons, interaction patterns |
| **Purchase Truth** | Purchase Truth Authority | Terminal conversion authority |
| **Cart Truth** | Cart Truth Authority | Cart identity, contents, abandon/active |
| **Recovery Truth** | Recovery Truth Authority | Lifecycle progression / timeline-aligned recovery facts |
| **Communication Truth** | Communication Truth Authority | Send / delivery / reply (channel-neutral) |
| **Evidence Freshness** | Evidence Truth Platform (cross-cutting) | Declares freshness policy; families supply per-type TTLs |
| **Evidence Eligibility** | Evidence Truth Platform | Readiness gates (§6); families supply type-specific predicates |
| **Evidence Confidence** | Evidence Truth Platform | Confidence vocabulary alignment with PoV; families supply inputs |
| **EvidenceBundle Composition** | Evidence Bundle Composer (consumption owner) | Projects only; **cannot** create evidence the family owner did not publish |

### 4.2 Why some ownership is platform-cross-cutting

**Freshness, Eligibility, Confidence, Bundle Composition** are *governance functions* over family outputs. They are not second writers of Visitor/Product facts. They:

- accept family-published evidence,  
- apply platform rules,  
- emit readiness/confidence metadata and Bundle projections.

They **must not** fabricate family facts when families publish Unknown/Unavailable.

### 4.3 Explicit non-owners (forbidden)

| Actor | Forbidden ownership |
|-------|---------------------|
| Business Findings Engine | Any evidence question — consumes Bundle only |
| Knowledge Layer / Home / Daily Brief | Any evidence question — consume routed knowledge / Bundle projections |
| Merchant Evidence Registry | Truth meaning — labels only |
| Reality Simulator | Production evidence meaning — may emit Raw/Observations into the same pipeline under simulation provenance |
| Provider adapters (Zid/Salla/Shopify) | Canonical evidence meaning — aliases and Raw only |
| Widget / SDKs | Canonical evidence meaning — Raw only |
| BFSV experiments | Architectural ownership — paused; may not redefine Evidence Truth |

### 4.4 Ownership conflicts

If ownership cannot be uniquely assigned, **the design is incomplete** — do not ship dual writers. Temporary dual-read during migration (§10) is allowed; dual-write is not.

---

## 5. Evidence Contracts

Contracts are normative. Implementers may choose storage technology; they may not weaken fields or skip stages.

### 5.1 Observation → Evidence

**Producer:** Family Evidence Authority  
**Input:** One or more Canonical Observations (+ identity + time context)  
**Output:** Zero or more Evidence versions

| Rule ID | Contract |
|---------|----------|
| OE-1 | Every Evidence record lists `sources[]` observation refs (or explicit `synthetic=false` denial — synthetics forbidden for production provenance) |
| OE-2 | Observation `observed_at` must fall within Evidence `observed_period` or be a declared point evidence |
| OE-3 | Dedupe key defined per `evidence_type`; duplicates yield same version or explicit supersession — never double count silently |
| OE-4 | Out-of-order observations are applied via reorder buffer / superseding version — never ignored |
| OE-5 | Authority emits readiness ∈ {Unknown, Unavailable, Insufficient, Conflicting, Ready, Trusted} |
| OE-6 | Fail closed on store identity mismatch |
| OE-7 | No Evidence field may encode guidance or finding text |

### 5.2 Evidence → EvidenceBundle

**Producer:** Evidence Bundle Composer  
**Input:** MQIC store + window + `as_of` + requested families  
**Output:** EvidenceBundle DTO (versioned)

| Rule ID | Contract |
|---------|----------|
| EB-1 | Bundle fields are projections of published Evidence only |
| EB-2 | Missing family → readiness Unavailable/Unknown on that slice — **not** zero-filled as if observed |
| EB-3 | `has_visitor_truth` / `has_product_views` (and successors) are **true** only when corresponding Evidence readiness ≥ Ready |
| EB-4 | Bundle carries `evidence_refs[]` / source digest for explainability |
| EB-5 | Bundle `schema_version` independent of family schema but compatible |
| EB-6 | Composer may cache projections; cache invalidation on new evidence version |
| EB-7 | Composer **must not** query Raw Event tables as authoritative substitutes for missing Evidence |
| EB-8 | Demo/fixture Bundles must set `loaded_from` / provenance ≠ production truth |

### 5.3 EvidenceBundle → Knowledge

**Producer:** Knowledge producers (KL, explanation, etc.)  
**Input:** EvidenceBundle and/or evidence refs  
**Output:** Knowledge State / insights with claim-level evidence ownership

| Rule ID | Contract |
|---------|----------|
| BK-1 | Each knowledge claim declares required evidence families/types |
| BK-2 | If any required evidence readiness < Ready → claim confidence Unknown/Insufficient — no proxy fill |
| BK-3 | Claim-level `evidence_id` (registry) must map to Evidence Truth family, not to UI section |
| BK-4 | Knowledge must not write Evidence or Bundle |
| BK-5 | Knowledge Routing metadata may attach only after knowledge is produced |

### 5.4 Knowledge → Business Findings

**Producer:** Business Findings Engine  
**Input:** EvidenceBundle (primary); optional knowledge refs for ranking context — **not** as substitute evidence  
**Output:** `BusinessFindingV1` (or successor)

| Rule ID | Contract |
|---------|----------|
| KF-1 | Findings evaluate Bundle projections only for factual predicates |
| KF-2 | Insufficient evidence is a valid deterministic result |
| KF-3 | Findings must not treat `visitor_total=None` as `0` |
| KF-4 | One finding → one commercial meaning |
| KF-5 | Finding explainability must cite Bundle evidence summary / refs |

### 5.5 Business Findings → Guidance

**Producer:** Guidance / Decision / Home composition consumers  
**Input:** Published findings (+ Trust Ladder / Decision Governance)  
**Output:** Guidance items, attention decisions, recommendations

| Rule ID | Contract |
|---------|----------|
| FG-1 | Guidance requires at least one published finding (or governed decision derived from findings/proof) — no free-floating advice from Raw Events |
| FG-2 | Trust MT-3/MT-6: silence legal; guidance is a privilege |
| FG-3 | Guidance must not mutate Evidence, Bundle, Knowledge, or Findings |
| FG-4 | Surface composers consume routed guidance/knowledge — they do not re-derive evidence |

---

## 6. Readiness Rules

Platform-wide readiness vocabulary. All families, Bundle fields, Knowledge gates, and Findings predicates **must** use these states — not ad-hoc booleans with overloaded meaning.

| State | Definition | Consumer rule |
|-------|------------|---------------|
| **Unknown** | Authority has not yet evaluated this subject/window (no publication) | Do not assert absence or presence |
| **Unavailable** | Authority evaluated: source channel not connected / not licensed / not implemented for this store | Speak “unavailable”; never proxy |
| **Insufficient** | Some observations exist but below eligibility thresholds (count, diversity, identity completeness) | Findings may emit insufficient-evidence outcomes |
| **Conflicting** | Observations disagree beyond reconciliation policy | Fail closed for that claim; escalate/audit; no silent pick |
| **Ready** | Eligibility passed; safe for Knowledge and Findings predicates | May compute patterns/findings with stated confidence |
| **Trusted** | Ready **and** reinforced (multi-source agreement, repeated windows, or higher-tier proof per PoV) | Eligible for stronger merchant speech / higher confidence labels |

### 6.1 Transition rules

```text
Unknown → Unavailable | Insufficient | Conflicting | Ready
Unavailable → Ready | Insufficient   (when source becomes available)
Insufficient → Ready | Conflicting
Conflicting → Ready | Trusted        (only via explicit reconciliation → new version)
Ready → Trusted                      (reinforcement)
Any published state → superseded by new evidence_version
```

**Forbidden:** Trusted → silently lower without new version; Unavailable → Ready by inventing zeros; Conflicting → Ready by arbitrary choice.

### 6.2 Mapping to today’s Bundle flags (informative, not implementation)

| Bundle-era signal | Readiness meaning |
|-------------------|-------------------|
| `visitor_total is None` + `has_visitor_truth=False` | Unavailable or Unknown (must be disambiguated by Visitor Authority) |
| `has_product_views=False` | Product View Truth not Ready |
| Non-null counts with thin N | Insufficient (Findings already treat some cases this way) |

---

## 7. Scalability

Evidence Truth is **provider-neutral and channel-neutral**. Scalability is a property of the architecture, not of a single marketplace.

### 7.1 Commerce providers

| Provider | Adapter role | Evidence Truth role |
|----------|--------------|---------------------|
| **Zid** | Emit Raw Events / Observations with Zid aliases | Resolve aliases → canonical store/product; same evidence types |
| **Salla** | Same | Same |
| **Shopify** | Same | Same |
| **Future providers** | New adapter only | **No new Evidence meaning** without Ownership + schema version |

Adapters **must not** publish Evidence records directly. They publish Raw → Observation under Ingress contracts.

### 7.2 Channels & SDKs

| Channel | Produces Raw/Observations for families |
|---------|----------------------------------------|
| **Widget** | Behaviour, Cart, Visitor (presence), Product (PDP) |
| **WhatsApp** | Communication, Recovery progression inputs |
| **Browser SDK** | Visitor, Behaviour, Product, Cart |
| **Mobile SDK** | Same families with mobile provenance tags |
| **Provider webhooks** | Purchase, Cart, Product catalog, optional traffic |

All channels share observation type vocabulary; provenance records `channel`.

### 7.3 Historical replay, archival, rollups

| Mode | Rule |
|------|------|
| **Historical replay** | Re-ingest Raw or Observations with original `observed_at`; Evidence versions get `provenance=replay` and must not clobber live versions without explicit supersession policy |
| **Archival** | Immutable Evidence versions are archive-friendly; Bundle projections are disposable |
| **Rollups** | Rollups are **derived Evidence types** (still owned by the family) or Knowledge — never silent replacements of atomic evidence |
| **Knowledge Routing** | Consumes knowledge/findings/guidance only; evidence scalability does not grant routing the right to mint evidence |
| **Reality Validation** | Simulator emits into the same pipeline with simulation provenance + MQIC attach; merchant trust review requires Identity + Time + Evidence alignment |

### 7.4 Multi-tenant scale principles

- Store isolation via canonical store identity on every record.  
- Windowed Bundle composition with explicit cost budgets (today’s capped loaders become Composer policies, not truth).  
- Family authorities scale independently; Bundle Composer is fan-in only.

---

## 8. Failure Governance

**Prime directive:** **No silent evidence loss.**

| Failure mode | Required handling |
|--------------|-------------------|
| **Missing evidence** | Publish Unavailable/Unknown/Insufficient — never invent; Findings/Knowledge degrade honestly |
| **Late evidence** | Accept into reorder/supersession path; emit new `evidence_version`; invalidate Bundle cache; audit `late_arrival` |
| **Duplicate evidence** | Idempotent dedupe keys; duplicates ack without double count; audit `duplicate_suppressed` |
| **Conflicting evidence** | Mark Conflicting; block Ready for that claim; retain both observation refs; require reconciliation policy per type |
| **Out-of-order evidence** | Buffer by `observed_at` / sequence; apply in order or supersede; never drop |
| **Stale evidence** | Freshness policy marks stale; consumers see Insufficient/Unavailable for live claims; historical as-of queries still valid |
| **Provider outages** | Observations cease; Evidence freshness decays to stale; status Unavailable for live windows; no synthetic fill |
| **Replay** | Isolated provenance; deterministic IDs; cannot silently overwrite production Trusted evidence |
| **Schema evolution** | Additive changes preferred; breaking changes require `schema_version` bump + dual-read migration window (§10); old versions remain readable |

### 8.1 Audit & observability (constitutional)

Evidence Truth **must** expose (admin/ops, not merchant chrome):

- publication counts by family/readiness  
- duplicate / late / conflict counters  
- silent-drop detector (ingress vs observation vs evidence lag)  
- Bundle composer cache invalidation events  

A drop from Raw→Observation or Observation→Evidence without audit entry is a **P0 constitutional defect**.

### 8.2 Correction policy

Corrections create **new versions** (`supersedes`). Prior versions remain for audit and as-of replay. Hard deletes of Evidence are forbidden except legal erasure workflows that still leave tombstone audit.

---

## 9. Architectural Principles

| ID | Principle | Meaning |
|----|-----------|---------|
| **ET-1** | **Evidence Before Knowledge** | Knowledge may not assert patterns without Ready/Trusted evidence dependencies |
| **ET-2** | **Knowledge Before Findings** | Findings interpret knowledge-capable evidence projections — not raw ingress |
| **ET-3** | **Findings Before Guidance** | Guidance is privileged speech after commercial findings (aligns MT-6) |
| **ET-4** | **Single Owner Per Truth** | Exactly one owner per evidence question (§4) |
| **ET-5** | **Canonical Provider-Neutral Evidence** | Zid/Salla/Shopify/Widget/SDK differences end at Observation |
| **ET-6** | **Evidence Is Immutable** | Published `(evidence_id, evidence_version)` never mutates |
| **ET-7** | **One Meaning Per Evidence Field** | No overloaded flags; readiness ≠ confidence ≠ freshness |
| **ET-8** | **EvidenceBundle Is Consumption Only** | Bundle projects; never owns or invents truth |
| **ET-9** | **No Silent Evidence Loss** | Every drop is audited or explicitly classified Unavailable |
| **ET-10** | **No Proxy Truth** | Carts are not traffic; sent is not delivered; absence is not zero |
| **ET-11** | **Identity & Time Before Evidence Speech** | MQIC + as-of required for merchant-grade publication |
| **ET-12** | **Presentation Never Creates Evidence** | Registry, UI, AI explanation cannot mint Evidence Truth |

---

## 10. Migration Strategy

Architecture-only path from current platform → Evidence Truth. **No implementation plan, tickets, or file-level rewrites here** — only evolutionary constraints so production does not break.

### 10.1 Current state (honest)

| Area | Today | Gap vs this constitution |
|------|-------|--------------------------|
| Raw persistence | Traffic / signals / carts persist | Not governed as Evidence |
| Family truths | Purchase / Recovery / Lifecycle / Delivery exist as modules | Not unified under Evidence Truth ownership |
| Visitor Truth | No owner (INV-008) | Must create Visitor Truth Authority before traffic enters Bundle |
| EvidenceBundle | Loader aggregates operational tables / fixtures | Acts as de-facto authority; missing Evidence → Bundle contract |
| Knowledge / Findings | Consume Bundle / tables | Sometimes encounter Unavailable visitor/product flags |
| BFSV | Experiment 2 paused | Remains paused until ratification + later authorized experiments |

### 10.2 Evolutionary phases (architectural, not a sprint plan)

**Phase A — Ratify & freeze meaning**  
Adopt this document as authority. Freeze: no new consumer may invent visitor/product proxies; BFSV stays paused.

**Phase B — Dual-read / single-write preparation**  
Introduce Evidence Truth as the **semantic owner** while existing tables remain physical sources. Bundle Composer begins to prefer family-published readiness over ad-hoc null flags — without changing merchant speech until parity is proven.

**Phase C — Family-by-family cutover**  
Order constrained by dependency and risk (illustrative): Purchase & Communication (already strong) → Recovery & Cart → Behaviour → Product → **Visitor last among core store metrics** (because ownership is new). Each family cutover requires readiness parity tests and no silent loss detectors green.

**Phase D — Bundle becomes pure projection**  
EvidenceBundle loaders stop being truth authorities. Findings/Knowledge depend only on Composer output + evidence refs.

**Phase E — Decommission dual-read**  
Remove obsolete direct table interpretation paths from Knowledge/Findings hot paths. Registry and Proof Surface remain presentation.

### 10.3 Non-breakage guarantees

1. **Merchant-visible speech does not get “more certain” during migration** without readiness upgrade — Trust MT-5.  
2. **Existing Purchase/Recovery stop behaviour** remains owned by their authorities; Evidence Truth wraps, does not weaken terminals.  
3. **Demo/fixture Bundles** remain allowed with explicit provenance for Review Labs — never mixed into production Trusted.  
4. **Reality Validation / Simulator** adopt the same contracts with simulation provenance — no parallel fake Evidence channel.  
5. **No Big-Bang rewrite** of Business Findings or Knowledge as a prerequisite — they become conformant consumers as Bundle contract hardens.

### 10.4 Explicitly deferred

- Storage engine choice  
- API shapes  
- Work package breakdown  
- BFSV Experiment 2 resume criteria (requires separate authorization after this ratification)  
- UI changes  

---

## 11. Conformance checklist (for future implementers)

Multiple engineers implementing independently should agree on all of the following:

1. Vocabulary: Raw ≠ Observation ≠ Evidence ≠ Knowledge ≠ Finding ≠ Guidance.  
2. Every evidence question maps to exactly one owner in §4.  
3. Visitor totals never derived from carts.  
4. Bundle fields for a family are absent/Unavailable until that family’s Evidence is Ready/Trusted.  
5. Immutability + supersession for corrections.  
6. Late/duplicate/conflict/out-of-order paths are defined and audited.  
7. Providers/channels only adapt Raw→Observation.  
8. Findings/Guidance never write Evidence.  
9. Readiness states are the six values in §6 — no silent synonyms.  
10. Migration never increases merchant certainty without evidence readiness.

---

## 12. Authority & amendment

| Role | Power |
|------|-------|
| This document (once ratified) | Architectural authority for Evidence Truth |
| Merchant Trust Constitution | Overrides any Evidence speech that violates MT-* |
| Identity / Time Authorities | Constrain publication context |
| Proof of Value / Decision / Knowledge Routing | Downstream of Evidence — may not redefine Evidence |

Amendments require Architecture (+ Product when merchant speech meaning changes). Additive family expansion allowed only with §4 ownership update.

---

## 13. STOP

**Deliverable complete:** `docs/architecture/EVIDENCE_TRUTH_ARCHITECTURE_V1.md`

**Await:** Architectural approval.

**Do not:** begin implementation · resume BFSV · change loaders · change Business Findings · change Knowledge · wire surfaces.

---

*End of Evidence Truth Architecture V1.*
