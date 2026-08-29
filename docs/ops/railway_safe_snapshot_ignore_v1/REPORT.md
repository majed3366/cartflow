# Railway — Safe Production Snapshot Ignore V1

**Date (UTC):** 2026-08-28  
**Status:** Hardening only. No deploy. No product-behavior change. No Scheduler / Postgres / autodeploy / Railway service mutation.

**Base:** `f7228c0628ed80e494d52c0710436de427720095`

## Step 1 — Required inventory (top-level)

| Path | Class |
|------|--------|
| `cartflow_api.py`, `main.py`, `start.py`, `extensions.py`, `models.py`, `schema_*.py`, `config_system.py`, `decision_engine.py`, `json_response.py` | PRODUCTION_REQUIRED |
| `routes/`, `services/`, `integrations/`, `static/`, `templates/` | PRODUCTION_REQUIRED |
| `Dockerfile`, `Procfile`, `requirements.txt`, `railway.toml`, `railway.api.toml`, `alembic/`, `alembic.ini` | BUILD_REQUIRED |
| `docs/investigations/` | PRODUCTION_REQUIRED (admin registry reads these files) |
| `cartflow_scheduler.py`, `railway.scheduler.toml` | PRODUCTION_REQUIRED for Scheduler image; **kept** in API snapshot (tiny; not excluded) |
| `scripts/` (`.py` helpers) | UNKNOWN for operator use; **kept** (API does not import them; `_out` dirs ignored separately) |
| `docs/product/`, `docs/architecture/`, `docs/operations/`, `docs/ops/`, root `*.md`, `tests/`, `e2e/`, `branding/`, `tools/`, `promptfoo/`, `synthetic/`, `.cursor/` | SAFE_TO_IGNORE |

## Step 3 — tests/docs policy

Production Docker build is `pip install` + `COPY . .` + `uvicorn cartflow_api:app`. It does not run pytest and does not serve `docs/product`. **`tests/` and review docs are excluded from the snapshot only** — they remain in git.

**Exception:** `docs/investigations/` stays in the snapshot.

## Step 7 — Exclusion safety

| PATTERN | WHY_SAFE | RUNTIME IMPACT |
|---------|----------|----------------|
| `docs/product/` | Visual-review packs / PNGs; not mounted or imported by API | NONE |
| `docs/architecture/` | Studies / Meta evidence; SRS manifests already gitignored | NONE |
| `docs/operations/`, `docs/ops/`, `docs/operational/`, `docs/implementation/`, `docs/institutional_memory/`, `docs/business_findings/`, `docs/investigation/` | Ops packs; not admin registry | NONE |
| `docs/*.md`, `docs/*.png`, `docs/*.html` | Single-segment under `docs/` only (`*` does not cross `/`) | NONE |
| `*_out/` | Generated capture/visual-gate directories | NONE |
| `tests/`, `e2e/`, `playwright.config.ts`, `playwright-report/`, `test-results/`, `promptfoo/`, `synthetic/` | QA only; API does not import | NONE |
| `.cursor/`, `branding/` | Editor / design exploration; brand runtime is `static/img/` | NONE |
| `tools/` | Meta CLI; only imported by tests | NONE |
| `/*.md` | Root review markdown; not imported | NONE |

`scripts/` as a whole was **not** ignored (uncertain operational use). Only `*_out/` under it is dropped.

## Snapshot simulation

gitignore-style match over `git ls-tree -r -l HEAD` (clean `f7228c0` plus this ignore file).

| | Files | Size |
|--|------:|-----:|
| Before | 3459 | 106.10 MiB |
| After | 1343 | 14.77 MiB |
| Reduction | 2144 files | **91.33 MiB (86%)** |

## Completeness

- `from cartflow_api import app` → `CartFlow`, 324 routes
- `railway.api.toml` start contract unchanged
- Home / Workspace / Carts / Communication V2 assets present and not ignored
- `docs/investigations/` not ignored
- Tests: 18 passed (`test_railway_safe_snapshot_ignore_v1` + composition + V2 template)

---

BASE SHA:  
`f7228c0628ed80e494d52c0710436de427720095`

NEW HARDENING SHA:  
(pending commit)

RAILWAYIGNORE:  
CREATED

BEFORE FILE COUNT:  
3459

AFTER FILE COUNT:  
1343

BEFORE SIZE:  
106.10 MiB

AFTER SIZE:  
14.77 MiB

SIZE REDUCTION:  
91.33 MiB (86%)

PRODUCTION REQUIRED FILES PRESERVED:  
YES

API START CONTRACT PRESERVED:  
YES

MERCHANT UI ASSETS PRESERVED:  
YES

COMMUNICATION V2 PRESERVED:  
YES

SCHEDULER FILES:  
PRESERVED

OPERATIONAL REGRESSION:  
NO

SAFE FOR ONE-OFF API DEPLOY:  
YES
