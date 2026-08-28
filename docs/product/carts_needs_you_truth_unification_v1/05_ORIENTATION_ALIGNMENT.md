# 05 — Orientation Alignment

`paint()` uses one `countPrimary(state.rows)` object.

| Count | Orientation |
|-------|-------------|
| `needs_you > 0` | «N سلال تحتاج تدخلك الآن» / «سلة واحدة…» |
| `needs_you == 0` and `wait > 0` | «لا توجد سلال تحتاج تدخلك الآن» + «CartFlow يتابع N» |
| only completed/archived | calm completed copy |
| snapshot pending / loading, no rows | not calm — see 06 |

`filterCounts().attention === countPrimary().needs_you` always.

يحتاجني chip and orientation cannot diverge on the same row list.
