# Merchant Product Language V1 — Presentation Layer

**Status:** Carts consumes Merchant Insight V1; other pages legacy-only  
**Date (UTC):** 2026-07-08  
**Scope:** Wording and display structure — **meaning owned by Merchant Insight Layer**  
**Authority:** `services/merchant_product_language_v1.py`  
**Wording constitution:** [cartflow_merchant_language_system_v1.md](cartflow_merchant_language_system_v1.md)

---

## Mission

Merchant Product Language (MPL) formats governed insight into the first visible narrative on merchant pages.

| Layer | Owns |
|-------|------|
| **Merchant Intelligence** | WHAT happened |
| **Merchant Value** | WHY it matters |
| **Merchant Insight** | WHAT IT MEANS for the merchant |
| **Merchant Product Language** | HOW it is presented (wording + display order) |

The merchant should understand the situation within **3 seconds** — insight before evidence.

---

## Architecture

```
Truth
  ↓
Merchant Intelligence
  ↓
Merchant Value
  ↓
Merchant Insight Layer
  ↓
Merchant Product Language   ← this document
  ↓
Merchant UI
```

### Display order (non-negotiable)

```
Headline (insight) → Reason → CartFlow Action → Evidence
```

Never: Evidence → Insight. MPL **never** derives meaning from raw counts.

---

## Modules

| Module | Responsibility |
|--------|----------------|
| `services/merchant_insight_layer_v1.py` | Meaning composition (`compose_page_insight_v1`) |
| `services/merchant_product_language_v1.py` | Presentation from insight (`render_product_language_from_insight_v1`) |
| `services/merchant_product_language_templates.py` | Evidence-line formatting templates |
| `static/merchant_insight_layer_v1.js` | Client MIL mirror (Carts) |
| `static/merchant_product_language_v1.js` | Client MPL renderer |

### Legacy (non-migrated pages only)

`compose_page_narrative_v1()` — composes headline from raw evidence directly. **Do not use** on new Carts path or future page migrations.

---

## Primary interfaces

### Input — Merchant Insight output

MPL consumes MIL fields only:

- `primary_insight`
- `reason`
- `cartflow_action`
- `evidence_summary`
- `confidence`
- `source_refs`

### `render_product_language_from_insight_v1(page_key, insight)`

Maps insight into narrative sections:

```python
{
  "version": "v1",
  "authority": "merchant_product_language_v1",
  "page_key": "carts",
  "primary_question_ar": "أي السلال تستحق الانتباه الآن؟",
  "sections": {
    "headline": {"text_ar": "جميع السلال الحالية تحتاج انتباهك.", ...},
    "reason": {"text_ar": "لأن 4 سلة مراقَبة تحتاج تدخلاً حالياً.", ...},
    "cartflow_action": {"text_ar": "...", ...},
    "evidence": {"lines_ar": ["CartFlow يراقب 4 سلة في متجرك.", ...], ...},
  },
  "composition_order": ["headline", "reason", "cartflow_action", "evidence"],
  "observability": {"renders_from_insight": True, "meaning_source": "merchant_insight_layer_v1"},
}
```

Certification: `validate_product_language_from_insight_v1(narrative)`.

### Carts pipeline helper

`compose_carts_narrative_from_payload_v1(payload, rows)` — evidence → insight → MPL (tests/certification).

---

## Page intent registry

| Page | Primary question (AR) |
|------|------------------------|
| **home** | ماذا يحتاج متجري اليوم؟ |
| **carts** | أي السلال تستحق الانتباه الآن؟ |
| **messages** | هل التواصل مع العملاء سليم؟ |
| **whatsapp** | هل قناة التواصل جاهزة؟ |
| **widget** | هل CartFlow يفهم تردد العملاء؟ |
| **settings** | هل إعدادات متجري صحيحة؟ |
| **plans** | ما حالة اشتراكي الحالية؟ |

---

## Carts consumption (implemented)

1. `buildCartsEvidenceFromPayload(d, rows)` — existing payload only
2. `composePageInsightV1("carts", evidence)` — MIL client mirror
3. `renderProductLanguageFromInsightV1("carts", insight)` — MPL presentation
4. `renderPageNarrativeHtml(narrative)` — existing `#ma-carts-product-language-v1` host

**Unchanged:** `merchant_intelligence_carts_v1.js` story/group cards (Section 4 details).

Tests: `tests/test_merchant_product_language_carts_consumption_v1.py`.

---

## Writing rules (enforced)

- Calm, operational, reassuring, explainable
- Headline answers meaning — never leads with raw count
- Counts appear only in evidence section
- No forbidden internal tokens (`group_key`, `lifecycle_state`, `bucket`, …)
- Every block traceable via `source_refs`

---

## Explicit non-goals

- No Home / WhatsApp / other page wiring in this phase
- No API, MI, MVC, or Truth changes
- No new design system — reuses `.ma-mpl-narrative*` block

---

## Related

- [merchant_insight_layer_v1.md](merchant_insight_layer_v1.md) — meaning composition authority
