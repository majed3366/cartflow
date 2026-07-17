# Business Findings Engine V1 — Coverage Gap Report

**Date (UTC):** 2026-07-17  
**Scope:** Insights merchants want that V1 cannot yet produce safely from durable truth  

## Principle

Gaps are first-class. The engine must say **insufficient evidence** rather than invent traffic, image quality, or payment-provider conclusions.

---

## Gaps by desired insight

| Desired merchant insight | V1 status | Missing durable data | Safe V1 behaviour |
|--------------------------|-----------|----------------------|-------------------|
| Shipping hesitation dominates a **category** (not only store) | Partial | Category taxonomy on products; reason×category join | Dominant reason at store/product scope when concentrated |
| Product high ATC / low purchase | Supported (ATC + purchase mappings) | Product view counts | Uses add-to-cart as interest proxy; states views unavailable in observability |
| Product low interest vs peers | Supported (relative ATC) | Views, traffic source | Peer ATC comparison only |
| Return without purchase after recovery | Supported (movement/logs fixture + DB returns) | Strong channel attribution on every return | Uses return/purchase cohorts; does not invent attribution |
| WhatsApp produces purchases | Supported when purchase counts exist | Timed send cohorts | Cohort rates from sent/returned/purchased |
| Widget shown / opened / ignored funnel | **Gap** | Durable widget impression/open events | Widget finding uses reason+contact capture only; `widget_shown_metrics_unavailable` |
| Traffic vs conversion diagnosis | **Honest insufficient** | Visitor / session truth | Never infers traffic from cart count |
| Warranty / Tabby / Tamara / TikTok claims | **Suppressed** | Direct evidence never present in V1 | Out of scope — not emitted as confirmed findings |
| “Images are definitely poor” | **Suppressed** | Creative quality scores | May appear only as test direction language, never confirmed cause |
| “Price is definitely too high” | **Suppressed** | Price elasticity evidence | Test recommendation only when conversion weak |
| Discount messaging A/B outcome | **Gap** | Experiment assignment + outcome table | Not produced in V1 |
| Finding strengthens/weakens over time | Partial (status fields) | Persisted finding lifecycle store | Contract supports lifecycle; V1 run is snapshot-ranked |
| Identity-confident repeat visitors | Partial | Strong MQIC on every ATC row | Uses repeat_adds / revisits when present |

---

## Evidence coverage flags (engine observability)

Emitted on every package:

- `visitor_truth_unavailable`
- `product_views_unavailable`
- `widget_shown_metrics_unavailable`

---

## What V1 does produce from demo-rich evidence

See `BUSINESS_FINDINGS_DEMO_REPORT_V1.md` — multiple families including hesitation, product conversion, channel effectiveness, WhatsApp **test** (not confirmed cause), traffic insufficient, contact blocker (single), return-without-purchase, hesitation resolution.

---

## Recommended next data investments (priority)

1. Durable storefront visitor sessions (enables Finding 7 for real).  
2. Widget impression / open / dismiss events.  
3. Persisted finding lifecycle table (strengthen / weaken / resolve).  
4. Reason × purchase × return cohort materialization (faster than joins).  
5. Experiment framework before any “discount messaging” finding.
