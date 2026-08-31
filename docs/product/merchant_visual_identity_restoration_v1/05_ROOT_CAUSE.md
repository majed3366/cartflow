# 05 — Root cause

## Founder-visible old dashboard

**Class:** `CONDITIONAL_BRANCH` / silent cookie selection.

Live proof on `480d7d52` + Living Store session:

| Request | UI | Renderer | Template |
|---------|----|----------|----------|
| `GET /dashboard` | v2 | `merchant_ui_v2` | `merchant_app_v2.html` |
| `GET /dashboard` + `Cookie: cf_ui_v2=0` | v1 | `merchant_ui_v1` | `merchant_app.html` |
| `GET /dashboard?cf_ui=v1` | v1 | `merchant_ui_v1` | `merchant_app.html` |

`?cf_ui=v1` wrote `cf_ui_v2=0` for 14 days. Later visits without the query still selected V1. That is **not** an explicit rollback action.

Falsified: missing Home emitters on V2 (they emit). Stale SHA (header was `480d7d52`). Landing `/` as Merchant proof (landing is not Merchant).

## Not the cause

| Candidate | Result |
|-----------|--------|
| RENDERER_NOT_EMITTING_PRIMITIVE | Falsified on default V2 |
| CSS_NOT_APPLIED | V2 language CSS linked |
| HISTORICAL_REWRITE of painters | Painters already restored on parent `90e28b8f` |
| UNMAPPED_FIGMA_PRIMITIVE | P1–P16 have runtime owners |

## Fix class

Stop treating `cf_ui_v2=0` as a selector. Persist V2 only. Heal leftover `=0` on canonical `/dashboard`. Keep `?cf_ui=v1` as the only request-scoped Merchant rollback (plus ops env).
