# CartFlow Operational Truth Integration Foundation V1 (OTIF)

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-22  
**Authority:** Independent producer subordinate only to durable operational facts; consumed by Surface Composition.  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Product Intelligence, AI, Recommendation Engine, Decision Engine, UI/Surface redesign, new Knowledge, new Guidance

> **Law:** Operational Truth answers what operational condition exists, how severe it is, whether it requires attention, and whether Surface Composition must expose it.  
> It does not recommend. It does not guide. It does not invent Knowledge.

---

## 0. Placement

```text
Canonical Truth
        ↓
Evidence
        ↓
Commerce Intelligence Synthesis
        ↓
Knowledge
        ↓
Commercial Guidance
        ↓
Operational Truth          ← THIS LAYER
        ↓
Surface Composition
        ↓
Merchant Experience
```

Closes Capability Gap **CG-MEH-02** (Operational Truth as SCF input).

---

## 1. Mission

Continuously answer:

| Question | Owner |
|----------|-------|
| What operational condition exists? | OT package |
| How severe is it? | Severity bands |
| Does it require merchant attention? | Attention flag |
| Is it stable / forming? | Stability governance |
| Does SCF need to expose it? | Visibility decision |

---

## 2. Input / output boundary

**Consumes:** durable operational counts only (`abandoned_carts`, `recovery_schedules`, `mock_whatsapp_sent`, `hesitation_reasons`, `purchase_truth`).

**Produces:** Operational Truth packages (`ot_v1`) with severity, visibility, stability, explainability, destination surfaces.

**Forbidden:** recommendations, Guidance, Knowledge generation, raw widget/WhatsApp event invention, page-owned calculations.

---

## 3. Packages → Surface Composition

```text
Operational Truth package (expose)
        ↓
evaluate_operational_truth_composition_v1
        ↓
information_class (critical_attention / operational_health / recovery_health)
        ↓
Surface Composition (Home / Decision / Carts / Communication)
```

SCF inputs now: Presentation + Knowledge + **Operational Truth**.

Empty-state governance skips false `no_operational_issues` when OT destinations cover that surface.

---

## 4. Stability governance

| Control | Behavior |
|---------|----------|
| Evidence threshold | Suppress below min count |
| Severity bands | critical / warning / informational enter thresholds |
| Hysteresis bands | exit thresholds documented for future persistence |
| Debounce | no expose when count &lt; threshold |
| Determinism | same as_of → same fingerprint |

---

## 5. Merchant explainability

Every exposed package includes:

- `what_happened_ar`
- `why_true_ar`
- `evidence_ar`
- structured `evidence` counts

---

## 6. Runtime

| Concern | Contract |
|---------|----------|
| Flag | `CARTFLOW_OPERATIONAL_TRUTH_V1` (default on) |
| Generator | `generate_operational_truth_v1` |
| Probe | `GET /dev/operational-truth?store=demo` |
| Registry | `operational_truth_registry_v1` / `docs/architecture/operational_truth_registry.md` |

---

## 7. STOP

After production closure + Reality Validation V3: proceed to next capability (e.g. Time Authority Binding). Every new merchant capability should be driven by governed operational truth rather than page-specific logic.
