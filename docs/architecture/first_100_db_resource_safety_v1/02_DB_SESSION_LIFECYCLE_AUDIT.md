# DB session lifecycle audit

Default HTTP pattern at `58a82f3`:

- Session created lazily via `db.session` (scoped_session).
- First checkout is often merchant-auth cookie resolve, then the route.
- Session is released only in `db_scoped_session_cleanup` `finally`.
- Hold time ≈ request duration after first checkout, not query time.

| Family | Session | Hold until response | Network while held (before this change) | Bound |
|---|---|---|---|---|
| Home summary | scoped | yes | no | snapshot / windowed KPI |
| Workspace projection | scoped | yes | no | unknown on enrich_fallback |
| Carts normal-carts | scoped | yes | no | page 50–250; some bulk `.all()` |
| Messages / followups | scoped, always live | yes | no | 40 / 50; reply map was unbounded |
| Settings | scoped | yes | no | yes |
| Auth / OAuth | scoped | yes | yes (Zid) | yes |
| /ping | none | n/a | no | n/a |
| /health?db=1 | scoped | brief | no | SELECT 1; could wait 5s on exhausted pool |
| cart-event / recovery execute | scoped | high | yes (WhatsApp/Meta) | yes |
| Scanner execute | scoped begin | high | yes (no release before send) | limit 25 |
| Delay dispatcher | scoped | low | released before sleep | yes |

`isolated_db_session()` existed but was unused on hot paths.
