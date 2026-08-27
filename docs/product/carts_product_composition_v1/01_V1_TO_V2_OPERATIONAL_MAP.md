# V1 → V2 Operational Map

V1 is the source of operational truth. V2 is a new PageStage composition, not a visual copy.

| V1 behavior | Canonical contract | V2 presentation |
|-------------|--------------------|-----------------|
| `#page-carts` work queue (`renderPeV2CartsQueue` / MI groups after ops paint) | `GET /api/dashboard/normal-carts` → `merchant_carts_page_rows` | `#cf2-carts-root` queue list |
| Filter chips `all / attention / nophone / sent / recovered` | `merchant_cart_visible_tabs` + `merchant_cart_filter_counts` | Same keys; merchant-intent labels (يحتاجني / بانتظار / اكتمل) |
| Attention labels تحتاج تدخل / بانتظار رقم العميل / بانتظار الجاهزية / يحتاج إعداد | `dashboard_attention_merchant_semantics_v1` + `merchant_explanation_v1.status_label_ar` / `customer_lifecycle_label_ar` | Row + detail state text; no invented labels |
| One primary action | `cart_page_primary_action_v1` + `resolveCartPagePrimaryAction` | Single `data-cf-primary-action` CTA |
| automatic → wait | `KEY_WAIT` | Secondary-styled «انتظر — CartFlow يتابع» |
| executable contact → contact_customer | `KEY_CONTACT` + contact href | Primary link if href exists |
| no-phone / VIP manual → follow_up_manually | `KEY_FOLLOW_UP` | Primary; «لا يوجد رقم» chip when truthful |
| not executable → review_cart | `KEY_REVIEW` | Primary label only |
| completed / purchased → no_action_required | `KEY_NO_ACTION` + purchase variant | Terminal state; no contact/recovery CTA |
| archived → reopen | `KEY_REOPEN` + `POST …/reopen` | Primary reopen |
| Archive demoted | `secondary_key=archive` + `secondary_demoted` | Quiet «إغلاق الحالة» only when valid |
| Timeline / proof surface | `merchant_proof_surface_v1` + movement / continuation lines | `<details>` operational timeline |
| Archived pool | `merchant_archived_carts_page_rows` | Recovered filter + quieter rows |
| VIP threshold form | Settings ownership | Not rendered on Carts |
| MI stories / MPL / CS publication | Workspace / transport only | Not painted |

Not carried from V1 UI:

- KPI / hero story band
- desktop conversation chrome as a second product
- group «لماذا هذه المجموعة؟» meaning blocks
- `#page-vip` policy fields
