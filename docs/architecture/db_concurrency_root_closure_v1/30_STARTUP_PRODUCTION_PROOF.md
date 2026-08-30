# Startup unowned checkout — production proof

**Live SHA:** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Deployment:** `bc48e3dd-36ec-47d2-a342-fa9c835b4c74` SUCCESS `2026-08-30T19:00:50.844Z`  
**Parent:** `76c0d4111afe5fedeb8e3f4fc24b7ede7915f9ab`

After process start and SHA proven, 39 consecutive `/health` + `/health?diag=1` samples:

- `checked_out=0`
- `holder_count=0`
- `IDLE_IN_TRANSACTION=0`
- `peak_checked_out=1` (startup work, then released)
- `timeout_count=0`

No restart after observation. Scheduler unchanged. Autodeploy OFF.
