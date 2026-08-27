# Operational Regression

Gates verified before Living Store deploy:

| Gate | Result |
|------|--------|
| Queue loads from `/api/dashboard/normal-carts` | YES (local + unit) |
| Filters use existing keys and change the list | YES |
| Selecting a cart opens detail | YES |
| Primary action mapping unchanged | YES (same keys / purchase override) |
| Timeline from proof/lifecycle truth | YES |
| Archive / reopen POST unchanged | YES |
| Purchase suppresses contact + recovery | YES |
| Attention labels not invented | YES |
| Workspace narratives absent | YES |
| VIP config absent | YES |
| Shell / Home / Workspace markers unchanged | YES |
| Contextual `carts: null` (no nav architecture change) | YES |
| No request loops (single fetch per `loadAndPaint`) | YES |
| No horizontal overflow (CSS + mobile probe) | YES (`overflowX: false`) |

No API or business-logic changes in this composition.
