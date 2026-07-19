# Commerce Intelligence Foundation V1

**Document type:** Platform foundation (intelligence layer)  
**Status:** **Implemented — Foundation**  
**Date (UTC):** 2026-07-19  
**Authority:** Commercial understanding SoT for future Home consumption  

**STOP:** No Home implementation · No E2 · No UI · Executive Home paused after Sprint 1 (E1)

---

## 1. Mission

Build the commercial intelligence layer that Home will consume.

| Layer | Responsibility |
|-------|----------------|
| **Commerce Intelligence** | Generates / projects commercial understanding |
| **Home** | Presents understanding only — **never calculates it** |

---

## 2. Four canonical domains

| Domain ID | Name | Answers |
|-----------|------|---------|
| `product_intelligence` | Product Intelligence | Attract / fail to convert / recover / repeatedly fail / deserve attention |
| `customer_intelligence` | Customer Intelligence | Repeating behaviors · hesitation · purchase · return patterns |
| `store_intelligence` | Store Intelligence | What changed · conversion · recovery · customer quality · evidence growth |
| `commercial_guidance` | Commercial Guidance | Merchant actions **only after sufficient evidence** (or honest “collect more evidence”) |

Domains overlay [`COMMERCIAL_QUESTION_REGISTRY_V1.md`](COMMERCIAL_QUESTION_REGISTRY_V1.md) — they do **not** replace CQ-* IDs.

---

## 3. Canonical record

Every intelligence record **must** contain:

| Field | Meaning |
|-------|---------|
| **Question** | Registered commercial question (`id`, `text_ar`, `text_en`) |
| **Finding** | Merchant-facing claim |
| **Evidence** | Summary + refs + sample_size (not engine dumps) |
| **Confidence** | Level + Arabic label |
| **Recommendation** | Text + type + `eligible` flag |
| **Status** | ready / actionable / monitor / insufficient_evidence / still_learning |
| **Source Domains** | One or more of the four domains (provenance) |

Runtime: `services/commerce_intelligence/contract_v1.py`

---

## 4. Pipeline (reuse, do not fork)

```text
Business Findings Engine V1
        ↓ project
Commerce Intelligence Foundation V1  (canonical records by domain)
        ↓ (future — not this task)
Home Executive bands / surfaces  (consume only)
```

| Module | Role |
|--------|------|
| `services/commerce_intelligence/domains_v1.py` | Domain taxonomy + CQ dimension overlay |
| `services/commerce_intelligence/project_from_finding_v1.py` | Finding → record (+ guidance projection) |
| `services/commerce_intelligence/engine_v1.py` | Package builder / runner |
| Reused | `business_findings_engine_v1`, `commercial_question_registry_v1` |

Optional later: Business Reasoning Engine for multi-finding guidance synthesis — not required for Foundation V1 completeness.

---

## 5. Guidance gate

Commercial Guidance may recommend action only when evidence/confidence/status allow (`is_guidance_eligible_v1`).

Otherwise recommendation type is `insufficient_evidence` — e.g. «اجمع أدلة إضافية قبل أي توصية تجارية» / «لا توصِ بخصم بعد» via monitor paths.

---

## 6. Home consumption contract

```text
Home consumes canonical records only.
Home must never calculate intelligence itself.
```

Package field `home_consumption_contract` documents required fields and future E1–E6 mapping eligibility.  
**This foundation does not change Home composition or UI.**

---

## 7. Success

After this foundation, Home (in a later sprint) can display:

- Products  
- Customers  
- Store  
- Knowledge / Recommendations  

by **mapping records → bands**, without adding new commercial logic inside Home.

---

## 8. API (library)

```python
from services.commerce_intelligence import run_commerce_intelligence_foundation_v1

pkg = run_commerce_intelligence_foundation_v1(store_slug="…", load_db=True)
# pkg["records"], pkg["by_domain"]["product_intelligence"], …
```

---

## 9. STOP

- No Home wiring  
- No E2 Decision of the Day  
- No UI / CSS / components  
- Executive Home remains paused after E1 Product Review  

Await Product Review of this foundation before Home consumption work.
