# CartFlow lifecycle consistency and state conflicts

Operational hardening layer: canonical precedence, transition validation (diagnostics), dashboard truth reconciliation, and safe behavioral merges. It does **not** replace the decision engine, recovery scheduler, duplicate-prevention module, identity safeguards, WhatsApp templates, or observability package entry points.

## Lifecycle model (canonical)

Abstract states used for precedence and validation (not 1:1 with DB rows):

| State | Meaning |
|-------|---------|
| `abandoned` | Baseline / pending outreach |
| `waiting_delay` | Delay gate not satisfied |
| `queued` | Logged as queued before provider |
| `send_started` | In-flight send window (logical) |
| `sent` | Successful delivery logged |
| `replied` | Customer engagement stops automation |
| `returned` | Return-to-site anti-spam / softer pressure |
| `converted` | Purchase / recovery complete |
| `stopped` | Manual or policy stop |
| `failed` | Provider failure |
| `duplicate_blocked` | Duplicate attempt blocked |

Mapping helpers translate `CartRecoveryLog.status`, dashboard `phase_key`, and `cf_behavioral` hints into these states where needed.

## Precedence (higher wins)

When two UI signals disagree (e.g. “sent” banner vs duplicate skip, or conversion vs send celebration), the higher precedence signal is treated as **authoritative** for merchant-visible hints:

1. **Converted** and hard **stopped**
2. **Replied**
3. **Returned**
4. **Sent**
5. **Failed** / **duplicate_blocked** / queue / delay / abandoned

Implemented in `services/cartflow_lifecycle_guard.py` (`_PRECEDENCE`, `reconcile_normal_recovery_dashboard_hints`).

## Terminal states

`converted` and certain **stopped** paths are terminal for automation-focused narratives. **`replied`** and **`returned`** are strong engagement terminals for suppression of pressure messaging. **`sent`** is not terminal for the whole journey (follow-ups may exist) but dominates duplicate-only noise in the dashboard.

## Transition matrix

`is_valid_transition(current, next)` encodes allowed progressions (diagnostics / tests). **Invalid pairs** such as `sent_after_conversion`, `send_after_reply`, and `send_after_return` generate:

- `[CARTFLOW LIFECYCLE]` lines (`type=invalid_transition`, `lifecycle_precedence_applied`, …)
- `[CARTFLOW STATE CONFLICT]` lines (`type=duplicate_terminal_state`, …)
- Buffered `impossible_state_transition` anomalies via `record_runtime_anomaly` (no silent repair of recovery data)

## Merge rules (`cf_behavioral`)

`merge_behavioral_state` prunes incoming patches that would **weaken** true engagement flags (`customer_replied`, return flags, link click) or downgrade a **stronger** `lifecycle_hint`. This reduces stale frontend or duplicate events overwriting stronger terminal truth.

## Async overlap handling

Delayed tasks and overlapping HTTP events can interleave log rows. Guard principles:

- Dashboard reconciliation **drops** contradictory **blocker** surfaces when aggregate state is strictly stronger (e.g. duplicate banner after a confirmed send count).
- Sequence celebration text can be cleared when **conversion** phase / purchase blocker dominates.
- No automatic DB rewrite — display-layer and merge-layer only.

## Dashboard truth rules

`main._normal_recovery_phase_steps_payload` calls `reconcile_normal_recovery_dashboard_hints` before composing blocker hints. Optional telemetry: `normal_recovery_lifecycle_notes` (internal reconciliation codes; still no raw engine enums in merchant labels).

## Runtime health

`build_runtime_health_snapshot()` includes **`lifecycle_consistency_runtime`** (counts, `lifecycle_runtime_ok`, `lifecycle_conflict_detected`, `invalid_transition_recently`). Trust derivation treats unhealthy lifecycle signals like other runtime degradations.

## Merchant-safe wording

Arabic hints such as «تم تجاهل حالة غير متوافقة» and «تم إيقاف الرسائل بعد تفاعل العميل» are chosen to avoid internal state names.

## Known limitations

- All bookkeeping is **in-process**; multi-instance deployments can still observe ordering surprises until a shared lifecycle store exists.
- Transition validation is **diagnostic**; it does not roll back or rewrite `CartRecoveryLog`.
- Precedence cannot fix incorrect historical data — only how the dashboard **surfaces** it.

## Future queue / worker implications

- Workers should reuse the same canonical state strings in logs for correlation.
- Idempotency keys for lifecycle side-effects should be persisted (Redis/DB) if execution moves off the web process.
- Merge rules should remain **monotonic** on terminal engagement flags.
