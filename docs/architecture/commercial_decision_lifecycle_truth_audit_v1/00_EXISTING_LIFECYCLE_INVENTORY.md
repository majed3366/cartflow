# Commercial Decision Lifecycle Truth Audit V1 — Existing Lifecycle Inventory

**Date (UTC):** 2026-09-05  
**Mode:** READ-ONLY architecture audit  
**Production / Console / COL:** UNCHANGED  
**DEPLOY:** NO  
**IMPLEMENTATION:** NOT AUTHORIZED  

**Live production context (untouched):** SHA `0f2ebc5a…` · Decision Console V1.1 frozen visually · Reality Coverage PASS  

---

## How to read this inventory

Classification keys (Phase 2):

| Code | Meaning |
|------|---------|
| **A** | Authoritative persisted truth |
| **B** | Authoritative derived truth |
| **C** | UI / composition state only |
| **D** | Scheduler execution state |
| **E** | Historical event / audit log |
| **F** | Domain-specific, non-reusable for commercial decision lifecycle |
| **G** | Legacy / duplicated / unclear / missing-as-system |

Do **not** equate same-looking names across domains (e.g. recovery `waiting_*` ≠ commercial `under_measurement`).

---

## System 1 — Merchant cart lifecycle archive / reopen

| Field | Value |
|-------|--------|
| **NAME** | MerchantCartLifecycleArchive |
| **DOMAIN** | Dashboard cart archive / reopen |
| **SOURCE OF TRUTH** | `models.MerchantCartLifecycleArchive` → `merchant_cart_lifecycle_archives` |
| **PERSISTED OR DERIVED** | Persisted |
| **STATE ENUM / VALUES** | `is_archived` bool; `archive_source`: `manual` \| `auto_exhausted` |
| **OWNER** | `services/merchant_cart_lifecycle_archive_v1.py` |
| **TRANSITION OWNER** | `archive_recovery_key` / `reopen_recovery_key`; dashboard cart lifecycle API bodies |
| **TRIGGER** | Merchant archive/reopen; auto-exhaustion paths |
| **IDEMPOTENCY** | Upsert by unique `recovery_key` |
| **TIMESTAMP MODEL** | `archived_at`, `reopened_at`, `updated_at` (UTC) |
| **STORE ISOLATION** | `store_slug` + unique `recovery_key` |
| **CAN REOPEN** | YES |
| **HAS TERMINAL STATE** | Soft archive only |
| **HAS OUTCOME STATE** | NO |
| **HAS MEASUREMENT WINDOW** | NO |
| **USED BY UI** | YES (Carts) |
| **USED BY SCHEDULER** | NO (archive does not own send) |
| **USED BY RECOVERY** | Indirect (evidence for classifier / checkout checks) |
| **USED BY COL** | NO |
| **USED BY OGL** | NO |
| **CLASS** | **A** + **F** (cart UI lifecycle, not commercial decision) |
| **EVIDENCE** | `models.py` ~410–430; `schema_merchant_cart_lifecycle_archive.py`; `services/merchant_cart_lifecycle_archive_v1.py` |

---

## System 2 — RecoverySchedule (scheduler execution)

| Field | Value |
|-------|--------|
| **NAME** | RecoverySchedule |
| **DOMAIN** | Delayed WhatsApp recovery execution / restart survival |
| **SOURCE OF TRUTH** | `models.RecoverySchedule` → `recovery_schedules` |
| **PERSISTED OR DERIVED** | Persisted |
| **STATE ENUM / VALUES** | From `services/recovery_restart_survival.py`: `scheduled`, `running`, `completed`, `cancelled`, `skipped_resume_unsafe`, `needs_review`, `failed_resume`, `failed_resume_stale`, `skipped_duplicate`, `skipped_no_phone`, `skipped_no_reason`, `whatsapp_failed`, … (+ send-path skip statuses in `main.py`) |
| **ACTIVE SET** | `{"scheduled","running"}` (`main.py`) |
| **OWNER** | `services/recovery_restart_survival.py` + materialization/dispatch |
| **TRANSITION OWNER** | Schedule writers / due scanner resume / purchase-truth cancel / send completion |
| **TRIGGER** | Reason capture → materialize; `due_at`; purchase/reply cancel |
| **IDEMPOTENCY** | Key `recovery_key + step + multi_slot_index`; completed protected from downgrade |
| **TIMESTAMP MODEL** | `scheduled_at`, `due_at`, `created_at`, `updated_at` |
| **STORE ISOLATION** | `store_slug` + `session_id` + `recovery_key` |
| **CAN REOPEN** | New schedule row; not “reopen commercial decision” |
| **HAS TERMINAL STATE** | YES |
| **HAS OUTCOME STATE** | completed / cancelled / failed_* / skipped_* |
| **HAS MEASUREMENT WINDOW** | Delay only (`due_at`) — **not** commercial measurement |
| **USED BY UI** | YES (next follow-up) |
| **USED BY SCHEDULER** | YES |
| **USED BY RECOVERY** | YES |
| **USED BY COL / OGL** | NO as lifecycle owner |
| **CLASS** | **A** + **D** + **F** |
| **EVIDENCE** | `models.py` ~374–407; `services/recovery_restart_survival.py`; `main.py` active status set |

**DANGEROUS TO REUSE** as commercial `under_measurement`: schedule “waiting” means *send delay*, not *post-merchant-action evidence watch*.

---

## System 3 — Purchase truth + lifecycle closure + attribution

| Field | Value |
|-------|--------|
| **NAME** | PurchaseTruthRecord / LifecycleClosureRecord / PurchaseAttribution |
| **DOMAIN** | Verified purchase + terminal cart closure + post-hoc attribution |
| **SOURCE OF TRUTH** | `purchase_truth_records`; `lifecycle_closure_records`; attribution **derived** |
| **PERSISTED OR DERIVED** | Purchase + closure persisted; attribution derived |
| **STATE ENUM / VALUES** | Closure (`services/lifecycle_closure_records_v1.py`): `purchase_completed`, `returned_to_site`, `customer_replied`, `failed`, `cancelled`, `max_attempts`, `user_rejected_help`, `vip_manual_handling`, … Attribution levels (`services/purchase_attribution_v1.py`): `confirmed_recovery`, `likely_recovery`, `assisted_recovery`, `organic_or_unknown`, `not_attributed` |
| **OWNER** | `services/purchase_truth.py`, `cartflow_purchase_truth.py`, `lifecycle_closure_records_v1.py`, `purchase_attribution_v1.py` |
| **TRANSITION OWNER** | Ingest / closure writers / classify-on-read |
| **TRIGGER** | Purchase webhook, reply claim, terminal logs |
| **IDEMPOTENCY** | Unique `recovery_key`; closure rank merge |
| **TIMESTAMP MODEL** | purchase/closure times; attribution window default **72h** |
| **STORE ISOLATION** | `store_slug` + `session_id` |
| **CAN REOPEN** | NO for purchase row |
| **HAS TERMINAL STATE** | YES |
| **HAS OUTCOME STATE** | YES (cart/recovery outcome — **not** commercial decision WON) |
| **HAS MEASUREMENT WINDOW** | Attribution window only |
| **USED BY UI / SCHEDULER / RECOVERY** | YES |
| **USED BY COL / OGL** | Indirect counts only |
| **CLASS** | **A** (truth/closure); **B** (attribution); **F** for commercial WON mapping |
| **EVIDENCE** | `models.py` ~606–661; `schema_purchase_truth.py`; `schema_lifecycle_closure.py` |

**Do not map** `purchase_completed` → commercial decision `WON` without action baseline + evaluation window + attribution to the commercial action.

---

## System 4 — Customer lifecycle states (merchant-facing cart classifier)

| Field | Value |
|-------|--------|
| **NAME** | CustomerLifecycleStatesV1 |
| **DOMAIN** | Merchant cart operational lifecycle (dashboard) |
| **SOURCE OF TRUTH** | Derived classifier — `services/customer_lifecycle_states_v1.py` (LT-C1 merchant SoT) from schedules/logs/timeline/purchase/archive |
| **PERSISTED OR DERIVED** | Derived (+ persisted inputs) |
| **STATE ENUM / VALUES** | `active`, `waiting_first_send`, `waiting_customer_reply`, `customer_engaged`, `customer_reply`, `return_to_site`, `waiting_purchase_window`, `waiting_next_scheduled`, `needs_intervention`, `completed`, `archived`, `recovery_followup_complete`, … |
| **OWNER** | `services/customer_lifecycle_states_v1.py` |
| **TRANSITION OWNER** | None writes a lifecycle column — `classify_customer_lifecycle_state_v1` |
| **TRIGGER** | Dashboard/snapshot compose |
| **IDEMPOTENCY** | Pure function of evidence |
| **TIMESTAMP MODEL** | Uses evidence timestamps |
| **STORE ISOLATION** | Via recovery_key / store on inputs |
| **CAN REOPEN** | Via archive reopen → reclassify |
| **HAS TERMINAL STATE** | completed / archived / … |
| **HAS OUTCOME STATE** | completed variants |
| **HAS MEASUREMENT WINDOW** | `waiting_purchase_window` (behavioral) |
| **USED BY UI** | YES |
| **USED BY SCHEDULER / RECOVERY** | Read evidence; not send gate |
| **USED BY COL / OGL** | NO |
| **CLASS** | **B** + **F** |
| **EVIDENCE** | `services/customer_lifecycle_states_v1.py`; guard abstraction `services/cartflow_lifecycle_guard.py` |

**DANGEROUS TO REUSE:** `waiting_*` ≠ commercial `under_measurement`.

---

## System 5 — Recovery truth timeline

| Field | Value |
|-------|--------|
| **NAME** | RecoveryTruthTimelineEvent |
| **DOMAIN** | Append-only recovery transition history |
| **SOURCE OF TRUTH** | `recovery_truth_timeline_events` |
| **PERSISTED OR DERIVED** | Persisted events |
| **STATE ENUM / VALUES** | Ordered: `scheduled` → `delay_started` → `before_send` → `provider_queued` → `provider_sent` → `webhook_delivered` → `customer_reply` → `continuation_started` |
| **OWNER** | `services/recovery_truth_timeline_v1.py` |
| **TRANSITION OWNER** | `record_timeline_event` writers |
| **TRIGGER** | Schedule / send / webhook / reply |
| **IDEMPOTENCY** | Most statuses once per `recovery_key` |
| **TIMESTAMP MODEL** | `created_at` |
| **STORE ISOLATION** | `store_slug` + `recovery_key` |
| **CAN REOPEN** | NO (append-only) |
| **HAS TERMINAL / OUTCOME / MEASUREMENT** | No commercial measurement; last event = evidence |
| **USED BY** | UI/debug, customer lifecycle, recovery |
| **CLASS** | **E** (+ **A** for presence queries); **F** |
| **EVIDENCE** | `models.py` ~540–556; `schema_recovery_truth_timeline.py` |

---

## System 6 — Communication follow-up / delivery truth / recovery logs

| Field | Value |
|-------|--------|
| **NAME** | MerchantFollowupAction + WhatsAppDeliveryTruth + CartRecoveryLog |
| **DOMAIN** | Merchant alert after reply; provider delivery; send logs |
| **SOURCE OF TRUTH** | `merchant_followup_actions`; `whatsapp_delivery_truth`; `cart_recovery_logs` |
| **PERSISTED OR DERIVED** | Persisted |
| **STATE ENUM / VALUES** | Followup: `needs_merchant_followup`; delivery send/delivery/read statuses; log statuses `sent_real`, `mock_sent`, `whatsapp_failed`, `skipped_*`, … |
| **OWNER** | `services/whatsapp_positive_reply.py`; delivery webhook paths; send writers |
| **TRANSITION OWNER** | Upsert followup; delivery SID updates; log append |
| **TRIGGER** | Inbound reply; provider webhooks; recovery send |
| **STORE ISOLATION** | store_id / store_slug / recovery_key |
| **USED BY COL** | Communication family uses **counts** (`no_phone`), not followup row lifecycle |
| **CLASS** | **A** + **F** |
| **EVIDENCE** | `models.py` ~433–490, 576–603 |

---

## System 7 — Business Findings + Business Findings Lifecycle (BFL)

| Field | Value |
|-------|--------|
| **NAME** | BusinessFinding + BFL lifecycle |
| **DOMAIN** | Durable commercial **findings** (evidence objects), not merchant action commitments |
| **SOURCE OF TRUTH** | `business_findings` (`models.BusinessFinding`) |
| **PERSISTED OR DERIVED** | Persisted |
| **FINDING STATUS** | `emerging`, `confirmed`, `strengthening`, `weakening`, `resolved`, `insufficient_evidence`, `conflicting_evidence` — `services/business_findings_contract_v1.py` |
| **BFL lifecycle_state** | `detected` → `validated` → `persisted` → `knowledge_routed` → `operational_truth_routed` → `surface_eligible` → `displayed` → `resolved` → `archived` — `services/business_findings_lifecycle_v1/types_v1.py` |
| **OWNER** | `services/business_findings_*`; `services/business_findings_lifecycle_v1/*` |
| **TRANSITION OWNER** | `materialize_v1` / `advance_state` / `consume_home_v1` (displayed) |
| **TRIGGER** | Findings engine / Home consume |
| **IDEMPOTENCY** | Unique `finding_id`; fingerprint; `is_current` / supersede |
| **TIMESTAMP MODEL** | `generated_at`, `expires_at`, `as_of`, `created_at`, `refreshed_at`, `superseded_at` |
| **STORE ISOLATION** | `store_slug` |
| **CAN REOPEN** | New finding / supersede; resolve/archive terminals |
| **HAS TERMINAL STATE** | resolved / archived |
| **HAS OUTCOME STATE** | finding `resolved`; recommendation types `act_now`\|`test`\|`monitor`\|… |
| **HAS MEASUREMENT WINDOW** | Optional `expires_at` — **not** post-action measurement of merchant change |
| **USED BY UI / DCE / KL** | YES |
| **USED BY COL** | Evidence inputs possible; COL primary path is reason counts |
| **CLASS** | **A** + **PARTIAL reuse** (identity/status patterns); **not** action→measure lifecycle |
| **EVIDENCE** | `models.py` ~1411+; `schema_business_findings_lifecycle_v1.py`; `lifecycle_v1.py` `advance_state` |

---

## System 8 — Decision Composition Engine (DCE)

| Field | Value |
|-------|--------|
| **NAME** | DecisionCompositionEngineV1 |
| **DOMAIN** | Home/Workspace decision **cards** from findings/waiting/recoverability |
| **SOURCE OF TRUTH** | Request-time compose (`services/decision_composition_engine_v1/*`) |
| **PERSISTED OR DERIVED** | Derived (`decision_id` e.g. `dce:finding:{fid}`, `dce:waiting_recovery`) |
| **TRANSITION OWNER** | Compose only |
| **CLASS** | **B** |
| **EVIDENCE** | `services/decision_composition_engine_v1/` |

---

## System 9 — Merchant Decision Registry / Layer

| Field | Value |
|-------|--------|
| **NAME** | MerchantDecisionRegistry + MerchantDecisionLayer |
| **DOMAIN** | Catalog of cart-level merchant actions (`decision_obtain_contact`, …) |
| **SOURCE OF TRUTH** | Code constants + composed instances |
| **PERSISTED OR DERIVED** | Derived (no durable decision instance table for commercial advisor) |
| **CLASS** | **B** + **F** |
| **EVIDENCE** | `services/merchant_decision_registry_v1.py`, `merchant_decision_layer_v1.py` |

---

## System 10 — Cart Workspace shadow DecisionRecord

| Field | Value |
|-------|--------|
| **NAME** | CartWorkspace ShadowStore DecisionRecord |
| **DOMAIN** | Sprint-1 cart workspace admission/ownership |
| **SOURCE OF TRUTH** | `services/cart_workspace/shadow_store_v1.py` (process memory) |
| **STATE** | `open` \| `resolving` \| `closed`; `allocate_decision_id()` → uuid4 |
| **CLASS** | **C** (ephemeral — **not** durable A) |
| **EVIDENCE** | `services/cart_workspace/contracts_v1.py`, `decision_identity_v1.py` |

---

## System 11 — Operational Guidance Layer (OGL)

| Field | Value |
|-------|--------|
| **NAME** | OperationalGuidanceLayerV1 |
| **DOMAIN** | Evidence→diagnosis→recommendation→recheck **object** for Home/Workspace |
| **SOURCE OF TRUTH** | Compose-time; **no OGL table** |
| **STATE** | `confidence_state`: `active` \| `insufficient_evidence` \| `abstained`; `guidance_id` `ogl:…` |
| **MEASUREMENT / RECHECK** | Arabic `recheck_condition` / expected outcome **text only** |
| **CLASS** | **B** |
| **EVIDENCE** | `services/operational_guidance_v1/contract_v1.py`, `compose_v1.py` |

Note: separate persisted `commercial_guidance_records` / eligibility / routes exist for the broader guidance pipeline — **not** the same as OGL merchant surface lifecycle.

---

## System 12 — Commercial Opportunity Layer (COL)

| Field | Value |
|-------|--------|
| **NAME** | CommercialOpportunityLayerV1 |
| **DOMAIN** | Primary commercial opportunity for Home + Workspace |
| **SOURCE OF TRUTH** | Compose from `merchant_reason_counts_week` + teasers; focus via `sessionStorage` key `cf2_col_focus_v1` |
| **PERSISTED OR DERIVED** | Derived (+ **C** browser focus handoff) |
| **TRUTH CLASSES** | `PRODUCTION_TRUTH_READY`, `PRODUCTION_PARTIAL`, `SIMULATION_ONLY`, `INSUFFICIENT` — `services/commercial_opportunity_layer_v1/contract_v1.py` |
| **IDENTITY** | `opportunity_id`: `col:{family}:{reason}:{store_slug}` (deterministic) |
| **MEASURE / RECHECK** | `measure_ar` / `recheck_ar` / `decision_contract_ar` — **copy fields**, not persisted windows |
| **TRANSITION OWNER** | `compose_v1` / `attach_v1`; UI `sessionStorage.setItem` |
| **CLASS** | **B** + **C** |
| **EVIDENCE** | `services/commercial_opportunity_layer_v1/*`; `static/merchant_ui_v2_home.js` |

---

## System 13 — Decision Console / CDA presentation

| Field | Value |
|-------|--------|
| **NAME** | Decision Console V1.1 + Commercial Decision Arc (`cf-cda`) |
| **DOMAIN** | Visual state expression |
| **SOURCE OF TRUTH** | Client paint from COL `truth_class` + optional paintOpts |
| **CONSOLE MODES** | `actionable` \| `measuring` \| `recheck` \| `insufficient` |
| **CDA ARCS** | `action_chosen`, `under_measurement`, `recheck_due`, `insufficient_evidence`, … |
| **PERSISTED?** | **NO** |
| **CLASS** | **C** |
| **EVIDENCE** | `static/merchant_ui_v2_workspace.js` (`consoleModeFromOpp`, `consoleArcForMode`); `static/commercial_decision_arc_production_v1.js` |

**Critical:** CDA `under_measurement` / `recheck_due` / `action_chosen` are **paint**, not lifecycle truth.

---

## System 14 — Adjacent persisted windows (not commercial action measurement)

| Name | Table / service | Role | Class |
|------|-----------------|------|-------|
| Product metrics/trends | `product_metric_values`, `product_trend_values` | Aggregates | A / F |
| Knowledge validity | `knowledge_statements.valid_from/until` | Statement TTL | A / F |
| Diagnostic snapshots | `diagnostic_snapshots` | Diagnosis status | A |
| Surface compositions / presentations | `surface_compositions`, `merchant_presentations` | Surface freshness | A |
| Provider retry ledger | `provider_retry_ledger` | Send retry | A+D |
| AbandonedCart.status / VIP | `abandoned_carts` | Coarse cart status | A / F |
| RRV missions | in-memory sim | Lab only | C / F |

---

## Count summary (inventory)

| Class | Approx count (systems above) |
|-------|------------------------------|
| A authoritative persisted | 9+ (archive, schedule, purchase/closure, timeline, followup/delivery/logs, findings/BFL, diagnostics, product metrics, abandoned cart) |
| B authoritative derived | 5+ (customer lifecycle, DCE, MDL instances, OGL, COL package, attribution) |
| C UI-only | 3 (CDA/Console, COL sessionStorage focus, cart workspace shadow) |
| D scheduler | 2 (RecoverySchedule, provider retry) |
| E historical events | 1+ (timeline; also logs) |
| F domain-specific | Most recovery/cart systems |
| G / missing | Commercial action→measure→recheck **as a system** |

---

## Stable commercial decision identity (Phase 4 answer)

| Candidate | Stable across copy changes? | Survives restart? | Prevents duplicate concurrent decisions? |
|-----------|----------------------------|-------------------|------------------------------------------|
| COL `opportunity_id` `col:{family}:{reason}:{store}` | YES (key not title) | Recomputable; **no commitment row** | Soft — same key recomposed; **no exclusive lock** |
| OGL `guidance_id` | YES | Derived only | Same |
| BFL `finding_id` | YES | YES persisted | Per finding fingerprint |
| DCE `decision_id` | YES | Derived | Soft |
| Cart workspace UUID | YES until restart | **NO** | In-process only |
| Title / Arabic copy | NO | — | — |

**Verdict:** **PARTIAL** — compositional IDs exist (especially COL `opportunity_id`), but **no persisted commercial decision commitment** spanning discover → action → measurement → recheck → outcome.

---

## Measurement / outcome gaps (Phases 6–7)

| Needed for commercial measurement | Exists today? |
|-----------------------------------|---------------|
| Merchant action acknowledgement timestamp | **NO** |
| Baseline snapshot at action time | **NO** |
| Measurement window start/end | **NO** (only copy / attribution 72h / finding expires) |
| Target metric + observed metric + comparison | **NO** as decision-bound |
| Recheck threshold fired as persisted event | **NO** |
| Outcome result bound to commercial action | **NO** |
| Bounded causal attribution for commercial action | **NO** (purchase attribution ≠ commercial action WON) |
| Persisted decision lesson (LEARNED) | **NO** |

STOP — inventory only; see `01_REUSE_MATRIX.md` and `REPORT.md`.
