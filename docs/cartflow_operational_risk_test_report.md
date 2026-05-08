# CartFlow operational risk test report

This document describes what the **`tests/operational/`** suite is intended to guard, and what it does **not** replace. It is intentionally conservative: no claims beyond what the tests and code inspection support.

## Covered risks (tests in place)

| Risk area | What the tests do |
|-----------|-------------------|
| **Complexity / imports** | `test_operational_module_imports.py` imports core modules (`main`, recovery strategy, WhatsApp send layer, behavioral modules). |
| **WhatsApp operational** | Integration tests exercise **missing phone** (`skipped_no_verified_phone`), **`send_whatsapp` returning `ok: False`** (`whatsapp_failed`, with `should_send_whatsapp` patched open), and **user returned** blocking send (`skipped_delay_gate`, no `send_whatsapp` call). Static checks assert failure logging strings exist in `services/whatsapp_send.py`. |
| **Duplicate sends / attempts** | Source asserts `skipped_duplicate` / `already_sent` appear in `main.py`. Existing suite elsewhere (`tests/test_cart_recovery_sequence_behavior.py`, etc.) remains the primary behavioral proof; operational tests document duplication markers. |
| **Widget maintainability (static)** | `widget_loader.js` / `cartflow_widget.js` are scanned for **single-flight guards** (`__CARTFLOW_*__`) and **exit intent** markers — no browser execution. |
| **Dashboard trust** | `skipped_no_verified_phone` does not count toward successful send totals; coarse status is not `"sent"`. Snapshot asserts stable **machine keys** on normal-recovery payload (`normal_recovery_phase_key`, `normal_recovery_status`, etc.). |
| **Behavioral + dashboard precedence** | When both `customer_replied` and `user_returned_to_site` are set in `cf_behavioral`, phase key is **`behavioral_replied`** (ordering contract). |
| **Observability markers** | Static presence of `[PHONE RESOLUTION]`, `[NORMAL RECOVERY STATUS UPDATE]`, `[WA SENT]` / `[WA STATUS]`, `[RETURN TO SITE BACKEND PERSISTED]`, `[CARTFLOW RUNTIME]`. Functional check: `_log_phone_resolution` prints the `[PHONE RESOLUTION]` banner. |
| **Integration identifiers** | `recovery_key` from cart-event payload matches `recovery_key_for_reason_session` for the same store + session. |
| **Duplicate abandoned row (sync)** | Two identical `cart_state_sync` posts yield **one** `AbandonedCart` row for the same `zid_cart_id`. |
| **Stale / corrupt client payload** | `behavioral_dict_for_abandoned_cart` returns `{}` for invalid JSON in `raw_payload` (no exception). |
| **Demo template wiring** | `demo_store.html` sets `window.CARTFLOW_STORE_SLUG`. |
| **AI / cost control (normal copy path)** | `services/recovery_message_strategy.py` has **no** `anthropic` / `openai` references; abandonment copy is rule/template-based. (**Note:** `main.generate_recovery_message` / Claude helpers exist but are **not referenced** elsewhere in this repo — not proof they are disabled in all future routes.) |
| **Scaling / process model** | Documented test: recovery dispatch uses **`asyncio.create_task`** in `main.py` (inline async, not a dedicated delay worker). |
| **Diagnostics helper** | `tests/operational/diagnostics.py` exposes a **read-only** snapshot (`runtime_status`, `duplicate_send_guard` sizes, phone-resolution probe). No HTTP route added. |

## Partially covered

| Risk | Gap |
|------|-----|
| **“One module failure does not break tracking”** | Only light checks (import smoke + WhatsApp module import). No systematic fault injection across all subsystems. |
| **Exit intent vs recovery** | Static strings only; no E2E browser test that exit intent never permanently blocks recovery. |
| **Reply + return + abandon combined in production** | Dashboard precedence test covers **display** ordering for two flags; full send/reply/return timeline is **not** replayed end-to-end here. |
| **Session/cart stability through full funnel** | `recovery_key` equality and duplicate sync are covered; **reply** and **inbound WhatsApp** steps rely on existing tests outside `operational/`. |
| **Recovery timing conflicts** | User-return and missing-phone paths are covered; **purchase completed** and **customer replied** early-exit paths are not all duplicated here (see existing recovery tests). |
| **Repeated `cart_abandoned` scheduling** | Not re-tested in `operational/`; covered by `test_cart_recovery_sequence_behavior.py`. |
| **Template approval / WhatsApp template failure** | `reason_template_disabled` and Twilio template approval are **not** fully simulated; the suite only documents that **`send_whatsapp` failure** yields `whatsapp_failed` log when gates are open (`should_send_whatsapp` patched `True`). |
| **Large widget runtime** | No headless JS; static guards only. |
| **`[WA SENT]` at runtime in mock mode** | Markers are asserted in source; mock send path may differ from real Twilio path. |

## Requires future infrastructure

- **Multi-process / multi-instance** delay and deduplication (in-memory `_session_*` guards are per process).
- **Real queue** for abandonment delays and WhatsApp send (today: async tasks + optional WhatsApp queue for real sends — see scaling note below).
- **E2E browser** coverage for widget listener duplication and exit intent.
- **Centralized log aggregation** assertions in CI (tests currently use stdout redirection or source scans, not log drains).

## Known current limitations (accurate)

1. **Delayed recovery** is driven by **`asyncio.create_task`** in the API process after abandon; there is no separate worker dedicated to the countdown phase.
2. **Duplicate-send guards** (`_session_recovery_*`) live in **process memory**; horizontal scaling without shared state can duplicate work unless architecture changes.
3. **Operational tests patch `should_send_whatsapp`** where needed to avoid flaky delay clocks; this documents intent (reach send/fail path) rather than reproducing exact wall-clock delay math every time.
4. **`generate_recovery_message` (Claude) in `main.py`** is not invoked from current automated recovery flow (no callers found); risk of future wiring is noted in the table above, not hidden.

## Running

```bash
python -m pytest tests/operational -q
```

Full suite: `python -m pytest` (all existing tests should remain green).
