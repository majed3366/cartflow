# INV-002 WP-4 Brief — Daily Brief Consumer Migration

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package ID | WP-4 |
| Title | Daily Brief → Identity Authority (Phase 4 surface) |
| Severity | Critical |
| Date opened (UTC) | 2026-07-16 |
| Branch | `feature/inv002-wp4` |
| Depends on | WP-1, WP-2, WP-3 approved / delivered |
| Blocked by open questions | None — surface = Daily Brief per WP-02 sequencing |

## 1. Objective

Migrate **Daily Brief** to consume Platform Identity Authority MQIC so Brief never resolves merchant/store identity independently (G-IA-1).

## 2. Scope

### In scope

- `routes/daily_brief.py` — session → Phase 3 MQIC bind
- `services/merchant_daily_brief_v1.py` — `daily_brief_identity_scope` / MQIC tenant key
- `services/identity_authority/daily_brief_consumer_v1.py` — consumer bridge
- Identity Contract Tests for Brief (ICT-12 class)

### Out of scope

- Dashboard/Home composition identity migration
- Timeline / Widget / Setup / Simulator / WhatsApp / Recommendations
- Phase 5 Attach · Phase 6 providers · global middleware
- WP-5
- `main.py` changes

## 3. Frozen contract source

`INV_002_EXECUTION_ARCHITECTURE.md` Phase 4 (per-surface consumer PR); next surface after Knowledge.
