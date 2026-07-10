# Commerce Signals Foundation V1

**Status:** Documentation only  
**Date (UTC):** 2026-07-10  
**Authority:** Subordinate to [`commerce_brain_v1_1.md`](commerce_brain_v1_1.md) and [`commerce_evidence_contract_v1.md`](commerce_evidence_contract_v1.md)  
**Out of scope:** Code, APIs, schemas, UI, analytics, event bus, recommendations, AI

> **If this foundation feels complicated, it is wrong.**  
> Merchant complexity = **zero**. Developer complexity = **minimal**. Longevity = **maximum**.

---

## What this is

A **Signal** is a stable business fact:

> **What happened?**

Platform events become Signals so every future CartFlow feature speaks the same language about reality.

## What this is not

| Not | Why |
|-----|-----|
| Analytics engine | No metrics, funnels, or aggregates |
| Event bus | No transport, queues, or pub/sub |
| Recommendation engine | No “what should we do” |
| AI | No models, prompts, or inferred meaning |
| Another Brain layer | Signals feed the Brain; they do not replace it |

---

## One rule

| Signals may | Signals must never |
|-------------|--------------------|
| Describe **what happened** | Ask **why** |
| Point at evidence | **Explain** |
| Name a subject and a time | **Decide** or **recommend** |
| | Score, prioritize, or invent confidence |

**Commerce Brain** owns interpretation (Explain / Decision / Guide).  
**Signals** only describe reality.

---

## V1 families only

| Family | Answers “what happened?” about… |
|--------|----------------------------------|
| **Recovery** | Recovery steps that occurred (scheduled, sent, delivered, stopped, …) |
| **Purchase** | Purchase / conversion facts that occurred |
| **Customer** | Customer identity or contact facts that occurred |
| **Product** | Product presence or change facts that occurred |
| **Traffic** | Visit / session / storefront presence facts that occurred |

**Not in V1:** WhatsApp, Price, Store Health, Marketing. Add later only if they fit naturally as “what happened.”

---

## Minimum contract

Every Signal has **exactly** these fields:

| Field | Meaning |
|-------|---------|
| `signal_type` | Stable name of what happened (within one family) |
| `subject` | What it happened to (cart, customer, product, session, store, …) |
| `observed_at` | When it was observed |
| `source` | Where the platform learned it |
| `evidence_refs` | Pointers to Evidence / truth records that back it |

**Nothing else in V1.**

No confidence. No freshness. No lifecycle. No scoring. No priority. No severity. No AI fields.

If a field is not required today, **do not add it**.

---

## Placement

```text
Platform event / truth
        ↓
    Evidence         ← proof assembly (existing contract)
        ↓
     Signal          ← stable “what happened” (+ evidence_refs)
        ↓
  Commerce Brain     ← interpretation (Explain / Decision / Guide)
        ↓
     Surfaces        ← Pulse, Work, Home, …
```

Signals sit **after** Evidence. See [`commerce_brain_signal_consumption_v1.md`](commerce_brain_signal_consumption_v1.md).

---

## Naming discipline

- `signal_type` is a **past fact**, not a wish: e.g. recovery message accepted — not “should recover.”
- One Signal = one happened thing. Do not pack stories or recommendations into `signal_type`.
- Families are namespaces, not engines. Do not build five mini-products.

---

## Acceptance

V1 passes only if:

1. A new engineer can read this in **under five minutes** and know what a Signal is.  
2. Every Signal answers only **what happened**.  
3. The contract has **five fields** and no more.  
4. Only the **five families** above exist.  
5. No feature uses Signals to decide, explain, or recommend.

**No implementation in this document.**

**Runtime (separate):** Recovery + Purchase only, behind `CARTFLOW_COMMERCE_SIGNALS_V1` (default off). See `services/commerce_signals_v1.py` and `GET /dev/commerce-signals`. Customer / Product / Traffic not implemented yet.
