# Gate 12 — Performance Sanity

Artifact: `performance_sanity.json`

| Metric | Value | Threshold |
|--------|------:|-----------|
| Home initial | 4371 ms | < 20000 ✓ |
| Home → Workspace | 1001 ms | < 15000 ✓ |
| Workspace → Home | 1260 ms | < 15000 ✓ |
| Home ctx cycle | 979 ms | — |
| Workspace ctx cycle | 894 ms | — |
| DOM growth (sequence) | +42 | < 5000 ✓ |
| Nav binder growth | 0 | stable ✓ |
| API on scroll | 0 | ✓ |

No excessive reflow loops or listener accumulation detected in this bounded sequence.
