# Merchant Onboarding Reality v1 — Audit

**Date (UTC):** 2026-05-19  
**Commit:** `audit: verify merchant onboarding reality v1`  
**Scope:** Read-only audit + readiness foundation. **No** recovery, lifecycle, send, queue execution, or dashboard merchant UX changes.

---

## Executive question

**Can a new merchant connect → understand readiness → fix missing pieces → become `production_ready` without manual intervention?**

| Verdict | Answer |
|---------|--------|
| **Merchant Onboarding Reality** | **PARTIAL** |
| **Self-serve to `production_ready`** | **NO** (today) |
| **Self-serve to `sandbox_only` / partial setup** | **YES** (dashboard + widget + templates) |

Foundation v1 adds **dimensions**, **`[MERCHANT READINESS]`** logs, and admin card **جاهزية المتجر**. It does not auto-fix blockers.

---

## Capability matrix

| Step | Merchant action | System support | Manual / ops required? |
|------|-----------------|----------------|------------------------|
| Connect store | Zid OAuth, tokens | `evaluate_onboarding_readiness` → `store_connected` | **YES** (OAuth) |
| Enable recovery + widget | Dashboard settings | `recovery_enabled`, `widget_installed` | **NO** (self-serve) |
| Configure delays | Dashboard | `delays_configured` | **NO** |
| Local templates | `reason_templates_json` | `templates_present` | **NO** |
| Provider templates approved | Meta / Twilio console | `templates_approved=unknown` | **YES** (no Meta sync) |
| Production WhatsApp | Env `PRODUCTION_MODE` + Twilio | `provider_connected` | **YES** (deploy/env) |
| Delivery truth | Status callback URL | `delivery_truth_ready` | **YES** (env URL) |
| 24h window evidence | Customer reply | `window_24h_ready` + v2 logs | **Partial** (dev simulate) |
| Queue / restart survival | Runtime | `queue_ready`, `restart_survival_ready` (foundation) | **Partial** (platform code present) |
| Understand gaps | — | `[MERCHANT READINESS]`, admin card | **NO** |
| Reach `production_ready` | All above | `onboarding_state=production_ready` | **YES** (multiple manual gates) |

---

## Readiness dimensions (v1 foundation)

| Dimension | Field | Source |
|-----------|-------|--------|
| Provider | `provider_connected` | Onboarding flags + Twilio readiness |
| WhatsApp delivery | `delivery_truth_ready` | `whatsapp_production_reality_v2` |
| 24h window | `window_24h_ready` | v2 foundation + milestone `first_reply_received` or send |
| Template routing | `template_routing_ready` | v2 + `templates_present` |
| Store config | `store_whatsapp_number_set`, `recovery_enabled`, `delays_configured`, `widget_enabled`, `store_connected` | `Store` + onboarding |
| Templates | `templates_present`, `templates_approved` | Store JSON; approval **unknown** without Meta |
| Operational | `queue_ready`, `restart_survival_ready` | Code/registry presence (not live worker health) |
| Level | `onboarding_state` | `not_started` → `sandbox_only` → `partial` → `production_ready` |

---

## PASS / FAIL matrix (automated tests)

| Scenario | Expected `onboarding_state` | Test |
|----------|----------------------------|------|
| Empty store (`None`) | `not_started` | PASS |
| Partial setup (connected, no templates, production env mocked) | `partial` | PASS |
| Fully configured mock store + production env + provider | `production_ready` | PASS |
| Self-serve audit verdict | `self_serve_to_production_ready=false` | PASS |

---

## Dangerous gaps (P0 before “real merchant production”)

1. **No self-serve Twilio/Meta connect** — platform env only; merchant dashboard `whatsapp_provider_mode` is not wired to send path.
2. **Template approval** — local JSON ≠ Meta-approved; outbound outside 24h will fail at provider.
3. **Delivery truth** — requires `CARTFLOW_PUBLIC_BASE_URL` / `TWILIO_STATUS_CALLBACK_URL` on server, not merchant UI.
4. **Sandbox join** — recipients must join Twilio sandbox manually.
5. **Single-store admin card** — uses latest dashboard `Store` row, not per-merchant multi-tenant admin picker yet.
6. **`production_ready` does not prove** first cart, first send, or first reply — milestones separate.

---

## Logs

```text
[MERCHANT READINESS] store_slug=demo level=partial missing=delivery_truth_callback,...
```

---

## Code map

| Piece | Location |
|-------|----------|
| Evaluation | `services/merchant_onboarding_reality_v1.py` |
| Admin card | `build_merchant_onboarding_admin_card` → `/admin/operational-health` card |
| Tests | `tests/test_merchant_onboarding_reality_v1.py` |
| Related | `cartflow_onboarding_readiness.py`, `whatsapp_production_reality_v2.py` |

---

## Recommended path (documentation only)

1. Merchant: connect store, enable widget/recovery, fill templates (dashboard).  
2. Ops: set `PRODUCTION_MODE`, Twilio, public URL, status callback.  
3. Merchant: join sandbox / approve templates with provider.  
4. Verify: `[MERCHANT READINESS] level=production_ready` + delivery truth + real send test.
