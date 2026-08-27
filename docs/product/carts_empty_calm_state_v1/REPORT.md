# Carts Empty / Calm State Visual Closure V1

Status: visual correction of the store-empty composition only. Not a Carts redesign.

## What changed

When total carts == 0 (no active rows and no archived rows):

- Page identity stays: the canonical Carts question.
- One calm statement: **لا يوجد عمل تشغيلي الآن**
- Filters, dashed empty panel, and desktop “اختر سلة من الطابور” are not rendered.
- Marker remains `carts-product-composition-v1`. Class `is-empty` / `data-carts-empty="store"`.

When carts exist, queue / filters / master-detail / mobile detail / primary actions are unchanged.

## Evidence

| Shot | File | Notes |
|------|------|--------|
| Mobile 430 zero-cart | `screenshots/01_mobile_430_zero_cart.png` | One calm line. No filters. No repeat stack. |
| Mobile 390 zero-cart | `screenshots/02_mobile_390_zero_cart.png` | Same composition. No overflow. |
| Desktop zero-cart | `screenshots/03_desktop_zero_cart.png` | No ghost “اختر سلة”. No master-detail shell. |
| Desktop non-empty | `screenshots/04_desktop_nonempty_regression.png` | Included only when a real cart existed. |

Living Store `smartreplyai.net` after one-off deploy `5f1296a` is store-empty. Shots 01–03 are live (no fabricated rows). Shot 04 is local demo only — one real waiting cart; Living Store had no cart to photograph.

## Regression

Non-empty: filters present, one waiting row, primary `wait`, detail + timeline intact. Shell / Home / Workspace untouched. No API or action-contract changes.

---

EMPTY STATE:
READY_FOR_VISUAL_REVIEW

OPERATIONAL REGRESSION:
NO
