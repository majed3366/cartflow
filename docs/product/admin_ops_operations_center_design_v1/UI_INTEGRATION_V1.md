# Operations Center UI Integration V1 — Isolated Candidate

**Status:** READY_FOR_CANDIDATE_REVIEW  
**Date (UTC):** 2026-08-29  
**Baseline:** `c6a912f` (Needs-You Truth Unification V1; matches live `75bb966c` start contract)  
**Scope:** Existing `GET /admin/operations` presentation only. Local candidate. No push, deploy, or Railway upload.

Security findings remain **OPEN**. Railway SNAPSHOT_CODE remains **separate**. Broader Admin implementation remains **DEFERRED**.

## Mapping (prototype → existing producer)

| V1.1 element | Existing producer | Notes |
|---|---|---|
| يحتاجني list + count | Stores: `priority != LOW`. Platform: existing `action_en` is an operator action | Same lists for count. `_PLATFORM_ONLY_KINDS` / severity are **not** actionability. Empty / “No immediate action required” / “No action required” → مراقبة المنصة |
| مراقبة | Same store queue, `priority == LOW`; platform alerts whose `action_en` is not an operator action | Excluded from يحتاجني |
| الرصد غير مكتمل لمتجر واحد | Count of action-queue rows with Widget Runtime group / beacon kinds | Store-scoped; not platform DEGRADED |
| Shared API / Scheduler | No live snapshot on this payload | Shown **UNKNOWN** — not HEALTHY |
| إعادة المحاولة | `provider_retry_ledger_v1.retry_active()` | Default off → غير مفعّلة |
| الاسترجاع التلقائي | `recovery_resume_health.running` only if the key is explicitly numeric (including 0) | Missing key / null → UNKNOWN — not inventing 0 |
| وقت إنشاء العرض | `generated_at_utc` | Presentation-generation time only |
| حداثة الدليل | No producer freshness field on SAC / critical_alerts / recovery_resume_health | UNKNOWN + missing sources named |
| أثر التجار counts | `summary.production_store_count` / `production_affected_count` | 0 only when explicitly supplied |
| Platform placement | `critical_alerts.alerts` kinds in `_PLATFORM_ONLY_KINDS` | Placement only; widget critical alert not duplicated |
| Typography | Admin layout IBM Plex Sans Arabic + system stack | **No new Tajawal / Google Fonts request.** Tajawal is not locally bundled. |
| Lazy DB Ready / Widget Health | Existing section GETs | Unchanged; read-only fetch |

No new eligibility rule. No new operational actions.

## Changed files (this candidate)

### Runtime

- `services/admin_operations_center_v11_present_v1.py` (new)
- `services/admin_operations_center_v1.py` — attach `presentation_v11`
- `routes/admin_operations.py` — exception fallback includes empty `presentation_v11`
- `templates/admin_operations_center_v1.html` — V1.1 layout
- `templates/layouts/admin_dashboard.html` — empty `{% block admin_extra_head %}`
- `static/admin_operations_center_v11.css` (new, `#ops-v11` + Kit V2)
- `static/admin_operations_center_v11.js` (new, local filter/segments)

### Tests

- `tests/test_admin_operations_center_v11_present_v1.py` (new)
- `tests/test_admin_operations_center_v1.py` — page copy + `presentation_v11` keys (also aligns version pin `v2_4` → `v2_5` already true on baseline)
- `tests/test_admin_operations_dashboard.py` — page copy

### Documentation

- `docs/SYSTEM_SUMMARY.md` §3 route row, §10
- this file + `ISOLATED_CANDIDATE_V1.md` + screenshots under `screenshots/`

`main.py`, `cartflow_api.py`, `railway.api.toml`, `Dockerfile`, and `Procfile` are **unchanged**.

## Test results (isolated candidate)

In-scope suite: **29 passed**.

Full `test_admin_operations_center_v1.py`: **77 passed, 2 failed** — both pre-existing / out of scope (`v2_2` vs `v2_4` on the unused full-center builder; shared-DB recovery-key collision). Baseline before paint also failed the stale `v2_4` command-center pin (now aligned to `v2_5`).

Live local checks (`ISOLATED_VERIFY.json`, `cartflow_api:app` :8788): unauth → login; `#ops-v11`; UNKNOWN; no «سيناريو»; logout-only POST; desktop overflow 0; mobile segments. Screenshots under `screenshots/candidate_*`.
