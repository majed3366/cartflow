# Infrastructure decision

| Option | Decision | Evidence |
|---|---|---|
| Larger QueuePool | NOT_JUSTIFIED | Exhaustion was hold + concurrency, not size. Law forbids masking. |
| More API replicas | JUSTIFIED_LATER | After production mixed-surface validation of this model. |
| PgBouncer / proxy | JUSTIFIED_LATER | Only if hold+admission still saturates 5+5 under real 50–100 merchants. |
| Redis | NOT_JUSTIFIED | Not required to fix session-hold or unbounded reads. |
| Worker queue | JUSTIFIED_LATER | Recovery send already has a scheduler; HTTP-held send was the bug. |
| Extra Postgres | NOT_JUSTIFIED | No capacity evidence after application-level fix. |

NEW INFRASTRUCTURE: NOT_JUSTIFIED now.
