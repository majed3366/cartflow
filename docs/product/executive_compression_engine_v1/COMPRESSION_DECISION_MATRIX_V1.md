# Compression Decision Matrix V1

**Status:** Architecture only — input → visibility mapping.  
**Date (UTC):** 2026-07-28  
**Authority:** Companion to [`EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md`](./EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md).  
**Non-goals:** No UI. No scoring product. No implementation.

---

## 1. Visibility legend

| Code | Meaning |
|------|---------|
| **M** | Merchant-visible (compressed) |
| **M\*** | Merchant-visible only when applicable / load-bearing |
| **I** | Internal only — never merchant-facing |
| **A** | Altitude-dependent (teaser may omit; commit may include if load-bearing) |

---

## 2. Input → output matrix

| Input | Merchant sees | Visibility | Compressed form |
|-------|---------------|------------|-----------------|
| **Evidence** | No chain | **I** | Absorbed into one **Why** line if needed |
| **Diagnosis** | Yes (causal core) | **M** | Short **Why** / “what is happening” when no playbook |
| **Confidence** | No number / no math | **I** | Gates publication; may soften wording only via readiness honesty |
| **Execution Readiness** | Yes (posture) | **M** | **Can I act now?** in merchant language |
| **Decision Playbook** | Yes (when published) | **M** | **What should I do?** |
| **Execution Location** | When needed to act | **M\*** | **Where?** |
| **Reality Validation** | Optional one line | **A** | How CartFlow will know — never metric dashboard |
| **Knowledge** | Only decision-bound insight | **A** | Same executive language; no knowledge essay |
| **Merchant Context** | Only as specificity inside task/why | **M\*** | Named product / cohort / stage inside task — not a context panel |
| **Playbook Validation (PBL-001)** | No | **I** | Pass → playbook may appear; fail → diagnosis only |
| **Publication Metadata (PBL-002)** | No | **I** | Engine only |
| **Collectors / Evidence expansion** | No | **I** | Never merchant tasks to “investigate” |
| **Routing / deep links** | Destination only as Where/CTA | **M\*** | No routing explanation |
| **Competing causes** | No list | **I** | Winning cause only in Why |
| **EM how / avoid / verify detail** | Only when READY and commit altitude | **A** | Subordinate to Compression Law; never replace What/Why/Whether/Where |

---

## 3. Decision states → compressed shape

| Upstream state | Merchant compressed shape |
|----------------|---------------------------|
| Playbook published + READY | What · Why · Act now: yes · Where (if applicable) |
| Playbook published + not READY | What (wait / prepare) · Why · Act now: no · Where withheld or conditional |
| Diagnosis only (no playbook) | What is happening · Why · Act now: no · no fake Where |
| BLOCKED | Block in one line · Act now: no · prerequisite named once |
| EXTERNAL_DEPENDENCY | External locus named · Act now: dependency · Where = external |
| No decision / empty | Honest none — not filler analysis |

---

## 4. Compression Law checklist (per instance)

| # | Question | Must be answerable from visible text |
|---|----------|--------------------------------------|
| 1 | What should I do? | Yes (or honest none / wait) |
| 2 | Why? | Yes |
| 3 | Can I act now? | Yes |
| 4 | Where? | Yes if applicable; omit if not |

Anything visible that answers none of these → **cut**.

---

## 5. Truth preservation

| Forbidden compression | Why |
|-----------------------|-----|
| Hide insufficiency behind a fake task | Loses truth |
| Upgrade NEEDS_MORE_EVIDENCE to READY in copy | Loses truth |
| Drop Where when Type B/C action needs a locus | Loses executability |
| Keep evidence museum “for trust” | Violates Cognitive Law |

Compression preserves truth by **honest shortness**, not by omission of readiness or diagnosis.

---

## 6. STOP

Matrix is architecture only.

**No UI. No implementation.**

Await approval with the Constitution pack.
