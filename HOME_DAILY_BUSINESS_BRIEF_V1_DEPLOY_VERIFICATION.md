# Home Daily Business Brief V1 — Deploy Verification

**Status:** Implementation complete — await merchant-value product review  
**Constitution:** [`MERCHANT_DAILY_BUSINESS_BRIEF_CONSTITUTION_V3.md`](MERCHANT_DAILY_BUSINESS_BRIEF_CONSTITUTION_V3.md) (**Approved**)  
**Date (UTC):** 2026-07-17  

## Product story (one question per section)

| # | Section | Business question | Payload owner |
|---|---------|-------------------|---------------|
| 1 | Business Health | كيف حال عملي اليوم؟ | `business_health` |
| 2 | Biggest Revenue Risk | أين أخسر أكثر الآن؟ | `biggest_revenue_risk` (CIL primary) |
| 3 | Biggest Opportunity | أين أفضل فرصة اليوم؟ | `biggest_opportunity` (nav evidence) |
| 4 | Today's Priority | ما أهم شيء أفعله اليوم؟ | `attention_today` / `todays_priority` (max 1) |
| 5 | Business Understanding | ماذا نفهم عن عملك الآن؟ | `store_understanding` / `business_understanding` |
| 6 | Learning Progress | كيف يتطوّر فهمنا للعمل؟ | `learning_progress` |
| 7 | Business Timeline | ما الذي حدث — ولماذا يهم؟ | `while_away` / `business_timeline` |

## Ownership rules enforced

- No duplicated risk / opportunity / priority headlines  
- Understanding explains business meaning — no CTA  
- Priority owns the single action  
- Risk owns commercial-loss framing  
- Timeline remains historical; `why_it_matters_ar` is contextual only  
- Home never mints CIL conclusions  

## Files

- `services/merchant_home_composition_v1.py` — finalize Daily Brief sections  
- `services/commercial_interpretation_v1.py` — revenue-risk mapping + understanding meaning fields  
- `static/merchant_dashboard_home_v1.js` — seven-section render story  
- Tests: `tests/test_home_daily_business_brief_v1.py` (+ updated redistribution / UI / PIB / CIL)

## Merchant value review checklist

Approve only if each section:

1. Improves business understanding  
2. Improves decision quality  
3. Creates commercial value  
4. Justifies merchant attention  
5. Would be missed if removed  

**Not a visual approval.**
