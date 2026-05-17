# CartFlow — System Summary (Architecture)

## 1) System Overview

CartFlow is a FastAPI application that:

- Embeds a storefront **widget** (JavaScript) for hesitation / exit-intent UX and **reason capture**.
- Receives **cart lifecycle events** (e.g. abandon, conversion) via **`POST /api/cart-event`** and schedules **delayed WhatsApp recovery** (Twilio path in `services/whatsapp_send.py`; Meta Cloud API path in `main.send_whatsapp_message` for interactive CTA messages used elsewhere).
- Persists **store settings**, **abandoned carts**, **recovery reasons**, and **recovery logs** in SQLAlchemy models (`models.py`), with optional schema patches via `schema_widget.py`.
- Serves **merchant dashboards** as Jinja2 HTML under `/dashboard/*`, loading/saving settings through **`GET`/`POST /api/recovery-settings`** and related APIs.
- **`GET /`** — public marketing page: `templates/cartflow_landing.html` (inline styles; may use `static/img/cartflow_landing_reference.jpg` when the build serves a pixel reference); **`GET /register`** — placeholder registration links from CTAs.

---

## 2) Frontend Layer

### 2.1 Widget Layer (VERY IMPORTANT)

| Asset | Role |
|--------|------|
| `static/widget_loader.js` | After **`window.load`**: schedules **`cartflow_return_tracker.js`**, then loads the widget. **Default storefront path:** layered **`cartflow_widget_runtime/cartflow_widget_loader.js`** (serial module chain) whenever **`window.__CARTFLOW_ALLOW_LEGACY_WIDGET !== true`** *or* **`window.CARTFLOW_WIDGET_RUNTIME_V2 === true`** (**`loadLayeredV2 = runtimeV2Explicit \|\| !legacyExplicit`** in shim). **Legacy `cartflow_widget.js`** loads **only** when **`__CARTFLOW_ALLOW_LEGACY_WIDGET === true`** **and** **`CARTFLOW_WIDGET_RUNTIME_V2` is not** `true` (rollback / QA — console **`[CF LEGACY WIDGET LOAD ALLOWED]`** vs **`[CF LEGACY WIDGET LOAD BLOCKED]`**). **`/demo/store*`** sets **`CARTFLOW_WIDGET_RUNTIME_V2 = true`** in the shim (**`cartflowIsDemoStorePrimaryV2Path()`**); **`templates/demo_store.html`** also sets **`CARTFLOW_WIDGET_RUNTIME_V2`** before the shim. Merchant dashboard embed (**`general_settings.html`**) references **`widget_loader.js` only** → **production default is V2**, not legacy. Skips tracker/widget bootstrap when session marked converted via `sessionStorage` / `cartflowIsSessionConverted`. Duplicate script detection skips re-injecting if runtime or legacy URL already present. |
| `static/cartflow_widget_runtime/*.js` | **Layered V2** storefront widget (config → API → state → triggers → phone → shell → UI → flows → legacy_bridge). Starts via **`Flows.start()`** after bootstrap. Does **not** append **`cartflow_widget.js`** at runtime; VIP mirrors use **`mirrorCartTotals()`** in **`cartflow_widget_flows.js`** only. |
| `static/cartflow_widget.js` | **Legacy monolith** (`B`): **not** the default shim branch — loads only with **explicit** **`window.__CARTFLOW_ALLOW_LEGACY_WIDGET === true`** while **`CARTFLOW_WIDGET_RUNTIME_V2` is not** `true`, or via **`GET /dev/widget-test*`** (**`main._DEV_LEGACY_WIDGET_HARNESS_HTML`**, **`ENV=development`** only — **not** in **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`**). Retained for **rollback**, **dev harness**, and **static/operational test reads** (`tests/**` grep static file). **`/demo/store*`** does **not** load this asset in the happy path. |
| `static/cartflow_return_tracker.js` | Loaded by **`widget_loader.js`** (return-to-site / behavioral handoff signalling). |
| `static/cart_abandon_tracking.js` | Included from dashboard templates (`partials/cart_abandon_tracking.html`) for analytics-style tracking where wired. |

**Primary backend calls from storefront widgets:**

- **V2 (`cartflow_widget_api.js`):** `POST /api/cartflow/reason`, `GET /api/cartflow/ready`, `GET /api/cartflow/public-config` (`routes/cartflow.py`).
- **Legacy (`cartflow_widget.js`):** `POST /api/cart-recovery/reason` — persist widget **Layer D** (`routes/cart_recovery_reason.py`); `POST /api/cartflow/reason` alternate path (`routes/cartflow.py`).
- Shared / either surface as wired: `GET /api/recovery/primary-reason` — `main.py`; `POST /api/cartflow/generate-whatsapp-message` — mock WhatsApp preview (no DB write in that handler).

**Cart abandon signal to backend:** the storefront integration is expected to call **`POST /api/cart-event`** with `event: cart_abandoned` (handled in `main.handle_cart_abandoned` → recovery dispatch). The widget focuses on reasons and UX; the actual **abandon event** is typically from page / platform integration.

### 2.1.1 Widget architecture — operational posture (audit 2026-05)

| Topic | Assessment |
|--------|------------|
| **Default production behavior** | **Layered V2** via **`widget_loader.js`** without any global legacy opt-in (evidence: **`templates/general_settings.html`** embed = `widget_loader.js` only; shim **`loadLayeredV2`** true when **`__CARTFLOW_ALLOW_LEGACY_WIDGET` is not** set). |
| **Demo / primary V2 enforcement** | **`demo_store.html`** sets **`CARTFLOW_WIDGET_RUNTIME_V2`** + **`CARTFLOW_RUNTIME_VERSION`** before shim; shim **also** forces V2 on **`^/demo/store(/|$)`**. Baseline tests: **`tests/test_v2_widget_baseline_lock.py`**, **`tests/test_demo_behavioral_navigation.py`**. |
| **`cartflow_widget_runtime` load model** | **`cartflow_widget_loader.js`** loads **nine** modules **sequentially** (`async: false` tags, ordered **config → api → state → triggers → phone → shell → ui → flows → legacy_bridge**), then **`__cartflowV2Bootstrap` / `Flows.start()`**. Failure of one module aborts the chain (logged **`[CF V2 MODULE FAILED]`**). |
| **Complexity / bundle** | V2 split across **~10** smaller files (~**118 KB** source on disk, pre-minify); legacy monolith ~**337 KB**. Default path avoids legacy download; total widget surface still **multiple HTTP round-trips** for V2 (shim + tracker + loader + 9 modules). |
| **Duplication / coupling** | **Dual** reason APIs (**`/api/cartflow/reason`** vs **`/api/cart-recovery/reason`**); **dual** exit-intent implementations (V2 modules vs legacy file); **shared** backend contract (**`exit_intent_*`**, templates). **Operational / static** tests still scan **`cartflow_widget.js`** for parity. |
| **Legacy isolation** | V2 **does not** inject legacy at runtime (**`cartflow_widget_flows.js`** / audit: no `injectLegacyCartflowWidget`). Rollback is **merchant opt-in** + dev harness only. |
| **Risk level** | **Moderate:** default is healthy (V2), but **two** storefront stacks and **serial** multi-file load remain **maintainability and performance** considerations until legacy sunset. |

### 2.2 Dashboard UI

| Path / files | Purpose |
|--------------|---------|
| `GET /dashboard` | `dashboard_v1.html` — **الرئيسية**: KPIs، أسباب التردد، الرسم، **آخر النشاطات** (أسباب فقط — بدون VIP). |
| `GET /dashboard/recovery-settings` | `recovery_settings.html` — delay, attempts, WhatsApp fields; **`GET`/`POST /api/recovery-settings`**. |
| `GET /dashboard/vip-cart-settings` | `vip_cart_settings.html` — **أولوية حقيقية:** `AbandonedCart.status=abandoned` و‎`coalesce(cart_value,0) >= Store.vip_cart_threshold` عند تعريف العتبة؛ بدون عتبة لا تُعرض قائمة VIP. **بيانات تجريبية** منفصلة (`interactive: false`). **إرسال يدوي** → **`POST /api/dashboard/vip-cart/{abandoned_cart_row_id}/merchant-alert`**. عتبة VIP عبر **`/api/recovery-settings`**. |
| `GET /dashboard/exit-intent-settings` | `exit_intent_settings.html` — exit intent copy; loads/saves via recovery settings API + `static/cartflow_dashboard_messages.js`. |
| `GET /dashboard/cart-recovery-messages` | `cart_recovery_messages.html` — recovery message templates. |
| `GET /dashboard/widget-customization` | `widget_customization.html` — widget appearance. |
| Shared chrome | `templates/partials/dashboard_sidebar.html`, `templates/partials/recovery_dashboard_styles.html`. |

### 2.3 Exit Intent UI

- **V2:** **`cartflow_widget_triggers.js`** / **`cartflow_widget_flows.js`** (orchestration) with shell UI modules; duplicate open guards (e.g. **`[CF TRIGGER BLOCKED]`** paths) live in layered code.
- **Legacy:** Implemented inside **`static/cartflow_widget.js`** when that file is the only widget bootstrap.

Server-side template control (**`exit_intent_*`** on **`Store`**): `services/store_template_control.py` merge through **`/api/recovery-settings`**.

### 2.4 Cart Recovery UI

- **Dashboard:** recovery settings + cart recovery messages pages above.
- **Widget (V2):** layered **Ui / Flows / Api** backed by **`/api/cartflow/*`** helpers above.
- **Widget (legacy):** reason capture, handoff, and preview in **`cartflow_widget.js`** (including **`/api/cart-recovery/reason`** where wired).

**How UI interacts with backend:** JSON `fetch` / XHR to FastAPI routes; dashboards use embedded scripts or `static/cartflow_dashboard_messages.js` for shared save/load patterns against **`/api/recovery-settings`**.

---

## 3) Backend Layer

### 3.1 FastAPI structure

- **`main.py`** — Core app: mounts `static/`, registers routers, **`POST /api/cart-event`**, **`/api/recovery-settings`**, **`/api/conversion`**, webhooks, **`GET /dashboard`**, **demo / commerce sandbox** routes (see §3.2.1), recovery sequence orchestration.
- **`routes/cartflow.py`** — `APIRouter(prefix="/api/cartflow")`: analytics, ready, public-config, generate-whatsapp-message, reason, etc.
- **`routes/cart_recovery_reason.py`** — `APIRouter(prefix="/api/cart-recovery")`: **`POST /reason`** (widget reason persistence).
- **`routes/ops.py`**, **`routes/demo_panel.py`** — operational / demo utilities.

### 3.2 Routes (representative)

| Route | Module | Role |
|--------|--------|------|
| `POST /api/cart-event` | `main.py` | Cart events (`cart_abandoned`, conversion flags, etc.). |
| `GET` / `POST /api/recovery-settings` | `main.py` | Store recovery + template + widget + VIP threshold merge/persist. |
| `POST /api/conversion` | `main.py` | Marks session converted; stops recovery. |
| `POST /api/cart-recovery/reason` | `routes/cart_recovery_reason.py` | Upsert `CartRecoveryReason` (Layer D). |
| `GET /api/cartflow/*`, `POST /api/cartflow/*` | `routes/cartflow.py` | Readiness, mock messages, analytics. |
| `GET /api/dashboard/recovery-trend` | `main.py` | Dashboard chart data. |
| `POST /api/dashboard/vip-cart/{cart_row_id}/merchant-alert` | `main.py` | VIP لوحة: تنبيه واتساب للتاجر فقط (`build_vip_merchant_alert_body` + `try_send_vip_merchant_whatsapp_alert`؛ `store_whatsapp_number` ثم `whatsapp_support_url`). |
| `POST /api/carts/{id}/send` | `main.py` | إرسال يدوي للعميل على الصفحة الرئيسية للوحة (`send_whatsapp_message` Meta path) — **ليس مسار VIP**. |
| `POST /dev/create-vip-test-cart` | `main.py` | Seed حقيقي: `AbandonedCart` VIP + `CartRecoveryReason` جلسة `test_vip_session` بدون ودجت (مسموح في الإنتاج عبر قائمة `_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`). |
| `GET /dev/widget-test`, `/dev/widget-test/cart` | `main.py` | **DEV-only legacy monolith harness** — HTML loads **`/static/cartflow_widget.js`** directly (no **`widget_loader`**, no **`cartflow_widget_runtime`**). **`no_dev_in_production`**: **`404`** unless **`ENV=development`**; intentionally **not** in **`_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT`**. **`/demo/store`** remains **layered V2**. |
| `POST /webhook/zid` | `main.py` | Zid webhook ingestion. |
| `POST` / `GET /webhook/whatsapp` | `main.py` | Twilio / inbound hook stubs (`[WA REPLY]` logging). |
| `GET /demo/store`, `/demo/store/cart`, `/demo/store/checkout`, `/demo/cart`, `/demo/cart/checkout`, `/demo/store/product/{id}` | `main.py` | **Commerce sandbox (default `store_slug=demo`):** multi-page catalog, cart, lightweight checkout. |
| `GET /demo/store2`, `/demo/store2/cart`, `/demo/store2/checkout`, `/demo/store2/product/{id}` | `main.py` | Same UI with **isolation** (`demo2` slug / `demo2_cart` localStorage) for recovery tests. |

### 3.2.1 Demo commerce sandbox (v1) — reference

**Purpose:** One in-app “realistic lightweight store” that exercises the **real** recovery pipeline (cart events, continuation, dashboard, offers/product intelligence when configured) without replacing production widget architecture.

| Piece | Location / behavior |
|--------|---------------------|
| **Catalog (data)** | **`services/demo_sandbox_catalog.py`** — `SANDBOX_PRODUCTS`, `SANDBOX_PRODUCT_ORDER`, PDP numbering (`SANDBOX_PRODUCT_KEY_BY_NUM`). Fields: `id`, `sku`, `name`, `price` / `unit_price`, `category`, **`normalized_category`**, **`product_family`** (per SKU), descriptions, `url` / `image` (picsum seeds), **`related_keys`**, **`cheaper_alternative_keys`**, **`available`**. **Rule-first only** (no AI): relationships are explicit lists on each SKU. |
| **URLs per store** | `product_demo_url(nav_base, key)` — `/demo/store/...` vs `/demo/store2/...` so `demo2` PDP links stay isolated. |
| **Merchant sync** | `merchant_catalog_for_intelligence_sync()` / `merchant_catalog_json_string()` — JSON shaped for **`product_catalog`** in **`/api/recovery-settings`** (paste in dashboard **العروض الذكية** so intelligence and offers match real catalog rows). Rows may include **`normalized_category`** and **`product_family`** for cheaper-matching (see **`cartflow_product_intelligence.py`**). Template context: `demo_merchant_catalog_json`. |
| **Store UI** | **`templates/demo_store.html`** — grid from `demo_grid_rows`, `window.CF_DEMO_PRODUCTS` + `window.CF_DEMO_NAV_BASE` from server JSON; PDP with image + related links; cart **subtotal** + link to checkout; **checkout** page with **COD** button → **`window.cartflowTriggerDemoConversion`** → **`POST /api/conversion`** (`purchase_completed: true`), then local cart clear + client converted flag (same as demo panel). |
| **Demo panel** | **`static/cartflow_demo_panel.js`** — cart page only UI; **`cartflowStartDemoScenario`** seeds **`hp_pro`** first (premium headphones) to surface **cheaper-alternative** scenarios; **`cartflowTriggerDemoConversion`** exported for checkout page. |
| **Abandon payload shape** | Demo sends **`cart` as a JSON array** of line objects (`id`, `name`, `price`, `category`, …). **`services/recovery_product_context.py`** `_first_line_items_list` accepts **`cart` as list** so product context / intelligence see line items. |
| **Tests** | `tests/test_demo_behavioral_navigation.py` (routes, checkout), `tests/test_cart_recovery_sequence_behavior.py`, `tests/test_recovery_product_context.py` (list-cart case). |

**Do not use the sandbox as:** a second application or a bypass of lifecycle, continuation, or dashboard settings — it is wired to the same APIs and session keys as the existing demo.

### 3.3 Services (`services/`)

| Area | Modules |
|------|---------|
| WhatsApp send / gates | `whatsapp_send.py` (`send_whatsapp`, `should_send_whatsapp`), `whatsapp_recovery.py`, `whatsapp_queue.py` |
| Delays | `recovery_delay.py` (`get_recovery_delay` per tag), timing also in `whatsapp_send.recovery_delay_to_seconds` from `Store` |
| Multi-message | `recovery_multi_message.py` (`multi_message_slots_for_abandon`) |
| Reason templates | `reason_template_recovery.py`, `store_reason_templates.py`, `recovery_message_templates.py` |
| Decision | `decision_engine.py` (Layer D.2 message/action); `main` imports `decide_recovery_action` via `decision_engine.py` shim |
| VIP | `vip_cart.py` (`is_vip_cart`, `merchant_vip_threshold_int`, `vip_operational_lane_diagnostics`, `abandoned_cart_in_vip_operational_lane`), `vip_merchant_alert.py` (merchant-only Twilio alert) |
| Session phone | `recovery_session_phone.py` |
| Store JSON fields | `store_trigger_templates.py`, `store_template_control.py`, `store_widget_customization.py` |
| AI / copy | `ai_message_builder.py` |
| Demo commerce catalog | `demo_sandbox_catalog.py` — static SKUs, grid/JS maps, merchant `product_catalog` export (§3.2.1). |
| Product context from cart | `recovery_product_context.py` — infers cheaper alternative from line items; supports **`cart` as list** for demo payloads. |
| Cheaper-product matching (continuation only) | `cartflow_product_intelligence.py` — normalized category / type signals, **`cheaper_candidate_score`**, strict lower-price + availability, structured logs (`[ALTERNATIVE REJECTED]`, `[ALTERNATIVE SCORE]`, `[FALLBACK USED]`); catalog normalization in **`cartflow_merchant_offer_settings.normalize_product_catalog`**. |

### 3.4 Database models

Defined in **`models.py`**; optional columns ensured at runtime via **`schema_widget.ensure_store_widget_schema`**.

---

## 4) Core Logic Layer (Hard-core)

### 4.1 Detection Logic (Layer B)

- **`config_system.py`** — `get_cartflow_config(store_slug=...)`: isolated defaults (`recovery_delay_minutes`, `max_recovery_attempts`, `whatsapp_recovery_enabled`, etc.). Documented in code as **Layer B** (no DB required).
- **`services/whatsapp_send.py`** — `_recovery_config(store)` merges Layer B with store slug via `get_cartflow_config` for delay / attempt gates inside **`should_send_whatsapp`**.

### 4.2 Reason Capture (Layer C / D)

- **Layer D (persistence)** — **`POST /api/cart-recovery/reason`** in `routes/cart_recovery_reason.py`: validates payload, upserts **`CartRecoveryReason`** (`store_slug`, `session_id`, `reason`, `sub_category`, `custom_text`, `customer_phone`, `user_rejected_help`, etc.).
- Widget stores session keys and posts **`reason_tag`** aligned with dashboard / templates (see layered sources and comments in **`cartflow_widget.js`**).

### 4.3 Persistence (Layer D)

- **`CartRecoveryReason`** — last reason per `(store_slug, session_id)`; drives `updated_at` / last activity for delay checks.
- **`CartRecoveryLog`** — append-only recovery attempts (`status`, `step`, `message`, …); includes **`vip_manual_handling`** for VIP dashboard lines.
- **`AbandonedCart`** — `zid_cart_id`, `cart_value`, `vip_mode`, etc.; VIP threshold comparison uses **`_abandoned_cart_cart_value_for_recovery`** in `main.py`.
- **`Store`** — recovery delays, units, attempts, templates, `vip_cart_threshold`, WhatsApp fields.
- **`schema_widget.py`** — idempotent `ALTER TABLE` helpers so ORM matches SQLite/Postgres deployments.

### 4.4 Decision Engine (D.2)

- **`services/decision_engine.py`** — `decide_recovery_action(reason_tag, store=..., is_vip_cart_flag=False)`:
  - **Normal:** maps reason → `action` + message via **`resolve_whatsapp_recovery_template_message`**؛ يُعاد أيضاً **`send_customer: true`** و **`send_merchant: false`**.
  - **VIP (`is_vip_cart_flag=True`):** قبل أي منطق قوالب — يُعاد **`action: vip_manual_handling`**, **`message: ""`**, **`send_customer: false`**, **`send_merchant: true`** مع سجل **`[VIP OVERRIDE ACTIVATED]`**, **`[VIP FLOW STOPPED]`**, **`[VIP CUSTOMER BLOCKED]`**.
- **`main._vip_recovery_decision_layer(reason_tag, store)`** يستدعي المحرك مع **`is_vip_cart_flag=True`** عند مسارات VIP في `main.py`.
- **Production recovery text** إلى العميل يمر غالباً بـ **`reason_template_recovery.resolve_recovery_whatsapp_message_with_reason_templates`** داخل **`main._run_recovery_sequence_after_cart_abandoned_impl`**؛ مسار VIP يوقف ذلك قبل الإرسال.

### 4.5 WhatsApp Integration (D.3)

- **Customer recovery (Twilio):** **`send_whatsapp`** in `services/whatsapp_send.py` — called from **`main._run_recovery_sequence_after_cart_abandoned_impl`** after gates. Logs **`[WA SEND PATH]`**, **`[WA SENT]`**, **`[WA STATUS]`** when trace/env allows.
- **Customer manual / CTA:** **`send_whatsapp_message`** in `main.py` — Meta Graph interactive `cta_url` (**`/api/carts/{id}/send`**).
- **Gates:** **`_blocked_send_whatsapp_if_user_rejected_help`** prints **`[BLOCK WA - USER REJECTED HELP]`**; **`should_send_whatsapp`** implements quiet period vs `CartRecoveryReason.updated_at`.

### 4.6 Delay Logic

1. **`handle_cart_abandoned`** claims session (`_try_claim_recovery_session`), loads store, **VIP short-circuit** (see §4.9), else may schedule **multi** or async **`_run_recovery_dispatch_cart_abandoned`**.
2. **`_run_recovery_dispatch_cart_abandoned_impl`** polls **`_reason_tag_for_session`**, then either **`_schedule_recovery_multi_slots`** or computes **`get_recovery_delay`** (`services/recovery_delay.py`) vs elapsed time, then **`asyncio.create_task(_run_recovery_sequence_after_cart_abandoned(..., delay_seconds=remain))`**.
3. **`_run_recovery_sequence_after_cart_abandoned_impl`**: **فحص VIP قبل **`asyncio.sleep`**** (خرج بدون إرسال عميل ولا انتظار)، ثم **`await asyncio.sleep(delay_seconds)`** → dedupe → conversion / user-rejected → **فحص VIP ثانٍ** دفاعيًا → القوالب و**`should_send_whatsapp`** و**`send_whatsapp`** للعميل حسب المسارات غير المحظورة.

Print-style trace: **`[DELAY STARTED]`**, **`[DELAY WAITING]`**, **`[DELAY FINISHED]`**, **`[CARTFLOW DELAY CHECK]`**, **`[DELAY BLOCKED]`**, **`[DELAY CONFIG]`** (from `whatsapp_send`).

### 4.7 Multi-message logic

- **`services/recovery_multi_message.multi_message_slots_for_abandon(reason_tag, store)`** — reads **`Store.reason_templates_json`**; if enabled and multiple messages → list of `{index, delay_seconds, text}`.
- **`main._schedule_recovery_multi_slots`** — one asyncio task per slot, each calling **`_run_recovery_sequence_after_cart_abandoned`** with **`multi_slot_index`** / **`multi_message_text`**.
- Logs: **`[MULTI MESSAGE MODE ACTIVATED]`**, **`[MULTI MESSAGE SCHEDULED]`**, **`[MULTI WA SEND ATTEMPT]`**, **`[MULTI WA SEND RESULT]`**, **`[MULTI MESSAGE SENT]`**, **`[MULTI MESSAGE FAILED]`**, **`[RECOVERY FULLY COMPLETED]`**.

### 4.8 Per-reason system

- **`get_recovery_delay(reason_tag, store_config)`** — per-tag default seconds in `services/recovery_delay.py` (extendable via `store_config.recovery_delays` if passed).
- **Reason templates** — `reason_templates_json` + `reason_template_recovery` / `store_reason_templates` / `recovery_message_templates` control message body and whether WhatsApp is blocked for a reason.

### 4.9 VIP handling

- **Threshold:** **`Store.vip_cart_threshold`** (null → VIP ignored); مجموع السلة من **`_abandoned_cart_cart_value_for_recovery`** / الحمولة مقابل **`services/vip_cart.is_vip_cart(cart_total, store)`**. **`cart_value`** مفقود → لا اعتبار VIP في الإشارة الأولى؛ يمكن للمهام اللاحقة إعادة التقييم.
- **لوحة السلال — مسار واحد:** **`/dashboard/normal-carts`** يستبعد السلال حيث `cart_value >= vip_cart_threshold`؛ **`/dashboard/vip-cart-settings`** يعرضها فقط عند وجود عتبة صالحة. التشخيص في JSON البطاقة: `cart_total`, `vip_threshold`, `is_vip_cart`, `operational_lane` (`normal` \| `vip`). **`vip_mode`** في DB يبقى للمزامنة/الاسترجاع؛ العرض والـ **`POST …/merchant-alert`** و**`…/lifecycle`** يعتمدون **`is_vip_cart`** على العتبة.
- **طبقة قرار D.2:** **`_vip_recovery_decision_layer`** → **`decide_recovery_action(..., is_vip_cart_flag=True)`**؛ لا إرسال قوالب للعميل من المحرك عند هذا العلم.
- **Activation:** **`main._activate_vip_manual_cart_handling`** يضع **`vip_mode`**، **`CartRecoveryLog`** بـ **`status=vip_manual_handling`**، **`try_send_vip_merchant_whatsapp_alert`** (نص: **`build_vip_merchant_alert_body`**؛ هدف: **`store_whatsapp_number`** ثم **`whatsapp_support_url`** القابل للتحليل)، ويضبط **`_session_recovery_sent`** عند النجاح أو عند كان **`vip_mode`** مفعّلاً مسبقاً؛ **`_mark_vip_customer_recovery_closed`** يمنع أي إرسال متابعة للعميل لهذه الجلسة بعد اعتبار السلة VIP في **`handle_cart_abandoned`**.
- **بدون عميل مهما كان تفعيل DB:** إذا **`is_vip_cart`** صحيحة في **`handle_cart_abandoned`** أو **`_run_recovery_dispatch_cart_abandoned_impl`** → لا يُجدول **`multi`** ولا **`_run_recovery_sequence`** كمسار عميل؛ فشل تمييز DB لا يفعّل **fallback** إلى استرداد عميل أوتوماتيكي. في **`_run_recovery_sequence_after_cart_abandoned_impl`**: فحص VIP **قبل **`asyncio.sleep`**** لعدم تأخير VIP؛ فحص لاحق دفاعي بعد التأخير يمنع **`send_whatsapp`** للعميل.
- **لوحة VIP — إرسال يدوي:** **`POST /api/dashboard/vip-cart/{id}/merchant-alert`**؛ سجل **`[VIP MANUAL SEND CLICKED]`**؛ نفس **`try_send_vip_merchant_whatsapp_alert`** مع رسالة UX عربية (**`لا يوجد رقم واتساب للمتجر`** عند انعدام الرقم).
- **اختبار بدون ودجت:** **`POST /dev/create-vip-test-cart`** ينشئ **`AbandonedCart`** ثابت `zid_cart_id=vip-codegen-test-cart-1` (**`cart_value=1200`**, **`vip_mode=true`**, **`status=abandoned`**) + **`CartRecoveryReason`** (**`session_id=test_vip_session`**, **`reason=price`**); يبيّن في قائمة أولوية VIP عند **`interactive`** حقيقية.
- **Logs (جزء):** **`[VIP CHECK]`**, **`[VIP MODE ACTIVATED]`**, **`[VIP CUSTOMER RECOVERY SKIPPED]`**, **`[VIP ACTIVATION FAILED]`**, **`[VIP MANUAL SEND CLICKED]`**, **`[VIP MERCHANT ALERT ATTEMPT]`**, **`[VIP MERCHANT ALERT SENT]`**, **`[VIP MERCHANT ALERT FAILED] reason=…`** (**`vip_merchant_alert.py`**).

---

## 5) End-to-End Flow

**Widget → Backend → Decision → Delay → WhatsApp → Dashboard**

1. User interacts with the layered **V2** runtime (`cartflow_widget_runtime/**`) or legacy **`cartflow_widget.js`** on the storefront; reason persistence follows the active surface (`/api/cartflow/reason` vs `/api/cart-recovery/reason`) → row in **`cart_recovery_reasons`** when applicable.
2. Store platform (or demo) sends **`POST /api/cart-event`** with `event: cart_abandoned`, `store`, `session_id`, optional `cart_id` / `phone`.
3. **`handle_cart_abandoned`**: conversion / duplicate / claim checks → load **`Store`** → **إذا VIP** (`is_vip_cart`): استدعاء **`_vip_recovery_decision_layer`** ثم **`_activate_vip_manual_cart_handling`** ثم **`_mark_vip_customer_recovery_closed`** و**`return`** (لا جدولة إرسال للعميل حتى لو فشل جزء التفعيل).
4. If **multi_message_slots_for_abandon** returns slots → schedule delayed tasks per slot; else **`_run_recovery_dispatch_cart_abandoned`** waits for reason if needed, then schedules **one** delayed **`_run_recovery_sequence_after_cart_abandoned`**.
5. After sleep (غير مسار VIP المتوقَّف مسبقاً): **VIP guard** دفاعي؛ ثم رسائل القوالب و**`should_send_whatsapp`** و**`send_whatsapp`** للعميل فقط خارج VIP.
6. **`_persist_cart_recovery_log`** records queued / sent / skipped / VIP rows.
7. **Dashboard** **`GET /dashboard`** — KPIs وأسباب ونشاط من **`AbandonedCart`** / **`CartRecoveryReason`** فقط. **قائمة أولوية VIP** في **`GET /dashboard/vip-cart-settings`** عبر **`_vip_priority_cart_alert_list()`** (الاسم **`_vip_cart_alerts_merchant_list()`** alias للتوافق؛ بدون تكرار في الرئيسية).

---

## 6) Data Models

### `Store` (`stores`)

Recovery: `recovery_delay`, `recovery_delay_unit`, `recovery_attempts`, `recovery_delay_minutes`. WhatsApp / UX: `whatsapp_support_url`, `store_whatsapp_number`, per-reason templates (`template_*`, `trigger_templates_json`, `reason_templates_json`), `template_mode` / `tone` / `template_custom_text`, exit intent fields, widget customization (`widget_name`, `widget_primary_color`, `widget_style`). **VIP:** `vip_cart_threshold`.

### `AbandonedCart` (`abandoned_carts`)

`zid_cart_id`, `cart_value`, `status`, URLs, timestamps, **`vip_mode`**, `raw_payload`, optional `store_id`.

### Recovery-related

- **`CartRecoveryReason`** — last widget reason + phones + rejection flags.
- **`CartRecoveryLog`** — recovery audit trail (`status`, `step`, `message`, …); statuses include **`vip_manual_handling`**, **`mock_sent`**, **`skipped_*`**, **`stopped_converted`**, etc.
- **`AbandonmentReasonLog`**, **`ObjectionTrack`**, **`RecoveryEvent`**, **`MessageLog`** — ancillary tracking / webhooks / messaging history as used across routes and webhooks.

---

## 7) Logs & Debugging

| Log / prefix | Where |
|----------------|--------|
| `[CF API]` | `main.handle_cart_abandoned` / cart-event |
| `[VIP OVERRIDE ACTIVATED]`, `[VIP FLOW STOPPED]`, `[VIP CUSTOMER BLOCKED]` | `services/decision_engine.py` (عند `is_vip_cart_flag`) |
| `[VIP CHECK]`, `[VIP MODE ACTIVATED]`, `[VIP CUSTOMER RECOVERY SKIPPED]`, `[VIP ACTIVATION FAILED]`, **`[VIP MANUAL SEND CLICKED]`** | `main.py` |
| `[VIP MERCHANT ALERT ATTEMPT]`, `[VIP MERCHANT ALERT SENT]`, **`[VIP MERCHANT ALERT FAILED]`** | `services/vip_merchant_alert.py` |
| `[DELAY STARTED]`, `[DELAY WAITING]`, `[DELAY FINISHED]`, `[DELAY BLOCKED]` | `main._run_recovery_sequence_after_cart_abandoned_impl` |
| `[CARTFLOW DELAY CHECK]`, `[CARTFLOW PRO LOGIC]` | `main.py` |
| `[DELAY CONFIG]` | `services/whatsapp_send.py` |
| `[MULTI MESSAGE *]` | `main.py` |
| `[WA SEND PATH]`, `[WA SEND REASON]`, … | `services/whatsapp_send.emit_recovery_wa_send_trace` |
| `[WA SENT]`, `[WA STATUS]` | `services/whatsapp_send.send_whatsapp` |
| `[BLOCK WA - USER REJECTED HELP]` | `services/whatsapp_send.py` |
| `[SKIP WA - USER REJECTED HELP]`, `[SKIP WA - MISSING REASON_TAG]`, `[SKIP WA - MISSING LAST_ACTIVITY]` | `main.py` |
| `[PHONE RESOLUTION]` | `main._log_phone_resolution` |
| `[WA SENDER MODE]` | `main.resolve_whatsapp_sender` |
| `[PHONE ATTACHED]` | `routes/cart_recovery_reason.py` |
| `[WA REPLY]`, `[WA FROM]` | `main` webhook/whatsapp |
| `[RECOVERY TASK EXIT CLEANLY]`, `[RECOVERY TASK CAUGHT ERROR]`, `[RECOVERY DISPATCH *]` | `main.py` |
| `[ANTI SPAM CHECK]`, `[ATTEMPT CONTROL]`, `[ATTEMPT BLOCKED]`, `[NO VERIFIED PHONE]` | `main.py` |
| `[WHATSAPP TEST]` | `main` dev endpoint |

---

## 8) Known Limitations

- **Two WhatsApp stacks:** Twilio (`send_whatsapp`) for scheduled recovery vs Meta Cloud (`send_whatsapp_message`) for manual cart send — different configuration and behavior.
- **Layer B vs DB:** `config_system` defaults apply when store-specific DB fields are null; merchants must align dashboard **Store** rows and migrations.
- **VIP merchant alert:** depends on **`store_whatsapp_number`** or parsable **`whatsapp_support_url`**; otherwise **`[VIP MERCHANT ALERT FAILED] reason=no_merchant_phone`** (لوحة: **`لا يوجد رقم واتساب للمتجر`**).
- **`/webhook/whatsapp`:** minimal handler (prints body); not a full inbound conversation engine.
- **Schema drift:** legacy SQLite DBs need **`schema_widget.ensure_store_widget_schema`** (called from critical paths) so new ORM columns exist.
- **Dual widget bundles:** **default** merchant embed loads **V2** only; **`cartflow_widget.js`** is **explicit rollback** (**`__CARTFLOW_ALLOW_LEGACY_WIDGET`**) or **dev harness** — not the default **`widget_loader`** outcome. **`cartflow_widget.js`** remains large; contributors and **operational tests** still grep **`/api/`** / static markers in **both** trees.

---

## 9) Final Status

| Capability | Status |
|------------|--------|
| Widget → API (reason, config, ready, mock message) | ✅ |
| Detection (Layer B config + store merge) | ✅ |
| Reason capture (`/api/cart-recovery/reason`, `CartRecoveryReason`) | ✅ |
| Persistence (ORM + `schema_widget` + logs) | ✅ |
| Decision engine (D.2 `decide_recovery_action` + template resolution in recovery path) | ✅ |
| WhatsApp send (customer recovery via Twilio gate path) | 🟡 (requires `PRODUCTION_MODE` + Twilio env for real sends; mock otherwise) |
| WhatsApp receive (`/webhook/whatsapp`) | 🟡 (stub / logging) |
| Multi-message (reason templates + scheduled slots) | ✅ |
| Per-reason delay (`get_recovery_delay` + store quiet period in `should_send_whatsapp`) | ✅ |
| VIP (عتبة التاجر فقط، مسار لوحة واحد مقابل عادي، decision-layer override، تنبيه تاجر، لوحة **`vip-cart-settings`** + **`POST …/merchant-alert`**, **`/dev/create-vip-test-cart`**) | ✅ |

**Legend:** ✅ implemented and wired in code · 🟡 partial or environment-dependent · ❌ not implemented

---

## 10) Recent updates (changelog)

**Convention:** After substantive project changes, append a short dated entry here so this file stays the single high-level record of behavior and wiring. **Maintain this section on every substantive change.** Cursor agents: see **`.cursor/rules/system-summary-always-update.mdc`** (`alwaysApply`) — update §10 and any affected sections **as part of the same task** before considering the work complete.

| Date (UTC) | Summary |
|------------|---------|
| 2026-05-17 | **Admin risk severity tiers:** operational control v2 — levels 0–3 (سليم / تحذير / خطر فعلي / أزمة), impact truth when affected=0, «لماذا؟» on actions, timeline severity colors. Commit: **`fix: add operational risk severity tiers and reduce false alarms`**. |
| 2026-05-17 | **Admin Operational Control v2:** `/admin/operational-health` — risk summary, impact, suggested actions, verification, revenue protection, timeline; modules under `services/admin_operational_control/`. Commit: **`feat: evolve admin operational health into operational control v2`**. |
| 2026-05-17 | **Admin Operational Health v1:** `GET /admin/operational-health` — read-only cards (cart-event, DB pool, background tasks, WhatsApp, warnings); `services/admin_operational_health.py`; same admin auth as `/admin/operations`. Commit: **`feat: add admin operational health v1`**. |
| 2026-05-17 | **Recovery attempts copy aligned with lifecycle:** `merchant_recovery_attempts_display_ar` — follow-up «محاولات الاسترداد» matches send count / customer reply (no «لا توجد رسائل» when a message was sent). Commit: **`ux: align recovery attempts wording with lifecycle truth`**. |
| 2026-05-17 | **Merchant dashboard reasoning truth (read-only):** Compact «الرسالة / الهدف / رد العميل» from `message_preview`, `reason_tag`, inbound reply — `services/merchant_lifecycle_reasoning_display.py` + interpretation partial / lazy JS. Commit: **`ux: expose compact reasoning truth in merchant lifecycle`**. |
| 2026-05-17 | **Merchant dashboard compact lifecycle copy:** Short labels (الحالة الحالية / الانتظار / الإجراء / تدخل التاجر: نعم|لا) in interpretation partial + `merchant_dashboard_lazy.js`; simplified completed-page list; no backend changes. Commit: **`ux: simplify lifecycle interpretation language`**. |
| 2026-05-17 | **Merchant dashboard sections (automation-first):** Nav/pages renamed — «سلال الانتظار» (carts), «سلال التفاعل» (follow-up), placeholder «السلال المكتملة»; removed default WhatsApp «متابعة يدوية» on normal/follow-up rows; 4-part lifecycle interpretation block in UI. Commit: **`ux: align dashboard lifecycle sections with automation-first recovery`**. |
| 2026-05-17 | **Merchant dashboard lifecycle copy (automation-first):** Arabic strings in `cartflow_merchant_lifecycle.py`, `merchant_normal_recovery_summary.py`, `merchant_recovery_lifecycle_truth.py`, clarity/blocker display, and VIP/follow-up buttons in `merchant_dashboard_lazy.js` — emphasize automatic continuation; «قد تحتاج تدخل التاجر» only for failures/blockers/VIP manual paths. Commit: **`ux: align dashboard lifecycle wording with automation behavior`**. |
| 2026-05-17 | **Merchant dashboard recovery lifecycle truth (read-only):** `services/merchant_recovery_lifecycle_truth.py` exposes WhatsApp sent/preview, return-to-site, purchase, and lifecycle labels on normal-cart API payloads and merchant UI (`merchant_dashboard_lazy.js`, ops normal-carts table partial). Commit: **`feat: show recovery lifecycle truth in merchant dashboard`**. |
| 2026-05-17 | **DB foundation / cart-event hot path:** `services/db_session_lifecycle.py` — release scoped sessions before recovery `asyncio.sleep`, isolate background tasks, clear inherited `cart_event` ORM caches; `[CART-EVENT] start/end` ops logs; Postgres `pool_reset_on_return=rollback`; report **`docs/db_foundation_stabilization.md`**. Commit: **`fix: stabilize db session lifecycle and cart event hot path`**. |
| 2026-05-13 | **Widget architecture audit (post-V2 default):** §2.1 loader branching corrected (**default V2** via **`loadLayeredV2 = runtimeV2Explicit \|\| !legacyExplicit`**); **`cartflow_widget.js`** row clarified (**rollback / dev / tests**, not default shim path); new §**2.1.1** operational posture (serial module chain, bundle sizes ~118 KB V2 modules vs ~337 KB legacy, **Moderate** maint./perf risk); §8 dual-bundle bullet aligned. Evidence: **`static/widget_loader.js`**, **`static/cartflow_widget_runtime/cartflow_widget_loader.js`**, **`templates/demo_store.html`**, **`templates/general_settings.html`**. |
| 2026-05-13 | **Legacy dev harness isolation:** **`/dev/widget-test`** pages as **DEV-only** legacy **`cartflow_widget.js`** harness (`main._DEV_LEGACY_WIDGET_HARNESS_HTML`); clarified **omit** from production **`_DEV_ROUTES`** allowlist (**`404`** unless **`ENV=development`**). Docs: **`widget_legacy_cleanup_audit`**, **`cartflow_production_readiness.md`**, §3.2 route row; **`tests/test_cartflow_production_readiness.py`**. **`/demo/store`** + V2 runtime unchanged. Commit: **`chore: isolate legacy widget dev harness`**. |
| 2026-05-13 | **Widget docs vs V2 isolation:** **`docs/SYSTEM_SUMMARY.md`** §2.1–2.4, §5, §8 — document **`widget_loader`** V2 vs legacy branching, **`cartflow_widget_runtime/**`**, **`/demo/store*`** coercion, **`mirrorCartTotals()`** VIP (no layered legacy injection); align end-to-end and limitation bullets. Chore with **`docs/cartflow_operational_risk_test_report.md`** + **`docs/widget_legacy_cleanup_audit.md`** (Tier 1 doc cleanup per cleanup audit). Commit: **`chore: remove safe legacy widget cleanup candidates`**. |
| 2026-05-11 | **Operational / enterprise testing pack:** **`docs/operational/ENTERPRISE_TESTING.md`** — k6 stress script **`synthetic/k6/widget-recovery-stress.js`** (smoke vs `LOAD_PROFILE=full`, p95 under 1s thresholds, `GET /health?db=1` probe), HTML summary output + **`scripts/reports/k6_summary_to_html.py`**; **Promptfoo** matrix (`promptfoo/`, 50 cases in **`tests.generated.yaml`**, stub JS provider); **pytest** discipline matrix **`tests/operational/test_enterprise_message_discipline_matrix.py`**; **Sentry** optional init **`services/cartflow_sentry.py`** + Twilio failure capture; **E2E** **`e2e/cartflow-lifecycle.spec.ts`**; **`GET /health?db=1`** DB probe in **`routes/ops.py`**. |
| 2026-05-10 | **Reason vs phone capture:** `vip_phone_capture` no longer overwrites **`CartRecoveryReason.reason`** when an objection tag (e.g. **`price_high`**, **`price`** + sub) is already stored — phone is attached only; audit row **`AbandonmentReasonLog`** unchanged. Implemented in **`routes/cartflow.py`**, **`routes/cart_recovery_reason.py`**, helper **`services/recovery_reason_preserve.py`**. Commit: **`fix: preserve objection reason during phone capture`**. |
| 2026-05-10 | **Product matching v1:** `cartflow_product_intelligence.py` — canonical category buckets (synonyms e.g. عطور / العناية والتجميل), **`cheaper_candidate_score`** (family, type, name overlap, closest lower price), safer strict price compare, `[ALTERNATIVE REJECTED]` / `[ALTERNATIVE SCORE]` / consolidated `[FALLBACK USED]`; snapshot **`alternative_score`** / **`fallback_reason`**; continuation vars **`cheaper_candidate_score`**, **`cheaper_fallback_reason`**. Demo catalog **`normalized_category`**, **`product_family`**; **`normalize_product_catalog`** preserves optional fields; merchant export includes them. Commit: **`improve product intelligence matching quality`**. |
| 2026-05-11 | **VIP vs عادي — مصدر حقيقة واحد للوحة:** تصنيف القائمة من **`Store.vip_cart_threshold`** و‎`is_vip_cart(cart_value, store)` فقط؛ استبعاد السلال العالية من **`/dashboard/normal-carts`**؛ قائمة VIP فارغة بدون عتبة؛ تشخيصات البطاقة + **`POST …/merchant-alert`** / **`lifecycle`** يتحققان من المسار التشغيلي وليس **`vip_mode`** وحدها؛ **`dev/create-vip-test-cart`** يشتق عتبة اختبار من قيمة السلة. Commit: **`fix: enforce single operational lane for vip and normal carts`**. |
| 2026-05-10 | **Agent convention:** `.cursor/rules/system-summary-always-update.mdc` (`alwaysApply`) — substantive tasks must update this document (§10 + affected sections). §10 convention text cross-references the rule. Commit: **`chore: enforce SYSTEM_SUMMARY updates via Cursor rule`**. |
| 2026-05-10 | **Commerce sandbox v1:** `services/demo_sandbox_catalog.py` (multi-category catalog, rule-first `related_keys` / `cheaper_alternative_keys`, merchant JSON for `product_catalog`); `templates/demo_store.html` (grid, PDP, cart total, `/demo/*/checkout` + fake COD → `POST /api/conversion`); `recovery_product_context` list-`cart` support; `cartflow_demo_panel.js` (`hp_pro` scenario, `cartflowTriggerDemoConversion`). Commit: **`feat: upgrade demo into realistic commerce sandbox v1`**. |
| 2026-05-03 | **لوحة VIP — أولوية مقابل تجريبي:** قسم **أولوية** مربوط بقاعدة البيانات فقط (`vip_mode` ∪ `CartRecoveryLog` بـ **`vip_manual_handling`** على `zid_cart_id`)؛ لا دمج صفوف **`demo_vip_cart_zid`** في الأولوية؛ قسم **بيانات تجريبية** منفصل. Commit: **`fix: bind VIP priority tab to real VIP carts`**. |
| 2026-05-03 | **VIP في محرّك القرار:** `decide_recovery_action(..., is_vip_cart_flag)` يعيد **`vip_manual_handling`** مع **`send_customer/send_merchant`**؛ لا **fallback** لاسترداد عميل بعد VIP؛ فحص قبل التأخير؛ سجلات D.2. Commit: **`fix: move VIP to decision engine override (real behavior)`**. |
| 2026-05-03 | **لوحة VIP — إرسال يدوي:** **`POST /api/dashboard/vip-cart/{id}/merchant-alert`**؛ واجهة **`vip_cart_settings.html`**؛ **`interactive`** للصفوف التجريبية؛ رسائل **`تم إرسال تنبيه التاجر`** / **`لا يوجد رقم واتساب للمتجر`**؛ سجلات يدوية. Commit: **`feat: wire VIP manual send action`**. |
| 2026-05-03 | **بيانات VIP للاختبار:** **`POST /dev/create-vip-test-cart`** (+ إدراج في مسارات `/dev` المسموحة دون ENV). Commit: **`dev: add vip test cart generator`**. |
| 2026-05-03 | **صفحة عامة:** `GET /` — قالب تسويق (`templates/cartflow_landing.html`؛ تصميم نظيف أو صورة مرجع **`static/img/cartflow_landing_reference.jpg`** حسب الإصدار). |
| 2026-05-02 | *(تاريخي — أجزاء VIP تطورت لاحقاً في 2026-05-03)* **Full VIP integration:** مسار تفعيل أولي؛ لاحقاً استُبدل تسجيل القرار بـ **`_vip_recovery_decision_layer`** وإزالة **fallback** عميل؛ راجع §4.9. Commit: `feat: full VIP integration (backend + whatsapp + dashboard + override)`. |
| 2026-05-02 | *(تاريخي للواجهة)* تنبيهات VIP + زر إرسال في `vip_cart_settings`؛ اليوم الإرسال عبر **`POST /api/dashboard/vip-cart/.../merchant-alert`** لا **`POST /api/carts/.../send`**. Commit: `fix: activate VIP handling + …`. |
| 2026-05-02 | **صفحة عامة CartFlow:** `GET /` يعرض `templates/cartflow_landing.html` مع `static/cartflow_landing.css` + `cartflow_landing.js` (تمرير سلس للروابط الداخلية)؛ **`GET /register`** → `register_placeholder.html` (مؤقت، بدون OTP). الصفحة التسويقية عربية RTL مع تخطيط رأس LTR (شعار / تنقل / CTA) كما في المواصفات. Commit: `feat: add pixel-accurate CartFlow landing page`. |

---

*This document reflects the repository layout and control flow as of the last update (see §10); verify against `main.py`, `routes/`, `services/`, and `static/` for line-level changes.*
