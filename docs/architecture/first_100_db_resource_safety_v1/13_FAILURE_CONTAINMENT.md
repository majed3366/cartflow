# Failure containment

Chosen mechanism (evidence-based, minimum):

**Per-route + global heavy-read admission** (`admission_v1`).

A heavy request that cannot acquire a slot degrades itself (`db_pressure`) instead of waiting on QueuePool timeout and blocking unrelated merchants.

Rejected for V1: larger pool, proxy, Redis, worker queue, per-merchant pools.
