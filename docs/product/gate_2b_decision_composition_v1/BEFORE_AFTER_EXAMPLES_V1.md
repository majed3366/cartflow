# Before / After Examples — Supported Decision Types

## 1. Recoverability Gap (43 carts without phone)

| | Before (Gate 2A raw OT) | After (Gate 2B DCE) |
|--|-------------------------|---------------------|
| Title | راجع سلال بلا رقم تواصل | حسّن قدرة المتجر على جمع أرقام العملاء القابلين للاسترجاع. |
| Why | 43 سلة لا يمكن متابعتها… | Explains recovery path blocked before it starts |
| Why now | *(missing)* | Daily loss of recovery chance — 43 blocked now |
| Ignore | *(missing)* | Carts stay outside recovery; no messages sent |
| First step | *(same as action)* | Open no-phone carts; find where number capture breaks |
| Nature | Counter-shaped | Business meaning |

## 2. Waiting Recovery Work

| Scenario | Result |
|----------|--------|
| waiting=3, no_phone=3, engaged=0 | **Suppressed** `normal_state_no_merchant_action` (automation) |
| waiting=8, engaged=2 | **Published** — merchant intervention required |

## 3. Verified Existing Finding

| Scenario | Result |
|----------|--------|
| FDE DECISION + named product | Published with product subject id |
| FDE DECISION + «هذا المنتج» / no id | **Suppressed** subject_unidentified / generic_product_language |
| FDE NO_DECISION | **Suppressed** insufficient_evidence (reason recorded) |
| Stale lifecycle | **Suppressed** stale_finding |

## 4. No valid decisions

All candidates suppressed → Workspace quiet band **لا قرار مدعوم حالياً**; Home teaser count=0.
