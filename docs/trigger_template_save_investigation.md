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

## Mitigations in this debug build

- Save bumps `__trigger_templates_load_gen` so **in-flight GET responses are ignored** (log `stale_response_after_save`) — reduces blank flash + stale overwrite (race **E**).
- Save uses `resp.text()` + JSON parse with explicit `parse_error` logging (race **C** / gateway HTML).
- Save does **not** call full `render()` on success (no scroll jump from re-render).

## Next step after evidence

Only apply further persistence changes if logs show enrich overwriting 5→60 **after** confirmed `POST 200` with `messages[0].delay: 5` in response body.
