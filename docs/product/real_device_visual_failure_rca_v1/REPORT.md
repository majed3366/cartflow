# Real-Device Visual Failure RCA V1 — Report

## Mission

Explain why candidate `67ed1432` passes structural/semantic contracts but fails founder-visible real-device review.

No painter/CSS/HTML/semantic-model/contract edits in this pack.

## Capture conditions

| Item | Value |
|------|-------|
| SHA | `67ed1432` proven on `/dashboard` |
| Server | `127.0.0.1:8777` |
| Auth | development dashboard bypass |
| Surfaces | Home · Workspace · Carts · Communication · Settings |
| Viewports | desktop + mobile metrics (390×844) |

---

## Failure inventory

### 1) HOME — gravity well + satellites

| Field | Finding |
|-------|---------|
| SURFACE | Home (`#home`) |
| VIEWPORT | Desktop + mobile |
| EXPECTED ORGANISM | Gravity well + satellites |
| ACTUAL RENDERED RESULT | Vertical executive card/list. Label «مركز الجاذبية» is copy. Primary board is a white narrative block; monitors remain equal grid/stack items with 2px teal start-edge. Evidence bars are the loudest non-text glyph. |
| VISIBLE GAP | No spatial well. No orbiting smaller satellites. Hierarchy reads as SaaS section + equal cards/list. |
| CONTRACT THAT PASSED | `data-cf2-organism=gravity-well`, 0× `cf2-co--attention`, satellite attrs, PSG marker tests |
| WHY CONTRACT MISSED | Asserted DOM markers / glyph absence — not spatial mass contrast or orbital layout readability |
| CLASSIFICATION | `COMPOSITION_NOT_VISIBLE`, `GEOMETRY_TOO_WEAK`, `HIERARCHY_WRONG`, `PAGE_SPECIFICITY_TOO_WEAK`, `GENERIC_SAAS_FEEL_REMAINS`, `CONTRACT_TOO_WEAK` |
| MERCHANT-VISIBLE WITHOUT EXPLANATION? | **NO → FAIL** |

Evidence: `evidence/home_desktop.png`, `evidence/home_mobile.png`

Live DOM probe: organism=`gravity-well`; primary board border 6px + radial wash; satellites `near/near/far` with 2px edges inside `.cf2-home__monitor-row` (`grid-template-columns: repeat(2, 1fr)` desktop) — equal column grammar, not satellite mass.

---

### 2) WORKSPACE — formation body

| Field | Finding |
|-------|---------|
| SURFACE | Workspace (`#workspace`) |
| VIEWPORT | Desktop (live); fixture paint for geometry |
| EXPECTED ORGANISM | One formation body (evidence → void → mass → terminus) |
| ACTUAL RENDERED RESULT | Live: error banner only — projection `404` `{error: feature_flag_off, flag: CARTFLOW_CART_WORKSPACE_V1}`. No formation painted. Fixture paint (when forced): void = **22px** @ opacity **0.72**, 4px offset — relationship exists as a faint gap, not a readable void/tension body. |
| VISIBLE GAP | Live: organism absent. Forced: void/offset too weak to read as conflict/formation without knowing the contract. |
| CONTRACT THAT PASSED | READY zero icons; conflict void/tension attrs in compositor tests |
| WHY CONTRACT MISSED | Compositor HTML string checks ≠ live merchant path; void size/opacity never gated as visible geometry |
| CLASSIFICATION | `COMPOSITION_NOT_VISIBLE` (live), `STATE_RENDERING_MISMATCH` (flag/404), `GEOMETRY_TOO_WEAK` (forced paint), `CONTRACT_TOO_WEAK` |
| MERCHANT-VISIBLE WITHOUT EXPLANATION? | **NO → FAIL** |

Evidence: `evidence/workspace_desktop_error.png`, `evidence/workspace_*_fixture.html`, capture_notes (void 22px)

---

### 3) CARTS — weighted operational queue

| Field | Finding |
|-------|---------|
| SURFACE | Carts (`#carts`) |
| VIEWPORT | Desktop + mobile |
| EXPECTED ORGANISM | Weighted queue of cart-objects |
| ACTUAL RENDERED RESULT | Filter pill strip + master/detail. Detail remains white card (`background #fff`, `border-radius: 12px`). Queue row carries dashed interrupted start-edge (wait) — readable only as a thin edge, not queue mass ranking. Single/low-count carts read as sparse cards in whitespace. |
| VISIBLE GAP | Not a weighted operational queue at glance; still ops list + white detail pane. |
| CONTRACT THAT PASSED | `weighted-queue` marker; incomplete withheld path; dashed wait continuity present in CSS/DOM |
| WHY CONTRACT MISSED | Marker + “not empty card on incomplete” — did not fail remaining white detail card / filter-first identity / weak mass ranking |
| CLASSIFICATION | `GENERIC_SAAS_FEEL_REMAINS`, `MASS_TOO_WEAK`, `PAGE_SPECIFICITY_TOO_WEAK`, `GEOMETRY_TOO_WEAK`, `CONTRACT_TOO_WEAK` |
| MERCHANT-VISIBLE WITHOUT EXPLANATION? | **NO → FAIL** |

Evidence: `evidence/carts_desktop.png`, `evidence/carts_mobile.png`

---

### 4) COMMUNICATION — lifecycle continuum

| Field | Finding |
|-------|---------|
| SURFACE | Communication (`#communication`) |
| VIEWPORT | Desktop |
| EXPECTED ORGANISM | Lifecycle continuum (send → delivery → response → wait → follow-up) |
| ACTUAL RENDERED RESULT | Organism attr `lifecycle-continuum` present. Live demo: **0 rows, 0 ticks**. Empty master-detail / “اختر حدث تواصل من السجل”. Continuum chrome never appears. |
| VISIBLE GAP | Continuum not visible; page reads as empty inbox/list shell. |
| CONTRACT THAT PASSED | Distinct class tokens vs Carts (`cf2-comms__tick` vs `cf2-carts__object`) |
| WHY CONTRACT MISSED | Source/token presence ≠ painted lifecycle under real store truth; empty continuum not required to still read as continuum scaffolding |
| CLASSIFICATION | `COMPOSITION_NOT_VISIBLE`, `STATE_RENDERING_MISMATCH`, `GENERIC_SAAS_FEEL_REMAINS`, `PAGE_SPECIFICITY_TOO_WEAK`, `CONTRACT_TOO_WEAK` |
| MERCHANT-VISIBLE WITHOUT EXPLANATION? | **NO → FAIL** |

Evidence: `evidence/comms_desktop.png`

---

### 5) SETTINGS — quiet configuration ledger

| Field | Finding |
|-------|---------|
| SURFACE | Settings (`#settings`) |
| VIEWPORT | Desktop (list often clipped / low salience in viewport captures) |
| EXPECTED ORGANISM | Quiet configuration ledger with joint states |
| ACTUAL RENDERED RESULT | `config-ledger` + joints exist (`open`/`half`/`closed`) but joint geometry is **10×10px** markers. List reads as ordinary settings rows; ledger metaphor not glance-readable. |
| VISIBLE GAP | Joints too small/quiet to define page organism; still generic settings list. |
| CONTRACT THAT PASSED | `data-cf2-joint` markers + CSS selectors present |
| WHY CONTRACT MISSED | Attribute/selector presence; no minimum visible joint mass / ledger rhythm gate |
| CLASSIFICATION | `GEOMETRY_TOO_WEAK`, `COMPOSITION_NOT_VISIBLE`, `PAGE_SPECIFICITY_TOO_WEAK`, `GENERIC_SAAS_FEEL_REMAINS`, `CONTRACT_TOO_WEAK` |
| MERCHANT-VISIBLE WITHOUT EXPLANATION? | **NO → FAIL** |

Evidence: `evidence/settings_desktop.png`, live joint probe (10×10px)

---

### Mobile

| Field | Finding |
|-------|---------|
| VIEWPORT | 390×844 device metrics |
| ACTUAL | Organisms remain marker-thin; Home becomes linear list; Carts becomes filter strip + flat rows; shell/stage framing can leave large unused canvas. Same organism-invisibility failures persist. |
| CLASSIFICATION | `MOBILE_TRANSFORMS_FAILURE`, `COMPOSITION_NOT_VISIBLE`, `PAGE_SPECIFICITY_TOO_WEAK` |
| RESULT | **FAIL** |

---

## Critical question answers

| Surface | Exists only in DOM/contracts? | Visible without explanation? |
|---------|--------------------------------|------------------------------|
| Home | Mostly yes (attrs + weak edge/wash) | **NO** |
| Workspace | Live: not painted; forced: attrs + 22px void | **NO** |
| Carts | Attr + dashed edge; detail still white card | **NO** |
| Communication | Attr only on empty shell | **NO** |
| Settings | Attr + 10px joints | **NO** |

---

## Why PAGE-NAME-HIDDEN PASS and REAL-DEVICE FAIL can both be true

PAGE-NAME-HIDDEN tests in `test_page_specific_semantic_composition_v1.py` prove:

1. Five **different organism string tokens** exist in JS/CSS sources.
2. Some structural CSS class names diverge (e.g. carts object vs comms ticks).
3. Shared start-edge family tokens remain.

They do **not** prove:

1. A merchant can name the organism from a screenshot with title/nav/logo hidden.
2. Geometry mass/void/joint size crosses a human visibility threshold.
3. Live truth states (flag-on Workspace, non-empty Comms continuum, actionable Carts mass) paint the intended body.
4. Residual generic white-card detail panes are gone.

**Blind spot type:** `CONTRACT_TOO_WEAK` — structural distinction ≠ perceptual organism identity.

---

## Future regression check categories (do not implement yet)

| ID | Category | Would catch |
|----|----------|-------------|
| FRC-01 | Screenshot organism ID (title/nav/logo masked) | Merchant-visible organism naming |
| FRC-02 | Primary/secondary mass ratio (px² + edge width) | Home well vs satellites |
| FRC-03 | Void/gap minimum geometry (height×opacity×offset) | Workspace conflict void |
| FRC-04 | Live surface paint gate (HTTP≠404 / flag-on path) | Workspace feature_flag_off |
| FRC-05 | Continuum tick visibility when rows>0 + empty-scaffold continuum | Comms continuum absence |
| FRC-06 | Forbidden residual white-card detail pane on Carts | Generic SaaS detail |
| FRC-07 | Joint minimum size / ledger rhythm contrast | Settings joints too weak |
| FRC-08 | Mobile stage occupancy / unused canvas ratio | Mobile transform failures |

---

## Root failure types (proven)

1. `CONTRACT_TOO_WEAK`
2. `COMPOSITION_NOT_VISIBLE`
3. `GEOMETRY_TOO_WEAK`
4. `PAGE_SPECIFICITY_TOO_WEAK`
5. `GENERIC_SAAS_FEEL_REMAINS`
6. `HIERARCHY_WRONG` (Home monitor grid)
7. `MASS_TOO_WEAK` (Carts)
8. `STATE_RENDERING_MISMATCH` (Workspace flag / Comms empty continuum)
9. `MOBILE_TRANSFORMS_FAILURE`

---

## Salvage assessment

| Question | Answer |
|----------|--------|
| CURRENT CANDIDATE SALVAGEABLE | **YES** — DOM organism hooks + shared grammar remain; failure is visibility/geometry amplitude, not wrong product truth |
| SAFE TO DESIGN CONTROLLED FIX | **YES** — amplify page-owned geometry without inventing truth or changing `semantic-visual-model-v1` |
| Redesign from scratch needed | **NO** |

---

## Final scoreboard

FAILED SHA: `67ed1432fb9e7cb9cd7366b2f9f08ab79d4dd7ee`

REAL-DEVICE FAILURE SURFACES: **5**

HOME: **FAIL**  
WORKSPACE: **FAIL**  
CARTS: **FAIL**  
COMMUNICATION: **FAIL**  
SETTINGS: **FAIL**  
MOBILE: **FAIL**

ROOT VISUAL FAILURE: **PROVEN**

ROOT FAILURE TYPES:  
`CONTRACT_TOO_WEAK`, `COMPOSITION_NOT_VISIBLE`, `GEOMETRY_TOO_WEAK`, `PAGE_SPECIFICITY_TOO_WEAK`, `GENERIC_SAAS_FEEL_REMAINS`, `HIERARCHY_WRONG`, `MASS_TOO_WEAK`, `STATE_RENDERING_MISMATCH`, `MOBILE_TRANSFORMS_FAILURE`

CONTRACT BLIND SPOTS: **8** (FRC-01…08)

CURRENT CANDIDATE SALVAGEABLE: **YES**

SAFE TO DESIGN CONTROLLED FIX: **YES**

IMPLEMENTATION PERFORMED: **NO**

PRODUCTION CHANGED: **NO**

STOP.
