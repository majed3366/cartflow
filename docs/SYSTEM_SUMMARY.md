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
| `static/widget_loader.js` | Injects `cartflow_widget.js` after `window.load` (skips if session marked converted via `sessionStorage` / `cartflowIsSessionConverted`). |
| `static/cartflow_widget.js` | Main widget: idle detection, reason UI, exit-intent flows, session keys for abandon reason, calls backend APIs. |
| `static/cart_abandon_tracking.js` | Included from dashboard templates (`partials/cart_abandon_tracking.html`) for analytics-style tracking where wired. |

**Primary backend calls from the widget (examples in `cartflow_widget.js`):**

- `POST /api/cart-recovery/reason` — persist widget **Layer D** reason (`routes/cart_recovery_reason.py`, router prefix `/api/cart-recovery`).
- `POST /api/cartflow/reason` — alternate/legacy reason path under `routes/cartflow.py` (`/api/cartflow/*`).
- `GET /api/recovery/primary-reason` — `main.py` route; widget uses for primary reason hints.
- `GET /api/cartflow/ready`, `GET /api/cartflow/public-config` — readiness / public widget config (`routes/cartflow.py`).
- `POST /api/cartflow/generate-whatsapp-message` — mock message text for UI preview (no DB write in that handler).

**Cart abandon signal to backend:** the storefront integration is expected to call **`POST /api/cart-event`** with `event: cart_abandoned` (handled in `main.handle_cart_abandoned` → recovery dispatch). The widget focuses on reasons and UX; the actual **abandon event** is typically from page / platform integration.

### 2.2 Dashboard UI

| Path / files | Purpose |
|--------------|---------|
| `GET /dashboard` | `dashboard_v1.html` — **الرئيسية**: KPIs، أسباب التردد، الرسم، **آخر النشاطات** (أسباب فقط — بدون VIP). |
| `GET /dashboard/recovery-settings` | `recovery_settings.html` — delay, attempts, WhatsApp fields; **`GET`/`POST /api/recovery-settings`**. |
| `GET /dashboard/vip-cart-settings` | `vip_cart_settings.html` — قسمان: **أولوية** (حقيقي فقط: `AbandonedCart` غير `recovered` حيث `vip_mode` **أو** `CartRecoveryLog.cart_id` = `zid_cart_id` مع `status=vip_manual_handling`) + **بيانات تجريبية** (صفوف ثابتة، `interactive: false`). **إرسال يدوي** → **`POST /api/dashboard/vip-cart/{abandoned_cart_row_id}/merchant-alert`** (تنبيه التاجر فقط؛ ليس `POST /api/carts/{id}/send`). عتبة VIP عبر **`/api/recovery-settings`**. |
| `GET /dashboard/exit-intent-settings` | `exit_intent_settings.html` — exit intent copy; loads/saves via recovery settings API + `static/cartflow_dashboard_messages.js`. |
| `GET /dashboard/cart-recovery-messages` | `cart_recovery_messages.html` — recovery message templates. |
| `GET /dashboard/widget-customization` | `widget_customization.html` — widget appearance. |
| Shared chrome | `templates/partials/dashboard_sidebar.html`, `templates/partials/recovery_dashboard_styles.html`. |

### 2.3 Exit Intent UI

Implemented inside **`static/cartflow_widget.js`** (exit-intent keys, pre-cart decline, smart exit with cart). Server-side template control: **`exit_intent_*`** columns on `Store`, applied via `services/store_template_control.py` and persisted through **`/api/recovery-settings`**.

### 2.4 Cart Recovery UI

- **Dashboard:** recovery settings + cart recovery messages pages above.
- **Widget:** reason capture, handoff, and message preview flows in **`cartflow_widget.js`** backed by **`/api/cart-recovery/reason`** and cartflow APIs.

**How UI interacts with backend:** JSON `fetch` / XHR to FastAPI routes; dashboards use embedded scripts or `static/cartflow_dashboard_messages.js` for shared save/load patterns against **`/api/recovery-settings`**.

---

## 3) Backend Layer

### 3.1 FastAPI structure

- **`main.py`** — Core app: mounts `static/`, registers routers, **`POST /api/cart-event`**, **`/api/recovery-settings`**, **`/api/conversion`**, webhooks, **`GET /dashboard`**, demo routes, recovery sequence orchestration.
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
| `POST /webhook/zid` | `main.py` | Zid webhook ingestion. |
| `POST` / `GET /webhook/whatsapp` | `main.py` | Twilio / inbound hook stubs (`[WA REPLY]` logging). |

### 3.3 Services (`services/`)

| Area | Modules |
|------|---------|
| WhatsApp send / gates | `whatsapp_send.py` (`send_whatsapp`, `should_send_whatsapp`), `whatsapp_recovery.py`, `whatsapp_queue.py` |
| Delays | `recovery_delay.py` (`get_recovery_delay` per tag), timing also in `whatsapp_send.recovery_delay_to_seconds` from `Store` |
| Multi-message | `recovery_multi_message.py` (`multi_message_slots_for_abandon`) |
| Reason templates | `reason_template_recovery.py`, `store_reason_templates.py`, `recovery_message_templates.py` |
| Decision | `decision_engine.py` (Layer D.2 message/action); `main` imports `decide_recovery_action` via `decision_engine.py` shim |
| VIP | `vip_cart.py` (`is_vip_cart`), `vip_merchant_alert.py` (merchant-only Twilio alert) |
| Session phone | `recovery_session_phone.py` |
| Store JSON fields | `store_trigger_templates.py`, `store_template_control.py`, `store_widget_customization.py` |
| AI / copy | `ai_message_builder.py` |

### 3.4 Database models

Defined in **`models.py`**; optional columns ensured at runtime via **`schema_widget.ensure_store_widget_schema`**.

---

## 4) Core Logic Layer (Hard-core)

### 4.1 Detection Logic (Layer B)

- **`config_system.py`** — `get_cartflow_config(store_slug=...)`: isolated defaults (`recovery_delay_minutes`, `max_recovery_attempts`, `whatsapp_recovery_enabled`, etc.). Documented in code as **Layer B** (no DB required).
- **`services/whatsapp_send.py`** — `_recovery_config(store)` merges Layer B with store slug via `get_cartflow_config` for delay / attempt gates inside **`should_send_whatsapp`**.

### 4.2 Reason Capture (Layer C / D)

- **Layer D (persistence)** — **`POST /api/cart-recovery/reason`** in `routes/cart_recovery_reason.py`: validates payload, upserts **`CartRecoveryReason`** (`store_slug`, `session_id`, `reason`, `sub_category`, `custom_text`, `customer_phone`, `user_rejected_help`, etc.).
- Widget stores session keys and posts **`reason_tag`** aligned with dashboard / templates (see comments in `cartflow_widget.js`).

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
- **طبقة قرار D.2:** **`_vip_recovery_decision_layer`** → **`decide_recovery_action(..., is_vip_cart_flag=True)`**؛ لا إرسال قوالب للعميل من المحرك عند هذا العلم.
- **Activation:** **`main._activate_vip_manual_cart_handling`** يضع **`vip_mode`**، **`CartRecoveryLog`** بـ **`status=vip_manual_handling`**، **`try_send_vip_merchant_whatsapp_alert`** (نص: **`build_vip_merchant_alert_body`**؛ هدف: **`store_whatsapp_number`** ثم **`whatsapp_support_url`** القابل للتحليل)، ويضبط **`_session_recovery_sent`** عند النجاح أو عند كان **`vip_mode`** مفعّلاً مسبقاً؛ **`_mark_vip_customer_recovery_closed`** يمنع أي إرسال متابعة للعميل لهذه الجلسة بعد اعتبار السلة VIP في **`handle_cart_abandoned`**.
- **بدون عميل مهما كان تفعيل DB:** إذا **`is_vip_cart`** صحيحة في **`handle_cart_abandoned`** أو **`_run_recovery_dispatch_cart_abandoned_impl`** → لا يُجدول **`multi`** ولا **`_run_recovery_sequence`** كمسار عميل؛ فشل تمييز DB لا يفعّل **fallback** إلى استرداد عميل أوتوماتيكي. في **`_run_recovery_sequence_after_cart_abandoned_impl`**: فحص VIP **قبل **`asyncio.sleep`**** لعدم تأخير VIP؛ فحص لاحق دفاعي بعد التأخير يمنع **`send_whatsapp`** للعميل.
- **لوحة VIP — إرسال يدوي:** **`POST /api/dashboard/vip-cart/{id}/merchant-alert`**؛ سجل **`[VIP MANUAL SEND CLICKED]`**؛ نفس **`try_send_vip_merchant_whatsapp_alert`** مع رسالة UX عربية (**`لا يوجد رقم واتساب للمتجر`** عند انعدام الرقم).
- **اختبار بدون ودجت:** **`POST /dev/create-vip-test-cart`** ينشئ **`AbandonedCart`** ثابت `zid_cart_id=vip-codegen-test-cart-1` (**`cart_value=1200`**, **`vip_mode=true`**, **`status=abandoned`**) + **`CartRecoveryReason`** (**`session_id=test_vip_session`**, **`reason=price`**); يبيّن في قائمة أولوية VIP عند **`interactive`** حقيقية.
- **Logs (جزء):** **`[VIP CHECK]`**, **`[VIP MODE ACTIVATED]`**, **`[VIP CUSTOMER RECOVERY SKIPPED]`**, **`[VIP ACTIVATION FAILED]`**, **`[VIP MANUAL SEND CLICKED]`**, **`[VIP MERCHANT ALERT ATTEMPT]`**, **`[VIP MERCHANT ALERT SENT]`**, **`[VIP MERCHANT ALERT FAILED] reason=…`** (**`vip_merchant_alert.py`**).

---

## 5) End-to-End Flow

**Widget → Backend → Decision → Delay → WhatsApp → Dashboard**

1. User interacts with **`cartflow_widget.js`** on the store page; widget may call **`POST /api/cart-recovery/reason`** → row in **`cart_recovery_reasons`**.
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
- **Widget file size:** `static/cartflow_widget.js` is very large; navigation for contributors is easier via grep for `/api/` paths.

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
| VIP (threshold, decision-layer override, لا إرسال عميل أوتوماتيك، تنبيه تاجر، **`vip_mode`**, لوحة **`vip-cart-settings`** + **`POST …/merchant-alert`**, **`/dev/create-vip-test-cart`**) | ✅ |

**Legend:** ✅ implemented and wired in code · 🟡 partial or environment-dependent · ❌ not implemented

---

## 10) Recent updates (changelog)

**Convention:** After substantive project changes, append a short dated entry here so this file stays the single high-level record of behavior and wiring. **Maintain this section on every substantive change.**

| Date (UTC) | Summary |
|------------|---------|
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
