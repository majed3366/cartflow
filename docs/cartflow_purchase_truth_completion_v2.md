# Purchase Truth Completion v2

**Date:** 2026-05-19  
**Commit:** `fix: complete durable purchase truth v2`

## Goal

Make purchase truth **durable and canonical** across all purchase sources, align lifecycle precedence, and ensure merchant/admin read paths prefer `purchase_truth_records` over stale `queued` / `sent` logs.

## What changed

### PART 1 — Canonical ingestion

Single entry: `services/purchase_truth.ingest_purchase_truth(...)`.

All verified paths route through it:

| Path | Source label |
|------|----------------|
| `POST /api/conversion` | `purchase_completed`, `order_paid`, … |
| Cart-event / `user_converted` | via `ingest_purchase_truth_payload` |
| Platform gateway | `ingest_purchase_truth_payload` |
| **`POST /webhook/zid`** (new) | `zid_webhook:order_paid` / `purchase_completed` |
| Manual / dev | `POST /dev/purchase-truth-test` |

**Proof log:**

```
[PURCHASE TRUTH INGESTED]
source=
recovery_key=
order=
store=
truth_written=true|false
```

### PART 2 — Reply PURCHASE → durable (low confidence)

`ingest_purchase_truth_from_reply_claim(...)` with `purchase_source=reply_purchase_claim` and `confidence=low|medium` in `evidence_detail`.

Not treated as `order_paid` (no full attribution run).

**Proof log:**

```
[PURCHASE TRUTH FROM REPLY]
confidence=low|medium
truth_written=true
```

Wired from `run_inbound_whatsapp_reply_intent_hook` when lifecycle intent is `PURCHASE`.

### PART 3 — Unified precedence

**All evaluators:** `purchase > reply > return > waiting > send`

- `services/lifecycle_intelligence.resolve_lifecycle_behavior` — reply before return (fixed v2 mismatch).
- `services/cartflow_lifecycle_truth.evaluate_lifecycle_truth` — unchanged canonical order.

**Audit log:**

```
[LIFECYCLE PRECEDENCE] winner=customer_replied candidates=purchase:false,reply:true,return:true,...
```

### PART 4 — Dashboard / diagnostics alignment

`lifecycle_purchased_evidence(..., recovery_key=)` checks `has_purchase(recovery_key)` **first**.

`build_merchant_recovery_lifecycle_truth` passes store slug → recovery key → purchased wins over `queued` in logs.

Admin diagnostics already overrides to `recovery_stopped_purchase` when `has_purchase` (unchanged).

### PART 5 — Durable closure

Table: `lifecycle_closure_records` (`LifecycleClosureRecord`).

Canonical statuses: `purchase_completed`, `returned_to_site`, `replied`, `failed`, `cancelled`.

Fields: `closure_reason`, `closure_time`, `closure_source`.

Written on verified purchase ingest and purchase lifecycle closure.

## Acceptance scenarios (automated)

| ID | Scenario | Result |
|----|----------|--------|
| A | Purchase before send | Truth + closure row; `[PURCHASE TRUTH INGESTED]` |
| B | Purchase after send | Dashboard `purchased` beats `queued` |
| C | Reply «اشتريت» | `reply_purchase_claim`, `confidence=low` |
| D | `queued` + purchase | `lifecycle_status=purchased` |
| E | Restart | `has_purchase` from DB after memory reset |

Tests: `tests/test_purchase_truth_completion_v2.py` (42 related lifecycle/purchase tests pass).

## Remaining gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| Zid adapter still scaffold | Medium | Webhook uses `zid_webhook_purchase_v2` heuristic mapping, not full `ZidAdapter.normalize_event` |
| Return/reply/failed durable closure | Low | Only `purchase_completed` wired to `lifecycle_closure_records` in v2; extend hooks for `returned_to_site` / `replied` / `failed` at behavioral sites |
| Reply claim vs platform order | Medium | `reply_purchase_claim` may precede late `order_paid`; upsert upgrades source on stronger ingest |
| KPI “recovered” vs purchase truth | Low | Separate KPI path; purchase truth stops recovery, KPI may lag |
| Cross-store recovery_key mismatch | Medium | Zid webhook must include same `session_id` / cart id as widget abandon |

## Confidence

| Area | Confidence |
|------|------------|
| Canonical ingest + logs | **High** — unit tests + existing v1 chain |
| Zid webhook ingest | **Medium** — event-name heuristics; needs live Zid payload validation |
| Dashboard purchased display | **High** — `has_purchase` in merchant lifecycle builder |
| Precedence alignment | **High** — intelligence + canonical tests |
| Durable closure completeness | **Medium** — purchase path only in v2 |

## Proof commands

```bash
python -m pytest tests/test_purchase_truth_completion_v2.py tests/test_purchase_truth_lifecycle_v1.py tests/test_cartflow_lifecycle_truth_v1.py tests/test_lifecycle_intelligence.py -q
```
