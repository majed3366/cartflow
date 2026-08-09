# Phase 2B — Session Event Diagnosis (`missing_session_asset_ids`)

**Date (UTC):** 2026-08-09  
**Mode:** Read-only implementation audit (+ temporary safe client diagnostics added; **no live ES retry**)  
**Observed live result:** authorization `code` present; `session.event/waba_id/phone_number_id/business_id` all `null`  
**`/register`:** not called  

---

## Verdict

### **E. UNKNOWN — NEED SAFE EVENT TRACE**

The live failure proves the client never accepted a usable `WA_EMBEDDED_SIGNUP` payload within the wait window. It does **not** yet prove whether:

1. Meta never emitted the Embedded Signup session message, or  
2. Meta emitted it and CartFlow **silently dropped** it (origin / parse / type filters), or  
3. Facebook Login for Business completed as a **generic OAuth code flow** without WhatsApp session info (dashboard configuration / variation mismatch).

Until a safe message-event trace exists from one controlled attempt, choosing A/B/C/D alone would be a guess.

---

## What the live result already proves

| Observation | Implication |
|-------------|-------------|
| `FB.login` opened | SDK init + App ID + domain allowlist are at least partly working |
| Meta authorization completed | User completed Facebook Login for Business consent |
| `authResponse.code` returned | `response_type=code` + `override_default_response_type` worked |
| `session.event === null` | No `WA_EMBEDDED_SIGNUP` object was **accepted** by our listener |
| `waba_id` / `phone_number_id` / `business_id` all null | Same — not a partial FINISH (e.g. `FINISH_ONLY_WABA`) |
| Wait ~10s after code then fail | Either no accepted ES message arrived in time, or none arrived at all |

Asset IDs are **not** in `FB.login` `authResponse`. Meta documents them only via `window.postMessage` session info (`type: "WA_EMBEDDED_SIGNUP"`). Missing session fields with a present code is therefore a **session-message path** failure, not an OAuth-code path failure.

---

## Inspection answers (1–11)

### 1. Exact `FB.login` invocation and options

From `static/admin_whatsapp_es_recovery.js`:

```js
FB.login(callback, {
  config_id: state.configurationId,
  response_type: "code",
  override_default_response_type: true,
  extras: { setup: {}, sessionInfoVersion: "3" },
});
```

Matches Meta’s current Embedded Signup implementation shape (config-driven v4 + session info v3).

### 2. Is `config_id` passed in Meta-supported form?

**Yes** — top-level `config_id` (from Railway `META_WHATSAPP_CONFIGURATION_ID`). Not missing from the client call.

### 3. Are `response_type=code` and `override_default_response_type` correct?

**Yes** — and live evidence confirms they work (code returned).

### 4. Are `extras` / `setup` / `sessionInfoVersion` required and present?

| Option | CartFlow | Meta guidance |
|--------|----------|---------------|
| `extras.setup` | `{}` | Present / recommended |
| `extras.sessionInfoVersion` | `"3"` (string) | Required for session postMessage payload |
| `extras.featureType` | omitted (`""` in some Meta snippets) | Optional for standard Cloud API ES |

**Not a clear FB.LOGIN CONFIGURATION BUG** on the code side — options look sufficient. Remaining risk is **dashboard configuration content** behind that `config_id`, not missing client flags.

### 5. Window message listener

Attached in `listenSession()` during `init()`, before the launch button is enabled.

### 6. `event.origin` validation

```js
event.origin.indexOf("facebook.com") === -1 → return
```

Accepts `https://www.facebook.com` and `https://web.facebook.com`.  
**Risk (unproven):** messages from an unexpected Meta origin that does **not** contain the substring `facebook.com` would be dropped silently. Uncommon, but possible without a trace.

### 7. Parsing of `event.data`

| Shape | Handled? |
|-------|----------|
| JSON string | Yes (`JSON.parse`) |
| Already-object | Yes |
| Non-JSON string | Silent drop |
| `type === "WA_EMBEDDED_SIGNUP"` required | Yes — any other type silent drop |
| Reads `data.data.waba_id` / `phone_number_id` | Yes — Meta FINISH schema |

**Schema risk (unproven):** if Meta sent a differently nested shape (or non-JSON callback-style string as in older SO reports), we would drop it and leave `session.event` null — exactly the live symptom.

### 8. Listener attached before `FB.login`?

**Yes.** Not a timing attach bug.

### 9. Could events be ignored due to origin/type/schema mismatch?

**Yes — possible.** Current listener has **three silent drop paths** and no operator-visible trace of dropped messages (until temporary diagnostics added below). Without a trace, this cannot be confirmed or ruled out.

### 10. Did Meta return an ES session event, or only generic Facebook Login completion?

**Unknown from current evidence.**  
Code-without-session is consistent with:

- Generic Facebook Login for Business completion (OAuth code only), **or**
- ES session messages emitted but dropped, **or**
- ES UI finished in a way that did not emit FINISH session info to the opener.

Live UI said “Meta user authorization completes successfully,” which can describe **Facebook Login** alone and does not prove WhatsApp asset-selection FINISH.

### 11. Is the Facebook Login for Business configuration sufficient for WhatsApp Embedded Signup?

**Cannot verify from code.** Must be confirmed in Meta App Dashboard:

1. App → **Facebook Login for Business** → **Configurations**  
2. Open configuration ID `27774549568822736`  
3. Confirm login variation is **WhatsApp Embedded Signup** (not a generic Login for Business config)  
4. Confirm WhatsApp / Cloud API assets are included  
5. Confirm App Review **Advanced** access for `whatsapp_business_management` + `whatsapp_business_messaging`  

If the configuration is not the WhatsApp Embedded Signup variation, Meta can still return an OAuth `code` while **never** sending `WA_EMBEDDED_SIGNUP` — a leading hypothesis for this exact symptom.

Also confirm Allowed Domains / Valid OAuth Redirect URIs include the admin host that spawned the flow (`smartreplyai.net`). Owner already states JS SDK login + domain allowlist are enabled; still verify the **configuration variation**, not only SDK enablement.

---

## Ruling out / ranking alternatives

| Code | Assessment |
|------|------------|
| **A. CLIENT LISTENER BUG** | Possible via silent drops; structure is otherwise correct (attached early; parses string/object; expects Meta FINISH keys). **Not proven.** |
| **B. FB.LOGIN CONFIGURATION BUG** | **Unlikely** — options match Meta docs; code returned; `sessionInfoVersion: "3"` already set. |
| **C. META DASHBOARD CONFIGURATION INCOMPLETE** | **Plausible leading hypothesis** — especially wrong Login variation / missing WhatsApp assets / missing Advanced access. |
| **D. META DID NOT EMIT EMBEDDED SIGNUP SESSION EVENT** | **Plausible** — indistinguishable from A/C without a message trace. |
| **E. UNKNOWN — NEED SAFE EVENT TRACE** | **Selected** — required next diagnostic step before fixing or retrying productively. |

---

## Temporary safe diagnostics added (not a live retry)

In `static/admin_whatsapp_es_recovery.js`, the message listener now records a ring buffer of **safe** fields only:

- `origin`  
- `dataType` / `parseOk`  
- `type` / `eventName`  
- `topKeys` / `nestedKeys`  
- booleans `hasWabaKey` / `hasPhoneKey` / `originAllowsFacebookSubstring` / `wouldAcceptType`  

On `missing_session_asset_ids`, the Result JSON includes `message_diagnostics` (last ≤20 entries) + `fb_login_options` echo (no secrets).

**Never logged:** authorization code, access token, App Secret, personal user data, raw message bodies.

These diagnostics are **temporary** for the next **authorized** attempt after this diagnosis is reviewed. Do not treat them as a permanent security relaxation of asset assertions.

---

## What NOT to do until diagnosis is reviewed

- Do **not** call `/register`  
- Do **not** retry live Embedded Signup until this report is reviewed  
- Do **not** delete / create / deregister Meta assets  
- Do **not** loosen hard WABA/phone asserts  

---

## Recommended next step (after review — not executed now)

1. Deploy the temporary diagnostics build (if not already).  
2. One controlled admin ES attempt.  
3. Capture Result JSON `message_diagnostics`.  
4. Reclassify:

| Trace pattern | Likely code |
|---------------|-------------|
| Zero facebook.com messages | **D** or popup/opener messaging failure |
| facebook.com messages, non-JSON only | Advanced access / config issue → **C** (or Meta non-ES payload) |
| JSON with other `type`, never `WA_EMBEDDED_SIGNUP` | **C** or **D** (generic login) |
| `WA_EMBEDDED_SIGNUP` present but dropped by origin check | **A** (origin filter) |
| `WA_EMBEDDED_SIGNUP` + FINISH keys present but IDs empty | Meta FINISH variant / incomplete asset selection → treat as **D**/product flow |
| `WA_EMBEDDED_SIGNUP` with IDs but client still null | **A** (parse/schema bug) |

---

## STOP

Diagnosis complete. Classification: **E. UNKNOWN — NEED SAFE EVENT TRACE**.  

No live Embedded Signup retry performed in this task. No `/register`.
