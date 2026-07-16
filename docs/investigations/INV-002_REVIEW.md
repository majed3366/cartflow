# INV-002 Architectural Review — Merchant Identity Drift

| Field | Value |
|-------|-------|
| Investigation | INV-002 |
| Title | Merchant Identity Drift |
| Review date (UTC) | 2026-07-16 |
| Branch | `feature/inv002-architecture-review` |
| Primary evidence | Reality Validation Checkpoint V2 · Lab V1 |
| Decision | **Root Cause Confirmed** |
| Implementation | **Not authorized** — STOP for Architecture Board; no Work Package until DoR |

> Investigation and architecture only. No fixes. No implementation architecture in this document beyond RCA confirmation.

---

## Executive answer to the primary question

**Why can Knowledge / Dashboard / Daily Brief “see” simulated data while merchant Home still feels incomplete?**

Because those Checkpoint V2 successes were measured on the **canonical simulation tenant** (`store_slug=demo`) under Query Time Context, while the **merchant walkthrough session** resolves a **different tenant** created at signup (`متجر-واقع-صغير-*`). Home, session Knowledge, session Daily Brief, and session Dashboard all correctly read that empty signup store. They are not broken relative to their identity — they are bound to the wrong store for the lab narrative.

Time Authority (INV-001) unified windows **within** a store context. It did not (and could not) unify **which store** the merchant session owns.

---

## 1. Symptom inventory

| # | Symptom | Observed where |
|---|---------|----------------|
| S1 | Merchant Home shows skeleton + “CartFlow يجهّز فهم متجرك…” | Checkpoint screenshots `01_desktop_home.png`, `02_mobile_home.png` |
| S2 | Summary activation `home_stage=activation`, `current_state_id=no_carts` | `checkpoint_evidence.json` summary body for session store |
| S3 | Session `store_slug` = `متجر-واقع-صغير-11c83d` (not `demo`) | Same evidence (`store_slug` fields throughout summary) |
| S4 | Session KPIs / normal-carts empty (0 rows) | Checkpoint + Lab V1 T1 |
| S5 | Durable sim truth on `demo`: 27 carts, 20 Purchase Truth | Checkpoint counts; Lab V1 |
| S6 | Service probes on `demo` + sim QTC: Knowledge `cart_count=27` | Checkpoint `time_authority_probes.simulation` |
| S7 | Session Home brief items narrate “no carts / insufficient” for signup slug | Checkpoint composed home/brief for session path |
| S8 | Lab “bind demo” attempted but session still not on `demo` | Lab script + evidence note |

---

## 2. Reproduction steps

1. Run Reality Validation Checkpoint V2 (or Lab V1 Small Reality): seed `20260715`, `store_slug=demo`, May 1–3 history.  
2. Lab signs up merchant via `POST /signup` (`store_name=متجر واقع صغير`).  
3. Lab attempts `_signup_and_bind_demo` (sets `demo.merchant_user_id`; does **not** set `MerchantUser.primary_store_id`).  
4. Open `/dashboard` with merchant session cookie → Home.  
5. Separately call `build_knowledge_report(..., "demo")` under `simulation_scope` → rich metrics.  

**Expected if identity aligned:** session store slug ≡ `demo` (or attached sim tenant); Home non-empty under correct QTC.  
**Observed:** session slug ≠ `demo`; Home incomplete; `demo` rich.

---

## 3. Evidence collection

| Artefact | Finding |
|----------|---------|
| `REALITY_VALIDATION_CHECKPOINT_V2_REPORT.md` | TA unified under QTC; merchant walkthrough unchanged |
| `docs/architecture/reality_validation_checkpoint_v2/checkpoint_evidence.json` | `merchant_store_scoping`: demo_carts=27, signup_merchant_stores_carts=0 |
| Same file · summary | `store_slug: "متجر-واقع-صغير-11c83d"`, `home_stage: "activation"`, `no_carts` |
| Same file · TA probes | sim Knowledge 27 carts; ambient production Knowledge 0 (INV-001 class) |
| Screenshots | Home preparing-understanding shell |
| `scripts/reality_validation_lab_v1_small.py` `_signup_and_bind_demo` | Bind writes `demo.merchant_user_id`; checks `user.store_id` (nonexistent) |
| `services/merchant_auth_v1.py` | Signup creates new Store + `primary_store_id`; resolve uses `primary_store_id` |
| `models.MerchantUser` | Field is `primary_store_id`, not `store_id` |
| `static/merchant_dashboard_home_v1.js` | Loading copy exactly “CartFlow يجهّز فهم متجرك…” |

---

## 4. Identity ownership map

| Identity | Owner | Key |
|----------|-------|-----|
| Merchant account | `MerchantUser` | `id`, email |
| Session | `cartflow_merchant_session` cookie | `merchant_user_id` only (no store id) |
| Primary tenant | `MerchantUser.primary_store_id` → `Store` | `Store.zid_store_id` |
| Simulation truth tenant | Store Reality Simulator config | hardcoded `demo` |
| Alias | `store_identity_v1` | maps aliases → a Store; does not remap signup→demo |
| Recovery key | write/read paths | `store_slug:session…` — slug half is tenant |

---

## 5. Store ownership flow

```text
POST /signup
  → register_merchant_account
  → create Store(zid = unique from store_name)
  → MerchantUser.primary_store_id = that Store.id
  → session cookie(merchant_user_id)

Simulation execute
  → all durable writes scoped to zid_store_id="demo"

Lab bind attempt
  → demo.merchant_user_id = user.id   ✓ ownership flag on demo
  → user.primary_store_id unchanged   ✗ still signup Store
  → user.store_id = …                 ✗ attribute does not exist
```

**Read path never uses “stores where merchant_user_id == me” as primary** when `primary_store_id` is set — it prefers `primary_store_id` (`get_primary_store_for_merchant`).

---

## 6. Merchant context lifecycle

1. Authenticate → cookie carries **user id**.  
2. Middleware / resolver → `resolve_authenticated_store_slug` → **primary store zid**.  
3. ContextVar `merchant_auth_store_slug` set for request.  
4. Dashboard / Home / Brief / Knowledge (merchant APIs) consume that slug.  
5. No store switcher; no simulation_run attach on read path.

---

## 7. Session lifecycle

| Stage | Behaviour |
|-------|-----------|
| Login/signup | Issue HMAC cookie with `merchant_user_id` |
| Each request | Parse cookie → load user → primary store → slug |
| Logout | Clear cookie |
| Store switch | **Not implemented** on this path |

Session does not embed store; **drift is in primary_store_id vs truth tenant**, not in a stale cookie store field.

---

## 8. Recovery-key lifecycle

- Format: `{store_slug}:{session_part}` (`cartflow_session_truth.parse_recovery_key`).  
- Simulator writes keys under `demo:…`.  
- Merchant session surfaces filter by session store slug `متجر-واقع-صغير-…` → **no keys match**.  
- Isolation (Phase 3.1) correctly prevents remapping demo writes onto linked production zids; it does not create a read bridge.

---

## 9. `store_slug` resolution chain

```text
cookie
  → merchant_user_id
  → MerchantUser.primary_store_id
  → Store.id
  → Store.zid_store_id          ← session slug
  → dashboard_canonical_store_row(slug)
  → Home / Brief / Knowledge / carts APIs
```

Lab/checkpoint **service probes** skip this chain and pass `"demo"` directly.

---

## 10. Merchant selection logic

- `get_primary_store_for_merchant`: (1) `primary_store_id` row if present; else (2) oldest `Store` with `merchant_user_id == user.id`.  
- After signup, (1) always wins → signup store.  
- Setting `demo.merchant_user_id` alone does not change selection while `primary_store_id` points elsewhere.  
- `resolve_merchant_onboarding_store` uses the same primary-store rule; rejects system/widget recovery zids; no multi-store picker.

---

## 11. Home composition ownership

| Layer | Role |
|-------|------|
| `GET /api/dashboard/summary` | Resolves dash store from session; embeds `merchant_home_experience_v1` |
| `build_merchant_home_experience_api_payload(db, slug, dash_store)` | Composes brief + KL for **that slug** |
| `static/merchant_dashboard_home_v1.js` | Renders loading shell until summary applied |
| Activation | `home_stage=activation` / `no_carts` when session store has no carts |

Home is an **Infrastructure Consumer** of the session store — not a second identity owner. It faithfully shows emptiness for the wrong tenant.

---

## 12. Dashboard ownership

- `_dashboard_recovery_store_row` / `dashboard_canonical_store_row(slug)` — session slug.  
- Normal carts / VIP / summary KPIs scoped to that store.  
- Checkpoint: session carts 0; `demo` carts 27.

---

## 13. Knowledge ownership

| Call site | Store used |
|-----------|------------|
| Merchant `GET /api/knowledge/report` | Must match authenticated slug |
| Home / Brief builders in product path | Session slug |
| Checkpoint TA probe `build_knowledge_report(..., "demo")` | Hardcoded `demo` |

**Product Home and product Knowledge share identity.** Lab “Knowledge sees data” ≠ merchant Knowledge UI.

---

## 14. Setup ownership

- Setup / readiness / activation consume the same primary store.  
- Evidence: `home_stage=activation`, `state_id=no_carts` for signup slug.  
- Setup narrative (“complete connection / day-zero”) is **locally honest** for an empty new store and **globally dishonest** relative to the lab’s simulated reality on `demo`.  
- INV-005 (Setup Lifecycle Drift) is a **child symptom surface** of this identity split, not an independent clock failure.

---

## 15. Data availability chain

```text
Simulator → demo tables (carts, PT, reasons, schedules, timeline)
                │
                ├─► Service probe (slug=demo) → data available
                │
                └─► Merchant session (slug=signup) → data unavailable
                         │
                         └─► Home / Carts / session KL / session Brief → empty / no_carts
```

---

## 16. Rendering chain

1. Dashboard loads → Home paints **loading skeleton** (`renderLoading` whisper).  
2. Summary fetch for signup store returns activation / no_carts / empty carts.  
3. Skeleton may clear into activation empty theatre or remain visible during slow/partial apply (capture timing).  
4. Copy “preparing understanding” is **presentation loading text**, not Time Authority emptiness — but it coincides with identity-empty truth, so merchants experience it as “CartFlow doesn’t understand my store.”

---

## 17. First divergence point

**At signup (and preserved by failed lab bind):**

1. Simulation policy targets `demo`.  
2. Signup creates a **new** `Store` and sets `primary_store_id` to it.  
3. Lab bind never updates `primary_store_id` to `demo` (and probes a nonexistent `user.store_id`).  

From that moment, every session-scoped merchant surface diverges from simulation truth.

---

## 18. Root-cause candidates

| ID | Candidate | Status |
|----|-----------|--------|
| RC-A | Session primary store ≠ simulation store (`demo`) | **Confirmed** |
| RC-B | Lab bind helper fails to set `primary_store_id` | **Confirmed** (contributing mechanism in Reality Lab) |
| RC-C | Home uses different identity than Knowledge in product | **Rejected** — same session slug |
| RC-D | Time Authority still wrong after WP-6 | **Rejected** for this symptom (INV-001 closed for reader windows under QTC) |
| RC-E | Rendering hides valid session evidence | **Rejected** as primary — session evidence is empty; skeleton is loading/activation presentation |
| RC-F | Missing governed merchant↔store↔simulation-run read contract | **Confirmed** (architectural gap) |
| RC-G | Alias remaps signup→demo on read | **Rejected** — no such alias; Phase 3.1 write isolation intentional |

---

## 19. Root-cause confidence

| Statement | Confidence |
|-----------|------------|
| Merchant walkthrough incompleteness after Checkpoint V2 is primarily **identity mismatch**, not Time Authority | **High** |
| First divergence is signup primary store vs `demo` | **High** |
| Lab bind does not repair primary_store_id | **High** (code + evidence) |
| Product Home/Knowledge/Brief share session identity | **High** |
| Checkpoint “surfaces see data” refers to **demo probes**, not session UI | **High** |

**Root cause (confirmed statement):**

> There is no governed **merchant session → store_slug → simulation-run** identity contract for lab/demo visibility. Signup establishes a distinct primary store; simulation writes `demo`; session reads follow `primary_store_id`. Reality Lab’s bind helper does not reassign primary store. Therefore Time-Authority-correct readers on `demo` coexist with empty merchant Home on the signup store.

---

## 20. Dependency graph

```text
INV-002 Merchant Identity Drift  (Root Cause Confirmed)
├── INV-003 Knowledge Surface Drift (session path contaminated)
├── INV-004 Attention Semantics Drift (empty queues on wrong store)
├── INV-005 Setup Lifecycle Drift (activation/no_carts on wrong store)
└── INV-007 Monthly Summary (materialisation for wrong/empty store)

INV-001 Time Authority — orthogonal parent for temporal windows;
         necessary but not sufficient for merchant trust after Checkpoint V2.
```

INV-002 remains **independent of Time Authority** (Wave 0 peer). Checkpoint V2 elevates INV-002 to the dominant remaining merchant-trust blocker for Reality Lab walkthroughs.

---

## 21. Systems affected

- Merchant auth / signup / primary store binding  
- Dashboard store resolution / summary / carts  
- Home composition + activation  
- Session-scoped Knowledge and Daily Brief  
- Setup readiness  
- Recovery-key filtered queues  
- Reality Lab / Checkpoint review validity  

Not primarily affected as root: Time Authority recipes (INV-001), visitor ingress (INV-008), WP-5 fixture flake (INV-009).

---

## 22. Merchant impact

- Catastrophic trust failure: “reality ran but my store looks empty.”  
- Cannot distinguish wrong store from product failure.  
- Contaminates judgment of Knowledge, Attention, Setup, Monthly — even when those engines work on `demo`.  
- Skeleton / “preparing understanding” reinforces the false belief that understanding is still computing.

---

## 23. Architectural impact

- `store_slug` is both **tenant key** and **experience key** without a binding layer for sim/lab attach.  
- Cookie carries user, not store; correctness depends entirely on `primary_store_id` hygiene.  
- Write isolation (demo pin) and read visibility are **separate contracts**; fixing one does not imply the other.  
- Child investigations cannot close honestly until session store ≡ truth store for the review under test (or mismatch is labelled).

---

## 24. Verification plan

*(For future implementation — not executed now.)*

1. Merchant session used for Reality review resolves the same `store_slug` as the simulation target (or an explicit attach).  
2. `GET /api/dashboard/normal-carts` under that session returns ≥1 row when `demo` holds Small Reality carts.  
3. Home summary `home_stage` / cart counts non-zero under INV-001 QTC for that store.  
4. Write isolation still holds: sim does not write Purchase Truth onto unrelated linked stores.  
5. UI or API surfaces the active store label so silent mismatch cannot present as “no understanding.”  
6. Evidence: same-session API JSON + screenshots.

---

## 25. Closure criteria

| # | Criterion |
|---|-----------|
| C1 | Written identity contract: merchant session → store slug → simulation run (accepted) |
| C2 | Walkthrough session sees ≥1 cart from Small Reality on that store |
| C3 | Write isolation to `demo` still green |
| C4 | Empty UI cannot occur solely from silent store mismatch without labelled viewing context |

---

## Architectural analysis checklist

| Question | Answer |
|----------|--------|
| Where identity first becomes incorrect | Signup: new Store + `primary_store_id`; sim on `demo` |
| Drift during request composition? | Composition is consistent; **input slug** is wrong for lab narrative |
| Home vs Knowledge different identity? | **No** in product APIs; **Yes** vs lab hardcoded `demo` probes |
| Setup influence? | Yes — activation/`no_carts` frames empty signup store as day-zero |
| Rendering hide valid evidence? | Not primary; session evidence empty; skeleton is loading/activation UX |
| Canonical store differ across layers? | Session layers agree; diverge from simulation tenant |
| Sim vs merchant identity diverge? | **Yes** — core finding |
| Production identity different? | Same mechanism: primary store is always the read key; production multi-store/agency will hit the same class of bug without a contract |

---

## Investigation Health V2 — architecture notes only

Do **not** implement metrics yet. Future scores should eventually consume:

| Score | Candidate evidence inputs |
|-------|---------------------------|
| **Merchant Trust Score** | Same-session cart count vs durable truth store; Home activation≠no_carts when truth exists; labelled store context present; skeleton duration; Reality Checkpoint walkthrough pass/fail |
| **Architecture Stability** | Single store resolution function used by Home/Dash/KL/Brief; primary_store_id↔merchant_user_id invariant checks; no dual hardcoded `demo` bypass in product paths |
| **Operational Stability** | Lab bind success rate; identity alias mismatch alerts; write-isolation guard pass rate |
| **Investigation Trend** | Count of Open/Blocked children of INV-002; time-in-status for INV-002; Checkpoint V2→V3 merchant walkthrough delta |

These remain definitions for a later Investigation Health V2 workstream.

---

## Decision

| Item | Value |
|------|-------|
| Status | **Root Cause Confirmed** |
| Ready for Fix | **No** — requires Definition of Ready / Implementation Architecture authorization |
| Work Packages | **None opened** |
| Next human gate | Architecture Board accepts this review → authorize Implementation Architecture only |

**STOP.** Do not design the solution in engineering. Do not implement. Do not begin Work Packages.
