# Admin Operations UI — Isolated Deployment Candidate V1

**Status:** TRUTH_CORRECTIONS_V1 — local candidate only  
**Date (UTC):** 2026-08-29  
**Worktree:** `C:/Users/Toshiba/Desktop/cartflow-admin-ops-ui-candidate`  
**Branch:** `candidate/admin-ops-ui-integration-v1`  
**Primary dirty tree:** preserved at `C:/Users/Toshiba/Desktop/cartflow` (`d08859a` + uncommitted work). Not reset, cleaned, or overwritten.

No push. No deploy. No `railway up`. Security findings remain **OPEN**. Railway SNAPSHOT_CODE remains **separate**.

---

## 1. Baseline SHA and evidence

**Baseline:** `c6a912f0bf1ce2f8ce3a889cbd338a20a534d306`  
**Subject:** `fix: unify Carts needs-you on merchant primary action`

### Why this is the strongest available live-compatible source

| Fact | Evidence | Sufficiency |
|---|---|---|
| Documented Needs-You source | Commit message + SYSTEM_SUMMARY 2026-08-28 Carts Needs-You Truth Unification V1 | Yes |
| Live API start contract | `railway.api.toml` `startCommand` = `uvicorn cartflow_api:app --host 0.0.0.0 --port "${PORT:-8000}"` | Matches Railway living deployment `75bb966c` |
| API entry | `cartflow_api.py`: `configure_api_entry` + `reject_scheduler_via_web_entry` + `from main import app` | Present on baseline |
| Live Railway | Service `smart-reply-ai`, deployment `75bb966c` SUCCESS, `configFile` `/railway.api.toml`, CLI message “Needs-You Truth Unification V1” | Confirmed earlier (read-only) |
| Railway-stored git SHA | `commitHash` UNKNOWN (CLI upload) | **Gap remains** |

Startup compatibility is established. **Image-byte / stored-git parity is not proven** because Railway `commitHash` is UNKNOWN. This candidate proceeds with that gap documented, not as proven live-source identity.

`d08859a` is Communication HEAD on the dirty workspace. It is **not** this paint and is **not** the live start contract (no `cartflow_api.py` / `railway.api.toml` in that commit).

---

## 2. Candidate SHA

Recorded after the local commit on this worktree (see git log on `candidate/admin-ops-ui-integration-v1`).

---

## 3. Changed-file list and scope review

### Runtime (paint only)

- `services/admin_operations_center_v11_present_v1.py` — new read-only projection
- `services/admin_operations_center_v1.py` — attach `presentation_v11` on command-center payload only
- `routes/admin_operations.py` — empty `presentation_v11` on overview exception fallback only
- `templates/admin_operations_center_v1.html` — V1.1 layout
- `templates/layouts/admin_dashboard.html` — empty `{% block admin_extra_head %}`
- `static/admin_operations_center_v11.css` — scoped `#ops-v11`
- `static/admin_operations_center_v11.js` — local filter/segments; no network except existing lazy GETs already in template

### Tests

- `tests/test_admin_operations_center_v11_present_v1.py` (new)
- `tests/test_admin_operations_center_v1.py` — page copy + `presentation_v11`; version pin `v2_4` → `v2_5` (already true on baseline)
- `tests/test_admin_operations_dashboard.py` — page copy

### Documentation / evidence

- `docs/SYSTEM_SUMMARY.md` §3 route row + §10
- `docs/product/admin_ops_operations_center_design_v1/*`

### Explicitly unchanged

`main.py`, `cartflow_api.py`, `cartflow_scheduler.py`, `railway.api.toml`, `railway.scheduler.toml`, `railway.toml`, `Dockerfile`, `Procfile`.  
No Communication, merchant UI, Scheduler, or branding files.

---

## 4. Test results

### Baseline (clean `c6a912f`, before paint)

Scoped Admin run: **25 passed, 1 failed**.

| Failure | Class |
|---|---|
| `test_command_center_payload_excludes_lazy_sections` expected `v2_4`, payload is `v2_5` | **Baseline-reproduced** (stale pin; payload already `v2_5` on `c6a912f`) |

### Candidate (after paint)

In-scope run: **29 passed** (includes new present tests + updated page-copy / `presentation_v11` asserts). The baseline `v2_4` pin is aligned to `v2_5`.

Full `tests/test_admin_operations_center_v1.py`: **77 passed, 2 failed**.

| Failure | Class |
|---|---|
| `test_build_payload_has_required_sections` — `build_admin_operations_center_v1_readonly` version `v2_2` vs expected `v2_4` | **Pre-existing / out of scope** (different builder; not this page) |
| `test_failed_recovery_alert_includes_recovery_key` — shared-DB fixture collision (`demo:lifecycle-ok-…`) | **Pre-existing / out of scope** |

No new in-scope failures. No real sends or operational mutations.

---

## 5. Screenshots (this candidate, `cartflow_api:app` :8788)

Local verify JSON: `ISOLATED_VERIFY.json` — `ok: true`.

- `screenshots/candidate_desktop_1440.png`
- `screenshots/candidate_desktop_filter_platform.png`
- `screenshots/candidate_mobile_390.png`
- `screenshots/candidate_mobile_390_platform.png`
- `screenshots/candidate_mobile_390_merchants.png`

Checks: unauth → login; `#ops-v11`; UNKNOWN shown; no «سيناريو»; logout is the only page POST; desktop overflow 0; platform filter; details keyboard toggle; mobile segments.

---

## 6. Remaining source / deployment blockers

1. Railway living `commitHash` still **UNKNOWN** — startup match ≠ proven image-byte parity.
2. Railway **SNAPSHOT_CODE** on the API service remains a **separate** blocker. Do not retry `railway up`.
3. Security findings remain **OPEN** and unaccepted.
4. This candidate is **local only**. Not pushed. Not deployed.
5. Dirty primary worktree still holds Communication / merchant / Scheduler / branding work and must not be used as the deploy source.

**STOP:** READY_FOR_CANDIDATE_REVIEW
