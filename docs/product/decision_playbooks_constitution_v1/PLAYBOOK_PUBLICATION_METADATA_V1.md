# Playbook Publication Metadata V1

**Status:** Constitutional amendment **PBL-002** — internal engine metadata only.  
**Date (UTC):** 2026-07-28  
**Authority:** Binding under [`DECISION_PLAYBOOKS_CONSTITUTION_V1.md`](./DECISION_PLAYBOOKS_CONSTITUTION_V1.md) §15.  
**Non-goals:** No UI. No merchant exposure. No implementation. No production copy.

---

## 1. Mission

Every Playbook Family must define **publication requirements** before the Decision Playbook Engine may emit instances of that family.

Metadata answers: *Under what internal conditions may this family publish?*  
It does **not** appear on Home, Workspace, Knowledge, Briefs, or any merchant surface.

---

## 2. Internal-only rule (binding)

| Audience | Access |
|----------|--------|
| **Decision Playbook Engine** | Required |
| **Merchant** | **Forbidden** — never expose |
| **Merchant-facing copy / UI** | **Forbidden** |

Surfaces may show Diagnosis, Playbook task, location, readiness posture, and expected result — never confidence floors, success thresholds, review cadence, or other engine metadata fields as merchant content.

---

## 3. Mandatory fields

Every family **must** define all of the following:

| Field | Meaning |
|-------|---------|
| **Playbook Family** | Catalog identity (e.g. Shipping / `PF-SHIPPING`) |
| **Business Domain** | Commercial domain governed by the family |
| **Execution Type** | EM Type **A** Internal · **B** Platform · **C** Business |
| **Minimum Evidence** | Evidence bar before a candidate may enter Playbook Validation (**PBL-001**) |
| **Minimum Confidence** | Confidence floor required before publication |
| **Minimum Readiness State** | Lowest EM-001 state that may publish a **full** playbook for this family (typically **READY** for executable playbooks) |
| **Execution Location** | CartFlow · Commerce Platform · Business Operation |
| **Reality Validation Metric** | What CartFlow observes after merchant action |
| **Success Threshold** | When reality validation counts as success |
| **Failure Behaviour** | Engine / lifecycle behaviour when validation fails or outcome fails |
| **Review Cadence** | How often family metadata and outcome quality are reviewed |
| **Supported Platforms** | Platforms covered for Type B locus (Zid / Salla / Shopify / future); `n/a` only for pure Type A with no platform locus |

A family missing any field is **not publication-eligible**.

---

## 4. Relationship to PBL-001 pipeline

```
Diagnosis
  ↓
Evidence          ← compared to Minimum Evidence (+ DP-004)
  ↓
Execution Readiness  ← compared to Minimum Readiness State
  ↓
Playbook Validation  ← seven YES questions (PBL-001); confidence ≥ Minimum Confidence
  ↓
Playbook Publication
```

If metadata gates or Playbook Validation fail → **Diagnosis only** · **no Playbook**.

**Preference (PBL-001):** rather no playbook than a weak playbook.

---

## 5. Worked example (illustrative — Shipping)

Directional example for constitutional shape only — not merchant-facing copy; numeric floors are family policy for the engine.

| Field | Value |
|-------|--------|
| **Playbook Family** | Shipping (`PF-SHIPPING`) |
| **Business Domain** | Shipping / fulfillment cost & rules |
| **Execution Type** | B (Commerce Platform); C when carrier/contract |
| **Minimum Evidence** | Leave-after-shipping linked to named threshold/cohort + shipping rule context |
| **Minimum Confidence** | 85% |
| **Minimum Readiness State** | READY |
| **Execution Location** | Commerce Platform |
| **Reality Validation Metric** | Shipping-stage abandonment decreases |
| **Success Threshold** | Observed decrease in shipping-linked abandonment for the named cohort/band after action window |
| **Failure Behaviour** | Return to Diagnosis · Continue collecting evidence · Suppress Playbook until gates pass again |
| **Review Cadence** | Periodic family review (engine/ops calendar — not merchant UI) |
| **Supported Platforms** | Zid · Salla · Shopify · future commerce platforms with shipping settings locus |

---

## 6. Failure Behaviour (canonical options)

Families must pick explicit failure behaviour. Allowed classes:

| Class | Meaning |
|-------|---------|
| **Return to Diagnosis** | Suppress playbook; keep / refresh diagnosis visibility |
| **Continue collecting evidence** | Do not publish playbook; evidence expansion continues |
| **Block until prerequisite** | Align with EM-001 **BLOCKED** |
| **External dependency hold** | Align with EM-001 **EXTERNAL_DEPENDENCY** |

Shipping example uses: **Return to Diagnosis** + **Continue collecting evidence**.

---

## 7. Catalog obligation

| Obligation | Rule |
|------------|------|
| Schema | Catalog family entries must eventually carry a complete PBL-002 metadata block |
| Before engine emit | Incomplete metadata → family **cannot** publish instances |
| Amendments | Changing Minimum Confidence / Success Threshold / Failure Behaviour requires constitutional or controlled ops amendment — not surface improvisation |
| Umbrella families | `PF-LOW-CONV` / unbound `PF-HIGH-INTEREST` inherit subordinate family metadata; they do not publish on umbrella metadata alone |

---

## 8. Published playbook properties (recap)

Every playbook that clears metadata + **PBL-001** validation is:

Specific · Evidence-backed · Consistent · Executable · Measurable · Governed · Repeatable.

---

## 9. STOP

**PBL-002** defines internal publication metadata only.

**No UI. No merchant exposure. No implementation.**

Await constitutional approval with the rest of this pack.
