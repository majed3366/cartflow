# 06 — Snapshot-Missing Fallback

Snapshot recovery is **not** performed. Reader may still miss.

| Phase | Rows | Paint |
|-------|------|--------|
| Request in flight | none | Loading — «جاري تحميل السلال…» |
| Response: miss/degraded/timeout, `data_freshness` ≠ `hot_merged`, no rows | none | **Degraded / unknown** — «تعذّر تأكيد حالة السلال». Never «لا توجد سلال تحتاج تدخلك الآن» |
| Response: `hot_merged` (or rows present) | page rows | Orientation + filters + queue from **those rows only** |
| Truthful empty after merge | 0 | «لا توجد سلال» |

Never mix empty snapshot filter counters with a hot-merged queue. Filter counts are computed from `state.rows` only.
