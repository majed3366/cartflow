# Embedded Signup Recovery Readiness — Phase 2A / 2B

**Date (UTC):** 2026-08-09  
**Task:** CartFlow WhatsApp Recovery V1 — Minimal Embedded Signup Recovery Path  
**Status:** **Phase 2B IMPLEMENTED** — live Meta click-through still required for full success gate  
**Target assets (must not change):**  
- WABA `1520530422625766`  
- Phone Number ID `1260388737156321` (`+966 57 970 6669`)

**Rules honored:** No `/register` · no WABA/phone delete · no deregister · no new assets · no guessed `config_id` · tokens never logged/returned.

---

## Executive verdict

| Question | Answer |
|----------|--------|
| Phase 2A blockers cleared? | **Yes** — owner reports Railway has App ID, Configuration ID, App Secret |
| Phase 2B code shipped? | **Yes** — admin recovery page + config API + complete API |
| Phase 2B live Meta authorization completed? | **Pending owner Facebook session** on Living Store recovery page |
| `/register` called? | **No** (hard-stopped) |

---

## Checklist (1–12) — post Phase 2B

### 1. Meta App ID

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Railway `META_WHATSAPP_APP_ID` (owner-confirmed); admin config API exposes App ID only |
| **REQUIRES CODE** | Done — `FB.init({ appId })` via recovery page |
| **BLOCKER** | No |

### 2. Embedded Signup configuration ID (`config_id`)

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Railway `META_WHATSAPP_CONFIGURATION_ID` (owner-confirmed) |
| **REQUIRES CODE** | Done — `FB.login({ config_id, response_type: 'code', … })` |
| **BLOCKER** | No |

### 3. Facebook JavaScript SDK initialization

| Classification | Detail |
|----------------|--------|
| **PRESENT** | `static/admin_whatsapp_es_recovery.js` loads `connect.facebook.net` + `FB.init` |
| **BLOCKER** | No |

### 4. `FB.login` with Embedded Signup configuration

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Launch button on `/admin/whatsapp/embedded-signup-recovery` |
| **BLOCKER** | No |

### 5. Required permissions / scopes

| Classification | Detail |
|----------------|--------|
| **REQUIRES META DASHBOARD CONFIG** | Advanced access still owner-confirmed at runtime if ES login fails |
| **BLOCKER** | Possible only if App Review incomplete |

### 6. Redirect / domain requirements

| Classification | Detail |
|----------------|--------|
| **REQUIRES META DASHBOARD CONFIG** | `smartreplyai.net` must remain allowlisted |
| **BLOCKER** | Possible if domain allowlist wrong |

### 7. HTTPS requirements

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Production HTTPS |
| **BLOCKER** | No |

### 8. Authorization-code capture

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Client captures `authResponse.code` + `WA_EMBEDDED_SIGNUP` message |
| **BLOCKER** | No |

### 9. Backend code → access-token exchange

| Classification | Detail |
|----------------|--------|
| **PRESENT** | `complete_embedded_signup_recovery` → Graph `/{version}/oauth/access_token` |
| **PRESENT** | App Secret server-only (`META_WHATSAPP_APP_SECRET`) |
| **BLOCKER** | No (assuming Railway secret set) |

### 10. WABA / phone-number extraction + hard assert

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Assert `1520530422625766` / `1260388737156321`; abort on mismatch (HTTP 409) |
| **BLOCKER** | No |

### 11. App subscription to the WABA

| Classification | Detail |
|----------------|--------|
| **DEFERRED** | Not required for Phase 2B success gate; no subscribe call added |
| **BLOCKER** | No for 2B |

### 12. System-user / token architecture

| Classification | Detail |
|----------------|--------|
| **PRESENT** | Ephemeral exchange only — `token_persisted: false`; Path A env token unchanged |
| **BLOCKER** | No |

---

## Phase 2B surfaces

| Surface | Location |
|---------|----------|
| Page | `GET /admin/whatsapp/embedded-signup-recovery` |
| Config | `GET /admin/api/whatsapp/embedded-signup-recovery/config` |
| Complete | `POST /admin/api/whatsapp/embedded-signup-recovery/complete` |
| Service | `services/admin_whatsapp_embedded_signup_recovery_v1.py` |
| Evidence | `PHASE_2B_EMBEDDED_SIGNUP_RECOVERY_EVIDENCE.md` |

---

## STOP

Phase 2B implementation complete in code.  

**Do not call** `POST /1260388737156321/register` until Phase 3 is separately authorized.  

Live success gate (Meta dialog finish + confirmed IDs) requires owner to complete Embedded Signup on the admin recovery page after deploy.
