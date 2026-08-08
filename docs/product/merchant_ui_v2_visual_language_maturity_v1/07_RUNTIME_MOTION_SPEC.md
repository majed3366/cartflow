# Runtime Motion Specification V1

**Scope:** Merchant UI V2 visual language only  
**Principle:** Static motion first. Runtime is scarce and semantic.

## Allowed runtime motions

| Trigger | Selector | Duration | Behavior |
|---------|----------|----------|----------|
| Evidence field paint / refresh | `.cf2-evfield.is-arriving .cf2-evfield__bar` | ≤520ms | Marks join from compressed opacity |
| Primary decision mass paint | `.cf2-dmass.is-forming` | ≤640ms | Soft settle into densified mass |

## Governance

- `prefers-reduced-motion: reduce` → no animation
- Calm, short, functional, interruptible
- Never loops
- Never neon / glow / particles / ambient dashboard motion
- Loading identity = waiting / gathering grammar — not spinner brand

## Not in V1 runtime (deferred until lifecycle hooks exist)

- Recovery continuation animation on real recovery events
- Attention emphasis on new high-priority Home gravity change
- Evidence arrival when live stream of new evidence exists
