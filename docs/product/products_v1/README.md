# Products V1 — Product Commercial Truth Surface

**Mode:** DSE / Production-Truth / Contract-First / Mobile-First  
**Target:** Merchant UI V2 `/dashboard` page = Products  
**Lab tenant:** `cf_live_reality_lab` / Dataset V2 / R17 نور العناية  
**GENERAL RELEASE:** NO  
**DEPLOY:** NO

## Question

أي المنتجات تستحق انتباهي الآن، وما الذي يحدث لكل منتج؟

This is not a catalog admin page and not a second recommendation / mission ranker.

## Ownership

| Concern | Owner |
|---------|--------|
| Product identity / price | `ProductCatalogEntry` + cart line snapshots |
| Cart count / cart value | snapshots joined to `AbandonedCart` |
| Purchases / revenue | `ProductPurchaseMapping` (0 is a real zero after the bounded query) |
| Hesitation | `ProductHesitationMapping` only (product-scoped) |
| Visit / exposure | `ProductSignalEvent` `product_viewed` + source `live_reality_lab_v2_synthetic_visit` — lab only |
| Read-model freeze | `product_read_model_contract_v1` |
| Products presentation compose | `products_commercial_truth_v1` |
| Commercial mission state | Catalog / CDC / Portfolio — unchanged |

## Visit law

- **REAL MERCHANT VISIT INGESTION:** NO
- Lab: labelled `LAB-SYNTHETIC PRODUCTION-SHAPED VISIT TRUTH`
- Normal merchants: `EXPOSURE: NOT_STORED` — never a painted 0, never inferred from carts, never unique visitors

## Attention

Deterministic presentation groups from existing facts only:

- يحتاج انتباه — named product, carts > 0, known purchases = 0
- مستقر — named product, known purchases > 0
- تحت المراقبة — leftover hesitation without the above
- بيانات غير كافية — missing name / unnamed

Owner: `products_commercial_truth_v1`. Not COL / OGL / Mission Catalog ranking.

## Query

One Products-page load:

- Normal merchant: **+4** grouped queries
- Lab tenant: **+5** (adds labelled visit group-by)
- N+1: 0
- Not attached to `/api/dashboard/summary`

## Founder review

Local 390px pack (DEPLOY: NO — not live stub):

`docs/product/products_v1/founder_review/`

Desktop copy:

`C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Products_V1\`

Gate: `tests/test_products_commercial_truth_v1.py`
