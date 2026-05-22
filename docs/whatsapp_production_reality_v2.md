# WhatsApp Production Reality v2 — Foundation

**Date (UTC):** 2026-05-19  
**Scope:** Additive observation + readiness signals only. **No** recovery, lifecycle, queue, attribution, widget, or send-gating changes.

Builds on [whatsapp_production_reality_v1.md](whatsapp_production_reality_v1.md) and [whatsapp_delivery_truth_v1.md](whatsapp_delivery_truth_v1.md).

---

## Goals

Prepare real merchant WhatsApp constraints before broad production:

1. **24-hour customer service window** — classify `inside_24h` / `outside_24h` / `unknown`
2. **Template routing foundation** — log `freeform_allowed` / `template_required` only (no router enforcement yet)
3. **Per-store readiness** — `provider_connected`, `templates_ready`, `delivery_truth_ready`
4. **Admin signal** — merchant level: `sandbox_only` → `partial` → `production_ready`

---

## Conversation window

| `conversation_window_status` | Meaning |
|------------------------------|---------|
| `inside_24h` | Last customer inbound within 24 hours |
| `outside_24h` | Last inbound older than 24 hours |
| `unknown` | No inbound history found |

**Evidence sources (read-only merge):**

- In-process observation on `POST /webhook/whatsapp`
- `cf_behavioral` timestamps on `AbandonedCart` when present
- `MerchantFollowupAction` / `RecoveryEvent` (`wa_customer_inbound_v2`)

**Log:**

```text
[WA WINDOW CHECK] window=inside_24h phone_key=...
```

---

## Template decision (foundation only)

| Window | `freeform_allowed` | `template_required` |
|--------|-------------------|---------------------|
| `inside_24h` | true | false |
| `outside_24h` | false | true |
| `unknown` | false | true (conservative) |

**Log:**

```text
[WA TEMPLATE DECISION] freeform_allowed=true template_required=false window=inside_24h
```

No send path blocking in v2 — future v3 may enforce.

---

## Store readiness

| Field | v2 meaning |
|-------|------------|
| `provider_connected` | `PRODUCTION_MODE` + Twilio ready + store recovery enabled |
| `templates_ready` | Local `reason_templates_json` / `trigger_templates_json` configured (not Meta approval sync) |
| `delivery_truth_ready` | Real Twilio + resolved status callback URL |

**Merchant readiness level:**

| Level | When |
|-------|------|
| `sandbox_only` | Mock / non-real WhatsApp path |
| `partial` | Real provider but missing templates and/or delivery callback |
| `production_ready` | All three signals true |

Admin operational health WhatsApp card includes Arabic label for v2 level.

---

## Code map

| Piece | Location |
|-------|----------|
| Core | `services/whatsapp_production_reality_v2.py` |
| Inbound observe | `main.py` `POST /webhook/whatsapp` |
| Outbound observe | `services/whatsapp_send.py` (log only, before `messages.create`) |
| Admin signal | `services/admin_operational_health.py` `_whatsapp_card` |
| Tests | `tests/test_whatsapp_production_reality_v2.py` |

---

## Dev simulation (no wait for 24h)

**`POST /dev/whatsapp-window-simulate`** — only when `ENV=development` (404 in production).

```json
{
  "phone": "9665XXXXXXXX",
  "last_inbound_hours_ago": 25
}
```

Expect `[WA WINDOW CHECK] window=outside_24h` and `[WA TEMPLATE DECISION] template_required=true`.

Use `last_inbound_hours_ago: 1` for `inside_24h` / `freeform_allowed=true`. No send or recovery runs.

---

## Real verification (production)

1. Customer replies on WhatsApp → `[WA WINDOW CHECK] window=inside_24h`
2. Trigger recovery send → `[WA TEMPLATE DECISION] freeform_allowed=true` (if still inside window)
3. Simulate or wait >24h without inbound → `template_required=true`, `outside_24h`
4. Confirm send still succeeds (v2 does not block)

**PASS** when logs match session reality; behavior unchanged except observability.

---

## Risks (unchanged from v1)

- `templates_ready` ≠ Meta-approved templates
- `unknown` window defaults to `template_required=true` in logs only
- Multi-worker: in-process inbound cache is per process; DB events help cross-instance
