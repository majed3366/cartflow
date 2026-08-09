# WhatsApp Phone Recovery Report — Phase 1 (Read-only)

**Date (UTC):** 2026-08-09  
**Status:** **STOP after Phase 1** — diagnosis only; no Meta mutations  
**Target phone:** `+966 57 970 6669`  
**Phone Number ID:** `1260388737156321`  
**WABA ID:** `1520530422625766`  
**WhatsApp Manager (operator-reported):** `SUSPENDED`  
**Prior register failure:** HTTP 400 · code `100` · subcode `2388001` · fbtrace `AoGAdi47IZQDf3KF-Z5iMT8`

---

## Phase 2B — Minimal Embedded Signup recovery (2026-08-09)

**Result:** **IMPLEMENTED** (admin recovery surface + hard asserts). Live Meta click-through still required for full success gate.

| Item | Detail |
|------|--------|
| Page | `/admin/whatsapp/embedded-signup-recovery` |
| Config API | `/admin/api/whatsapp/embedded-signup-recovery/config` |
| Complete API | `/admin/api/whatsapp/embedded-signup-recovery/complete` |
| Assert | WABA `1520530422625766` · Phone `1260388737156321` |
| `/register` | **Not called** |

Evidence: [`PHASE_2B_EMBEDDED_SIGNUP_RECOVERY_EVIDENCE.md`](PHASE_2B_EMBEDDED_SIGNUP_RECOVERY_EVIDENCE.md) · readiness: [`EMBEDDED_SIGNUP_RECOVERY_READINESS.md`](EMBEDDED_SIGNUP_RECOVERY_READINESS.md)

---

## Phase 2A — Embedded Signup recovery readiness (2026-08-09)

**Result:** **STOP — BLOCKED** before Phase 2B implementation.

Full matrix: [`EMBEDDED_SIGNUP_RECOVERY_READINESS.md`](EMBEDDED_SIGNUP_RECOVERY_READINESS.md)

| Blocker | Detail |
|---------|--------|
| Meta App ID | Env keys missing (`META_WHATSAPP_APP_ID` / aliases) |
| Embedded Signup `config_id` | Env keys missing (`META_WHATSAPP_CONFIGURATION_ID` / aliases) — **must not invent** |
| App Secret | Missing for server code→token exchange |

**Not done:** FB.login recovery UI · code exchange · `/register` · asset create/delete.

**Owner:** complete Meta Dashboard checklist in the readiness doc (App ID, Configuration ID, App Secret, domains, App Review), then re-authorize Phase 2B.

---

## Phase 1 verdict

| Question | Finding |
|----------|---------|
| Can CartFlow run a fresh Embedded Signup in-product today? | **No** — foundation/placeholder only; no `FB.login`, no config_id wiring, no code→token exchange |
| Can CartFlow register this phone today? | **Yes (admin API path exists)** — `POST /admin/api/whatsapp/meta-register` → Graph `v23.0/{PHONE_NUMBER_ID}/register`, allowlisted to `1260388737156321` only |
| Should Phase 3 register run now? | **No** — Meta guidance + prior 2388001: Embedded Signup refresh required first when ES phone was not registered in time |
| Live Graph probe from this workspace? | **Blocked** — local `.env` Meta token is placeholder / not production; no admin password for Living Store admin API |

**STOP.** Do not start Phase 2–4 until Phase 1 review + a real Embedded Signup path (Meta UI / Tech Provider tools) is approved.

---

## 1. Meta integration implementation (CartFlow)

### Platform Path A (CartFlow-managed Cloud API) — **implemented**

| Concern | Location |
|---------|----------|
| Env credentials | `services/admin_whatsapp_meta_status_v1.py` → `read_whatsapp_meta_env()` |
| Graph version | **`v23.0`** (`META_GRAPH_VERSION`) |
| Read status | `GET /admin/api/whatsapp/meta-status` → `fetch_whatsapp_meta_status` |
| List WABA phones | `GET /admin/api/whatsapp/meta-phone-numbers` → `fetch_waba_phone_numbers` |
| Register phone | `POST /admin/api/whatsapp/meta-register` → `register_whatsapp_phone` in `services/admin_whatsapp_meta_register_v1.py` |
| Send test | `POST /admin/api/whatsapp/meta-send-test` |
| Cloud send | `services/whatsapp_providers/meta_cloud.py` |
| Webhook | `GET\|POST /webhooks/meta/whatsapp` |

**Token storage:** environment only (not DB):

- Token: `WHATSAPP_ACCESS_TOKEN` → `WHATSAPP_API_TOKEN` → `WHATSAPP_CLOUD_API_TOKEN` → `META_WHATSAPP_TOKEN`
- Phone ID: `WHATSAPP_PHONE_NUMBER_ID` → `WHATSAPP_PHONE_ID`
- WABA: `WHATSAPP_BUSINESS_ACCOUNT_ID` → `WABA_ID`

**Hardcoded allowlist:** `ALLOWED_REGISTER_PHONE_IDS = {"1260388737156321"}`  
WABA `1520530422625766` is **not** hardcoded in Python (docs + env only).

### Merchant Path B (Embedded Signup) — **foundation only**

| Item | Status |
|------|--------|
| Design | `docs/cartflow_whatsapp_embedded_signup_foundation_v1.md` (ES v4 research) |
| Readiness states | `services/merchant_whatsapp_embedded_signup_readiness_v1.py` (`foundation_only=True`) |
| UI | `#whatsapp-connect` — CTA **disabled** («سيتوفر قريباً») |
| `FB.login` / Meta SDK | **Not present** |
| `config_id` / App ID env wiring | Documented future only (`META_WHATSAPP_CONFIGURATION_ID`, etc.) — **not runtime** |
| `POST /api/whatsapp/embedded-signup/complete` | **Does not exist** |
| Code → business token exchange | **Not implemented** |
| Per-store WABA/phone DB columns | Future / not on `Store` model |

**Implication for Phase 2:** A “fresh Embedded Signup session” **cannot** be executed through CartFlow merchant UI today. It must be done via Meta Business / WhatsApp Manager / Tech Provider Embedded Signup tooling outside this placeholder, then CartFlow register may proceed with the existing admin path.

---

## 2. Authorization code / token exchange

| Flow | Implemented? |
|------|----------------|
| Meta ES `code` (30s TTL) → business access token | **No** |
| Platform long-lived token in env | **Yes** (ops-managed) |
| Zid `exchange_code_for_token` | Unrelated (store OAuth) |

No CartFlow endpoint currently captures Embedded Signup authorization results into storage.

---

## 3. Confirmed target assets

| Asset | ID / value | Source |
|-------|------------|--------|
| WABA | `1520530422625766` | Operator + prior docs (`register_production_whatsapp_phone_v1`) |
| Phone Number ID | `1260388737156321` | Operator + register allowlist + docs |
| Display phone | `+966 57 970 6669` | Operator + docs |
| Graph API version for register | `v23.0` | `admin_whatsapp_meta_status_v1.META_GRAPH_VERSION` |

Register body contract already in code:

```json
{
  "messaging_product": "whatsapp",
  "pin": "<6-digit PIN>"
}
```

---

## 4. Live Graph diagnostics (this environment)

Probe script: `scripts/_whatsapp_phone_recovery_phase1_readonly.py`  
Output: `docs/architecture/whatsapp_phone_recovery_v1/phase1_live_probe.json`

| Check | Result |
|-------|--------|
| Local production Meta token usable | **No** — token present but treated as missing/placeholder (`access_token_missing`); env phone id shows placeholder `your_id` |
| Forced GET phone `1260388737156321` | Not executed against Meta (token rejected as placeholder) |
| WABA phone list `1520530422625766` | Not executed against Meta |
| Living Store admin `/admin/api/whatsapp/meta-status` | Not run — `CARTFLOW_ADMIN_PASSWORD` unavailable in this session |

**No Meta state was modified.**

---

## 5. Last known Graph state (prior read-only evidence)

From `docs/architecture/register_production_whatsapp_phone_v1/SAUDI_PHONE_PENDING_ROOT_CAUSE_V1.md` (2026-08-07) — **not re-verified today**:

| Field | Last known value |
|-------|------------------|
| display_phone_number | `+966 57 970 6669` |
| verified_name | `Cartflow` |
| name_status | `AVAILABLE_WITHOUT_REVIEW` |
| quality_rating | `UNKNOWN` |
| account_mode | `LIVE` |
| code_verification_status | `VERIFIED` |
| registration_status (Graph `status`) | `PENDING` |
| platform_type | `NOT_APPLICABLE` |
| cloud_api_registered | `false` |
| is_pin_enabled | `false` |
| health_status.can_send_message | `BLOCKED` |
| health error | **141000** — phone not linked; Meta solution = register |
| search_visibility | `NON_VISIBLE` |
| last_onboarded_time | `null` |

WhatsApp Manager **SUSPENDED** is operator-reported for this recovery task; it was **not** returned as a Graph enum in prior CartFlow diagnostics (prior docs did not map Manager SUSPENDED ↔ Graph `status`).

### Prior `/register` failure (do not retry yet)

From `REGISTER_2388001_ROOT_CAUSE_REPORT.md`:

| Item | Value |
|------|--------|
| Endpoint | `POST https://graph.facebook.com/v23.0/1260388737156321/register` |
| HTTP | `400` |
| error.message | `Invalid parameter` |
| error.type | `OAuthException` |
| error.code | `100` |
| error.error_subcode | `2388001` |
| Interpretation (prior report) | Certificate-creation failure class; request body was contract-valid |

---

## 6. Phase readiness matrix

| Phase | Ready? | Blocker |
|-------|--------|---------|
| 1 Read-only diagnosis | **Done** (code + prior Graph evidence; live Graph refresh blocked locally) | Need Living Store admin or production token to refresh fields today |
| 2 Fresh Embedded Signup | **Blocked in CartFlow product** | ES not implemented; must use Meta-side ES for same WABA/phone |
| 3 Register phone | Code ready; **must wait** for successful Phase 2 | Meta: re-ES before register if ES phone aged out; prior 2388001 |
| 4 Validation | Not started | Depends on Phase 3 success |

---

## 7. Recommended next actions (after review — not executed)

1. Refresh live Graph via production: `GET /admin/api/whatsapp/meta-status?phone_number_id=1260388737156321` and `GET /admin/api/whatsapp/meta-phone-numbers` (confirm WABA `1520530422625766`).
2. Complete **fresh Embedded Signup** in Meta for the **same** business / WABA / phone (no new WABA, no phone delete).
3. Immediately call CartFlow `POST /admin/api/whatsapp/meta-register` with 6-digit PIN (allowlisted ID only).
4. If `100/2388001` persists after fresh ES → **STOP** (per task rules).

---

## Safety confirmation

- Phone number **not** deleted  
- WABA **not** deleted  
- No deregister  
- No new WABA / phone created  
- No `/register` call in this phase  
- No send / template test in this phase  

## STOP

Phase 1 complete. Awaiting review before Phase 2 (fresh Embedded Signup).
