# Live Decision Hierarchy & Portfolio Visibility V1

Lab-only presentation of existing Catalog + CDC + Portfolio truth.

**Tenant:** `cf_live_reality_lab`  
**Scenario:** `R17_shipping_hesitation`  
**GENERAL RELEASE:** NO  
**PRODUCTS V1:** BLOCKED  
**FOUNDER PRODUCT PASS:** NOT YET

## Law

- Commercial mission **state** is owned by Catalog / CDC / Portfolio.
- OGL / HES may give operational instruction and must not contradict commercial sufficiency.
- Frontend ranking: **0**.
- Server-owned tenant gate. No query-parameter bypass. No frontend tenant spoof.
- Normal merchants unchanged (package omitted).

## Surfaces

Home answers: ما الذي يستحق انتباهي الآن؟

- مهمتك الآن
- تحت المراقبة (Portfolio `safe_secondaries`)
- المهمة التجارية التالية (only if `next_mission` is a different family)
- لاحقاً (deferred, not executable)

Decision Workspace is one flow: EVIDENCE → DECISION → EXECUTION → MEASUREMENT → RECHECK.

Contextual sidebar organizes lifecycle state. It does not rank missions.

## Live proof

Exact-SHA API deploy `eceb0d0719713be3c81244187c365714f1e12313` (`f7568b2e`).  
6 live mobile shots: `docs/product/live_decision_hierarchy_portfolio_visibility_v1/live/`  
Desktop copy: `C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Live_Decision_Hierarchy_Portfolio_Visibility_V1\`
