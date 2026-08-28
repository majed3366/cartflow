# 07 — Regression

**Source:** Living Store `demo` after review bind, `GET /api/dashboard/normal-carts` (read-only).  
**Evidence:** `regression_living_store.json`

| Metric | Legacy dual contract | Unified contract |
|--------|----------------------|------------------|
| Queue rows | 25 | 25 |
| يحتاجني (attention tab) | 15 | — retired for Carts |
| يحتاجني (canonical) | — | **0** |
| wait | 21 | 21 |
| completed | 4 | 4 |
| Orientation | calm + يتابع 21 **and** يحتاجني 15 | calm + يتابع 21 **and** يحتاجني **0** |
| Default filter | attention (empty-looking vs 15 chip) | **الكل** (needs_you == 0) |

**Consistency:** orientation count = يحتاجني count = queue membership for `attention` = **0**. الكل = 25.

## Raven — حزام جلد للساعة

| | |
|--|--|
| Lifecycle | `needs_intervention` |
| Label | بانتظار الجاهزية |
| Primary | wait — انتظر — CartFlow يتابع |
| Tabs | all, attention (legacy) |
| Ownership | WAITING_ON_CARTFLOW |
| In يحتاجني | **No** |
| Visible in | الكل |

Unambiguous: CartFlow owns the next step; merchant is not required now.

## Operational regression

- Primary-action keys unchanged  
- Archive / reopen APIs unchanged  
- No snapshot write, no Scheduler  
- nophone / sent / recovered still same-generation row membership  
- Tests: `tests/test_carts_needs_you_truth_unification_v1.py` + composition V1  

**CURRENT 25-ROW CONSISTENCY:** CONSISTENT
