# Decision Admission Matrix V1.1

**Status:** Foundation — pending review/approval before UX / Architecture / Engineering  
**Version:** V1.1 (Admission Economics + Auditability + Rejection Stability)  
**Date (UTC):** 2026-07-12  
**Output:** Binary only — **Admit** | **Do Not Admit**  
**Authority parents:**  
- [`cart_workspace_constitution_v2.md`](cart_workspace_constitution_v2.md)  
- [`cart_workspace_constitutional_decisions_log_v1.md`](cart_workspace_constitutional_decisions_log_v1.md)  
- [`cart_workspace_glossary_v1.md`](cart_workspace_glossary_v1.md)  
- [`merchant_decision_and_ownership_map_v1.md`](merchant_decision_and_ownership_map_v1.md) (V1.1)  
- [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md)  

**Nature:** Constitutional admission engine — whether a case may consume merchant attention.  
**Not:** a workflow, UI, API, database schema, ranking engine, or solution planner.

**Philosophy source:** Governance Pack + Ownership Map only. No new philosophy.  
**V1.1:** Decision Governance only — economics, auditability, rejection stability. **Does not change** Admit/Do Not Admit outcomes in Part 4. **Does not change** runtime behavior.

---

## Part 1 — Admission Purpose

### Definition (Glossary-aligned)

**Decision Admission** is the constitutional gate that determines whether consuming merchant attention is justified — i.e. whether a Decision may exist and appear in Cart Workspace.

### What Admission decides

| Decides | Does not decide |
|---------|-----------------|
| **Should this consume merchant attention?** | How to solve the case |
| Whether a Decision may enter Workspace | Message copy, channel, schedule |
| Whether Decision Ownership may transfer to Merchant (Ownership Map T1 / T2) | Execution steps, retries, provider calls |
| Binary: **Admit** or **Do Not Admit** | Sort order, card design, analytics |

Nothing reaches Cart Workspace without Admission (normal path or Priority Override path).

---

## Part 2 — Admission Pipeline

Canonical sequence. **No stage may be skipped.** Evaluation is design-compiled into rules; runtime executes the compiled result, not this narrative.

```
1. Signal
2. Evidence
3. Status
4. Proof
5. Ownership Check
6. Automation Capability Check
7. Human Gain Check
8. Attention Cost Check
9. Priority Override Check
10. Final Admission Decision  →  Admit | Do Not Admit
```

| Stage | Role |
|-------|------|
| Signal | Raw observation present |
| Evidence | Validated material derived from Signal(s) |
| Status | Internal operational state (never Workspace category) |
| Proof | Evidence sufficient for business reasoning / Override eligibility |
| Ownership Check | Dual-axis posture (Execution / Decision) per Ownership Map |
| Automation Capability | Can CartFlow still improve outcome under policy? |
| Human Gain | Will human judgment improve recovery? |
| Attention Cost | Does expected business value justify attention? |
| Priority Override | If L0 applies, Override policy governs (Gate F) |
| Final | Single binary outcome |

**Compile rule:** Stages 1–9 become pre-defined predicates in the Decision Engine. Stage 10 is a deterministic function of those predicates — never free-form constitutional reasoning at request time.

---

## Part 3 — Admission Gates

Gates fire in pipeline order. First hard reject wins unless Gate F Override path applies (then Override-specific gate set applies; normal Human Gain / Attention Cost may be superseded by Override policy, but Evidence and Ownership invariants still hold).

### Gate A — Evidence Sufficiency

| Pass | Fail |
|------|------|
| Proof exists at governed standard for the candidate Decision (or Override eligibility Proof for Override path) | No Evidence / insufficient Proof |

### Gate B — Execution Ownership

| Pass | Fail |
|------|------|
| Execution Owner is CartFlow (default) or Merchant under scoped handoff that still allows Decision Admission | Ownership posture illegal / unknown; Customer or CS treated as owner |

Gate B does **not** require Merchant Execution Ownership. Default CartFlow Execution is correct for Admit.

### Gate C — Automation Capability

| Pass (toward Admit) | Fail → Do Not Admit |
|---------------------|---------------------|
| Automation **cannot** safely improve further under current policy | Automation **can** still improve outcome (OE-2) |

### Gate D — Human Gain

| Pass | Fail → Do Not Admit |
|------|---------------------|
| Expected Human Gain from merchant judgment exceeds continued automation alone | Human Gain not expected / unknown |

### Gate E — Attention Cost

| Pass | Fail → Do Not Admit |
|------|---------------------|
| Expected business value (Human Gain) **exceeds** Attention Cost (OE-3) | Human Gain ≤ Attention Cost |

### Gate F — Priority Override

| When L0 inactive | When L0 active |
|------------------|----------------|
| Continue normal Gates A–E | **Normal admission value rules stop for queueing and delay.** Override policy governs: Override Admission path; never wait behind normal queues; immediate Decision eligibility → Merchant on Override Admit (T2). Still requires Override eligibility Evidence (Gate A-equivalent). Does **not** skip Admission itself (Ownership I8). |

---

## Part 4 — Admission Matrix (canonical)

**Legend**

| Symbol | Meaning |
|--------|---------|
| Y | Condition true / capable / gain justifies |
| N | Condition false / insufficient |
| — | Not applicable / not required for this row’s path |
| CF | CartFlow |
| M | Merchant |

**Admit?** is only **Yes** or **No**.

**Destination** when Admit=Yes: Ownership Map state after T1 or T2. When No: remain Quiet / Background / Completed as listed.

| ID | Signal (class) | Evidence / Proof | Ownership (Exec / Dec) | Automation capable? | Human Gain > Cost? | Priority Override | Admit? | Destination | Reason | Primary Action if Admitted |
|----|----------------|------------------|-------------------------|---------------------|--------------------|-------------------|--------|-------------|--------|----------------------------|
| **R01** | Hesitation / idle cart | Weak / none | CF / CF | Y | — | Inactive | **No** | S1 Quiet | Automation still owns; insufficient Proof | — |
| **R02** | Hesitation | Proof: recovery progressing safely | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Automation still capable | — |
| **R03** | Hesitation | Proof: automation exhausted under policy | CF / CF | N | Y | Inactive | **Yes** | S2 (T1) | Normal Admission | Single policy Action (e.g. approve next step) |
| **R04** | Customer reply (answerable) | Proof: automation can answer | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Automation still capable | — |
| **R05** | Customer question (business exception) | Proof: exception needs judgment | CF / CF | N | Y | Inactive | **Yes** | S2 (T1) | Human Gain justifies | Single judgment Action |
| **R06** | Discount / exception request | Proof: approve/deny required | CF / CF | N | Y | Inactive | **Yes** | S2 (T1) | Business exception | Approve or deny discount |
| **R07** | VIP / Override eligible | Override eligibility Proof | CF / CF | — | — *(Override policy)* | **Active** | **Yes** | S4 (T2) | Override Admission | Single Override Decision Action |
| **R08** | VIP detect (duplicate while L0 Active) | Same Override Evidence | CF / M *(already)* or CF / CF | — | — | Active | **No** | Stay S4 or await T2 once | Duplicate / Override non-oscillation | — |
| **R09** | Phone missing | Status: phone absent; automation may wait/retry | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Status ≠ Decision; automation owns | — |
| **R10** | Phone missing | Proof: merchant must supply contact to proceed; automation blocked | CF / CF | N | Y | Inactive | **Yes** | S2 (T1) | Human Gain (provide phone) | Provide / confirm phone |
| **R11** | Purchase completed | Terminal completion Proof | CF / CF | — | — | * | **No** | S7 Completed | Already completed | — |
| **R12** | Provider failure | Failure Signal; retry allowed | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Operational noise / retry | — |
| **R13** | Provider failure | Proof: policy requires merchant decision after exhausted retries | CF / CF | N | Y | Inactive | **Yes** | S2 (T1) | Automation exhausted | Single recovery Action |
| **R14** | Merchant inactive (Decision already open) | Prior Admission id active | CF / M | — | — | * | **No** | Stay S2/S4 | Duplicate admission; Decision already open | — |
| **R15** | Customer inactive | Silence only | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Operational noise / Wait strategy | — |
| **R16** | Message sent / Status tick | Status only | CF / CF | Y | N | Inactive | **No** | S1 Quiet | Operational noise | — |
| **R17** | Refresh / poll / re-observe same Proof | Identical Evidence fingerprint | * / * | — | — | * | **No** | Unchanged | Duplicate admission / stability | — |
| **R18** | Knowledge claim published | Claim without Admission Proof of Human Gain | CF / CF | Y | N | Inactive | **No** | S9 Knowledge only | Knowledge ≠ Escalation | — |
| **R19** | Archived / history browse | L4 / history | — | — | — | — | **No** | S8 | Outside L2 | — |
| **R20** | Scoped reopen with new Evidence | Governed reopen Proof (T12) then fresh pipeline | CF / CF | *per pipeline* | *per pipeline* | * | **Per re-run** | S1 then R0x | Reopen ≠ auto-Admit; full pipeline | If Yes: one Action |

**Determinism:** Every row yields exactly one Admit? value. Ambiguous situations must be classified into an existing row class or rejected **No** (fail closed) until a new matrix row is governance-approved.

---

## Part 5 — Admission Invariants

| ID | Invariant |
|----|-----------|
| **AI-1** | No Evidence / insufficient Proof → **Do Not Admit**. |
| **AI-2** | Automation still capable of improving outcome → **Do Not Admit** (normal path). |
| **AI-3** | Human Gain ≤ Attention Cost → **Do Not Admit** (normal path). |
| **AI-4** | Priority Override Active → Override policy path; never wait behind normal queues; still requires Override Admission (not detection alone). |
| **AI-5** | Every **Admit** yields exactly **one** primary merchant Action. |
| **AI-6** | Output is binary only: Admit or Do Not Admit. |
| **AI-7** | Signal or Status alone never Admit. |
| **AI-8** | Completed (S7) / Archived (S8) never Admit without governed reopen + full pipeline. |
| **AI-9** | Duplicate Evidence fingerprint never re-Admits (OS-3). |
| **AI-10** | Already-open Decision (Merchant Decision Owner) → **Do Not Admit** again for same Decision. |
| **AI-11** | Admit transfers Decision Ownership only via Ownership Map T1 (normal) or T2 (Override). |
| **AI-12** | Execution Ownership remains CartFlow on Admit unless prior scoped T6. |
| **AI-13** | Customer / CS never become Decision Owners via Admission. |
| **AI-14** | Pipeline stages are never skipped in the compiled rule set. |
| **AI-15** | Fail closed: unclassified case → **Do Not Admit**. |
| **AI-16** | Rejected admission remains rejected until **new evidence** changes the governing decision (see Part 10). |
| **AI-17** | Repeated rejection must not create repeated evaluation noise — scans may repeat; admission reasoning stays stable. |
| **AI-18** | Admission history is deterministic: same Evidence under same governance → same admission outcome. |

---

## Part 6 — Admission Rejection Catalogue

| Code | Rejection reason | Typical gate |
|------|------------------|--------------|
| **RJ-EVIDENCE** | More evidence required / insufficient Proof | A |
| **RJ-AUTOMATION** | Automation still owns / still capable | C |
| **RJ-VALUE** | Low business value (Human Gain ≤ Attention Cost) | D/E |
| **RJ-DUPLICATE** | Duplicate admission (same Evidence / Decision already open) | Stability |
| **RJ-COMPLETED** | Already completed | Terminal |
| **RJ-NOISE** | Operational noise (Status, send tick, silence, provider blip under retry) | C / pipeline |
| **RJ-STATUS** | Status presented as if Decision | AI-7 |
| **RJ-KNOWLEDGE** | Knowledge/claim without Admission justification | Pipeline |
| **RJ-HISTORY** | History / archive surface — outside L2 | AI-8 |
| **RJ-OWNERSHIP** | Illegal ownership posture | B |
| **RJ-OVERRIDE-DUP** | Override already Active / Decision already Override-admitted | F / OS-4 |
| **RJ-UNCLASSIFIED** | No matrix row — fail closed | AI-15 |

---

## Part 7 — Admission Stability

Anti-oscillation (inherits Ownership Map OS-1…OS-5, OE-4, OE-5).

| Rule | Statement |
|------|-----------|
| **AS-1** | Same Evidence fingerprint → at most one Admit per Decision identity. |
| **AS-2** | Polling, refresh, duplicate webhook, repeated observation → **Do Not Admit** (RJ-DUPLICATE / RJ-NOISE). |
| **AS-3** | After Admit, further observations update explanation material only — they do not create a second Admit for the same Decision. |
| **AS-4** | After return to CartFlow (T3/T4), re-Admit requires **new** Evidence (not the prior fingerprint alone). |
| **AS-5** | Override does not flap Active/Inactive on duplicate VIP Signals (OS-4); duplicate VIP → RJ-OVERRIDE-DUP. |
| **AS-6** | Completed → no Admit without T12 reopen + new pipeline (OS-5). |

---

## Part 8 — Runtime Simplicity Validation

**Governance Must Compile Into Runtime Simplicity** (Ownership Map Part 12). Extended by V1.1 Decision Governance (Parts 10–12).

| Claim | How the matrix satisfies it |
|-------|----------------------------|
| No governance evaluation on hot path | Engine evaluates compiled predicates matching Gates A–F / rows R01–R20 — not markdown |
| No dynamic constitutional reasoning | No “read Constitution” step; rules are pre-defined |
| Deterministic | Each input class → one Admit?; AI-18 |
| Zero extra ownership types | Uses Ownership Map only |
| Strengthens Admission without execution complexity | Rejects noise/automation-capable cases before Workspace; no new recovery steps |
| **V1.1 zero runtime overhead** | AE/AA/AI-16…18 are design-time; no new hot-path stages |
| **V1.1 zero additional hot-path evaluation** | Economics not scored live; audit fields compile from rule ids |
| **Binary preserved** | Still only Admit / Do Not Admit |
| **Reduced architectural drift** | One explanation contract (AA-5); stable rejection (AI-16) |

**Compiled runtime shape (conceptual — not an API):**

```
if completed_or_archived: return DoNotAdmit(RJ_COMPLETED|RJ_HISTORY)
if duplicate_fingerprint_or_open_decision: return DoNotAdmit(RJ_DUPLICATE)
if override_eligible and override_admission_rules: return Admit(T2, one_action)
if insufficient_proof: return DoNotAdmit(RJ_EVIDENCE)
if automation_capable: return DoNotAdmit(RJ_AUTOMATION)
if human_gain <= attention_cost: return DoNotAdmit(RJ_VALUE)
if normal_admission_rules: return Admit(T1, one_action)
return DoNotAdmit(RJ_UNCLASSIFIED)
```

No polling. No live economics scoring beyond pre-coded predicates. No governance document I/O.  
**V1.1 does not add lines to this shape** — it constrains how rows/gates are authored and how outcomes are explained.

---

## Part 9 — Admission Validation Report

| Scenario | Matrix row | Admit? | Gate that decided | Exec / Dec after | Primary Action if Yes |
|----------|------------|--------|-------------------|------------------|------------------------|
| Normal hesitation (safe automation) | R01/R02 | **No** | C / A | CF / CF | — |
| Customer reply (answerable) | R04 | **No** | C | CF / CF | — |
| Discount request | R06 | **Yes** | D/E pass; C fail (automation cannot) | CF / M (T1) | Approve or deny discount |
| VIP | R07 | **Yes** | F Override Admission | CF / M (T2) | Override Decision Action |
| Missing phone (automation can wait) | R09 | **No** | C / AI-7 | CF / CF | — |
| Purchase completed | R11 | **No** | AI-8 | S7 | — |
| Provider failure (retryable) | R12 | **No** | C / RJ-NOISE | CF / CF | — |
| Merchant inactive (Decision open) | R14 | **No** | AS-3 / RJ-DUPLICATE | unchanged | — |
| Customer inactive | R15 | **No** | C / RJ-NOISE | CF / CF | — |

**Validation verdict:** Every listed scenario produces exactly one admission outcome. Ownership remains dual-axis deterministic. Quiet preserved when Do Not Admit.  
**V1.1:** Outcomes in this table are **unchanged**. Governance now requires each row to carry a single governing reason (AA-1) and rejection/admit audit fields (AA-2/AA-3) at design time.

---

## Part 10 — Admission Economics

### 10.1 Philosophy

Admitting a case into Cart Workspace is itself an **operational cost**.

Admission consumes:

- merchant attention  
- cognitive capacity  
- operational focus  
- workspace complexity  

Admission is therefore an **expensive resource** (aligned with Ownership Economics OE-1…OE-4 and Attention Budget). Computational cost is irrelevant to this chapter.

### 10.2 Principles

| ID | Principle |
|----|-----------|
| **AE-1** | **Admission is never free.** Every admitted case consumes merchant attention. |
| **AE-2** | **The burden of proof belongs to admission, not rejection.** Default position is **Do Not Admit**. Admission must justify itself. |
| **AE-3** | **Admission is justified only when Expected Human Gain > Admission Cost.** Admission Cost includes interruption, workspace complexity, context switching, and decision fatigue — **not** computational cost. |
| **AE-4** | **Reducing unnecessary admissions is itself a product KPI.** Goal is higher-value admitted cases, not more admitted cases. |
| **AE-5** | **Admission Economics is evaluated during product design, not during runtime.** The Decision Engine executes compiled admission rules only. |

### 10.3 Non-goals

- Live Admission Cost scoring on the hot path  
- Changing Part 4 row outcomes  
- New pipeline stages  
- Polling to “re-price” admission  

### 10.4 Design consequence

Matrix rows that Admit (R03, R05, R06, R07, R10, R13, …) must be authorable only when AE-3 holds under Override-or-normal policy. Rows that reject embody AE-2 (default No).

---

## Part 11 — Admission Auditability

### 11.1 Philosophy

Every admission decision must be explainable. Every rejection must be explainable. No admission result may be a black box.

### 11.2 Principles

| ID | Principle |
|----|-----------|
| **AA-1** | Every admission outcome has a **single governing reason**. |
| **AA-2** | Every **rejected** admission identifies: failed gate, evidence evaluated, governing invariant. |
| **AA-3** | Every **admitted** case identifies: admitting gate, ownership state, human gain justification, expected merchant Action. |
| **AA-4** | Audit explanations are generated from **governance** (matrix row + gates + RJ/AI codes), not reconstructed from implementation. |
| **AA-5** | Support, Knowledge Layer, Admin Operations, and future diagnostics derive explanations from the **same** admission reasoning. One explanation. One truth. |

### 11.3 Audit record shape (design contract — not an API)

**On Do Not Admit:**

| Field | Source |
|-------|--------|
| outcome | Do Not Admit |
| governing_reason | Single AA-1 reason (usually RJ-* code + short text) |
| failed_gate | A–F or stability/terminal |
| evidence_evaluated | Evidence/Proof class referenced |
| governing_invariant | AI-* / AS-* / AE-* as applicable |

**On Admit:**

| Field | Source |
|-------|--------|
| outcome | Admit |
| governing_reason | Single AA-1 reason (matrix Reason column) |
| admitting_gate | Gate that authorized (normal D/E path or F Override) |
| ownership_state | Destination (e.g. S2 T1 / S4 T2) |
| human_gain_justification | Why AE-3 / Override policy holds |
| expected_merchant_action | Primary Action column (exactly one) |

### 11.4 Opposite-decision clarity

For every outcome, governance must make answerable:

- Why this decision was made (governing reason)  
- Why the opposite was rejected (failed opposite path — e.g. Admit rejected because Gate C passed automation-capable; or Do Not Admit’s opposite would fail AE-3)

---

## Part 12 — Rejection Stability

Extends Part 7 Admission Stability with explicit reject-side permanence.

| ID | Rule |
|----|------|
| **AI-16** | **Rejected admission remains rejected** until **new evidence** changes the governing decision. Re-evaluation may occur only when: new customer behavior; new operational evidence; ownership transition; Priority Override; or a **policy-defined trigger**. **Never** because of: polling; refresh; duplicate observation; repeated scheduler execution. |
| **AI-17** | **Repeated rejection must not create repeated evaluation noise.** Operational scans may repeat. Admission reasoning must remain stable (same governing reason / RJ code). |
| **AI-18** | **Admission history must remain deterministic.** The same Evidence under the same governance must always produce the same admission outcome. |

### Change conditions (when a prior No may become Yes)

| Allowed | Forbidden |
|---------|-----------|
| New customer behavior Evidence | Poll / refresh / duplicate observe |
| New operational Evidence / Proof | Scheduler tick alone |
| Ownership transition (policy) | Reconstructing reason from code paths |
| Priority Override activation (Gate F path) | Re-pricing economics at runtime |
| Explicit policy-defined re-eval trigger | Silent outcome flip |

---

## Part 13 — V1.1 Governance Validation

| Check | Result |
|-------|--------|
| Zero runtime overhead from V1.1 chapters | **Pass** — design-time only |
| Zero additional hot-path evaluation | **Pass** — compiled rules unchanged in shape |
| Strengthens determinism | **Pass** — AI-16…18, AA-1, AI-18 |
| Reduces future architectural drift | **Pass** — AA-4/AA-5 single explanation truth |
| Preserves binary admission | **Pass** — Part 4 outcomes unchanged |
| Preserves runtime simplicity | **Pass** — AE-5; no live economics |

**Success criterion:** Economically justified, fully explainable, operationally stable — without changing runtime behavior.

---

## Engineer checklist (success criteria)

For any recovery scenario, without reading code:

| Question | Answer from |
|----------|-------------|
| Should the merchant see this? | Admit? column (binary) |
| Why was this decision made? | AA-1 governing reason + Reason / RJ-* |
| Why was the opposite decision rejected? | AA-2/AA-3 opposite path (failed gate or AE-3 / Override) |
| Can this decision change, and under what governed conditions? | AI-16 change conditions; else remains stable (AI-17/AI-18) |
| Which gate allowed or rejected? | Gates A–F / AI / AS |
| Who owns it? | Ownership column + Destination |
| What single action if admitted? | Primary Action column |

---

## Derivation gate

| Stage | Status |
|-------|--------|
| Governance Pack | Ratified |
| Ownership Map V1.1 | Parent |
| **Decision Admission Matrix V1.1** | Foundation — [`decision_admission_matrix_v1.md`](decision_admission_matrix_v1.md) |
| **Cart Workspace UX Blueprint V1** | Behavioral architecture — [`cart_workspace_ux_blueprint_v1.md`](cart_workspace_ux_blueprint_v1.md) — **review/approve before Architecture/Engineering/visual** |
| Architecture Review | **Blocked** until UX Blueprint approved |
| Engineering Implementation | **Blocked** |

---

## Change log

| Version | Change |
|---------|--------|
| **V1** | Purpose, pipeline, Gates A–F, matrix R01–R20, AI-1…15, rejection catalogue, AS-1…6, runtime compile, scenario validation |
| **V1.1** | Admission Economics AE-1…AE-5; Admission Auditability AA-1…AA-5; Rejection Stability AI-16…AI-18; Part 13 governance validation. **No change** to Part 4 Admit outcomes or compiled runtime shape. |

---

**End of Decision Admission Matrix V1.1.**
