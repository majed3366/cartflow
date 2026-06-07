# CartFlow WhatsApp Production Strategy Phase 3 — Template Execution Policy

**Date (UTC):** 2026-06-07  
**Phase:** Policy architecture + read-only helpers  
**Commit message:** `whatsapp production strategy phase 3 template execution policy`  
**Status:** Documented (no Meta/send/runtime migration)

**Builds on:** Phase 1 (WhatsApp mode), Phase 2 (template registry + reason mapping), UX cleanup (WhatsApp = transport, `#trigger-templates` = content)

**Explicitly not implemented:** Meta Cloud API, provider migration, recovery runtime migration, delivery truth changes, entitlement enforcement, public send quotas

---

## Executive summary

Phase 3 freezes **what happens after a reason is captured** — the execution policy that governs template selection, timing, follow-ups, stops, VIP isolation, and CartFlow Managed sender guardrails.

| Question | Owner |
|----------|-------|
| **HOW** do we send? | `#whatsapp` — mode, connection, recovery toggle |
| **WHAT** do we send? | `#trigger-templates` — content + stages |
| **WHEN / WHY stop or follow up?** | **This document** + `merchant_whatsapp_template_execution_policy_v1.py` |

**Regression safety:** `RecoverySchedule`, delay logic, `whatsapp_send.py`, VIP alerts, timeline, purchase truth, lifecycle, widget, dashboard carts — **unchanged**. Helpers are read-only.

---

## Part A — Template execution model

Canonical sequence after reason capture:

| Step | Action | Runtime owner today (reference) |
|------|--------|--------------------------------|
| 1 | Reason captured | Widget → `POST /api/cartflow/reason` / cart-event |
| 2 | Select template by `reason_tag` | `merchant_whatsapp_reason_mapping_v1.resolve_template_key_for_reason()` |
| 3 | Apply merchant override if available | `reason_templates_json` (runtime) + `whatsapp_template_overrides_json` (registry layer, future) |
| 4 | Apply timing policy | `Store.recovery_delay*`, `reason_templates.messages[]`, `RecoverySchedule` |
| 5 | Send first recovery message | `whatsapp_send.py` (unchanged this phase) |
| 6 | Wait for customer behavior | Lifecycle / behavioral state |
| 7 | Decide next step | `lifecycle_intelligence.decide_lifecycle_recovery()` + schedule wake |

**Next-step outcomes:** `stop` · `follow_up` · `merchant_intervention` · `archive` · `continuation_handoff`

---

## Part B — Message stages (max 3)

| Stage | Purpose | Registry template |
|-------|---------|-------------------|
| **1** | Reason-specific recovery message | `PRICE_TEMPLATE`, `SHIPPING_TEMPLATE`, … per reason map |
| **2** | General follow-up / reminder | `FOLLOWUP_1_TEMPLATE` |
| **3** | Final follow-up / close | `FOLLOWUP_2_TEMPLATE` |

**Rule:** No more than **3 customer recovery stages** per abandonment sequence. `FOLLOWUP_3_TEMPLATE` reserved for extended library / Meta variants — not a fourth automatic stage in v1 policy.

Merchant multi-message editor (`#trigger-templates`) may define up to 3 timed messages per reason — policy aligns stage index with schedule attempt, not duplicate sends of identical copy.

---

## Part C — Hard stop conditions

When any condition is true, **normal customer recovery sequence stops** (no further scheduled stages):

| Stop reason key | Trigger |
|-----------------|---------|
| `customer_purchased` | Purchase truth / conversion |
| `customer_replied_positive` | Positive WhatsApp reply intent |
| `customer_declined` | Explicit stop / negative intent |
| `customer_returned` | Return-to-site behavioral signal |
| `merchant_archived` | Merchant archived cart |
| `recovery_expired` | Schedule cap / expiry |
| `template_disabled` | Reason or stage template disabled with no allowed fallback |
| `store_whatsapp_disabled` | `whatsapp_recovery_enabled=false` |
| `provider_unavailable` | Provider gate / ops pause |
| `sequence_complete` | All 3 stages exhausted with no qualifying behavior |

**Precedence (aligned with lifecycle audits):** purchase → reply → return → merchant archive → expiry → template/provider gates.

---

## Part D — Follow-up policy

| Customer signal | Policy |
|-----------------|--------|
| No response after stage 1 | May advance to stage 2 |
| No response after stage 2 | May advance to stage 3 |
| No response after stage 3 | **Stop** (`sequence_complete`) |
| Customer replies | **Stop** normal sequence → continuation / merchant handoff |
| Customer returns to site | **Stop** sequence (anti-spam) |
| Purchase detected | **Close** recovery immediately |

Continuation path is separate from staged recovery templates — uses bounded reply automation, not merchant freeform stage 2/3 copy.

---

## Part E — VIP policy

| Rule | Value |
|------|-------|
| VIP alert audience | **Merchant** (not customer recovery) |
| Counts as customer recovery message | **Never** |
| Replaces normal recovery by default | **No** — unless explicit merchant setting (future) |
| Triggers | Merchant intervention path when VIP threshold + notify enabled |
| Lane isolation | VIP must not share customer `reason_tag`, stage counters, or recovery `sent_count` |
| Template | `VIP_ALERT_TEMPLATE` only |

Reference: `vip_merchant_alert.py`, `vip_operational_truth_v1.py`.

---

## Part F — CartFlow Managed sender policy

Internal fair-usage controls — **not exposed as public quota** in this phase:

| Control | Behavior |
|---------|----------|
| Daily store send guard | Internal cap per store per day — skip with `daily_store_send_guard` |
| Repeated failure suppression | Cooldown after provider failures |
| Provider unavailable skip | No open retry storm |
| No open-ended retries | Max 3 stages + schedule caps |
| Template disabled skip | Clear skip reason, no silent send |

Mode: `whatsapp_mode=cartflow_managed` (Phase 1). Enforcement wiring is **future** — policy defined here.

---

## Part G — Template disabled policy

When reason template is disabled (`reason_templates.enabled=false` or registry override):

1. **Do not send** reason-specific message for that reason.
2. If policy allows: fallback to `UNKNOWN_REASON_TEMPLATE`.
3. If fallback not allowed: **skip** with `template_disabled` / `unknown_fallback_not_allowed`.
4. Log skip reason for ops (today: `[TEMPLATE SKIPPED]` in `reason_template_recovery.py`).

Stage 2/3 follow-ups: if follow-up registry entry disabled → stop sequence for that cart.

---

## Part H — Admin / operations visibility (architecture)

Future admin row fields (read-only policy schema):

- `selected_template`
- `execution_stage`
- `stop_reason`
- `skip_reason`
- `provider_status`
- `next_action`
- `whatsapp_mode`
- `future_meta_template_status`

**API (architecture):** `GET /api/admin/whatsapp/execution-policy` — exports frozen policy vocabulary.

---

## Implementation reference

| Module | Role |
|--------|------|
| `merchant_whatsapp_template_execution_policy_v1.py` | Read-only policy helpers + API export |
| `merchant_whatsapp_reason_mapping_v1.py` | Stage 1 template selection |
| `merchant_whatsapp_template_registry_v1.py` | Canonical keys + Meta-ready metadata |
| `lifecycle_intelligence.py` | Behavioral stop / handoff decisions (existing) |
| `reason_template_recovery.py` | Template disabled gate (existing runtime) |

**Tests:** `tests/test_merchant_whatsapp_template_execution_policy_v1.py`

---

## Next phases (out of scope)

- Wire policy helpers into send path as single decision owner
- Meta approved-template enforcement per stage
- Admin per-cart execution trace UI
- Public plan quotas for Managed sender
