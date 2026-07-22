# Time Authority Model V1

**Status:** Canonical temporal model for CartFlow  
**Owner:** Time Authority Binding Foundation (TABF)  
**Companion:** `time_authority_binding_foundation_v1.md`

## Purpose

One governed vocabulary for time. Every platform layer must declare which clock it consumes. No implicit wall-clock assumptions on Product Performance paths.

## Canonical clocks

| Clock | Meaning | Typical consumers |
|-------|---------|-------------------|
| `event_time` | When the merchant/customer event actually occurred | Truth facts, purchase detection, waiting-period anchors |
| `processing_time` | When CartFlow executed a job / wrote a side effect | Schedulers, recovery due evaluation, cooldowns |
| `observation_time` | As-of instant for reads, assembly, freshness | Evidence, Knowledge, Guidance chain, OTIF, SCF |
| `display_time` | Chronology shown (or implied) to the merchant | MEIF packages, dashboard chronology cues |
| `replay_time` | Frozen as-of for historical / simulation replay | QTC historical/recovery/simulation scopes |

## Resolution precedence (observation / display)

`resolve_bound_as_of_v1(as_of)`:

1. Explicit caller `as_of` (replay / test / probe)
2. Active Query Time Context `authoritative_now`
3. Time Authority `authority_now()` (system or bound provider)

Flag off (`CARTFLOW_TIME_AUTHORITY_BINDING_V1=0`): falls back to wall UTC (legacy).

## Binding rules

- No page-owned freshness or chronology ordering.
- SCF freshness uses `freshness_state_v1(valid_until, as_of)` with bound `as_of` only.
- Event timestamps on facts are preserved; late processing must not reorder merchant-visible event chronology by process time alone.
- When event / observation / action times differ, preserve the distinction internally; expose only when material to understanding.

## Merchant chronology questions

| Question | Clock |
|----------|-------|
| What happened? | Fact / composition content |
| When did it actually happen? | `event_time` |
| When did CartFlow observe it? | `observation_time` |
| When did CartFlow act? | `processing_time` |

## Non-goals

Not analytics, timeline redesign, scheduler rewrite, Knowledge/Guidance business-rule changes, or new merchant features.
