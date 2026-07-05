# Merchant Explanation Unification V1

**Date:** 2026-07-05  
**Scope:** Presentation-only — one unified merchant explanation layer for cart detail.  
**Unchanged:** Purchase Truth, Lifecycle Truth ownership, Recovery scheduling, Provider Truth, Decision Layer, Daily Brief Composer.

---

## 1. Problem

Cart detail explanations came from multiple sources (`customer_lifecycle_*`, `merchant_lifecycle_*`, proof surface, JS composition). Some surfaces still leaked internal keys (`waiting_first_send`, `حالة المسار`, etc.).

---

## 2. Architectural principle

**One Source of Merchant Explanation**

```
Lifecycle Truth (internal state_key)
        ↓
customer_lifecycle_states_v1 (classifier copy — input)
        ↓
merchant_explanation_v1 (sanitized unified output)
        ↓
Cart detail UI / synced legacy fields
```

Internal diagnostics stay in `diagnostic_internal` and existing ops/dev payloads — **not rendered** in merchant cart detail.

---

## 3. Implementation

### 3.1 `services/merchant_explanation_v1.py`

- Catalog covers all merchant-visible lifecycle states
- Answers: ماذا حدث؟ / ماذا فعل CartFlow؟ / ماذا سيحدث؟ / هل يحتاج إجراء؟
- Sanitizer rejects raw state keys and diagnostic tokens in merchant fields
- Knowledge Routing prep metadata: `explanation_id`, `knowledge_event_type`, `merchant_visibility`, `eligible_surfaces`, `action_required`, `attention_level`
- `attach_merchant_explanation_v1` wired in `main.py` after proof surface attach

### 3.2 Cart detail UI

- `merchant_dashboard_lazy.js` renders **only** `merchant_explanation_v1`
- Proof surface steps removed from merchant cart detail block
- Legacy fallback if bundle missing (older snapshots)

### 3.3 Readability

- `merchant_app.css`: stronger contrast, 13–14px mobile body, clearer label hierarchy

### 3.4 Snapshots

- `merchant_explanation_v1` on slim snapshot allowlist (merchant fields only, no `diagnostic_internal`)

---

## 4. Verification

| Check | Result |
|-------|--------|
| All catalog states merchant-safe | `tests/test_merchant_explanation_v1.py` |
| Return-without-purchase copy | `explanation_id=return_without_purchase` |
| Internal keys not in merchant fields | Sanitizer + attach sync |
| Diagnostics preserved | `diagnostic_internal` + proof `why_we_know_diagnostic_ar` |
| Recovery behavior unchanged | No scheduler/lifecycle classifier changes |
| Mobile/desktop readability | CSS `.merchant-explanation-v1` contrast bump |

---

## 5. Knowledge Routing (future)

Metadata is present but **does not route**. Composer and Decision Layer unchanged.

---

## 6. Related

- Prior task: `docs/return_without_purchase_merchant_explanation_v1.md`
- Foundation before: Knowledge Routing Foundation V1 (not in scope)
