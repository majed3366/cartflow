# CartFlow identity model

## Canonical store / session / cart

Runtime recovery treats three fields as **joined identities**, not loose metadata:

- **store** — resolved from widget slug via a single loader (`_load_store_row_for_recovery`), surfaced to events through `resolve_store_pk_for_event_slug` and `identity_snapshot_from_payload`.
- **session** — `recovery_session_id` / widget `session_id` (normalized in `main` helpers).
- **cart** — `zid_cart_id` / widget `cart_id` (normalized in `main` helpers).

If the storefront sends a slug that resolves to store **A** while an abandoned row is tied to store **B**, behavioral merges must **not** copy return-to-site state onto the wrong row. Silent skips are forbidden where drift is detectable: operations log `[CARTFLOW IDENTITY WARNING]` and, where appropriate, mark a merchant-safe trust flag (see below).

## Why it matters

Identity drift looks like a healthy pipeline (events accepted, dashboard loads) while **behavioral state attaches to a different cart or store**. Merchants lose trust because metrics and automation no longer describe the same real cart.

## Behavioral merge rules (return-to-site)

Implemented in `services/behavioral_recovery/user_return.py` with helpers in `services/cartflow_identity.py`:

1. Resolve expected store PK from the event slug when possible; if missing, infer **only** when all non-VIP candidate rows agree on `store_id`.
2. If inference is **ambiguous** (multiple stores among candidates), **do not merge**; log `behavioral_merge_blocked_ambiguous_store_scope`, set identity trust failure on a representative row, commit, return.
3. For each candidate row, `should_merge_behavioral_for_store` blocks when the row’s `store_id` contradicts the expected PK (except `store_id` **NULL**, which still merges for legacy rows).
4. If every row was skipped for store mismatch, log `behavioral_merge_skipped_all_rows_store_mismatch`, set trust failure, commit.
5. A successful merge clears `identity_trust_failed` / `identity_trust_message_ar` on merged rows so recovery from transient misconfiguration is possible.

## Store / session / cart invariants

- **Store PK** for events should come from **one code path** (`resolve_store_pk_for_event_slug` / `identity_snapshot_from_payload`), not ad-hoc queries.
- **Dashboard trust surface** (`_normal_recovery_identity_trust_surface`): reads persisted trust failure; otherwise runs `detect_abandoned_cart_identity_anomaly` for the row’s session/cart (non-VIP scope).
- **Anomaly detection** flags:
  - multiple non-VIP rows for the same `(session_id, zid_cart_id)` if the DB ever allows it;
  - **multiple distinct `store_id` values** among non-VIP rows reachable via `abandoned_carts_for_session_or_cart`.

Merchant-visible copy is fixed Arabic text **«تعذر ربط بيانات السلة»** (no internal reason strings in the UI payload).

## Observability

Structured operational logs use the banner **`[CARTFLOW IDENTITY WARNING]`** with fields:

`store_slug`, `resolved_store_id`, `expected_store_id`, `session_id`, `cart_id`, `reason`.

Reasons include `behavioral_merge_skipped:*`, `behavioral_merge_blocked_*`, `dashboard_identity_anomaly:*`, etc.

## Known limitations

- **`zid_cart_id` is unique** in the current schema, so “duplicate abandoned row same session+cart” is only reachable if that constraint changes or in tests that bypass the ORM.
- **Legacy rows** with `store_id` NULL still merge; operators should backfill `store_id` for stricter guarantees.
- **Other endpoints** that upsert abandons or process cart events should prefer `identity_snapshot_from_payload` when adding new store-resolution logic; this document does not list every call site.
