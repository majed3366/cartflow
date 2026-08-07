# Meta Dispatch Request Evidence V1

Wire-level sanitized capture of the outbound Meta Graph `messages` request.

- Capture happens immediately before `requests.post` in `send_via_meta`.
- Never stores access tokens, Authorization headers, or checkout tokens.
- Last capture: `GET /dev/meta-dispatch-request`
- Artifacts: `request_payload.json`, `request_summary.md`

Does not change send behavior, provider selection, or template contracts.
