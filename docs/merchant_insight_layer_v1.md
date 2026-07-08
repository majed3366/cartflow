# Merchant Insight Layer V1 — Foundation

**Status:** Foundation (composition defined; pages not migrated)  
**Date (UTC):** 2026-07-08  
**Scope:** Convert existing platform truths into operational **meaning** — composition only  
**Authority:** `services/merchant_insight_layer_v1.py`  
**Wording constitution:** [cartflow_merchant_language_system_v1.md](cartflow_merchant_language_system_v1.md)

---

## Mission

Before showing evidence, explain **what the situation means** for the merchant.

The merchant should understand within **3 seconds**.

| Layer | Answers |
|-------|---------|
| **Merchant Intelligence** | WHAT happened |
| **Merchant Value** | WHY it matters |
| **Merchant Insight** | WHAT IT MEANS for the merchant |
| **Merchant Product Language** | HOW it is presented (future: presentation-only) |

---

## Architecture

```
Truth
  ↓
Merchant Intelligence
  ↓
Merchant Value
  ↓
Merchant Insight Layer   ← this document
  ↓
Merchant Product Language
  ↓
Merchant UI
```

### Composition order (non-negotiable)

```
Insight → Reason → CartFlow Action → Evidence summary
```

Never: Evidence → Insight.

---

## Insight types (governed)

| Type | Label (AR) |
|------|------------|
| `healthy` | وضع مستقر |
| `attention` | يستحق انتباه |
| `risk` | نمط يستحق المراقبة |
| `opportunity` | فرصة للمتابعة |
| `waiting` | بانتظار |
| `automatic_progress` | تقدم تلقائي |
| `merchant_required` | يحتاج قرارك |
| `recovery_working` | الاسترداد يعمل |
| `store_ready` | المتجر جاهز |
| `monitoring_only` | مراقبة فقط |

Templates: `services/merchant_insight_layer_templates.py`

---

## API

### `compose_page_insight_v1(page_key, evidence)`

**Input:** explicit evidence from MI / Value / counts / readiness — never inferred.

**Output:**

```python
{
  "version": "v1",
  "authority": "merchant_insight_layer_v1",
  "page_key": "carts",
  "insight_type": "merchant_required",
  "insight_type_label_ar": "يحتاج قرارك",
  "primary_insight": "جميع السلال الحالية تحتاج انتباهك.",
  "reason": "لأن 4 سلة مراقَبة تحتاج تدخلاً حالياً.",
  "cartflow_action": "أكمل CartFlow العمل التلقائي... CartFlow ينتظر قرارك قبل المتابعة.",
  "evidence_summary": {"monitored_count": 4, "attention_count": 4, "automatic_count": 0},
  "source_refs": ["attention_count", "monitored_count"],
  "confidence": "high",
  "composition_order": ["primary_insight", "reason", "cartflow_action", "evidence_summary"],
}
```

### `build_page_insight_evidence_v1(page_key, payload, rows)`

Builds evidence from existing dashboard payload. Carts delegates to `build_carts_page_evidence_v1()` (Product Language evidence builder — same facts, no duplication of truth).

### `validate_page_insight_v1(insight)`

Certification gate — violations list.

---

## Certification rules

1. Supported by evidence (`source_refs`).
2. Understandable within 3 seconds (meaning-first `primary_insight`).
3. Answers: **"What does this mean?"** — not "What data do we have?"
4. Does not duplicate story cards (page-level meaning vs card-level story).
5. Does not repeat raw counts in `primary_insight` (counts live in `evidence_summary`).
6. Leads naturally into Merchant Value stories below.

---

## Forbidden

- Revenue / ROI claims
- Predictions / probability
- AI opinions / business advice
- Marketing copy / speculation
- Internal tokens (`group_key`, `lifecycle_state`, …)

---

## Explicit non-goals (this phase)

- No Home / WhatsApp / other page wiring
- No changes to MI, MVC, or Truth
- MPL Carts consumption implemented — see [merchant_product_language_v1.md](merchant_product_language_v1.md)

---

## Next phase

Migrate remaining pages; MPL renders insight blocks only on each page.
