# Cart Workspace Projection Parity Report V1

**Status:** Sprint 2 deliverable — Projection Truth Parity  
**Date (UTC):** 2026-07-12  
**Scope:** Compare Workspace Projection (shadow) outcomes to production operational intent / current carts-page behavior for canonical cases.  
**Flag:** `CARTFLOW_CART_WORKSPACE_V1=false` (merchant surface unchanged)

**Method:** Golden scenarios GS-01…GS-10 execute the compiled Admission + Ownership + Projection pipeline. Classification uses Product Foundation (Constitution, Ownership Map, Admission Matrix, Behavior Blueprint) versus observed current `#carts` Status-oriented UX.

---

## Classification legend

| Code | Meaning |
|------|---------|
| **Expected improvement** | Projection is quieter / more Decision-correct than Status-driven carts page — intentional Product outcome |
| **Projection defect** | Projection violates approved Product/Architecture — must fix before Sprint close |
| **Current-page limitation** | Old page shows Status/noise the Workspace correctly hides |
| **Data inconsistency** | Upstream truth/evidence gap (not introduced by Projection) |

---

## Parity matrix

| Case | Golden | Projection result | Current carts page (typical) | Classification | Notes |
|------|--------|-------------------|------------------------------|----------------|-------|
| **Waiting** (hesitation, automation owns) | GS-01 | Quiet; no Decision card; R01 Do Not Admit | Often visible as waiting/active cart row | **Expected improvement** | Status ≠ Decision (§6.5). Workspace protects Attention Budget. |
| **Customer Reply** (answerable) | GS-02 | Quiet; R04 | May surface as activity / reply signal | **Expected improvement** | Automation still capable — no merchant interrupt. |
| **VIP** | GS-03 | Zone A Override card; R07; Exec remains CartFlow | VIP banner / higher urgency in same list | **Expected improvement** | Priority Override isolation (not sort-in-same-queue). |
| **Purchase** | GS-05 | Quiet; R11; Zone D rollup | Purchased/completed filters or row state | **Expected improvement** | Completions are L4 compact — not active Decisions (UX-10). |
| **Completed** (recovery terminal) | GS-10 | After purchase path: Quiet; open=0; Zone D | Archive/completed tabs | **Expected improvement** | Calm Recovery / terminal OS-5. |
| **Missing Phone** (wait/retry) | GS-06 | Quiet; R09 | Phone-missing status often listed | **Expected improvement** | Status alone never Admit (AI-7). |
| **Duplicate Event** | GS-07 | One card; second fingerprint refresh rejected | Refresh may reshuffle/reflash rows | **Expected improvement** | AS-1 / OS-3 idempotency. |
| **Provider Failure** (retryable) | GS-08 | Quiet; R12 | May appear as send/failure noise | **Expected improvement** | Operational noise hidden until automation exhausted (R13). |
| **Merchant Inactivity** | GS-09 | Open Decision retained; no re-Admit | Possible re-prompt / list churn | **Expected improvement** | R14 / OST-1 — no nag. |
| **Discount / exception** (needs judgment) | GS-04 | Zone B Decision + one Action | May lack single Decision framing | **Expected improvement** | One Card = One Decision when Admit=Yes. |
| **Recovery Completed** | GS-10 | See Completed | Same as completed path | **Expected improvement** | Aligns with T10/T5 close. |

---

## Defect scan

| Check | Result |
|-------|--------|
| Unexplained mismatch | **None** |
| Projection defect (fails Product law) | **None** found in GS-01…GS-10 |
| Data inconsistency introduced by Projection | **None** — shadow uses candidacy fixtures; live P0 wiring is later sprint |
| Current-page limitation acknowledged | **Yes** — Status taxonomy / activity density vs Decision Workspace |

---

## Residual risks (not parity failures)

| Risk | Notes |
|------|-------|
| Live P0→candidate mapping | Sprint 1–2 use shadow candidacy; production event→candidate adapters remain future work |
| Current `#carts` RSC | Remains production; must not be mixed into Workspace P4 |

---

## Verdict

**Projection Parity Report: APPROVED for Sprint 2 scope.**

All ten operational cases map to governed Projection outcomes with classified deltas. No unexplained mismatch. Merchant carts page remains authoritative production UI while Workspace stays shadow/dev-only.

---

**End of Projection Parity Report V1.**
