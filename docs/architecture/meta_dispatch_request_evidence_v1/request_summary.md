# Meta Dispatch Request Evidence V1

- captured_at: `2026-08-07T12:51:10.499697+00:00`
- recovery_key: `demo:cf_cart_meta_err_persist`
- provider: `meta`
- phone_number_id: `pn-err-1`
- template: `cartflow_cart_reminder_ar_v2`
- language: `ar`
- graph_endpoint: `https://graph.facebook.com/v23.0/pn-err-1/messages`
- to (masked): `+966*******11`
- verification_all_passed: `True`

## Checks

- phone_number_id_in_endpoint: `True`
- template_name_ok: `True`
- language_ok: `True`
- body_param_count_ok: `True`
- url_button_present: `True`
- quick_reply_present: `True`
- provider_is_meta: `True`

## Response

- http_status: `400`
- error.code: `100`
- error.error_subcode: `2388044`
- error.message_safe: `(#100) Invalid parameter`
- error.fbtrace_id: `AGxYz_trace99`
