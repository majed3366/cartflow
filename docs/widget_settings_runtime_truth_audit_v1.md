# Widget Settings Runtime Truth Audit (v1)

**Date (UTC):** 2026-06-02  
**Scope:** Read-only audit — dashboard → database → `GET /api/cartflow/public-config` → V2 layered runtime (`static/cartflow_widget_runtime/*`) → Zid storefront behavior.  
**Out of scope:** No setting redesign, no UX/recovery/OAuth/Zid/WhatsApp changes.

**Storefront path audited:** Zid embed via `static/widget_loader.js` → `cartflow_widget_loader.js` → `cartflow_widget_config.js` + `cartflow_widget_triggers.js` + `cartflow_widget_flows.js` + `cartflow_widget_shell.js` + `cartflow_widget_ui.js`.

**Live API sample:** `GET https://smartreplyai.net/api/cartflow/public-config?store_slug=4hz49e` (2026-06-02) exposes `cartflow_widget_enabled`, `widget_primary_color`, `widget_style`, `widget_trigger_config`, etc. It does **not** expose `widget_enabled` or `widget_display_name` from General Settings.

---

## Summary

| Result | Count | Meaning |
|--------|------:|---------|
| **PASS** | 14 | End-to-end: change in dashboard affects observable storefront behavior (or gate blocks widget). |
| **FAIL** | 6 | Saves/loads in dashboard but breaks before storefront applies, or storefront ignores runtime value. |
| **N/A** | 4 | Preview-only / duplicate control / not on primary widget panel. |

**Operational truth today:** The **Widget** section in the merchant app (`#page-widget`, `POST /api/dashboard/merchant-widget-settings`) and **Recovery settings** gate/delay fields are the reliable controls for the live Zid widget. **General Settings** `widget_enabled` / `widget_display_name` are **not** wired into `public-config` or V2 runtime.

**Update (2026-06-02, `fix: widget title runtime truth`):** Header uses `Config.merchant().widget_brand_name` ← `applyVisual` ← `public-config` `widget_name`. Failure mode when `widget_display_name=CARTFLOW` but `widget_name` stayed default `مساعد المتجر` — dashboard showed CARTFLOW via display fallback while API served default. Fixed via canonical name resolution + sync cache load on miss.

---

## Audit table

| Setting | Dashboard saves? | DB persists? | Public config exposes? | Runtime reads? | Storefront applies? | **PASS / FAIL** | Break point |
|---------|------------------|--------------|----------------------|----------------|---------------------|-----------------|-------------|
| **Widget enable (Widget panel)** — `cartflow_widget_enabled` | PASS — `merchant_widget_panel.js`, recovery POST | PASS — `stores.cartflow_widget_enabled` | PASS — `cartflow_widget_public_bundle.py` | PASS — `cartflow_widget_config.js` → `merchant.widget_enabled` | PASS — `cartflow_widget_triggers.js` `merchantWidgetDisabled()`, `flows.js` `merchantAllowsUi()` | **PASS** | — |
| **Widget enable (General Settings)** — `widget_enabled` | PASS — `merchant_general_settings.js` | PASS — `stores.widget_enabled` | **FAIL** — not in `merge_widget_template_bundle_from_store_row` | **FAIL** — runtime never receives it | **FAIL** — toggling general checkbox does not block widget | **FAIL** | **API** (not merged into public bundle) |
| **Widget name (Widget panel)** — `widget_name` | PASS | PASS — `stores.widget_name` | PASS | PASS — `widget_brand_name` in `cartflow_widget_config.js` | **FAIL** — shell title hardcoded `مساعدة`; recovery copy hardcoded | **FAIL** | **Storefront** (`cartflow_widget_shell.js` `HEADER_DEFAULT`; `flows.js` `getCartRecoveryQuestion()`) |
| **Widget name (General Settings)** — `widget_display_name` | PASS | PASS — `stores.widget_display_name` | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **API** |
| **Widget color** — `widget_primary_color` | PASS | PASS | PASS | PASS — `merchant.widget_primary_color`, `flows.js` `primaryHex()` | PASS — chrome bar + primary buttons (`stampPrimary`, `ensureShell`) | **PASS** | — |
| **Widget style** — `widget_style` | PASS — customization / general widget section | PASS | PASS | PASS — `widget_chrome_style` set in config | **FAIL** — no V2 consumer (shell/UI ignore style) | **FAIL** | **Storefront** |
| **Widget delay** — `cartflow_widget_delay_*` | PASS — recovery / general settings | PASS | PASS | PASS — `prompt_not_before_ms` once per load | PASS — widget blocked until delay elapses | **PASS** | — |
| **Exit intent on/off** | PASS | PASS — `cf_widget_trigger_settings_json` | PASS — `widget_trigger_config` | PASS | PASS — exit path gated in `cartflow_widget_triggers.js` | **PASS** | — |
| **Exit intent delay** | PASS | PASS | PASS | PASS — `exitIntentDelaySeconds()` | PASS | **PASS** | — |
| **Exit intent sensitivity** | PASS | PASS | PASS | PASS | PASS — used in exit scheduling | **PASS** | — |
| **Exit intent frequency** | PASS | PASS | PASS | PASS | PASS — session / 24h gates | **PASS** | — |
| **Hesitation on/off** | PASS | PASS | PASS | PASS | PASS — `hesitation_trigger_enabled` check | **PASS** | — |
| **Hesitation delay** | PASS | PASS | PASS | PASS — `hesitationDelaySeconds()` | PASS | **PASS** | — |
| **Hesitation condition** | PASS | PASS | PASS | PASS — `hesitationCondition()` | PASS (storefront recovery mode uses cart-path heuristics where relevant) | **PASS** | — |
| **Visibility — globally enabled** | PASS — general settings advanced / widget trigger | PASS | PASS | PASS — `widgetGloballyAllowed()` | PASS | **PASS** | — |
| **Visibility — temporarily disabled** | PASS — general settings only | PASS | PASS | PASS | PASS | **PASS** | — |
| **Visibility — page scope** | PASS | PASS | PASS | PASS — `pageScopeAllows()` | PASS — e.g. `cart` scope limits paths | **PASS** | — |
| **Suppress after dismiss** | PASS (merchant app advanced) | PASS | PASS | PASS | PASS — `sessionStorage` + flow gates | **PASS** | — |
| **Suppress after purchase** | PASS | PASS | PASS | PASS | PASS (where purchase signal exists) | **PASS** | — |
| **Suppress when checkout started** | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Phone capture mode** | PASS — merchant app radios | PASS | PASS | PASS — `phoneCaptureMode()` | PASS — `cartflow_widget_phone.js` | **PASS** | — |
| **Reason enable / order** | PASS | PASS — `reason_templates_json` + trigger order | PASS | PASS — `buildVisibleReasonRows()` | PASS — reason grid contents | **PASS** | — |
| **Exit intent message (custom/preset)** | PASS — `exit_intent_settings.html` / recovery POST | PASS — `exit_intent_*` columns | PASS | **FAIL** — not read by V2 flows | **FAIL** — approved copy fixed: `تبي أساعدك تكمل طلبك؟` | **FAIL** | **Storefront** |
| **Widget brand line (`widget_brand_line_ar`)** | **FAIL** — merchant app save forces `""` | PASS if set elsewhere | PASS if non-empty in DB | Would read if present | **FAIL** — cleared on panel save | **FAIL** | **Dashboard** (`merchant_widget_panel.js` line 93) |
| **Preview: position / avatar / dark / welcome** | N/A — localStorage / preview only | N/A | N/A | N/A | N/A | **N/A** | By design (see `widget_customization.html` footnote) |
| **Duplicate name fields** | Two columns: `widget_name` vs `widget_display_name` | Both persist independently | Only `widget_name` public | Only `widget_name` → runtime | Merchants can set both to different values | **FAIL** (product confusion) | **API / dashboard** split |

---

## Verification chain evidence

### Dashboard → DB

| Endpoint | Fields applied |
|----------|----------------|
| `POST /api/dashboard/merchant-widget-settings` | `widget_name`, `widget_primary_color`, `widget_style`, `cartflow_widget_*`, `widget_trigger_config`, `reason_templates`, `exit_intent_*` — `main.py` + `update_from_dashboard_store_row` |
| `POST /api/recovery-settings` | Full recovery bundle including widget customization + gate + triggers + **general** if included |
| `POST /api/merchant/general-settings` (fast path) | **Only** `widget_enabled`, `widget_display_name`, notifications, automation mode — **does not** refresh widget cache keys beyond commit on full recovery POST |

### DB → Public config

Built in `services/cartflow_widget_public_bundle.py` → cached in `services/widget_config_cache.py` → `GET /api/cartflow/public-config`.

**Not included in bundle:** `widget_enabled`, `widget_display_name` (general settings).

### Runtime → Storefront

| Module | Role |
|--------|------|
| `cartflow_widget_api.js` | Fetches `public-config`, calls `Config.applyPayload` |
| `cartflow_widget_config.js` | Normalizes gate, trigger, visual fields |
| `cartflow_widget_triggers.js` | When widget may open |
| `cartflow_widget_flows.js` | Recovery UI; `primaryHex()`, `merchantAllowsUi()`, hardcoded question |
| `cartflow_widget_shell.js` | Chrome; uses color only |
| `cartflow_widget_ui.js` | Buttons stamped with `primaryColor` |

Automated guards: `tests/test_widget_settings_runtime_truth_audit_v1.py`.

---

## Zid storefront manual verification (required for PASS on behavior)

Use store slug from dashboard (`zid_store_id`, e.g. `4hz49e`) on `https://{slug}.zid.store` after hard refresh.

1. **Color PASS:** Widget panel → set color `#FF0000` → save → open storefront → primary buttons / top chrome bar red.
2. **Enable PASS:** Uncheck «إظهار الودجيت للعملاء» (`cartflow_widget_enabled`) → save → widget must not open on exit/hesitation (console: `[CF TRIGGER BLOCKED]` / `widget_disabled`).
3. **General enable FAIL:** General Settings → uncheck widget enabled only → storefront **still** opens if `cartflow_widget_enabled` true.
4. **Style FAIL:** Set style `bold` → save → shell/button geometry unchanged vs `minimal`.
5. **Name FAIL:** Change «اسم المساعد» → shell header stays `مساعدة`; question stays approved Arabic line.
6. **Exit custom text FAIL:** `exit_intent_settings` custom message → storefront recovery still shows `تبي أساعدك تكمل طلبك؟`.

Do **not** mark FAIL rows as PASS without observing storefront behavior.

---

## Minimal fix proposals (audit-only; not implemented)

| Issue | Break | Minimal fix |
|-------|-------|-------------|
| General `widget_enabled` ignored | API | Map `widget_enabled` → `cartflow_widget_enabled` on general save **or** merge `widget_enabled` into public bundle and teach `applyMerchantGate` to honor it (single source of truth). |
| `widget_display_name` ignored | API | Expose as `widget_name` fallback in `widget_customization_fields_for_api` when `widget_name` empty, or stop showing duplicate field in General Settings. |
| `widget_name` not visible | Storefront | Set `[data-cf-shell-title]` from `Config.merchant().widget_brand_name` on `ensureShell` / `applyVisual`. |
| `widget_style` not visible | Storefront | Apply `widget_chrome_style` classes in `cartflow_widget_shell.js` / `cartflow_widget_ui.js` (match legacy `cartflow_widget.js` behavior). |
| Exit intent copy ignored | Storefront | In recovery mode, `getCartRecoveryQuestion()` should read `exit_intent_template_*` from config when mode is `custom` (keep approved default as fallback). |
| `widget_brand_line_ar` cleared | Dashboard | In `merchant_widget_panel.js` `collectTrigger`, preserve `base.trigger.widget_brand_line_ar` instead of `t.widget_brand_line_ar = ""`. |

---

## Related tests

- `tests/test_cartflow_widget_runtime_public_config.py` — trigger/reason public mirror  
- `tests/test_cartflow_widget_recovery_gate_settings.py` — gate/delay public mirror  
- `tests/test_widget_settings_runtime_truth_audit_v1.py` — regression locks for FAIL break points  
