# Trigger template save — investigation notes

## Observed (production)

1. Change Price delay 60 → 5, click Save
2. UI: «جاري الحفظ…» for a long time
3. Then «تعذر الحفظ»
4. Section briefly blanks / partial reload
5. After full page refresh, value not persisted

## Local verification (TestClient)

| Step | Result |
|------|--------|
| `POST /api/dashboard/trigger-templates` (price, 5 min) | **200** ~360ms, `ok: true`, `delay_value: 5` |
| `GET /api/dashboard/trigger-templates` | **200** ~47ms, `delay_value: 5` |

Persistence and enrich logic work locally; failure in production is likely **environmental** or **frontend race**, not the 60→5 enrich rule alone.

## Hypotheses (use console + server logs)

| ID | Cause | Evidence to look for |
|----|--------|----------------------|
| **A** | Save endpoint timeout (proxy/gateway) | `[SAVE TEMPLATE FAIL]` `failure_class: network_or_timeout`, long `duration_ms`, no server `[SAVE TEMPLATE SUCCESS]` |
| **B** | DB write / commit error | Server `[SAVE TEMPLATE FAIL]` with exception, HTTP 500, `api_error: failed` |
| **C** | Payload validation | HTTP 400, `failure_class: api_ok_false`, `api_error: json_object_required` / `reason_templates_object_required` |
| **D** | Reload GET fails after save | `[SAVE TEMPLATE SUCCESS]` then `[TEMPLATE RELOAD FAIL]` with `http_error` or `json_parse` |
| **E** | **Stale GET race** | Save starts while initial GET in flight; GET finishes after save and re-renders skeleton + old data. Log: `[TEMPLATE RELOAD FAIL] failure_class: stale_response_after_save` (ignored) or old data if gen check missing |
| **F** | Slow POST (widget cache rebuild) | Server `[SAVE TEMPLATE SUCCESS]` with high `duration_ms` (>5s); browser waits then times out |

## Debug logs (temporary)

### Browser console

- `[SAVE TEMPLATE START]` — reason, stage, delay, unit, `load_gen`
- `[SAVE TEMPLATE SUCCESS]` — `http_status`, `duration_ms`, `persisted_delay`
- `[SAVE TEMPLATE FAIL]` — `failure_class`, `api_error`, `parse_error`, `http_status`
- `[TEMPLATE RELOAD START]` / `SUCCESS` / `FAIL` — GET or cache path, `load_gen`

### Server

- `[SAVE TEMPLATE START]` / `SUCCESS` / `FAIL` — `store_id`, `store_slug`, `duration_ms`, `reason_keys`

## How to capture (Network tab)

1. **Save:** `POST /api/dashboard/trigger-templates` — status, response body (`ok`, `error`), time
2. **Reload (if any):** `GET /api/dashboard/trigger-templates` — only if fired after save (not required for save path; save response includes full payload)

## Root cause (confirmed)

**POST `/api/dashboard/trigger-templates` was doing too much work per save:**

1. `db.session.commit()` — required
2. `update_from_dashboard_store_row()` — **full widget snapshot rebuild** (`merge_widget_template_bundle_from_store_row` for all template fields)
3. `build_trigger_templates_get_payload()` — **enrich all 6 reasons** and return large JSON

On slow hosts / large stores this exceeded client/proxy patience → «جاري الحفظ…» then «تعذر الحفظ». A concurrent in-flight **GET** could also re-render the skeleton and show stale data.

## Fix (shipped)

| Layer | Change |
|--------|--------|
| **POST** | `save_ack` + 1 patched `reason_rows` only; logs `[TEMPLATE SAVE *]` |
| **Cache** | `patch_reason_templates_in_widget_cache` — patch `reason_templates` in existing snapshot, no full rebuild |
| **GET** | Cached `guided_defaults`; enrich unchanged but only on GET |
| **JS** | Merge save patch into `lastPayload`; no full grid re-render; skip skeleton on cache revisit |

## Verify in production

- POST: **200**, `save_ack: true`, small body (<8KB), `[TEMPLATE SAVE SUCCESS]` duration_ms < 2000
- GET after refresh: `delay_value: 5` for saved price stage
- No `[TEMPLATE RELOAD FAIL]` immediately after save unless user navigates away
