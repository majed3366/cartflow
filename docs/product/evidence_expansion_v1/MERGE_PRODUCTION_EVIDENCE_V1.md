# Evidence Expansion V1 — Merge + production evidence

**PR:** [#114](https://github.com/majed3366/cartflow/pull/114)  
**Merge commit:** `1a95fb33cd29fab590a6efd606c407145b26c670`  
**Tip commits in PR:** `570cec9` (foundations) · `17ace12` (terminal reopen guard)  
**Date (UTC):** 2026-07-27

## Final verification (pre-merge)

See `FINAL_MERGE_VERIFICATION_V1.md` — all 7 criteria **PASS** (incl. terminal reopen guard).

## Railway / GitHub deploy

| Check | Result |
|-------|--------|
| GitHub deployment SHA | `1a95fb33cd29fab590a6efd606c407145b26c670` |
| Environment | `authentic-motivation / production` |
| `authentic-motivation - smart-reply-ai` | **Success** (smartreplyai.net) |
| `authentic-motivation - cartflow` | **Success** |

## Production smoke (`PASS_EVIDENCE_EXPANSION_SMOKE`)

Script: `scripts/_evidence_expansion_prod_smoke_v1.py`  
JSON: `prod_smoke_after_merge.json`  
Shots: `prod_smoke_desktop_home.png`, `prod_smoke_mobile_home.png`

| Check | Result |
|-------|--------|
| Review session | Living Store `demo` · `cf.living.store.review@smartreplyai.net` |
| Home summary HTTP | 200 (desktop + mobile) |
| Home payload evidence-gap fields | **none** (banned-key walk clean) |
| Diagnostic publication present | yes |
| HES `diagnostic_reasoning` | `diagnostic_reasoning_v1` |
| `diagnostic_snapshot_read_ms` | ~13.8 ms desktop / ~13.2 ms mobile |
| Summary `api_ms` | ~3327 / ~3297 (request path; not gap compose) |
| Materialize probe | `ok=true`, composed=2; EE register isolated (`merchant_exposure=false`) |

### Notes

- Evidence Expansion on `/dev/diagnostic-reasoning-materialize` reported `enabled=false` in this smoke (probe does not setdefault EE flags; snapshot builder does). Diagnostics + Home unaffected.
- No collectors activated. No new observables added.

## STOP

Do **not** start collectors, add observables, or open the next implementation package until a separate collector-prioritization task is approved.
