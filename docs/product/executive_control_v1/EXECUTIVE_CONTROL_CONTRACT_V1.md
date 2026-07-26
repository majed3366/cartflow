# Executive Control Contract V1

**Status:** Implemented on `merchant_publication_v1` (no new engine).  
**Gate:** Gate 2 remains OPEN until certified Living Store CEO review.  
**Locked:** Gate 3 / Product Intelligence.

## Authority

`merchant_publication_v1` is the single executive authority for:

- Home
- Decision Workspace
- Products
- Carts
- Communication

No merchant surface may independently reinterpret the primary truth.

## Required published fields

| Field | Meaning |
|-------|---------|
| `store_condition` | Merchant store state (`status_ar` + `summary_ar`) |
| `primary_executive_decision` | Exactly one lead decision object |
| `primary_situation_id` | Transport/link id (never painted on merchant UI) |
| `primary_subject` | Affected product / area (merchant Arabic) |
| `primary_action` | Single first action (product-specific when evidence supports) |
| `supporting_secondary_situations` | Distinct secondary context only |
| `communication_condition` | Communication truth |
| `cart_condition` | Cart operational condition |
| `truth_version` | Composition digest (diagnostics only) |
| `simulation_run_id` | Living Store run binding (diagnostics only) |

## Store-condition states

- مستقر
- مستقر مع فرصة تستحق الانتباه
- يحتاج انتباهك
- يحتاج تدخلاً عاجلاً
- أدلة غير كافية

“Not critical” must never mean “nothing needs attention.”  
If an actionable high-priority decision exists, calm/healthy wording is forbidden.

## Home executive order

1. حالة المتجر  
2. أهم قرار اليوم (dominant)  
3. أهم منتج يستحق الانتباه  
4. حالة السلال  
5. حالة التواصل  
6. Secondary situations only when they add distinct understanding  

## Workspace order (same primary)

1. القرار الأهم  
2. لماذا هو الأولوية؟  
3. المنتج/المجال المتأثر  
4. الأدلة  
5. الإجراء الأول  
6. الأثر المتوقع  
7. Secondary distinct decisions  

## Merchant-safe rule

Forbidden on merchant pages:

- `Status = CONSISTENT`, `CEO_REVIEW_SAFE`, `store_slug`, `merchant_id`
- `simulation_run_id`, `truth_version`, `situation_id`, `cs:…`
- Raw English architecture terms (`operations`, internal registry keys)

Diagnostics remain on `/dev/reality-validation-*` only.

## Semantic parity

Mobile and Desktop may differ in layout only.  
They must consume the same publication payload and share identical meaning fields via `semantic_parity_fingerprint_v1()`.

## Tests

- `tests/test_executive_control_parity_v1.py`
- `tests/test_merchant_understanding_repair_v1.py`
