# WhatsApp Template / 24h Enforcement Audit v1

**Date (UTC):** 2026-05-19  
**Scope:** Read-only audit + minimal production send guard. **No** Meta implementation, **no** new provider, **no** full template manager, **no** recovery/lifecycle/widget/purchase-truth changes.  
**Commit message:** `fix: enforce whatsapp template window guard`

**Related:** `docs/cartflow_whatsapp_production_readiness_audit_v1.md`, `services/whatsapp_production_reality_v2.py`, `services/whatsapp_send.py`

---

## Executive question

**Can CartFlow accidentally send a freeform recovery message outside the 24h window?**

| Before guard | **Yes** — sync Twilio path sent freeform `body` with only observe logs |
| After guard (production) | **No** — blocked when `template_required` and no provider-approved template signal |
| Sandbox | **Unchanged** — mock/Twilio test without production gate block |

---

## 1. Current enforcement map (post-fix)

| Send mode | Entry | Template required? | Template selected? | Window checked? | Blocked if invalid? |
|-----------|-------|-------------------|-------------------|-----------------|---------------------|
| **Sandbox** | `send_whatsapp` / `send_whatsapp_mock` | Logged only | Local JSON (copy) | Yes (`evaluate_conversation_window`) | **No** |
| **Twilio production** | `send_whatsapp` when `recovery_uses_real_whatsapp()` | Yes if outside/unknown 24h | **No** provider template ID — freeform `body` | Yes | **Yes** (v1 guard) |
| **Meta / manual** | `main.send_whatsapp_message` (Graph CTA) | N/A (interactive) | CTA payload | **No** | **No** (out of scope) |
| **Queue** | `whatsapp_queue._one_send` → `send_whatsapp_real` / mock | Same as Twilio path | Same | Same | **Yes** when `use_real` + production |
| **Sync recovery** | `main._run_recovery_sequence_after_cart_abandoned_impl` → `send_whatsapp` | Same | `resolve_recovery_whatsapp_message_with_reason_templates` (freeform text) | Same | **Yes** in production |

### Provider-approved template signal (v1 minimal)

| Signal | Meaning |
|--------|---------|
| `CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED=1` | Ops confirms Meta/Twilio templates approved |
| `Store.whatsapp_provider_templates_approved` (optional future column) | Per-store flag |
| `reason_templates_json` present | **Not** treated as provider approval |

---

## 2. Risk classification

| Scenario | Verdict | Notes |
|----------|---------|-------|
| **Cold abandoned cart** (no inbound) | **PARTIAL → guarded** | Window `unknown`; production blocks without approval signal; sandbox allowed |
| **Customer replied within 24h** | **READY** | `inside_24h` → freeform allowed in production |
| **Merchant manual send** (`POST /api/carts/{id}/send`) | **NOT READY** | Meta Graph path; no 24h gate in v1 |
| **Follow-up send** (continuation after reply) | **READY** if inbound recorded | `record_customer_inbound_observed` / webhook sets window inside |
| **Outside 24h + ops approval env** | **READY** | Env flag allows send (still freeform — provider may still reject until template IDs wired) |

---

## 3. Implementation (minimal guard)

**Module:** `services/whatsapp_production_reality_v2.py`

- `evaluate_whatsapp_template_enforcement`
- `enforce_whatsapp_template_window_before_send` — called from `send_whatsapp()` only when `recovery_uses_real_whatsapp()`

**Log:**

```text
[WA TEMPLATE ENFORCEMENT] mode=production window_24h=outside_24h template_available=false action=block reason=template_required_outside_24h
```

**Block payload:** `error=template_required_outside_24h`, `log_status=blocked_template_required` → `CartRecoveryLog.status` via `resolve_whatsapp_recovery_log_status`.

**Unchanged:** Message copy, template JSON editing, Meta send, queue retry policy, idempotency statuses.

---

## 4. Verification

| Case | Expected |
|------|----------|
| Sandbox + cold cart | `action=send`, Twilio/mock proceeds |
| Production + outside 24h + no approval | `action=block`, no Twilio API call |
| Production + inside 24h | `action=send` |
| Production + outside 24h + `CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED=1` | `action=send` |

**Tests:** `tests/test_whatsapp_template_enforcement_v1.py`

---

## 5. Remaining gaps (not in v1)

- No Twilio/Meta **template_id** on outbound API
- Meta manual cart send path unguarded
- `templates_ready` in readiness still means local JSON only
- Provider rejection after allow (copy mismatch) still possible when env flag set without real approval
