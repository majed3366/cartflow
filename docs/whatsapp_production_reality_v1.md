# WhatsApp Production Reality v1 — Audit

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit before onboarding real merchants. **No** new provider implementation, **no** send/runtime changes.  
**Commit:** `audit: verify whatsapp production reality v1`

---

## Executive verdict

| Verdict | Meaning |
|---------|---------|
| **WhatsApp Production Readiness: PARTIAL** | CartFlow can run **demo / sandbox / mock** recovery today; **real merchant WhatsApp at scale** needs provider onboarding, template policy, per-store config, delivery webhooks, and ops visibility — mostly **documented gaps**, not hidden failures. |

**Safe now (with ops discipline):** internal demo, Twilio sandbox with joined recipients, mock sends when `PRODUCTION_MODE` off, inbound reply → continuation path on Twilio webhook form POST.

**Not production-ready for arbitrary merchants:** per-merchant WABA ownership, Meta Cloud send path, WhatsApp template approval for outbound recovery, delivery status reconciliation, store-level provider credentials, merchant self-serve connect flow.

---

## Audit matrix

### 1. WhatsApp provider model

| | Detail |
|---|--------|
| **Current state** | **Twilio-first:** `services/whatsapp_send.py` → Twilio REST `Client.messages.create`. Real send only when `PRODUCTION_MODE` truthy **and** `TWILIO_*` env complete (`recovery_uses_real_whatsapp()`). Otherwise **mock** (`send_whatsapp_mock`). **Meta:** `get_meta_readiness()` in `cartflow_provider_readiness.py` — placeholder (`meta_path_not_active`, `ready: false`). No Graph send module. **Abstraction:** partial — readiness + failure classification (`classify_provider_failure`), not a swappable `ProviderAdapter` interface. **Queue:** `whatsapp_queue.py` alternate path with bounded retry (`failed_retry` → `failed_final`); primary recovery path often sends **synchronously** in `main._run_recovery_sequence_after_cart_abandoned_impl`. |
| **Risk** | Operators assume “WhatsApp works” because UI shows recovery enabled; production may still be mock. Meta env vars could be set but never used. Two send paths (sync vs queue) complicate failure ops. |
| **Required production behavior** | Single documented primary send path; provider interface with Twilio + Meta implementations; explicit mode per environment (sandbox / production). |
| **Gap** | No Meta send; no formal provider adapter; merchant `whatsapp_provider_mode` on `Store` is **display/persist only** — runtime uses platform env Twilio. |
| **Priority** | **P0** Meta/Twilio strategy; **P1** adapter boundary |

### 2. Merchant WhatsApp ownership

| Case | Recommended onboarding path (v1 doc only) |
|------|-------------------------------------------|
| **Normal WhatsApp (consumer app)** | **Not supported** for API recovery at scale. Path: migrate merchant to **WhatsApp Business Platform** (Meta) or use **Twilio ISV / hosted** model with CartFlow-owned sender until per-merchant WABA. |
| **WhatsApp Business app** | Same as above — app-only number cannot power CartFlow server sends without Cloud API registration. Onboarding: explain upgrade to Cloud API + verify business. |
| **WhatsApp Business Platform / Meta** | Future: OAuth + WABA + `phone_number_id` per store. CartFlow stores `wa_phone_id`, `wa_business_id`, template namespace. |
| **No WhatsApp setup** | Keep **widget + reason capture**; disable `whatsapp_recovery_enabled`; show merchant readiness card (`merchant_whatsapp_readiness_ui.py`) — “الواتساب غير مفعل”. |

| | Detail |
|---|--------|
| **Current state** | Platform-level Twilio credentials; `Store.store_whatsapp_number`, `whatsapp_support_url`, `whatsapp_recovery_enabled`, `whatsapp_provider_mode` (sandbox/test/production labels). |
| **Risk** | Merchant believes their dashboard “production mode” controls real sends — it does **not** wire to Twilio account selection. |
| **Gap** | No per-merchant provider account linking. |
| **Priority** | **P1** ownership model + legal/compliance copy |

### 3. Template approval reality

| Message type | Current state | Approval risk |
|--------------|---------------|---------------|
| **Recovery (first outbound)** | Merchant-editable text via `reason_templates_json`, `Store.template_*` columns, `resolve_recovery_whatsapp_message_with_reason_templates` — **session/custom body**, not Meta template IDs in code. | **High** outside 24h window: WhatsApp requires **approved templates** for business-initiated messages. Twilio sandbox may allow lax testing; production WABA will reject unapproved shapes. |
| **Reminder / multi-slot** | `recovery_multi_message` slots from templates with delays. | Same — each outbound touch may need template registration if outside session. |
| **Follow-up / continuation** | `cartflow_reply_intent_engine` sends after inbound — typically **session message** if customer replied within 24h. | Lower **if** inbound opened session; still content-policy risk. |
| **Dynamic variables** | Reason tags, product names, prices interpolated into free text in recovery path. | Variable placeholders must match **approved template** definitions on Meta. |
| **Language** | Arabic-first copy in templates and engine. | Templates must be submitted in AR (and EN if needed) per WABA locale. |

| | Detail |
|---|--------|
| **Risk** | First production merchant blast uses custom strings → mass `template_not_approved` / 63013-class failures (`FAILURE_TEMPLATE_NOT_APPROVED` in provider readiness). |
| **Required production behavior** | Template catalog per store, status `approved/pending/rejected`, send only approved names; map reason_tag → template_id. |
| **Gap** | No template_id layer; no approval sync; readiness mentions template class but no enforcement before send. |
| **Priority** | **P0** before broad merchant launch |

### 4. 24-hour customer service window

| | Detail |
|---|--------|
| **Current state** | **Not modeled in code.** Inbound: `POST /webhook/whatsapp` (Twilio form: `Body`, `From`) → reply intent + behavioral + positive reply. Continuation auto-reply when `CARTFLOW_CONTINUATION_AUTO_REPLY` enabled and cooldown/dedup pass. Outbound recovery ignores window — uses delay/attempt gates only. |
| **Risk** | Recovery or continuation send **after 24h** without customer message → provider rejection; ops blames “CartFlow bug”. |
| **Required production behavior** | Track `last_customer_message_at`; classify outbound as `template_required` vs `session_allowed`; block or route template sends. |
| **Gap** | No window state machine; no template-vs-session send router. |
| **Priority** | **P0** for Meta-compliant production |

### 5. Deliverability and provider failures

| | Detail |
|---|--------|
| **Current state** | Send result: `ok` + Twilio `sid`/`status` in `send_whatsapp` return dict; failures logged + Sentry `capture_whatsapp_failure`. `CartRecoveryLog.status`: `sent_real`, `mock_sent`, `whatsapp_failed`, `skipped`, `queued`, `failed_retry`, `failed_final`. **Idempotency:** `recovery_whatsapp_idempotency.py` blocks duplicate `sent_real`/`mock_sent`/`queued` per step/session. **Retries:** queue worker retries failed sends up to max (env backoff); **not** blind infinite — tests assert `failed_final`. **Webhooks:** inbound reply only; **no** Twilio status callback handler for `delivered`/`failed`/`read` in repo grep. |
| **Risk** | “Sent” in logs ≠ delivered; no automatic reconciliation; retries on provider-hard-fail may annoy providers (queue retries exist). |
| **Required production behavior** | Status webhooks → update `CartRecoveryLog` / MessageLog; no retry on permanent failures (630xx, invalid number); ops alert on spike. |
| **Gap** | Delivery webhook readiness **missing**; delivered/read not first-class. |
| **Priority** | **P1** status webhooks; **P2** delivered metrics |

### 6. Store-level provider settings (future structure — audit only)

| Field | Exists today? | Notes |
|-------|---------------|-------|
| `provider_type` | ❌ | Platform Twilio only at runtime |
| `provider_status` | Partial | `whatsapp_provider_mode`, onboarding flags |
| `wa_phone_id` | ❌ | Meta Cloud future |
| `wa_business_id` | ❌ | Meta Cloud future |
| `template_status` | ❌ | No per-template rows |
| `sandbox` / `production` mode | Partial | Env `PRODUCTION_MODE` + store `whatsapp_provider_mode` (not wired to send) |
| `last_provider_error` | Partial | Failure class via `classify_provider_failure`; not persisted per store |

**Recommendation:** add nullable columns or `store_integration_settings` JSON in a later migration — **not in this audit commit**.

### 7. Operational visibility

| | Detail |
|---|--------|
| **Current state** | Admin: `/admin/operational-health` — provider slice via runtime snapshot + `get_whatsapp_provider_readiness()` in production-readiness report. Merchant: `whatsapp_readiness_card` (Arabic, no provider names). Logs: `[CARTFLOW PROVIDER]`, `[WA SENT]`, `[WA STATUS]`, idempotency tags. |
| **Required (eventually)** | Admin: WhatsApp healthy?, provider connected?, templates approved?, failed sends count, affected stores, recommended action. |
| **Gap** | No centralized “templates approved” or per-store WA health dashboard; failed send aggregation partial (`CartRecoveryLog` only). |
| **Priority** | **P2** admin WA panel |

### 8. Safety controls (Operational Control v1)

| Control | Compatible? |
|---------|-------------|
| **Pause WA** | ✅ `operational_control_v1` gates `send_whatsapp` / mock |
| **Pause provider** | ✅ `provider_paused` blocks Twilio path |
| **Store / reason pause** | ✅ scoped gates |
| **No duplicate sends** | ✅ `recovery_whatsapp_idempotency` + `cartflow_duplicate_guard` |

| | Detail |
|---|--------|
| **Risk** | Ops controls are **in-process** — multi-worker split brain without shared store. |
| **Priority** | **P2** durable ops flags |

### 9. Production onboarding (not implemented)

Target flow (document only): connect WhatsApp → verify number → choose mode → test send → go live.

**Current:** merchant settings page + readiness card + demo paths; no OAuth, no test-send API bound to merchant credentials.

### 10. Cost / scale risks (categories only)

| Category | Considerations |
|----------|----------------|
| **Message cost** | Per conversation / per template category (marketing vs utility) — Meta pricing; Twilio markup. |
| **Provider cost** | Twilio fees + potential Meta direct billing if migrated. |
| **Template limitations** | Approval latency; variable caps; locale copies. |
| **Support burden** | Sandbox join steps, “message not received”, template rejects. |
| **Onboarding burden** | WABA verification, display name, quality rating. |

No pricing finalized in this audit.

---

## Provider options (summary)

| Option | Fit today | Notes |
|--------|-----------|-------|
| **Twilio WhatsApp API** | ✅ Implemented | Sandbox for dev; production = env + `PRODUCTION_MODE`. |
| **Meta Cloud API direct** | ❌ Not implemented | Readiness stub only. |
| **BSP / ISV** | ❌ | Future partner model. |

---

## Phased rollout plan

| Phase | Goal | Blockers addressed |
|-------|------|-------------------|
| **0 — Now** | Demo + internal merchants on sandbox/mock | Ops runbook, `GET /dev/production-readiness` |
| **1** | Template catalog + approval gate before first outbound | P0 template risk |
| **2** | 24h window + session vs template router | P0 policy |
| **3** | Delivery status webhooks + no retry on hard fail | P1 deliverability |
| **4** | Per-store provider settings + merchant connect UI | P1 ownership |
| **5** | Meta Cloud adapter (optional Twilio coexistence) | P0 provider strategy |

---

## Launch blockers (real merchants)

1. **Approved WhatsApp templates** (or provable session-only outbound) for recovery copy.  
2. **Production Twilio or Meta** credentials scoped to merchant/legal entity — not shared sandbox forever.  
3. **24-hour window policy** implemented or ops manual procedure until coded.  
4. **Delivery/status visibility** — at minimum failed-send alerting.  
5. **Clarify** merchant dashboard `whatsapp_provider_mode` vs platform `PRODUCTION_MODE`.  
6. **Runbook** for Operational Control pause WA/provider during incidents.

---

## Gaps summary

### Closed gaps ✅

- Twilio send path exists with production gate (`recovery_uses_real_whatsapp`).  
- Mock path for non-production (no accidental Twilio bill if env incomplete).  
- Provider readiness report (`cartflow_provider_readiness.py`) + failure classification.  
- Inbound webhook for replies → continuation / intent.  
- WA send idempotency + duplicate guard + operational pause gates.  
- Merchant readiness card (Arabic, actionable).  
- Production readiness env checklist documented (`cartflow_production_readiness.md`).

### Remaining gaps 🟡

- Meta Cloud send path.  
- Formal provider abstraction.  
- Per-store provider credentials and template registry.  
- 24-hour window modeling.  
- Delivery status webhooks.  
- Admin “WhatsApp ops” consolidated view.  
- Merchant self-serve connect / test-send / go-live.  
- Store `whatsapp_provider_mode` wired to runtime.

### Dangerous gaps 🔴

- **Custom free-text recovery** to cold users without template approval → mass provider rejection at launch.  
- **Assuming `sent_real` = delivered** without status callbacks.  
- **Shared platform Twilio** for all merchants without compliance review.  
- **Queue retry** on permanent failures (may exist for transient only — ops must monitor `failed_final`).  
- **Multi-worker ops controls** for WA pause (split brain).

---

## Code map (audit references)

| Area | Path |
|------|------|
| Send | `services/whatsapp_send.py` |
| Queue / retry | `services/whatsapp_queue.py` |
| Provider readiness | `services/cartflow_provider_readiness.py` |
| Production report | `services/cartflow_production_readiness.py` |
| Idempotency | `services/recovery_whatsapp_idempotency.py` |
| Inbound | `main.py` `POST /webhook/whatsapp` |
| Merchant settings | `services/merchant_whatsapp_settings.py` |
| Templates | `services/reason_template_recovery.py`, `Store.template_*` |
| Ops pause | `services/operational_control_v1.py` |
| Logs | `CartRecoveryLog`, `MessageLog` |

---

## Verification (no runtime change)

```bash
python -m pytest tests/test_whatsapp_production_reality_audit_v1.py -q
python -c "import main; print('import_ok')"
```

**Deploy PASS:** recovery messages unchanged; no new outbound HTTP from audit code; Twilio path identical.

**Staging smoke:** trigger recovery with `PRODUCTION_MODE` + Twilio → `[WA SENT]`; purchase truth unchanged; no new provider SDK calls from audit module.
