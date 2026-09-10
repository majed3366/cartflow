# Zid Dual-Header Auth Restoration V1

**Status:** AUTHORIZED IMPLEMENTATION + CONTROLLED RECONNECT + PROOF  
**Date (UTC):** 2026-09-10  
**General release:** NO  

Manager API headers are built from one store row:

- `Authorization: Bearer <stores.zid_authorization_token>`
- `X-MANAGER-TOKEN: <stores.access_token>`

No `ZID_API_AUTHORIZATION` fallback. Missing either credential fails closed (`zid_manager_auth_incomplete`). Cross-store pairs are rejected.

See `REPORT.md`.
