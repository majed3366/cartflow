# CartFlow — System Summary (Architecture)

## 1) System Overview

CartFlow is a FastAPI application that:

- Embeds a storefront **widget** (JavaScript) for hesitation / exit-intent UX and **reason capture**.
- Receives **cart lifecycle events** (e.g. abandon, conversion) via **`POST /api/cart-event`** and schedules **delayed WhatsApp recovery** (Twilio path in `services/whatsapp_send.py`; Meta Cloud API path in `main.send_whatsapp_message` for interactive CTA messages used elsewhere).
- Persists **store settings**, **abandoned carts**, **recovery reasons**, and **recovery logs** in SQLAlchemy models (`models.py`), with optional schema patches via `schema_widget.py`.
- Serves **merchant dashboards** as Jinja2 HTML under `/dashboard/*`, loading/saving settings through **`GET`/`POST /api/recovery-settings`** and related APIs.

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
| `GET /dashboard/vip-cart-settings` | `vip_cart_settings.html` — **تنبيهات السلال المميزة** (قائمة `AbandonedCart.vip_mode` + **إرسال يدوي** → `POST /api/carts/{id}/send`) + عتبة VIP عبر نفس **`/api/recovery-settings`**. |
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
| `POST /api/carts/{id}/send` | `main.py` | Manual send to customer (`send_whatsapp_message` Meta path). |
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

- **`services/decision_engine.py`** — `decide_recovery_action(reason_tag, store=...)`: maps reason → `action` + **`resolve_whatsapp_recovery_template_message`** for message text. Used in dev/test endpoints and as the conceptual D.2 layer.
- **Production recovery text** often flows through **`reason_template_recovery.resolve_recovery_whatsapp_message_with_reason_templates`** and **`canonical_reason_template_key`** inside **`main._run_recovery_sequence_after_cart_abandoned_impl`**, not only `decide_recovery_action`.

### 4.5 WhatsApp Integration (D.3)

- **Customer recovery (Twilio):** **`send_whatsapp`** in `services/whatsapp_send.py` — called from **`main._run_recovery_sequence_after_cart_abandoned_impl`** after gates. Logs **`[WA SEND PATH]`**, **`[WA SENT]`**, **`[WA STATUS]`** when trace/env allows.
- **Customer manual / CTA:** **`send_whatsapp_message`** in `main.py` — Meta Graph interactive `cta_url` (**`/api/carts/{id}/send`**).
- **Gates:** **`_blocked_send_whatsapp_if_user_rejected_help`** prints **`[BLOCK WA - USER REJECTED HELP]`**; **`should_send_whatsapp`** implements quiet period vs `CartRecoveryReason.updated_at`.

### 4.6 Delay Logic

1. **`handle_cart_abandoned`** claims session (`_try_claim_recovery_session`), loads store, **VIP short-circuit** (see §4.9), else may schedule **multi** or async **`_run_recovery_dispatch_cart_abandoned`**.
2. **`_run_recovery_dispatch_cart_abandoned_impl`** polls **`_reason_tag_for_session`**, then either **`_schedule_recovery_multi_slots`** or computes **`get_recovery_delay`** (`services/recovery_delay.py`) vs elapsed time, then **`asyncio.create_task(_run_recovery_sequence_after_cart_abandoned(..., delay_seconds=remain))`**.
3. **`_run_recovery_sequence_after_cart_abandoned_impl`**: `await asyncio.sleep(delay_seconds)` → dedupe flags → conversion / user-rejected / **VIP** checks → template blocks → **`should_send_whatsapp(last_activity, store=...)`** → **`send_whatsapp`**.

Print-style trace: **`[DELAY STARTED]`**, **`[DELAY WAITING]`**, **`[DELAY FINISHED]`**, **`[CARTFLOW DELAY CHECK]`**, **`[DELAY BLOCKED]`**, **`[DELAY CONFIG]`** (from `whatsapp_send`).

### 4.7 Multi-message logic

- **`services/recovery_multi_message.multi_message_slots_for_abandon(reason_tag, store)`** — reads **`Store.reason_templates_json`**; if enabled and multiple messages → list of `{index, delay_seconds, text}`.
- **`main._schedule_recovery_multi_slots`** — one asyncio task per slot, each calling **`_run_recovery_sequence_after_cart_abandoned`** with **`multi_slot_index`** / **`multi_message_text`**.
- Logs: **`[MULTI MESSAGE MODE ACTIVATED]`**, **`[MULTI MESSAGE SCHEDULED]`**, **`[MULTI WA SEND ATTEMPT]`**, **`[MULTI WA SEND RESULT]`**, **`[MULTI MESSAGE SENT]`**, **`[MULTI MESSAGE FAILED]`**, **`[RECOVERY FULLY COMPLETED]`**.

### 4.8 Per-reason system

- **`get_recovery_delay(reason_tag, store_config)`** — per-tag default seconds in `services/recovery_delay.py` (extendable via `store_config.recovery_delays` if passed).
- **Reason templates** — `reason_templates_json` + `reason_template_recovery` / `store_reason_templates` / `recovery_message_templates` control message body and whether WhatsApp is blocked for a reason.

### 4.9 VIP handling

- **Threshold:** **`Store.vip_cart_threshold`** (null → VIP ignored); cart total from **`_abandoned_cart_cart_value_for_recovery`** vs **`services/vip_cart.is_vip_cart(cart_total, store)`**. Missing **`cart_value`** → normal recovery only.
- **Decision override (read-only):** **`main._vip_log_decision_override_after_engine`** calls **`decide_recovery_action(reason_tag, store=...)`** only to log **`[VIP DECISION OVERRIDE] decision=vip_manual_handling`** (مع `base_engine_action=...`) — لا يعدّل **`services/decision_engine.py`** ولا يُستخدم نص المحرك لإرسال العميل.
- **Activation:** **`main._activate_vip_manual_cart_handling`** → **`bool`**: on success (or cart already **`vip_mode`**) sets **`AbandonedCart.vip_mode`**, **`CartRecoveryLog`** with **`status=vip_manual_handling`**, merchant **`try_send_vip_merchant_whatsapp_alert`** (body: Arabic VIP high-value line from **`build_vip_merchant_alert_body`**; target: **`store_whatsapp_number`** then **`whatsapp_support_url`**), sets **`_session_recovery_sent[recovery_key]`**, logs **`[VIP RECOVERY BYPASSED]`**. On DB mark / guarded persist failure → **`False`** and **`[VIP FALLBACK]`** so the **existing** customer recovery pipeline runs unchanged.
- **Entry points:** (1) **`handle_cart_abandoned`**; (2) **`_run_recovery_dispatch_cart_abandoned_impl`**; (3) **`_run_recovery_sequence_after_cart_abandoned_impl`** after **`[VIP CHECK]`** — each: override log → activate; if **`False`**, continue normal flow (multi-message, delay, templates, **`send_whatsapp`**).
- **Logs:** **`[VIP ALERT]`** (`cart_total`, `threshold`, `session_id` داخل **`_activate_vip_manual_cart_handling`**), **`[VIP CHECK]`**, **`[VIP MODE ACTIVATED]`**, **`[VIP CUSTOMER RECOVERY SKIPPED]`**, **`[VIP RECOVERY BYPASSED]`**, **`[VIP FALLBACK]`**, **`[VIP ACTIVATION FAILED]`**, **`[VIP MERCHANT ALERT SENT] status=...`** في **`services/vip_merchant_alert.py`**.

---

## 5) End-to-End Flow

**Widget → Backend → Decision → Delay → WhatsApp → Dashboard**

1. User interacts with **`cartflow_widget.js`** on the store page; widget may call **`POST /api/cart-recovery/reason`** → row in **`cart_recovery_reasons`**.
2. Store platform (or demo) sends **`POST /api/cart-event`** with `event: cart_abandoned`, `store`, `session_id`, optional `cart_id` / `phone`.
3. **`handle_cart_abandoned`**: conversion / duplicate / claim checks → load **`Store`** → **if VIP**: try activate; on success **return** (no customer sequence); on activation failure **fall through** to the same scheduling logic as non-VIP.
4. If **multi_message_slots_for_abandon** returns slots → schedule delayed tasks per slot; else **`_run_recovery_dispatch_cart_abandoned`** waits for reason if needed, then schedules **one** delayed **`_run_recovery_sequence_after_cart_abandoned`**.
5. After sleep: **VIP guard** again; resolve message via **reason templates** / fallbacks; **`should_send_whatsapp`** vs **`CartRecoveryReason.updated_at`**; resolve phone via **`_resolve_cartflow_recovery_phone`**; **`send_whatsapp`** (Twilio) on success path.
6. **`_persist_cart_recovery_log`** records queued / sent / skipped / VIP rows.
7. **Dashboard** **`GET /dashboard`** — KPIs وأسباب ونشاط من **`AbandonedCart`** / **`CartRecoveryReason`** فقط. **قائمة VIP** تُحمّل في **`GET /dashboard/vip-cart-settings`** عبر **`_vip_cart_alerts_merchant_list()`** (بدون تكرار في الرئيسية).

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
| `[VIP ALERT]`, `[VIP CHECK]`, `[VIP MODE ACTIVATED]`, `[VIP CUSTOMER RECOVERY SKIPPED]`, `[VIP RECOVERY BYPASSED]`, `[VIP DECISION OVERRIDE]`, `[VIP FALLBACK]`, `[VIP ACTIVATION FAILED]` | `main.py` |
| `[VIP MERCHANT ALERT SENT]` | `services/vip_merchant_alert.py` |
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
- **VIP merchant alert:** depends on **`store_whatsapp_number`** or parsable **`whatsapp_support_url`**; otherwise alert is skipped with logged **`[VIP MERCHANT ALERT SENT] ok=False`**.
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
| VIP (threshold, skip customer auto-recovery, merchant alert, `vip_mode`, VIP alerts UI on **vip-cart-settings** only, override log, safe fallback) | ✅ |

**Legend:** ✅ implemented and wired in code · 🟡 partial or environment-dependent · ❌ not implemented

---

## 10) Recent updates (changelog)

**Convention:** After substantive project changes, append a short dated entry here so this file stays the single high-level record of behavior and wiring.

| Date (UTC) | Summary |
|------------|---------|
| 2026-05-02 | **Full VIP integration:** `_vip_log_decision_override_after_engine` (read-only `decide_recovery_action` + logs); `_activate_vip_manual_cart_handling` returns **`bool`** with **`[VIP RECOVERY BYPASSED]`** / **`[VIP FALLBACK]`** on failure; merchant alert copy and **`[VIP MERCHANT ALERT SENT] status=...`** in `services/vip_merchant_alert.py`. Commit: `feat: full VIP integration (backend + whatsapp + dashboard + override)`. |
| 2026-05-02 | **VIP UI dedup + logs:** الرئيسية (`dashboard_v1`) — KPIs وأسباب ونشاط فقط (بدون VIP في الشاشة الرئيسية)؛ **تنبيهات السلال المميزة** + **إرسال يدوي** في `vip_cart_settings.html` فقط؛ إزالة دمج VIP من `live_feed`؛ **`[VIP ALERT]`** + **`decision=vip_manual_handling`** في سجلات التجاوز؛ **`_vip_cart_alerts_merchant_list()`** لصفحة السلال المميزة؛ تسمية **الرئيسية** في الشريط الجانبي وعنوان KPI. Commit: `fix: activate VIP handling + remove duplication + enforce priority behavior + rename dashboard`. |
| 2026-05-02 | **صفحة عامة CartFlow:** `GET /` يعرض `templates/cartflow_landing.html` مع `static/cartflow_landing.css` + `cartflow_landing.js` (تمرير سلس للروابط الداخلية)؛ **`GET /register`** → `register_placeholder.html` (مؤقت، بدون OTP). الصفحة التسويقية عربية RTL مع تخطيط رأس LTR (شعار / تنقل / CTA) كما في المواصفات. Commit: `feat: add pixel-accurate CartFlow landing page`. |

---

*This document reflects the repository layout and control flow as of the last update (see §10); verify against `main.py`, `routes/`, `services/`, and `static/` for line-level changes.*
