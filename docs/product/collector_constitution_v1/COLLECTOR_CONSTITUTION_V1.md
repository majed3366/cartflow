# Collector Constitution V1

**Status:** Architecture and governance only.  
**Authority:** Constitutional contract for every future CartFlow Collector.  
**Non-goals of this pack:** No production code. No collectors. No UI. No Evidence Expansion changes.  
**Related (subordinate):** Evidence Expansion Framework V1, Evidence Gap Registry, Collector Prioritization V1, Diagnostic Engine Law.

---

## Preamble

This Constitution is the **highest governance instrument** for Collectors.

A Collector that violates this Constitution is **unconstitutional**, even if it is technically elegant, commercially attractive, or already partially built.

No Collector may ship, expand, or remain in production without continuous conformity to this document.

---

## Article I — Mission

### §1 Sole purpose

A Collector exists **only** to improve diagnostic quality.

It does **not** exist to collect more data.

### §2 Non-mission (forbidden purposes)

Collectors must not be justified by:

- “We may need this later”
- analytics vanity
- product completeness for its own sake
- provider feature parity theater
- merchant curiosity without diagnostic use

### §3 Build veto

If a Collector cannot **measurably** improve a diagnosis, **it must not be built**.

If ROI cannot be measured, **it must not be approved**.

---

## Article II — Lifecycle (mandatory, no skips)

Every Collector must follow **exactly** this lifecycle:

```
Need
  ↓
Evidence Gap
  ↓
Collector Proposal
  ↓
Architecture Review
  ↓
Collector Constitution Validation
  ↓
Implementation
  ↓
Reality Validation
  ↓
Diagnostic Impact Measurement
  ↓
Production
```

### §4 Stage definitions

| Stage | Meaning |
|-------|---------|
| **Need** | A real merchant / diagnostic need is named (not a wishlist). |
| **Evidence Gap** | A registered Evidence Gap exists (or is formally registered) that blocks honest diagnosis. |
| **Collector Proposal** | Written proposal using the Mandatory Collector Contract (Article III). |
| **Architecture Review** | Review against Diagnostic Engine Law, Evidence Expansion, provider isolation, performance law. |
| **Collector Constitution Validation** | Explicit check that every Article of this Constitution is satisfied. |
| **Implementation** | Code, adapters, persistence, tests — **after** prior stages pass. |
| **Reality Validation** | Correctness verified against real / Living Store / provider reality (not mocks alone). |
| **Diagnostic Impact Measurement** | Evidence ROI metrics (Article IV) measured before or as gate to Production. |
| **Production** | Enabled only after impact and performance are acceptable. |

### §5 Skip ban

No Collector may skip any stage.

Skipping a stage voids approval. Work that proceeds past a skipped stage is unconstitutional until the skipped stage is completed retroactively **and** re-validated.

---

## Article III — Mandatory Collector Contract

Every Collector **must declare** all fifteen fields below. Incomplete contracts fail Constitution Validation.

| # | Field | Requirement |
|---|--------|-------------|
| 1 | **Collector Name** | Stable identifier + human title. |
| 2 | **Business Purpose** | Why merchants / diagnosis need this — one clear purpose. |
| 3 | **Observable** | Exactly what is being observed (canonical observable key — Article VI). |
| 4 | **Observation Trigger** | When collection begins. |
| 5 | **Observation End** | When collection stops. |
| 6 | **Evidence Produced** | Exactly which evidence becomes available to diagnosis. |
| 7 | **Evidence Gap Closed** | Which registered gap is reduced or closed. |
| 8 | **Diagnosis Improved** | Which diagnosis / family / cause separation becomes more accurate. |
| 9 | **Recommendations Enabled** | Which recommendations become safer (or remain correctly suppressed without this evidence). |
| 10 | **Provider Capability** | Support matrix: Zid / Salla / Shopify / Generic / Unsupported. |
| 11 | **Performance Cost** | CPU, Database, Network, Storage — expected bounds. |
| 12 | **Retention** | How long data lives; deletion / aggregation rules. |
| 13 | **Privacy** | Customer information collected; minimization stance. |
| 14 | **Failure Behaviour** | What happens if collection fails (must degrade honestly — Article VII). |
| 15 | **Reality Validation** | How correctness is verified in reality. |

Use the blank template: [`COLLECTOR_CONTRACT_TEMPLATE_V1.md`](./COLLECTOR_CONTRACT_TEMPLATE_V1.md).

---

## Article IV — Evidence ROI

### §6 Measurable success required

Every Collector must define measurable success **before** Implementation approval.

### §7 Required metrics

At minimum:

1. **Diagnosis improvement** — named diagnosis / cause separation quality delta  
2. **Reduction of `insufficient_evidence`** — where this Collector is the limiting gap  
3. **Reduction of `conflicting_evidence`** — if applicable; else N/A with justification  
4. **Increase in supported diagnoses** — honest supported outcomes enabled by new evidence  
5. **Recommendation accuracy** — safer enablement / continued correct suppression  
6. **Merchant usefulness** — merchant can act on improved diagnosis / recommendation without false confidence  

### §8 ROI veto

If ROI cannot be measured, the Collector **must not be approved**.

---

## Article V — No Random Collection

### §9 Forbidden justification

> “We may need this later.”

### §10 Allowed justification

> “This observable improves Diagnosis X by closing Evidence Gap Y.”

### §11 Catalog alignment

Canonical observables must appear in the Evidence Expansion observable catalog (or a formally approved successor) with:

- non-empty `separates_causes`
- non-empty `diagnosis_families`

Catalog entry alone does **not** authorize a Collector. Lifecycle stages still apply.

---

## Article VI — Canonical Observable

### §12 One definition

Every observable must have **one** canonical definition.

### §13 Adapter translation

Provider adapters translate provider payloads **into** the canonical observable.

### §14 Provider field ban

Collectors must **never** depend directly on Zid, Salla, or Shopify field names in diagnosis or recommendation logic.

Provider-specific code belongs only in adapters / collectors’ provider layers that emit canonical evidence.

---

## Article VII — Provider Isolation

### §15 Unsupported honesty

If one provider cannot expose an observable:

- Diagnosis must **degrade honestly** (`insufficient_evidence` or equivalent).
- **Never guess.**
- **Never emulate** unsupported signals.
- **Never invent** parity by synthesizing fake observations.

### §16 Capability matrix truth

The Provider Capability matrix (Contract field 10) must reflect reality, not aspiration. Unsupported means unsupported until a Reality Validation proves otherwise.

---

## Article VIII — Performance Law

### §17 Merchant request path ban

Collectors must **never** execute on merchant request paths (Home, Live, dashboard read APIs that serve the merchant UI).

### §18 Lawful pipeline

Collection must follow:

```
Collection
  ↓
Background
  ↓
Persistence
  ↓
Evidence
  ↓
Diagnosis
  ↓
Snapshot
  ↓
Merchant UI
```

### §19 Material degradation veto

A Collector that materially degrades platform performance (especially Home / snapshot / Live read latency) fails Constitution Validation and must not enter Production until remediated.

---

## Article IX — Required Tests

Every Collector must ship with:

1. **Contract tests** — Mandatory Collector Contract fields / invariants  
2. **Provider tests** — capability matrix; supported vs unsupported behaviour  
3. **Identity tests** — store / session / merchant binding correctness  
4. **Performance tests** — no merchant-path execution; cost bounds  
5. **Failure tests** — Failure Behaviour degrades honestly  
6. **Reality Validation tests** — correctness against approved reality fixtures / Living Store / provider truth  

Absence of any category blocks Production.

---

## Article X — Success

### §20 Definition of success

A Collector is successful **only** when:

1. It **measurably** improves diagnosis quality, **and**  
2. It does so **without materially degrading** platform performance.

Shipping code, collecting volume, or filling storage is **not** success.

---

## Article XI — Relationship to Other Law

| Instrument | Relationship |
|------------|--------------|
| Diagnostic Engine Law | Collectors may only feed Observation → Evidence; never invent causes or skip evidence comparison. |
| Evidence Expansion Framework V1 | Gaps and catalog govern *what may be missing*; Collectors govern *how signals are obtained*. |
| Evidence Gap Registry | Field 7 must cite a registered gap. |
| Collector Prioritization V1 | Ordering of *which* Collector next; this Constitution governs *whether* any may exist. |
| Home / Snapshot / Live | Merchant UI reads snapshots / published diagnoses only — never live collection. |

In conflict: **this Constitution prevails for Collector existence and shape**; Diagnostic Engine Law prevails for diagnosis honesty.

---

## Article XII — Amendment

Amendments require a new version (`Collector Constitution V2+`) with explicit change log. Silent reinterpretation is forbidden.

---

## Ratification checklist (Constitution Validation gate)

Before Implementation:

- [ ] Mission satisfied (diagnosis quality only)  
- [ ] Lifecycle stages through Constitution Validation complete  
- [ ] All 15 contract fields filled  
- [ ] Evidence ROI metrics defined and measurable  
- [ ] No random-collection justification  
- [ ] Canonical observable named; no direct provider field coupling in diagnosis  
- [ ] Provider matrix honest; unsupported → degrade  
- [ ] Performance law: background-only; cost bounds stated  
- [ ] Test plan covers all six required test categories  
- [ ] Success criteria stated in measurable terms  

---

## Explicit stop

**Shipping Cost First Shown** and all other Collectors remain **unimplemented** until this Constitution is approved and a Collector Proposal passes Constitution Validation.

**STOP.**
