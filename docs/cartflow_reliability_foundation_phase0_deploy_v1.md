# Reliability Foundation V1 — Phase 0 deployment

Phase 0 hardens the **smart-reply-ai** public API service: role verification at startup, no schema work on merchant HTTP paths, fail-fast DB pool (30/30/5), and permanent request timing markers.

**Out of scope:** WhatsApp, Recovery Engine, Purchase Truth, dashboard snapshots, Redis, replicas.

---

## What changed (code)

| Component | File | Behavior |
|-----------|------|----------|
| Runtime role verify | `services/runtime_role_verification_v1.py` | Fail startup if API service has scheduler/scanner/resume enabled; emit `[API ROLE VERIFIED]` |
| Schema guard | `services/schema_runtime_guard_v1.py` | Disable `production_store_schema_middleware` on production-like / API paths |
| Pool | `extensions.py` | `pool_size=30`, `max_overflow=30`, `pool_timeout=5` |
| Request timing | `services/request_timing_audit_v1.py` | Always on in production-like; `[REQUEST_ENTER]`, `[DB_WAIT_*]`, `[ROUTE_*]` with `pool_wait_ms`, `route_ms`, `pre_route_ms`, `checked_out_connections` |
| Wiring | `main.py` | `verify_runtime_role_at_startup()` first on startup; schema middleware gated |
| Railway defaults | `railway.toml` | `CARTFLOW_ENFORCE_API_ONLY=1` + API role env |

---

## Required env — smart-reply-ai (API service)

| Variable | Value |
|----------|-------|
| `CARTFLOW_PROCESS_ROLE` | `api` |
| `CARTFLOW_DB_DUE_SCANNER_ENABLED` | `false` |
| `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` | `0` |
| `CARTFLOW_ENFORCE_API_ONLY` | `1` |
| `ENV` | `production` (or staging) |

Optional: `CARTFLOW_REQUEST_TIMING_AUDIT=0` disables timing markers (default **on** in production-like).

---

## Deploy steps (Railway)

1. **Authenticate** (if CLI shows Unauthorized):
   ```powershell
   railway login
   railway link   # select smart-reply-ai service
   ```

2. **Deploy from repo root** (after merge/push):
   ```powershell
   git push origin main
   ```
   Or trigger redeploy from Railway dashboard for **smart-reply-ai only**.

3. **Verify env** (script or manual):
   ```powershell
   .\scripts\railway_smart_reply_ai_api_only_v1.ps1
   python scripts/verify_api_role_production_v1.py
   ```

4. **Post-deploy smoke**:
   ```powershell
   curl -s -o NUL -w "%{http_code} %{time_total}s\n" https://smartreplyai.net/ping
   curl -s https://smartreplyai.net/health/scheduler | jq .process_role,.due_scanner_enabled
   ```

---

## Expected startup logs (API)

```text
[API ROLE VERIFIED] process_role=api may_resume=false may_due_scan=false may_delay_dispatch=false scanner_env=false resume_env=false enforce_api_only=true
[RUNTIME STARTUP] process_role=api ...
[RUNTIME STARTUP] resume_scan_skipped reason=role_api
[RUNTIME STARTUP] db_due_scanner_loop_skipped reason=role_api
```

If misconfigured (scanner or resume on API), startup **fails** with:

```text
[RUNTIME ROLE VERIFICATION FAILED] runtime role verification failed: ...
```

Container will not become healthy until env is corrected.

---

## Expected request logs (merchant traffic)

```text
[REQUEST_ENTER] path=/api/dashboard/normal-carts method=GET checked_out_connections=2 elapsed_ms=0
[ROUTE_START] path=/api/dashboard/normal-carts pre_route_ms=0.3 checked_out_connections=2
[DB_WAIT_START] path=/api/dashboard/normal-carts request_elapsed_ms=1.2 pool_wait_ms=0.5 checked_out_connections=3
[DB_WAIT_END] path=/api/dashboard/normal-carts request_elapsed_ms=45.1 checkout_hold_ms=43.2 checked_out_connections=2
[ROUTE_END] path=/api/dashboard/normal-carts elapsed_ms=46.0 route_ms=45.5 checked_out_connections=2
```

`/ping` should show `[REQUEST_ENTER]` / `[ROUTE_*]` only — **no** `[DB_WAIT_*]`.

---

## Scheduler service (unchanged layout)

Keep a **separate** Railway service with:

| Variable | Value |
|----------|-------|
| `CARTFLOW_PROCESS_ROLE` | `scheduler` |
| `CARTFLOW_DB_DUE_SCANNER_ENABLED` | `true` |
| `CARTFLOW_RECOVERY_RESUME_ON_STARTUP` | `1` |
| `CARTFLOW_ENFORCE_API_ONLY` | *(unset)* |

Do **not** set `CARTFLOW_ENFORCE_API_ONLY=1` on the scheduler service.

---

## Local verification

```powershell
python -m pytest tests/test_reliability_foundation_phase0_v1.py -q
```

All 14 tests should pass.

---

## Rollback

1. Revert the Phase 0 commit on `main` and redeploy smart-reply-ai.
2. Or temporarily set `ENV=development` on Railway (skips role verify — **not recommended for production**).
3. Pool settings revert with the code revert; no DB migration required.

---

## Success criteria

- [ ] `GET /ping` returns 200 in &lt;1s consistently
- [ ] Startup log contains `[API ROLE VERIFIED]`
- [ ] No `[DB_WAIT_*]` on `/ping` in logs
- [ ] `/health/scheduler` shows `process_role=api`, `due_scanner_enabled=false`
- [ ] Pool timeout errors (if any) fail within ~5s, not 30s
- [ ] No `ensure_production_store_schema_before_request` in production request logs
