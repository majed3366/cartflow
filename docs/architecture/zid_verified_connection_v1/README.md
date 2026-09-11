# Zid Verified Connection V1

**Status:** AUTHORIZED IMPLEMENTATION + TESTS + EXACT-SHA DEPLOY  
**Date (UTC):** 2026-09-11  
**General release:** NO  
**Ready for Level 3:** NO  

CartFlow must never show **تم الربط** because `access_token` exists.

For Zid, CONNECTED means the connection is actually usable. Canonical owner is `services/merchant_connection_capability_v1.py`. Zid Manager probe + identity bind live only in the Zid adapter (`services/zid_connection_verification_v1.py`).

See `REPORT.md`.
