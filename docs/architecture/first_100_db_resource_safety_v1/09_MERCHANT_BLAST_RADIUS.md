# Merchant blast radius

**Before:** YES. One merchant with two tabs (Workspace + Communication) can issue projection + messages + followups + summary concurrently. That is four live DB-bound requests. A second merchant doing the same saturates 5+5.

**Minimum current-architecture protections (implemented):**

1. Keep inactive surfaces at zero startup work (`58a82f3` law).
2. Heavy-route admission: global 4, per-route 2. Extra heavy work degrades itself (503 `db_pressure` or quiet projection).
3. Release-before-wait so send/OAuth cannot pin a connection for the network RTT.
4. Bound the largest live bulk reads.

This does not give hard multi-tenant isolation. It makes one merchant materially less able to take the whole pool.

ONE-MERCHANT BLAST RADIUS: CONTROLLED (application admission + bounds; not a separate pool).
