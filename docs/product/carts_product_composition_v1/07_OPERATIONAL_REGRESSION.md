# Operational Regression

Gates verified before Living Store deploy:

| Gate | Result |
|------|--------|
| Queue loads from `/api/dashboard/normal-carts` | YES (local 200, one fetch) |
| Filters use existing keys and change the list | YES (all shows 1; يحتاجني is calm empty) |
| Selecting a cart opens detail | YES |
| Primary action mapping unchanged | YES (`wait` on live row) |
| Timeline from proof/lifecycle truth | YES (proof-surface steps) |
| Archive / reopen POST unchanged | YES (endpoints unchanged; archive demoted) |
| Purchase suppresses contact + recovery | YES in code — no local purchased row |
| Attention labels not invented | YES (`بانتظار الإرسال`) |
| Workspace narratives absent | YES |
| VIP config absent | YES |
| Shell / Home / Workspace markers unchanged | YES |
| Contextual `carts: null` (no nav architecture change) | YES |
| No request loops (single fetch per `loadAndPaint`) | YES |
| No horizontal overflow | YES (`overflowX: false`) |

No API or business-logic changes in this composition.
