# CartFlow Identity Authority Architecture V1

**Status:** Proposed for Product + Architecture ratification  
**Date (UTC):** 2026-07-16  
**Investigation:** INV-002 — Merchant Identity Drift (Root Cause Confirmed)  
**Governing product law:** [`MERCHANT_TRUST_CONSTITUTION_V1.md`](MERCHANT_TRUST_CONSTITUTION_V1.md)  
**Sibling authority:** Time Authority Architecture V2 (orthogonal — *when* vs *which store*)  
**Scope:** Permanent Merchant Identity Authority — architecture only  
**Out of scope:** Implementation · code · migrations · schema · Work Packages · demo-only hacks  

> This is not a plan to “fix demo.”  
> This is the identity model that must remain correct for Demo, Reality Simulator, Production, Zid, Salla, Shopify, and future providers.

---

## 0. Primary question

### What is the single authoritative identity model that every merchant-facing surface must consume?

**Answer:** the **Merchant Query Identity Context (MQIC)** — an immutable, request-scoped identity bundle resolved once by the **Platform Identity Authority** and consumed by every merchant-facing surface.

Surfaces must not invent, hardcode, or silently substitute `store_slug`.

```text
Platform Identity Authority
        │
        ▼
Merchant Query Identity Context (MQIC)   ← single read contract
        │
        ├── Home / Dashboard / Cart Workspace
        ├── Knowledge / Daily Brief / Recommendations
        ├── Timeline / WhatsApp merchant views / Setup
        └── Reality Validation walkthrough (same contract)
```

**Time Authority** answers: *as of when?*  
**Identity Authority** answers: *for which merchant + which canonical store?*  
Both must be present for lawful understanding speech (Trust Constitution MT-1, MT-2).

---

## 1. Architectural questions

### 1.1 What is Merchant Identity?

The durable binding between:

1. a **human/account principal** (who is logged in), and  
2. one or more **canonical CartFlow stores** they may operate, and  
3. the **active store context** for the current request/session.

Merchant Identity is **not** a provider shop id, not a simulation run id, and not a display name.

### 1.2 What owns merchant identity?

| Owner | Owns |
|-------|------|
| **Platform Identity Authority** | Resolution rules, MQIC construction, invariants, mismatch detection |
| **Merchant Account store** (conceptual) | Durable `merchant_id`, credentials, membership |
| **Surfaces** | Nothing — they consume MQIC only |

### 1.3 What owns store identity?

| Owner | Owns |
|-------|------|
| **Canonical Store Registry** (under Identity Authority) | CartFlow store record: `canonical_store_id`, `store_slug`, lifecycle |
| **Provider adapters** | External ids (Zid / Salla / Shopify / …) as **aliases only** |
| **Simulator** | May **claim** or **create** a canonical store for a run — never bypass MQIC on read |

### 1.4 What owns canonical store identity?

**Platform Identity Authority → Canonical Store Registry.**

Canonical identity is CartFlow-native (`canonical_store_id` + stable `store_slug`).  
Provider ids resolve **to** canonical; they never replace it in merchant reads.

### 1.5 What owns merchant session identity?

| Layer | Owner |
|-------|-------|
| Authentication session (who logged in) | Auth service (cookie/token → `merchant_id`) |
| **Active store selection** for that session | Identity Authority (membership + primary + explicit switch/attach) |
| Propagation into the request | Identity middleware / composition root → MQIC |

The auth cookie may carry only `merchant_id`.  
**Active store must still be resolved into MQIC** — never left implicit in ad-hoc helpers.

### 1.6 What owns simulation identity?

| Concept | Owner |
|---------|-------|
| `simulation_run_id` | Reality Simulator / run registry |
| Store targeted by the run | Simulator config **must bind** to a `canonical_store_id` |
| Merchant walkthrough of that run | Identity Authority **attach** (session → canonical store of the run) |
| Time of the run | Time Authority (QTC / simulation scope) — orthogonal |

Simulation identity does **not** own merchant reads. Attach does.

### 1.7 What owns provider identity?

Provider adapters own **external identity tuples**:

`(provider, external_shop_id[, install_id]) → canonical_store_id`

Write isolation (Phase 3.1 class): provider/sim writes pin to the **canonical** store declared for the operation.  
Alias expansion must never silently remap truth onto a different merchant’s primary store.

### 1.8 How are identities resolved?

**Single resolve function (conceptual):**

```text
ResolveMQIC(auth_principal, request_hints) → MQIC | IdentityError
```

Resolution order (normative):

1. Authenticate → `merchant_id`  
2. Determine **candidate active store**:
   - explicit request store (if allowed + membership verified), else  
   - session active store, else  
   - merchant primary store, else  
   - fail closed (`no_active_store`)  
3. Resolve aliases → **canonical_store_id** + `store_slug`  
4. Attach optional **simulation_run_id** / **replay_id** if present and authorized  
5. Bind provider provenance if relevant  
6. Emit MQIC + identity provenance  

Fail closed on conflict. Never “best effort” to a different store.

### 1.9 How is identity propagated?

- **One resolution per request** at the composition root / middleware.  
- MQIC stored in request-scoped context (parallel to Query Time Context).  
- Downstream services accept MQIC (or derive `store_slug` **only** from MQIC).  
- Background jobs carry explicit identity stamps (merchant/store/run) — no ambient guess.

### 1.10 How is identity verified?

Mandatory checks before merchant speech (MT-2):

| Check | Failure |
|-------|---------|
| Merchant authenticated | 401 / login |
| Merchant is member of active store | 403 / identity mismatch |
| `store_slug` in API query matches MQIC (if provided) | 403 forbid mismatch |
| Simulation attach authorized for this merchant | reject attach |
| Provider alias resolves to same canonical as MQIC on write | reject write |

### 1.11 How is identity observed?

Identity Authority exposes **read-only diagnostics** (Admin / ops — not merchant chrome):

- Active MQIC fields  
- Resolution path taken (primary / explicit / attach)  
- Alias chain  
- Membership proof  
- Mismatch counters  

### 1.12 How is identity replayed?

For Reality Validation / historical review:

1. Time Authority supplies QTC (as-of / simulation end).  
2. Identity Authority supplies MQIC with the **same canonical store** the run wrote to.  
3. Optional `simulation_run_id` / `replay_id` for provenance.  

Replay without MQIC≡truth-store is **invalid for merchant trust review**.

### 1.13 How is identity audited?

Append-only identity audit events (conceptual):

- store created / primary changed / membership granted  
- active store switched  
- simulation attach / detach  
- alias linked / unlinked  
- mismatch detected  
- forbidden cross-store read/write blocked  

Audits support INV closure and Investigation Health — not merchant UI.

### 1.14 How are identity mismatches detected?

| Signal | Example |
|--------|---------|
| **Hard mismatch** | Query `store_slug` ≠ MQIC `store_slug` |
| **Truth divergence** | Lab/ops: simulation target ≠ session MQIC (Checkpoint V2 class) |
| **Alias conflict** | Two canonicals claim same provider id |
| **Orphan primary** | `primary_store_id` missing or not a member store |
| **Write isolation breach** | Write attempted to non-declared canonical |

Hard mismatches **fail closed**. Soft/ops divergences raise diagnostics.

### 1.15 How are identity conflicts prevented?

| Prohibition | Rationale |
|-------------|-----------|
| Surfaces hardcoding `demo` or any slug | Breaks MT-9 / MQIC singularity |
| Lab bind that sets ownership flags without primary/active store | INV-002 RCA |
| Silent alias remap of writes across merchants | Phase 3.1 |
| Multiple competing “get store for request” helpers | Dual authority |
| Recommendations under ambiguous MQIC | MT-2, MT-6 |

**One Authority. One MQIC. One store story per request.**

---

## 2. Merchant Trust Constitution compliance

| Principle | Architectural effect |
|-----------|----------------------|
| **Evidence Before Speech (MT-1)** | Evidence queries keyed only by MQIC canonical store — never by a parallel probe store |
| **Identity Before Understanding (MT-2)** | Understanding APIs refuse to run (or must silence claims) if MQIC missing/ambiguous |
| **Silence Is Legal (MT-3)** | IdentityError / no_active_store → honest empty / login — not invented demo data |
| **Progressive Trust (MT-10)** | Trust Ladder evaluated **per MQIC store**; stage does not transfer across stores |
| **No Fake Intelligence (MT-7)** | “Preparing understanding” cannot cite another store’s evidence; loading ≠ cognition |
| **One Store Story (MT-9)** | Home, Knowledge, Brief, Carts, Setup share one MQIC per request |
| **Guidance privilege (MT-6)** | Recommendations forbidden unless MQIC verified and Trust stage allows |

---

## 3. Platform Identity Authority

### 3.1 Components

```text
┌─────────────────────────────────────────────────────────┐
│              Platform Identity Authority                 │
├─────────────────────────────────────────────────────────┤
│  Merchant Account Registry     → merchant_id             │
│  Canonical Store Registry      → canonical_store_id, slug│
│  Membership & Primary Binding  → who may operate what    │
│  Provider Alias Directory      → external → canonical    │
│  Session Active Store          → per-session selection   │
│  Simulation / Replay Attach    → run → canonical store   │
│  MQIC Factory                  → immutable request ctx   │
│  Verification & Audit          → fail-closed + events    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Identity kinds (ownership boundaries)

| Kind | Meaning | Owner | Consumed by surfaces? |
|------|---------|-------|------------------------|
| **Canonical Merchant Identity** | Account principal | Merchant Account Registry | Via MQIC only |
| **Canonical Store Identity** | CartFlow tenant | Canonical Store Registry | Via MQIC only |
| **Session Identity** | Authenticated visit + active store pointer | Auth + Identity Authority | Via MQIC |
| **Context Identity (MQIC)** | Immutable request bundle | MQIC Factory | **Yes — mandatory** |
| **Simulation Identity** | Run id + bound canonical store | Simulator + Attach API | Via MQIC fields |
| **Replay Identity** | Historical as-of review stamp | Time + Identity attach | Via MQIC + QTC |
| **Provider Identity** | External shop tuple | Provider Alias Directory | Never directly in UI logic |

### 3.3 MQIC — canonical fields (logical)

| Field | Purpose |
|-------|---------|
| `merchant_id` | Who |
| `canonical_store_id` | Which CartFlow store |
| `store_slug` | Stable tenant key for reads/writes |
| `store_display_name` | Label only (not identity) |
| `membership_role` | Operator rights |
| `resolution_path` | primary \| explicit \| attach \| … |
| `provider_bindings[]` | Provenance (optional) |
| `simulation_run_id` | Optional |
| `replay_id` | Optional |
| `identity_provenance` | Internal audit bundle |
| `identity_confidence` | resolved \| degraded \| failed |
| `correlation_id` | Cross-authority trace with QTC |

MQIC is **immutable** after creation for the request.

---

## 4. Identity pipeline (ownership transitions)

```text
Signup
  │  [Owner: Auth + Identity Authority]
  │  create merchant_id
  │  create canonical store (or bind invited store)
  │  set membership + primary
  ▼
Merchant
  │  [Owner: Merchant Account Registry]
  │  durable principal
  ▼
Store (Canonical)
  │  [Owner: Canonical Store Registry]
  │  store_slug is CartFlow-native
  │  provider aliases may attach later (Zid/Salla/Shopify/…)
  ▼
Session
  │  [Owner: Auth → merchant_id]
  │  [Owner: Identity Authority → active store]
  │  FORBIDDEN: active store left unresolved
  ▼
MQIC resolution (request)
  │  [Owner: Identity Authority]
  │  fail closed on conflict
  ▼
Dashboard / Home / Cart Workspace
  │  [Owner: Surface projectors — consume MQIC]
  │  FORBIDDEN: local store invent
  ▼
Knowledge
  │  [Owner: Knowledge — filters by MQIC.store_slug]
  │  FORBIDDEN: hardcoded demo in product path
  ▼
Daily Brief
  │  [Owner: Brief — same MQIC]
  ▼
Recommendations
  │  [Owner: Decision/Intelligence projectors]
  │  require MQIC + Trust stage + evidence
  ▼
Reality Validation walkthrough
  │  [Owner: Lab uses Identity Attach + same MQIC contract]
  │  FORBIDDEN: parallel “probe as demo, UI as signup”
```

**Every arrow is an ownership transition.**  
Surfaces below MQIC are **consumers**, never identity authors.

---

## 5. Identity contracts

### 5.1 Contracts

| Contract | Statement |
|----------|-----------|
| **C-ID-1** | Every merchant-facing read resolves MQIC exactly once. |
| **C-ID-2** | All tenant-scoped queries use `MQIC.store_slug` / `canonical_store_id`. |
| **C-ID-3** | Provider ids are aliases; canonical CartFlow store is the read/write tenant. |
| **C-ID-4** | Simulation runs declare a canonical store; merchant review attaches to it via Identity Authority. |
| **C-ID-5** | Time Authority QTC and Identity MQIC are composed; neither substitutes for the other. |
| **C-ID-6** | Admin/ops may observe identity; they must not invent a second merchant identity channel. |

### 5.2 Invariants

| ID | Invariant |
|----|-----------|
| **I-1** | `primary_store_id` (or successor) ∈ merchant’s membership set |
| **I-2** | Active store ∈ membership set |
| **I-3** | Alias → exactly one canonical (no ambiguous fan-out on resolve) |
| **I-4** | Recovery keys’ store half equals MQIC.store_slug for session-scoped views |
| **I-5** | Product paths never hardcode tenant slugs |

### 5.3 Guarantees

- Fail closed on mismatch (no silent empty from wrong store without identity diagnostic).  
- Merchant speech about store X cites evidence only from store X (MT-2).  
- Write isolation: sim/provider writes stay on declared canonical.  
- Replay/review can reconstruct MQIC + QTC pair.

### 5.4 Assumptions

- A merchant may eventually operate multiple stores (membership model).  
- Demo is a canonical store like any other — not a magical bypass.  
- Providers will multiply; alias directory must scale without changing MQIC.  
- Trust Constitution ratification governs speech; Identity Authority governs binding.

### 5.5 Prohibitions

- Demo-only special cases in product read paths  
- Lab scripts mutating random ownership fields outside Identity Attach  
- Surface-level “if empty, try demo” fallbacks  
- Dual resolve helpers with different precedence  
- Recommendations under `identity_confidence=failed`  
- Treating display name as identity  

---

## 6. Multi-environment correctness

| Environment | Identity rule |
|-------------|----------------|
| **Production** | MQIC from auth + membership + primary/explicit switch |
| **Zid / Salla / Shopify** | OAuth/install creates/links **alias → canonical**; merchant reads always canonical |
| **Demo** | Canonical store `demo` (or successor); merchants access only via membership/attach |
| **Reality Simulator** | Run binds writes to canonical; walkthrough **must Attach** before merchant UI review |
| **Future integrations** | New provider = new alias adapter; MQIC unchanged |

---

## 7. Identity observability

| Capability | Purpose |
|------------|---------|
| **Diagnostics** | Admin view of current MQIC, resolution_path, membership |
| **Provenance** | Why this store was chosen (primary / switch / attach) |
| **Tracing** | `correlation_id` shared with QTC / request logs |
| **Mismatch reporting** | Structured events for Investigation Dashboard / ops |
| **Identity confidence** | `resolved` \| `degraded` (e.g. display-only gap) \| `failed` |

Merchant UI may show **store label** (MT-9 honesty).  
Merchant UI must not show raw authority internals.

---

## 8. Relationship to Time Authority

| Concern | Authority |
|---------|-----------|
| Which store | **Identity Authority → MQIC** |
| What time window | **Time Authority → QTC** |
| Understanding speech | Requires **both** + Trust Ladder |

INV-001 fixed temporal drift **within** a store.  
INV-002 requires Identity Authority so the merchant stands in the **correct** store before Trust speech applies.

---

## 9. Non-goals (this architecture document)

- Choosing UI for store switcher  
- SQL schema / migration design  
- Work Package breakdown / DoR  
- Patching Reality Lab scripts  
- Provider-specific OAuth details beyond alias ownership  

Those follow only after ratification + Definition of Ready.

---

## 10. Success criteria (architectural)

Architecture is adequate when:

1. A single MQIC definition exists and is mandatory for merchant surfaces.  
2. Demo, Simulator, Production, and all providers share the same resolve model.  
3. Reality Validation cannot claim merchant trust using a probe store ≠ session MQIC.  
4. Trust Constitution MT-2 is enforceable as an identity precondition.  
5. No surface owns a private store resolution policy.

---

## 11. Decision & STOP

| Item | Value |
|------|-------|
| Document | `IDENTITY_AUTHORITY_ARCHITECTURE_V1.md` |
| Status | **Proposed** — awaiting Product + Architecture approval |
| Implementation | **Not authorized** |
| Definition of Ready | **Not started** |
| Work Packages | **None** |

**STOP.**

Do not design implementation.  
Do not begin Definition of Ready.  
Do not begin INV-002 coding.  
Wait for Product and Architecture approval.
