# Commerce Brain Signal Consumption V1

**Status:** Documentation + architectural wiring review only  
**Date (UTC):** 2026-07-10  
**Authority:** Subordinate to [`commerce_brain_v1_1.md`](commerce_brain_v1_1.md), [`commerce_signals_foundation_v1.md`](commerce_signals_foundation_v1.md), [`commerce_evidence_contract_v1.md`](commerce_evidence_contract_v1.md), [`commerce_decision_contract_v1.md`](commerce_decision_contract_v1.md)  
**Out of scope:** New Signals, new Truths, UI, code migration, schemas

> **Law:** Signals answer **what happened**.  
> Brain answers **what it means** and **what stance is allowed**.  
> Do not migrate everything. Migrate only what is safe and already Signal-backed.

---

## 1. Canonical pipeline (verified)

```text
Reality
   ↓
Truth          (domain owners: Purchase Truth, Recovery Timeline, …)
   ↓
Evidence       (proof assembly for a claim)
   ↓
Signals        (stable “what happened” — Recovery + Purchase in runtime V1)
   ↓
Commerce Brain (Understand → Explain)
   ↓
Decision       (stance: Require / No action / Unknown / …)
   ↓
Merchant Pulse (surface projection of Brief + Decision + Progress + one next)
```

| Stage | Owns | Must not |
|-------|------|----------|
| **Reality** | What is true in the world / platform | Meaning |
| **Truth** | Durable domain records | Merchant advice |
| **Evidence** | Proof for a claim | Decisions |
| **Signals** | Named “what happened” + `evidence_refs` | Why / what to do |
| **Brain** | Understand + Explain | Bypass Truth/Evidence |
| **Decision** | Allowed stance now | Rewrite Truth |
| **Pulse** | Print Brain/Decision outputs | Invent narrative or re-read Truth |

**Placement note:** Signals sit **after** Evidence (they cite `evidence_refs`). They are not a second Truth store.

**Today’s gap:** Merchant Pulse and most Brain composers still read **composed summary fields** (Home / Brief / WA / connection) that were built from Truths **below** Signals. Runtime Signals exist (`commerce_signals_v1`) but are **not** on the Brain → Decision → Pulse path yet.

**Runtime wiring (flagged):** When `CARTFLOW_COMMERCE_SIGNALS_V1=1` and summary carries store-scoped `commerce_signals_v1.signals`, Pulse overlays **executive_brief** + **cartflow_progress** from Recovery/Purchase Signal types only. Decision Summary / Merchant Decision / fork stay on governed Decision inputs. Flag off or missing signals → legacy Pulse unchanged.

---

## 2. Brain inputs — inventory (Pulse path)

Pulse today (`build_merchant_pulse_v1_from_summary`) reads only summary attachments. Underneath, those attachments were composed from many sources. This table answers three questions for each Brain-relevant input:

1. Does it come from Signals today?  
2. Should it (eventually / next)?  
3. If no, why not?

| Brain input (what Understand needs) | From Signals today? | Should it? | Why / why not |
|-------------------------------------|---------------------|------------|---------------|
| **Purchase confirmed** for a cart/recovery | **No** (Purchase Truth / Home-Brief composition) | **Yes** | Runtime Signal `purchase_confirmed` exists. Brain should not re-query Purchase Truth for “what happened.” |
| **Recovery started** | **No** (timeline / lifecycle composers) | **Yes** | Signal `recovery_started` exists. |
| **Recovery progressed** (sent / delivered / reply steps as facts) | **No** | **Yes** | Signal `recovery_progressed` exists. One fact per evidence; Brain interprets. |
| **Recovery completed** | **No** | **Yes** | Signal `recovery_completed` exists (started + purchase). |
| **Recovery blocked** (e.g. missing phone stop) | **No** | **Yes** | Signal `recovery_blocked` exists. |
| **Home / Daily Brief attention lines** | **No** | **Not yet** | Already **Explain/Guide-shaped** copy + decision_class. Migrating wholesale would pull Decision into Signals. Wrong layer. |
| **Home / Brief while-away achievements** | **No** | **Partial later** | Progress *facts* should come from Recovery/Purchase Signals; Arabic achievement *wording* stays Brain/Explain. |
| **Merchant Intelligence “needs merchant”** | **No** | **No (V1)** | Stance/need is Decision-adjacent, not “what happened.” No Signal family for it. |
| **Decision class on attention items** (`critical_action`, …) | **No** | **No** | That **is** Decision output (or precursor). Signals must never carry stance. |
| **WhatsApp readiness / connection state** | **No** | **No (V1)** | No WhatsApp Signal family by charter. Trust/channel health stays out of Pulse Signal migration. |
| **Store connection** | **No** | **No (V1)** | Integration/health — not Recovery/Purchase Signal. |
| **Counter / ops health** | **No** | **No** | Diagnostics ≠ commerce “what happened.” |
| **Customer / Product / Traffic facts** | **No** | **No until families exist** | Runtime V1 did not implement those families. |
| **Confidence / freshness / Unknown** | **No** | **No** | Properties on Brain/Decision objects — forbidden on Signals. |

---

## 3. Minimum safe migration

Migrate **only** the Recovery + Purchase **fact** inputs that already have Signal types. Leave everything else on current composers until a Signal family exists and the input is still a pure “what happened.”

### In scope (next implementation — not this doc)

| Consume from Signals | Instead of reading directly |
|----------------------|-----------------------------|
| `purchase_confirmed` | `has_purchase` / `purchase_context` inside Brain Understand for Pulse progress / completion facts |
| `recovery_started` | Timeline “scheduled/delay_started” checks inside Brain Understand for Pulse |
| `recovery_progressed` | Timeline progress status sets for “what moved” facts |
| `recovery_completed` | Ad-hoc “purchased after recovery” joins in Brain |
| `recovery_blocked` | Schedule `last_error` / block markers when Brain only needs “blocked happened” |

### Explicitly out of migration (keep as today)

| Keep | Reason |
|------|--------|
| Pulse reading Home / Brief / WA / store_connection summary fields | Surface contract; not Truth bypass if those fields later cite Signals underneath |
| Decision class / MI need / Require vs Recommend | Decision layer — never Signals |
| WhatsApp / store health / counters | No Signal family; Trust/ops |
| Customer / Product / Traffic | No runtime Signals yet |
| Lifecycle write paths, scheduler, WhatsApp send, purchase closure | Signals are read-only projections — never drive operations |

### Safe wiring shape (when code lands)

```text
Truth (unchanged writers)
   ↓
Signals builder (flagged, read-only)     ← already exists
   ↓
Brain Understand (new: prefer Signals for Recovery/Purchase facts)
   ↓
Explain → Decision → Pulse               ← Pulse still prints; does not call Truth
```

**Rule:** Operational code keeps reading Truth. Brain Understand for merchant cognition prefers Signals for the five Recovery/Purchase types. One direction only.

---

## 4. What “consume” means (and does not)

| Consume means | Does not mean |
|---------------|---------------|
| Brain Understand takes Signal list for a store/subject | Deleting Purchase Truth or Recovery Timeline |
| Pulse progress/brief facts derive from Signal types | Pulse calling `/dev/commerce-signals` |
| Decision still cites Evidence via Knowledge | Decision reading Signals as stance |
| Flag stays default-off until attach is proven | Enabling Signals in merchant UI |

---

## 5. Acceptance (review only)

This document passes if:

1. The pipeline above is the only allowed cognition path for Signal-backed facts.  
2. Every listed Brain input has a clear Signals / not-yet / never answer.  
3. Minimum migration is **only** the five Recovery + Purchase signal types.  
4. No requirement to migrate Home copy, WA, MI, or Decision into Signals.  
5. No new Signal families, Truths, or UI are introduced here.

**No implementation in this document.**
