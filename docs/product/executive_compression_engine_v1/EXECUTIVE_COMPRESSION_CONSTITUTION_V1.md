# Executive Compression Constitution V1

**Status:** Architecture only — binding presentation law.  
**Date (UTC):** 2026-07-28  
**Object:** Executive Compression Engine (presentation layer)  
**Non-goals:** No UI. No implementation. Not a decision / diagnostic / recommendation engine.

**Authority:** Binding law for **how CartFlow intelligence is compressed** before any merchant surface.  
**Related (peer / upstream):**  
- Product Constitution V1 · Principle 0 · Principle 7  
- [`Decision Playbooks Constitution V1`](../decision_playbooks_constitution_v1/DECISION_PLAYBOOKS_CONSTITUTION_V1.md)  
- [`Execution Methodology V1`](../execution_methodology_v1/EXECUTION_METHODOLOGY_V1.md)  
- Decision Workspace / Cards / Information Budget · Home Constitution V2 · Diagnostic Reasoning Foundation V1  

A merchant-facing decision that violates this Constitution is **unconstitutional**, even if diagnostically correct or playbook-valid.

Companion packs in this folder:

| Document | Role |
|----------|------|
| [`COMPRESSION_RULES_V1.md`](./COMPRESSION_RULES_V1.md) | Compression rules |
| [`COMPRESSION_DECISION_MATRIX_V1.md`](./COMPRESSION_DECISION_MATRIX_V1.md) | Visibility matrix |
| [`SURFACE_COMPRESSION_RULES_V1.md`](./SURFACE_COMPRESSION_RULES_V1.md) | Per-surface altitude |
| [`EXAMPLES_BEFORE_AFTER_V1.md`](./EXAMPLES_BEFORE_AFTER_V1.md) | Before / after examples |

---

## 1. Mission

Everything inside CartFlow may be complex.

Everything presented to the merchant must feel simple.

The Executive Compression Engine is responsible for **compressing platform intelligence without losing truth**.

---

## 2. Core Principle

**Complex reasoning. Simple decisions.**

| Layer | Allowed complexity |
|-------|--------------------|
| **Internal** | Evidence chains, competing causes, gates, collectors, confidence math |
| **Merchant** | Minimum information required to decide and act |

---

## 3. What this engine is / is not

| Is | Is not |
|----|--------|
| Presentation / compression layer | New decision engine |
| Consumer of Playbooks + Diagnosis + Readiness | New diagnostic engine |
| Single executive language for all surfaces | Another recommendation layer |
| Truth-preserving reduction | Simplification that invents or hides uncertainty dishonestly |

**Hard rule:** Compression must not invent actions, fake readiness, or bury honest insufficiency.

---

## 4. Input (consumes — does not invent)

The engine receives (when available):

| Input | Source (illustrative) |
|-------|------------------------|
| **Evidence** | Diagnostic / observation stack |
| **Diagnosis** | Diagnostic Reasoning |
| **Confidence** | Diagnostic / playbook gates (internal) |
| **Execution Readiness** | EM-001 |
| **Decision Playbook** | Playbooks Constitution (when published) |
| **Reality Validation** | EM-002 class / metric (outcome posture) |
| **Knowledge** | Knowledge layer statements eligible for altitude |
| **Merchant Context** | Store / platform / ops context needed for locus |

Missing playbook → compress **Diagnosis only** (aligned with **PBL-001**).  
Never invent a playbook at compression time.

---

## 5. Output

The merchant receives **only** the minimum information required to make the correct decision.

**Nothing more.**

Editorial altitude may vary by surface (teaser vs commit), but the **decision identity** and executive answers remain the same language.

---

## 6. Compression Law

Every published decision must answer **only**:

| # | Merchant question | Notes |
|---|-------------------|--------|
| **1** | **What should I do?** | Business task (playbook) — or honest wait / diagnosis-only when no playbook |
| **2** | **Why?** | Short causal reason from diagnosis — not the evidence chain |
| **3** | **Can I act now?** | Readiness posture in merchant language |
| **4** | **Where do I perform it?** | Only when applicable (execution location) |

**Everything else remains internal.**

---

## 7. Internal information (platform knowledge)

The following are **platform knowledge**, not merchant knowledge. They remain invisible unless a future constitution explicitly elevates a single field:

- Evidence chains  
- Confidence calculations  
- Routing logic  
- Publication gates  
- Validation logic  
- Playbook validation (**PBL-001**)  
- Publication metadata (**PBL-002**)  
- Collectors  
- Diagnostic reasoning traces  
- Evidence expansion tasks  
- Competing-cause ledgers  
- Engine IDs, family IDs, thresholds, review cadence  

---

## 8. Executive Cognitive Law

A merchant should never feel that CartFlow is **explaining itself**.

The merchant should feel that CartFlow **understands the store**.

| Feels like failure | Feels like success |
|--------------------|--------------------|
| System tour / methodology lecture | Store-specific decision |
| “Here is how we calculated…” | “Here is what matters for your store” |
| BI report | Executive instruction |

---

## 9. Compression Quality Test

Every decision presentation **must** pass:

| Test | Required answer |
|------|-----------------|
| Can it be understood within **15 seconds**? | **YES** |
| Does it require scrolling to understand? | **NO** |
| Does it answer the business question immediately? | **YES** |
| Would removing any sentence reduce decision quality? | **YES** (every remaining sentence is load-bearing) |

If not → the decision is **over-explaining** → fails compression → must be re-compressed before publish.

---

## 10. Shared engine (single presentation layer)

The Executive Compression Engine is the **single presentation layer** for:

| Surface |
|---------|
| Home |
| Decision Workspace |
| Knowledge |
| Daily Brief |
| Weekly Brief |
| Monthly Summary |
| Notifications |
| Future AI |

**Every surface speaks the same executive language.**

Surfaces may change **altitude** (how much is shown), never the **meaning** of What / Why / Whether / Where.

---

## 11. Relationship to other constitutions

| Layer | Owns |
|-------|------|
| Diagnostic Reasoning | Truth of what is happening |
| Decision Playbooks | Whether an executable task may exist |
| Execution Methodology | How / avoid / verify when readiness allows |
| **Executive Compression** | What of the above is merchant-visible and in what altitude |
| Cards / Workspace / Home | Layout that **consumes** compressed output — must not re-expand into reports |

---

## 12. Success

| Merchant must never say | Merchant must say |
|-------------------------|-------------------|
| “This system explains a lot.” | “I know exactly what I need to do.” |

---

## 13. Constitutional IDs

| ID | Title |
|----|--------|
| **EC-001** | Compression Law — only What / Why / Whether now / Where (when applicable) |
| **EC-002** | Internal Information Law — platform knowledge stays invisible |
| **EC-003** | Executive Cognitive Law — understand the store, do not explain the system |
| **EC-004** | Compression Quality Test — 15s · no scroll-to-understand · load-bearing sentences |
| **EC-005** | Shared Engine — one executive language across all surfaces |

---

## 14. Approval checklist

- [ ] Mission + Core Principle accepted  
- [ ] Compression Law (EC-001) accepted  
- [ ] Internal Information Law (EC-002) accepted  
- [ ] Cognitive Law (EC-003) accepted  
- [ ] Quality Test (EC-004) accepted  
- [ ] Shared Engine (EC-005) + Surface Rules accepted  
- [ ] Matrix + Rules + Examples accepted as architecture  
- [ ] **No UI / no implementation until approved**

---

## 15. STOP

Architecture only.

**No UI. No implementation.**

Await constitutional approval.
