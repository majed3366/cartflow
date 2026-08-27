# State and Empty State Map

All copy is calm and truthful. No manufactured work.

| Condition | Orientation | Queue empty copy |
|-----------|-------------|------------------|
| Loading, no rows yet | جاري تحميل السلال… | — |
| Fetch / partial failure | تعذّر تحميل السلال | تعذّر تحميل الطابور — لا بيانات مخترعة |
| No carts at all | لا توجد سلال | لا يوجد عمل تشغيلي الآن |
| Carts exist, none actionable | لا توجد سلال تحتاج تدخلك الآن | Same when filter=`attention` |
| All waiting | لا توجد سلال تحتاج تدخلك الآن + CartFlow يتابع N | Empty nophone/sent if that filter is vacant |
| All completed | لا توجد سلال تحتاج تدخلك الآن + مكتملة أو مؤرشفة | لا توجد سلال مكتملة when recovered is vacant |
| Archived-only | recovered default | Quieter archived rows |
| Filter vacant but store not empty | — | لا سلال في هذه التصفية |

Never fill the page with recommendations.
