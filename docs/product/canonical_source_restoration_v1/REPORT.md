# CartFlow Canonical Source & Deployment Path Restoration V1

**Date (UTC):** 2026-08-29  
**Status:** FOUNDER_REVIEW_BEFORE_PUSH  
**Mode:** Authorized source reconciliation. No deploy. No `railway up`. No autodeploy change. No dirty-primary mutation.

**Integration worktree:** `C:\Users\Toshiba\Desktop\cartflow-canonical-source-restoration-v1`  
**Integration branch:** `candidate/canonical-source-restoration-v1`  
**Primary dirty worktree (untouched):** `C:\Users\Toshiba\Desktop\cartflow`  
**Preservation copy (external):** `C:\Users\Toshiba\Desktop\cartflow-source-preservation-v1`

---

## 1. Source topology

```
origin/main  439f572a55e6b9c1fd722118f2d402270b400124
    └── c6a912f0bf1ce2f8ce3a889cbd338a20a534d306     live-compatible Needs-You (not on origin/main)
            └── 1c3fd13d6b6114a1b4f31b9953c767617f5f42e0   Admin V1.1 paint
                    └── ed0c5cf663e8ba3cc8be7fd17b0a9ef7a49be11f   Admin truth corrections
                            └── candidate/canonical-source-restoration-v1   this docs commit (local)

aedd9573cd3aaea28d2d05f343fcc4fbc15d1c7f   merge-base(c6a912f, d08859a)
    └── …divergent Carts/Communication line…
            └── 41486f91ce0b50544045d69cce6257a7c7f248c0   origin/feat/platform-visual-assimilation-live-v1
                    └── d08859a498792b885b44ab818bb79c1fbd3a1fca   local HEAD + dirty tree
```

| Ref | SHA | Notes |
|---|---|---|
| Documented live-compatible baseline | `c6a912f0bf1ce2f8ce3a889cbd338a20a534d306` | Ancestor of Admin candidate. Has `cartflow_api.py` + `railway.api.toml`. On `origin/candidate/admin-ops-ui-integration-v1` only — **not** on `origin/main`. |
| GitHub `origin/main` | `439f572a55e6b9c1fd722118f2d402270b400124` | Ancestor of `c6a912f` (Needs-You is +1). |
| Local `main` | `00066a7e3b111ca0e1f14e3499e8fa63077a7c20` | **Stale.** Trails `origin/main`. Do not use. |
| Primary HEAD | `d08859a498792b885b44ab818bb79c1fbd3a1fca` | Communication V2 on `feat/platform-visual-assimilation-live-v1` (ahead 1 of origin). **Not** an ancestor of `ed0c5cf`. Lacks API entry files. |
| Remote Admin candidate | `ed0c5cf663e8ba3cc8be7fd17b0a9ef7a49be11f` | `origin/candidate/admin-ops-ui-integration-v1`. Already pushed. Autodeploy OFF. No deploy triggered. |
| Living Railway API (documented) | deployment `75bb966c` | Start `cartflow_api` + `/railway.api.toml` + `${PORT}`. Stored `commitHash` **UNKNOWN**. |

`c6a912f` is **not** an ancestor of `d08859a`. `ed0c5cf` and `d08859a` are **siblings after `aedd957`**, not a merge pair.

Remote of interest: `origin` = `https://github.com/majed3366/cartflow.git`. Many historical `feat/` / `docs/` / `deploy/` remotes exist; they are not this reconciliation line.

Active worktrees observed (not deleted): dirty primary, Admin candidate `ed0c5cf`, this integration tree, plus older temp/desktop worktrees (`cf-admin-ops-baseline-c6a912f`, carts/home/identity trees). Left in place.

---

## 2. Dirty-work preservation inventory

**Primary at inventory time**

| Item | Value |
|---|---|
| Path | `C:\Users\Toshiba\Desktop\cartflow` |
| Branch | `feat/platform-visual-assimilation-live-v1` |
| HEAD | `d08859a498792b885b44ab818bb79c1fbd3a1fca` |
| Staged | 0 |
| Modified tracked | **58** |
| Untracked (exclude-standard) | **933** |
| Stashes | 8 (historical WIP; not dropped) |

**Preservation method (no mutation of the primary tree)**

1. Files remain on disk in the primary worktree.
2. Byte-copy of every modified + untracked path to `C:\Users\Toshiba\Desktop\cartflow-source-preservation-v1\files\` with SHA-256 rows in `MANIFEST.jsonl`.
3. `PRESERVATION_SUMMARY.json`: `copied_count=991`, `bytes_copied=40024240`, `missing_count=0`, `destructive_commands_used=[]`, `primary_worktree_mutated=false`.

**Not used:** `git reset --hard`, `git checkout --`, `git clean`, force push, rebase, stash pop/drop, worktree or branch deletion.

**Modified tracked files (58)** — still in the primary tree and in the preservation copy:

`Dockerfile`, `Procfile`, `railway.toml`, `main.py`, `start.py`, `extensions.py`, `routes/admin_operations.py`, `routes/ops.py`, `routes/public.py`, `services/admin_operations_center_v1.py`, `services/dashboard_snapshot_builder_v1.py`, `services/dashboard_snapshot_loop_v1.py`, `services/dashboard_snapshot_v1.py`, `services/recovery_db_due_scanner.py`, `services/recovery_db_due_scanner_loop.py`, `services/recovery_process_role_v1.py`, `services/recovery_scheduler_guardrails.py`, `services/runtime_role_verification_v1.py`, `static/commerce_situations_surfaces_v1.js`, `static/merchant_app.js`, `static/merchant_dashboard_lazy.js`, `static/merchant_experience_integration_v1.js`, `static/merchant_intelligence_carts_v1.js`, `static/merchant_ui_v2_carts.js`, `templates/admin_operations_center_v1.html`, `templates/layouts/admin_dashboard.html`, `templates/merchant_app.html`, Admin/Scheduler/recovery tests (11), capture scripts (6), branding kit READMEs (3), `docs/SYSTEM_SUMMARY.md`, institutional-memory docs (2), Meta evidence (4), product reports (4).

**Untracked top-level groups (933)**

| Group | Count | Meaning |
|---|---|---|
| `branding/` | 447 | Identity / monogram / color / symbol explorations |
| `docs/` | 419 | Ops, Admin, landing, Meta, product packs |
| `scripts/` | 26 | Capture / review helpers |
| `research-screenshots/` | 17 | Visual research |
| `services/` | 8 | API/Scheduler split + Admin `presentation_v11` sitting on `d08859a` (those files are **committed** on `c6a912f`/`ed0c5cf`) |
| `tests/` | 5 | Matching tests for those untracked modules |
| `static/` / `templates/` | 5 | Admin V1.1 assets + visual-proof extras |
| deploy entries | 4 | `cartflow_api.py`, `cartflow_scheduler.py`, `railway.api.toml`, `railway.scheduler.toml` (untracked on `d08859a` because that SHA does not contain them) |
| `.cursor/` | 2 | Local editor config |

Dirty `cartflow_api.py` and dirty `railway.api.toml` are **byte-identical** to `ed0c5cf` (`git hash-object` match). They are **not** a third source of truth; they are copies on the wrong branch.

**Stashes (recoverable via `git stash show -p`; not applied)**

`stash@{0}` … `stash@{7}`: landing / business-findings / time-authority WIPs. Classification: **UNKNOWN** historical. Left untouched.

**Confirmation:** no work was deleted or overwritten. Primary HEAD is still `d08859a`.

---

## 3. Commit and branch classification

Do not treat “exists in the tree” as approved.

| Object | Class | Why |
|---|---|---|
| `c6a912f` Needs-You | **APPROVED_AND_VERIFIED** | Documented live-compatible API contract; living deploy `75bb966c` documented against this start command. Image-byte parity still unproven (`commitHash` UNKNOWN). |
| `1c3fd13` Admin paint | **APPROVED_AND_VERIFIED** | Isolated candidate; scoped paint; tests + screenshots. |
| `ed0c5cf` Admin truth corrections | **APPROVED_AND_VERIFIED** | Isolated candidate; pushed to GitHub candidate branch; not deployed. |
| `origin/main` `439f572` | **APPROVED_AND_VERIFIED** | Published GitHub main; ancestor of `c6a912f`. |
| `41486f9` Carts composition (diverged line) | **IN_PROGRESS** | On origin feat branch. Not live-compatible (no `cartflow_api.py` in this line). Parallel Carts work already exists on `origin/main` as `de87061`. |
| `d08859a` Communication V2 | **IN_PROGRESS** + **DEPLOYMENT_SENSITIVE** | Clean SHA previously STOP’d: would revert live start to `main:app`. |
| Dirty start-file edits (`Dockerfile`/`Procfile`/`railway.toml`/`start.py`/`main.py`) | **IN_PROGRESS** + **DEPLOYMENT_SENSITIVE** | Attempt to bolt `cartflow_api` onto `d08859a`. Not an isolated verified commit. |
| Dirty Admin files on primary | **IN_PROGRESS** | Superseded by `ed0c5cf` on the live-compatible line. |
| Dirty merchant JS/HTML | **IN_PROGRESS** | Unfinished Merchant UI. Not independently approved for this candidate. |
| Dirty Scheduler/recovery services + tests | **IN_PROGRESS** + **DEPLOYMENT_SENSITIVE** | Must not ride an API deploy. |
| Untracked branding / landing research | **DEFERRED** / **UNRELATED** | Explorations. Not runtime. |
| Untracked Admin/ops docs + Meta evidence | **IN_PROGRESS** / **UNRELATED** | Documentation and evidence; not merged. |
| Local `main` `00066a7` | **UNRELATED** | Stale checkout. |
| Historical local feat/docs/deploy branches | **UNRELATED** unless separately authorized | Not this line. |
| Security D-AO-01/09/10/13/14/15 | **OPEN** (separate track) | Not accepted; not closed by this task. |

---

## 4. Live-compatible baseline evidence

| Check | Result |
|---|---|
| `railway.api.toml` start | `sh -c 'exec python -m uvicorn cartflow_api:app --host 0.0.0.0 --port "${PORT:-8000}"'` on `c6a912f` and `ed0c5cf` (identical) |
| `cartflow_api.py` | `configure_api_entry` + `assert_entry_matches_role` + `reject_scheduler_via_web_entry` + `from main import app` |
| `railway.scheduler.toml` | `python -m cartflow_scheduler`; role `scheduler` |
| `d08859a` API files | **Absent** (`cartflow_api.py`, `cartflow_scheduler.py`, `railway.api.toml`, `railway.scheduler.toml` all missing at that SHA) |
| Documented living API | `75bb966c` SUCCESS, `configFile` `/railway.api.toml`, CLI “Needs-You Truth Unification V1” |
| Railway stored git SHA | **UNKNOWN** — startup contract match, not image-byte identity |

`main.py` on `c6a912f`/`ed0c5cf` is already the lightweight composition layer (scanner/resume/snapshot loops not started from the web entry). Dirty `main.py` on the primary tree repeats some of that extraction on the **wrong** SHA and is excluded.

---

## 5. Canonical source recommendation

**Canonical base SHA:** `c6a912f0bf1ce2f8ce3a889cbd338a20a534d306`

**Strategy:** one clean integration line = live-compatible API contract + the only independently approved product delta (Admin Operations V1.1 / truth corrections). Do **not** merge the dirty primary tree, `d08859a`, Communication, Merchant UI, Scheduler, or branding to “make the tree look clean.”

| Topic | Decision |
|---|---|
| Commits included | `c6a912f` (base), `1c3fd13`, `ed0c5cf`, plus this documentation commit |
| Commits excluded | `41486f9`, `d08859a`, all dirty/untracked primary work, stale local `main` |
| Dirty primary treatment | Leave in place. External byte-copy exists. Future work must move to **new feature branches from this canonical line**, not from `d08859a`. |
| Admin `ed0c5cf` | **Included by ancestry** (branch created at that SHA). No conflict resolution required. |
| API entry | `cartflow_api:app` + `railway.api.toml` + `${PORT}` |
| Scheduler isolation | Separate service / `cartflow_scheduler`. Web entry rejects scheduler role. |
| Railway configuration | Do not change live Railway in this task. Autodeploy stays OFF. Do not assign Scheduler config here. |
| Future `main` ownership | After founder approval: fast-forward or merge **this candidate** onto `origin/main` (currently 1 commit behind `c6a912f`, then Admin + docs). Retire `d08859a` as a workspace HEAD, not as a silent reset. |
| Future deploy trigger | GitHub exact-SHA / one-off to `smart-reply-ai` only. Never `railway up`. Never dirty-tree upload. |

Semantic merge of `ed0c5cf` onto `d08859a` was **not** attempted: different API contracts, unfinished Communication/merchant/Scheduler, and no approval to combine them.

---

## 6. Integration candidate SHA

Created:

```
git worktree add -b candidate/canonical-source-restoration-v1
  C:\Users\Toshiba\Desktop\cartflow-canonical-source-restoration-v1
  ed0c5cf663e8ba3cc8be7fd17b0a9ef7a49be11f
```

Primary worktree was not checked out, reset, or cleaned. After the documentation commit on this branch, **HEAD of `candidate/canonical-source-restoration-v1` is the integration candidate SHA** (recorded in the footer after commit).

Parent of that commit remains `ed0c5cf663e8ba3cc8be7fd17b0a9ef7a49be11f`.  
Documentation commit on this branch: `a2851c11ccbcd0b3ece468995dca0206b5067e4a`. Review/push tip is `git rev-parse` of `candidate/canonical-source-restoration-v1`.

---

## 7. Included and excluded change lists

### Included (runtime vs `c6a912f` — already on `ed0c5cf`)

- `services/admin_operations_center_v11_present_v1.py` (new)
- `services/admin_operations_center_v1.py` — attach `presentation_v11`
- `routes/admin_operations.py` — fallback `presentation_v11` keys only
- `templates/admin_operations_center_v1.html` — V1.1
- `templates/layouts/admin_dashboard.html` — empty `admin_extra_head`
- `static/admin_operations_center_v11.css` / `.js`
- Admin tests + isolated-candidate docs/screenshots
- `docs/SYSTEM_SUMMARY.md` Admin + this restoration rows
- This pack: `docs/product/canonical_source_restoration_v1/REPORT.md`

**Unchanged vs `c6a912f` (verified):** `main.py`, `cartflow_api.py`, `cartflow_scheduler.py`, `railway.api.toml`, `railway.scheduler.toml`, `Dockerfile`, `Procfile`.

### Excluded

- All 58 dirty tracked files and 933 untracked primary paths
- Communication V2 (`d08859a`)
- Diverged Carts feat `41486f9`
- Merchant UI / Scheduler / branding / Meta / landing research WIP
- Any new Admin POST, send, or retry
- Security remediations D-AO-*

---

## 8. API / Scheduler isolation verification

| Check | Result |
|---|---|
| `import cartflow_api` | `FastAPI`; route `/admin/operations` present |
| `railway.api.toml` | start `cartflow_api:app` + `"${PORT:-8000}"`; `CARTFLOW_PROCESS_ROLE=api`; no `cartflow_scheduler` start |
| `railway.scheduler.toml` | `python -m cartflow_scheduler` |
| Import `cartflow_api` with `CARTFLOW_PROCESS_ROLE=scheduler` + `ENV=production` | **REJECTED** `ProcessEntryError: API entry requires CARTFLOW_PROCESS_ROLE=api` |
| Isolated uvicorn `:8793` startup banner | `process_role=api`; resume/scanner/snapshot **disabled**; `[SCHEDULER OWNER] role=api … block_reason=role_api` |
| `tests/test_cost_recurrence_prevention_v1.py` process-entry cases | **Passed** (scheduler role rejected on web entry) |

Scheduler cannot start through the API/web entry on this candidate.

---

## 9. Test and startup results

### Scoped pytest (integration worktree)

```
tests/test_admin_operations_center_v11_present_v1.py
tests/test_admin_operations_center_v1.py
tests/test_admin_operations_dashboard.py
tests/test_cost_recurrence_prevention_v1.py
```

**113 passed, 1 failed, 3 skipped.** Failures are not hidden in a total.

| Result | Class | Notes |
|---|---|---|
| `AdminOperationsCenterV1Tests.test_build_payload_has_required_sections` expects `admin_operations_center_v2_4`, unused builder returns `v2_2` | **BASELINE_REPRODUCIBLE** | Same failure on clean `c6a912f` worktree (`C:\Users\Toshiba\AppData\Local\Temp\cf-admin-ops-baseline-c6a912f`). Command-center payload on this line is already `v2_5`. Not changed to force a pass. |
| Remaining Admin / isolation tests | — | Pass |
| Production DB / WhatsApp / Meta | — | Not used |

No **NEW_FAILURE** in this scoped run.

### Isolated TestClient smoke (temp SQLite)

- Unauth `GET /admin/operations` → **302** `/admin/operations/login`
- Login → **303**
- Auth page **200**, `id="ops-v11"` present, `وقت إنشاء العرض` present, no new Google Fonts Tajawal request

### Isolated uvicorn smoke (`127.0.0.1:8793`, temp SQLite, no production `.env`)

- `GET /health` → **200**
- Unauth `GET /admin/operations` → **302** login
- Login POST → **303** + `cartflow_admin_session`
- Auth `GET /admin/operations` → **200**, `#ops-v11` present, existing IBM Plex Google Font (baseline), no Tajawal
- No production database mutation
- No WhatsApp/Meta send
- Process stopped after the check

Existing Admin POSTs (login/logout, subscription action, WhatsApp recovery/register/test) are **baseline** routes on `c6a912f`. This candidate adds **no new** Admin mutations or sends. Security findings on those routes remain **OPEN**.

---

## 10. Permanent GitHub → Railway workflow

Normal path after this line is adopted:

1. **Feature branch** from the canonical SHA (`candidate/canonical-source-restoration-v1` / later `main`).
2. **Verification** in an isolated worktree (tests + local API smoke). Dirty primary is never the deploy source.
3. **Approved merge** into the canonical branch (`main` once founder fast-forwards it).
4. **GitHub-based Railway API deployment** of that exact SHA to `smart-reply-ai` only (dashboard one-off / GitHub-connected deploy). **Never `railway up`.**
5. **Post-deploy verification** on living URL (start command, `/health`, Admin login + `#ops-v11` if Admin is in the SHA).
6. **Rollback** to the previous exact SHA / previous successful Railway deployment.

### API deployment policy

- Service: `smart-reply-ai`
- Config file: `railway.api.toml`
- Start: `uvicorn cartflow_api:app` + `${PORT}`
- Source: GitHub SHA on the canonical branch only
- Autodeploy: **OFF for this task.** Keep **manual GitHub one-off** until founder enables it after gates (see recommendation).
- Do not upload a dirty working tree.

### Scheduler deployment policy

- Service: `cartflow` (Scheduler)
- Config file: `railway.scheduler.toml`
- Start: `python -m cartflow_scheduler`
- **Never** deploy Scheduler as a side effect of an API change
- **Never** start Scheduler through the web/API entry
- Separate founder authorization for any Scheduler SHA
- Jobs remain default OFF unless explicitly enabled in Railway

### Autodeploy recommendation

**Keep API autodeploy OFF.** Use GitHub one-off deployments of an approved SHA.

| Factor | Why manual one-off is safer now |
|---|---|
| Safety | `origin/main` is still behind the live-compatible Needs-You commit; historical dirty-tree and CLI uploads caused source ambiguity. Autodeploy on a connected repo can fire on the wrong branch if settings drift. |
| Cost | Prior Railway cost lockout required autodeploy disabled. Accidental API+Scheduler rebuilds are expensive. |
| Operations | SNAPSHOT_CODE / CLI archive failures are a Railway infrastructure track. GitHub one-off avoids CLI upload. Post-deploy verification stays a human gate. |

Enable API autodeploy **later only if** all of these are true: `main` *is* the canonical line; watchPatterns (or branch filter) cannot fire on feature branches; Scheduler service cannot autodeploy with API; SNAPSHOT_CODE/CLI is no longer the deploy path; a rollback SHA is recorded before each prod deploy.

---

## 11. Rollback procedure

**Today (nothing new deployed):** living API remains documented `75bb966c` / intended source `c6a912f`. This task did not change production.

**After a future authorized deploy of the integration SHA:**

1. Do not `railway up`.
2. Redeploy the **previous successful API SHA** (today: `c6a912f` / living `75bb966c`) to `smart-reply-ai` via GitHub/Railway one-off.
3. Confirm start command still `cartflow_api` + `${PORT}`.
4. Leave Scheduler on its last authorized deployment (`2b1e5665` documented) unless a separate Scheduler rollback is authorized.
5. Dirty primary and preservation copy are independent of rollback.

---

## 12. Remaining blockers

1. **SAFE_TO_DEPLOY is NO.** Founder review required before push; a separate authorization is required before any Railway API deploy.
2. **`origin/main` is not yet the canonical line** (`c6a912f` and Admin are only on the candidate remote today).
3. **Railway `commitHash` UNKNOWN** on the living CLI-originated deploy — live/source byte parity still unproven.
4. **SNAPSHOT_CODE / `railway up`** remains an infrastructure blocker. Do not retry CLI upload.
5. **Autodeploy stays OFF** (last documented `watchPatterns: []`; live GraphQL re-query in this session was Not Authorized — settings were not changed).
6. **Dirty primary work** (Communication, merchant, Scheduler, branding) is preserved but **not** on the canonical line. It needs its own isolated branches from `c6a912f`/`ed0c5cf` later.
7. **Security findings** D-AO-01, D-AO-09, D-AO-10, D-AO-13, D-AO-14, D-AO-15 remain **OPEN**.
8. **Baseline-reproducible** unused-builder version pin (`v2_2` vs test `v2_4`) remains; not a new regression.

This candidate was **not pushed**. `main` was **not** merged.

---

PRIMARY_WORK_PRESERVED:
YES

CANONICAL_BASE_SHA:
c6a912f0bf1ce2f8ce3a889cbd338a20a534d306

ADMIN_CANDIDATE_INCLUDED:
YES

ADMIN_CANDIDATE_SHA:
ed0c5cf663e8ba3cc8be7fd17b0a9ef7a49be11f

INTEGRATION_CANDIDATE_SHA:
a2851c11ccbcd0b3ece468995dca0206b5067e4a

INTEGRATION_WORKTREE_CLEAN:
YES

API_START_CONTRACT_VERIFIED:
YES

SCHEDULER_ISOLATION_VERIFIED:
YES

SAFE_TO_PUSH_CANONICAL_CANDIDATE:
YES

SAFE_TO_DEPLOY:
NO

NEXT_ACTION:
FOUNDER_REVIEW_BEFORE_PUSH

STOP.
