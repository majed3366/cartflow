# Gate 2X Completion Report — Merchant Understanding V1

**Gate:** Gate 2X  
**Date (UTC):** 2026-07-25  
**No Product Intelligence. Gates 3–7 LOCKED.**

---

## 1. Constitutional principle

> Every surface must increase the merchant's understanding of the business.  
> If a surface explains CartFlow more than it explains the store, it fails.

Desired merchant feedback after opening Home:

**«I understand my store.»** — not — **«I understand what CartFlow is doing.»**

---

## 2. Pipeline

```text
Operational Reality
        ↓
Observation
        ↓
Business Understanding     ← explains the store
        ↓
Merchant Understanding     ← explains what the merchant should care about (Gate 2X)
        ↓
Executive Summary (Home)
        ↓
Decision Workspace
```

Gate 2X is the **publication gate** above Store Executive / Business Understanding.

---

## 3. Page questions (one each)

| Page | Merchant question |
|------|-------------------|
| Home | What should I know about my business right now? |
| Decision Workspace | What should I decide today, and why? |
| Carts | What is happening to every customer cart? |
| Communication | What happened during customer communication? |
| Settings | How do I configure CartFlow? |

---

## 4. Four questions before publish

1. Does this help the merchant understand the business?  
2. Is this about the store rather than CartFlow?  
3. Does it naturally lead to a business decision?  
4. Would a merchant act differently after reading it?

If **No** → suppress / replace with safe understanding language.

---

## 5. Executive language

**Prefer:** product demand, purchase completion, recovery opportunities, customer interest, shipping vs conversion, no critical issues.

**Avoid:** queue size, missing-phone counts as conclusions, scheduler state, internal recovery process, technical counters, validation.

Example Home carts rewrite:

| Before (ops) | After (understanding) |
|--------------|------------------------|
| 86 سلة قيد المتابعة مع العملاء. | سلال العملاء تحتاج متابعة نشطة. |

---

## 6. Module / wiring

| Piece | Path |
|-------|------|
| Layer | `services/decision_composition_engine_v1/merchant_understanding_v1.py` |
| Pipeline stamp | `compose_v1.py` → `gate_2x_merchant_understanding` |
| Home defense | `home_executive_summary_v1/compose_v1.py` carts section |
| Tests | `tests/test_gate_2x_merchant_understanding_v1.py` |

---

## 7. Definition of Done

| Criterion | Status |
|-----------|--------|
| Merchant Understanding layer above Business Understanding | **DONE** |
| Four-question publication gate | **DONE** |
| Queue/counter executive language suppressed on Home | **DONE** |
| Pipeline stamps `gate_2x_merchant_understanding` | **DONE** |
| Guiding principle for post–Gate 2 features | **DONE** |
| Product Intelligence | **NOT STARTED** (locked) |
