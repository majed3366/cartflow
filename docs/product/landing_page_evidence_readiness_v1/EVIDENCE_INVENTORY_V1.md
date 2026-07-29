# Evidence Inventory V1

**Status:** Candidate evidence inventory for future landing publication.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Evidence Readiness V1  

Decorative assets are never evidence. 3D images are never proof of product capability.

### Evidence types

`Product UI Evidence` · `Customer Journey Evidence` · `Operational Evidence` · `Reality Validation Evidence` · `Performance Evidence` · `Integration Evidence` · `Commercial Path Evidence` · `Trust/Governance Evidence` · `Legal Evidence` · `Illustrative Evidence` · `Decorative Support`

---

## Inventory

| Evidence ID | Evidence Name | Product Layer | Section(s) | Evidence Type | Current Source | Environment | Level | Freshness | Sensitive Data Risk | Capture Needed | Validation Needed | Publication Decision |
|-------------|---------------|---------------|------------|---------------|----------------|-------------|-------|-----------|---------------------|----------------|-------------------|----------------------|
| EI-001 | Signup path | Auth | LP-01,15 | Commercial Path | `routes/merchant_auth.py` `/signup` | Production | E4 | Current | Low | No | No | **Eligible** (path claim) |
| EI-002 | Login path | Auth | LP-01,15 | Commercial Path | `routes/merchant_auth.py` `/login` | Production | E4 | Current | Low | No | No | **Eligible** |
| EI-003 | Demo booking path | Auth/Sales | LP-15 | Commercial Path | — | — | E0 | — | — | N/A | N/A | **Rejected** — does not exist |
| EI-004 | Landing contact email | Support | LP-16 | Commercial Path | `cartflow_landing.html` mailto | Production | E4 | Current | Low | No | No | **Eligible** |
| EI-005 | Privacy page | Legal | LP-16 | Legal Evidence | — | — | E0 | — | — | Create page | Legal | **Rejected** until exists |
| EI-006 | Terms page | Legal | LP-16 | Legal Evidence | — | — | E0 | — | — | Create page | Legal | **Rejected** until exists |
| EI-007 | Widget V2 runtime | Storefront | LP-05,06 | Engineering / Customer Journey | `static/cartflow_widget_runtime/*` | Production default | E2–E3 | Current | Med (customer) | Yes storefront | Soft | **Not publishable alone** |
| EI-008 | Reason capture API | Storefront | LP-06 | Operational Evidence | `POST /api/cartflow/reason` | Production | E3 | Current | Med | Yes UI | No | Supports claim after capture |
| EI-009 | Landing widget_settings.png | Settings | LP-06 | Product UI (wrong surface) | `static/img/landing/widget_settings.png` | Landing | E1 | **Stale 2026-05-31** | Low | Replace | — | **Ineligible** (settings ≠ storefront) |
| EI-010 | Visual-gate widget flow PNGs | Demo storefront | LP-06 | Customer Journey | `scripts/_production_visual_gate_out/` | Demo/test | E3–E4 | Mid (audit 2026-06) | Low (demo) | Retake for landing | Truth review | **Not E6** — candidate source only |
| EI-011 | Mobile storefront widget pack | Storefront | LP-06 | Customer Journey | — | — | E0 | — | Med | **Yes** | Soft | **Missing** |
| EI-012 | Widget load strategy (async) | Storefront | LP-06, FAQ | Performance Evidence | `widget_loader.js` async; V2 serial modules | Code | E2 | Current | Low | Measure | Perf study | **Not sufficient for speed claim** |
| EI-013 | Measured storefront Web Vitals with/without widget | Storefront | FAQ CL-31 | Performance Evidence | — | — | E0 | — | Low | Benchmark | Perf validation | **Blocked** |
| EI-014 | Purchase Truth stop engine | Recovery | LP-07,12 | Operational Evidence | tests + services Purchase Truth | Prod/tests | E3 | Current | Low | Prefer UI | No | Supports bounded claim |
| EI-015 | Merchant carts purchase state | Merchant UI | LP-07,08,12 | Product UI | `#carts` / proof surface | Production | E4 | Current | Med | Yes | No | Eligible after capture scrub |
| EI-016 | Communication status UI | Merchant UI | LP-07 | Product UI | `#communication` | Production | E4 | Current packs ~2026-07-26 | Med | Yes | Ops wording | Eligible after capture |
| EI-017 | Landing whatsapp_settings.png | Settings | LP-07 | Product UI (wrong) | `static/img/landing/whatsapp_settings.png` | Landing | E1 | Stale | Low | Replace | — | **Ineligible** for journey |
| EI-018 | Meta production readiness | Provider | LP-07 | Operational / Integration | Meta readiness audit; `integration_health_v1` | Production | E2–E3 | Current | Low | N/A | Ops | Disclosure: often blocked |
| EI-019 | Twilio recovery send path | Provider | LP-07 | Operational | WhatsApp send services | Ops-gated | E3 | Current | Med | Journey UI | Ops | Bounded claim only |
| EI-020 | Home Constitution V2 screenshots | Merchant UI | LP-08,10 | Product UI / RV | `docs/product/home_constitution_v2/prod_*.png` | Living Store/prod | E4–E5 | 2026-07-27 | Med | Re-capture landing-safe | Face OK | **Capture candidate** |
| EI-021 | Workspace Simplification screenshots | Merchant UI | LP-08,10,12 | Product UI | `decision_workspace_simplification_v1/prod_*.png` | Living Store | E4–E5 | **2026-07-29** | Med | Re-capture landing-safe | Face OK | **Capture candidate** |
| EI-022 | Observation admission Home shots | Merchant UI | LP-08,09 | Product UI | `observation_admission_bridge_v1/` | Prod | E4 | 2026-07-25–27 | Med | Optional | Empty-state honesty | Candidate |
| EI-023 | Landing carts/ops crops | Merchant UI | LP-08 | Product UI | `static/img/landing/carts_dashboard.png` etc. | Landing | E1 | **Stale 2026-05-31** | Low | Replace | — | **Ineligible** as current face |
| EI-024 | ORV findings Home screenshots | Knowledge | LP-09 | Reality Validation + UI | `observation_reality_validation_v1/*.png` | Released ORV | E5 | 2026-07-24 | Med | Landing-safe retake | Theme check | Candidate with disclosure |
| EI-025 | Insufficient / wait merchant language | Knowledge / Trust | LP-09,10,12 | Product UI / Trust | Workspace meta `NEEDS_MORE_EVIDENCE` | Production | E4 | 2026-07-29 | Low | CAP-12 | No | **Eligible** for principle |
| EI-026 | Empty Home before admission | Knowledge | LP-09 | Product UI | `prod_before_empty_*` | Prod | E4 | 2026-07 | Low | Optional | Honesty | Shows empty risk — not “intelligence” |
| EI-027 | CISYN shipping/pattern engines | Knowledge | LP-09 | Engineering / Ops | CISYN closure evidence | Prod closed | E2–E3 | Closed | Low | Merchant UI | Theme RV | Not alone |
| EI-028 | Traffic vs conversion landing theme | Knowledge | LP-09,10 | Knowledge | Language audit warns visit language | Partial | E2 | — | Low | — | **RV required** | **Not claimable** yet |
| EI-029 | Living Store historical continuity | Continuity | LP-11 | Reality Validation (lab) | `living_store_reality_v1/` | Lab/SRS | E3–E4 | Lab | Low | Optional illustrative | Disclosure | Conceptual/illustrative only |
| EI-030 | Store isolation tests | Trust | LP-12 | Trust / Engineering | `tests/test_recovery_isolation.py` | CI | E2 | Current | Low | N/A | Legal for absolutes | Bounded isolation only |
| EI-031 | Zid OAuth + snippet install | Integration | LP-13 | Integration | Zid docs + adapters | Ops-gated | E3 | Current | Low | Text/status UI | Revalidate | **Supported with disclosure** |
| EI-032 | Salla adapter scaffold | Integration | LP-13 | Integration | `integration_health_v1.py` | Scaffold | E1 | Current | Low | No | — | **Planned only** |
| EI-033 | Shopify adapter scaffold | Integration | LP-13 | Integration | same | Scaffold | E1 | Current | Low | No | — | **Planned only** |
| EI-034 | Platform logos | Marketing | LP-13 | Decorative / Legal | — | — | E0 | — | — | Rights | Legal | **Not claimable** |
| EI-035 | Beta/free landing language | Commercial | LP-15 | Commercial Path | Current landing beta note | Production | E4 | Current | Low | Align wording | Honesty | Keep bounded |
| EI-036 | 3D / decorative hero concepts | Design | Any | Decorative Support | — | — | E0 as proof | — | Low | Never as proof | — | **Never evidence** |

---

## Family rollup

| Family | Best inventory IDs | Max level | Landing publish |
|--------|-------------------|-----------|-----------------|
| EV-WIDGET | EI-007…011 | E3–E4 | Block until storefront capture |
| EV-WIDGET-PERF | EI-012…013 | E2 / E0 | **Not claimable** |
| EV-WA | EI-014…019 | E3–E4 | Bounded after capture + ops |
| EV-DASHBOARD | EI-020…023 | E5 packs | After fresh landing capture |
| EV-KNOWLEDGE | EI-024…028 | E5 ORV | Themes gated; principle OK |
| EV-DECISION | EI-021,025 | E5 | Bounded outcomes |
| EV-CONTINUITY | EI-029 | E3 | Conceptual / illustrative |
| EV-TRUST | EI-014,025,030 | E4 | Bounded; legal for absolutes |
| EV-INTEGRATIONS | EI-031…034 | E3/E1 | Text states; no logos |
| EV-CTA | EI-001…003,035 | E4/E0 | Signup/Login; no Demo |
| EV-LEGAL | EI-004…006 | E4/E0 | Contact only |
