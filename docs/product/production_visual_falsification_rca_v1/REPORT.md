# Production Visual Falsification RCA V1 — Report

## Mission

Explain why **REAL-DEVICE REVIEW = PASS** (FRC-01…08 + controlled fix review) while founder-visible production evidence on live SHA `c20627167c759145b65b591bc4df75a8dd6262a3` shows material visual failures.

**Forbidden in this pack:** CSS patch, icon moves, redesign, deploy, production mutation.

---

## Capture conditions

| Item | Value |
|------|-------|
| CURRENT SHA | `c20627167c759145b65b591bc4df75a8dd6262a3` (meta + live probe) |
| Surface | Production Living Store `/dashboard` |
| Viewport | Mobile Emulation **390×844**, `deviceScaleFactor=2` |
| Direction | **RTL** (`dir=rtl`) |
| Method | CDP `Runtime.evaluate` bounding boxes (not screenshot impression alone) |

---

## Core answer (why PASS vs founder FAIL)

The real-device gate (`tests/test_real_device_visual_composition_fix_v1.py` FRC-01…08) asserts **static CSS/string thresholds** (joint width ≥16px mobile, void height, tick size, organism markers, “no white detail card” on Carts detail). It does **not** assert:

- runtime collision / reserved-width cascade integrity
- merchant-legible meaning of geometry without explanation
- withheld-queue vs skeleton ambiguity
- empty-state page identity vs generic surface card
- relative visual weight / relational orbit on live layout
- production screenshot evidence

Amplifying marker size without reserved space made Settings **worse** (larger joint into unpadded text). Geometry that meets min-height can still read as decoration or skeleton.

---

## SETTINGS — mandatory measurement (PROVEN)

### Live numbers (row 0, vw=390, RTL)

| Box | left | right | top | bottom | w×h |
|-----|------|-------|-----|--------|-----|
| **Joint** `.cf2-settings__joint` | 343 | 359 | 262.52 | 278.52 | **16×16** |
| **Line** `.cf2-settings__row-line` (element) | 28 | 355 | 261.72 | 278.52 | 327×16.8 |
| **Text ink** (Range on line) | 305.25 | **355** | 260.72 | 277.72 | 49.75×~17 |
| **Chip0** «يحتاج ضبط» | 285.86 | **355** | 284.52 | 305.33 | 69.14×20.8 |
| **Row** | 16 | 370 | — | — | 354 wide |

| Metric | Value |
|--------|-------|
| Viewport width | **390** |
| `padding-inline-start` (computed) | **12px** (intended mobile reserve **30px**) |
| Joint `position` | **absolute** |
| Joint `inset-inline-start` | **8px** |
| Gap joint → text ink (RTL: `joint.left − text.right`) | **−12px** |
| Overlap joint ∩ text ink | **12×15.2 px — collides: true** |
| Gap joint → chip0 | **−12px** (horizontal; chip below joint on Y) |
| Colliding rows in first 5 | **5 / 5** |

### RTL attachment

Joint is attached to **inline-start** (physical **right** in RTL). Text and chips extend to `right=355`, into the joint’s `[343,359]` band. Attachment side is correct; **reserved start padding is not**.

### Root cause (proven mechanism)

1. `.cf2-settings__ledger-row` sets `padding-inline-start: 30px` (mobile) / `34px` (desktop) to reserve joint space.
2. Same element also has class `.cf2-settings__row`, whose rule **after** the ledger rule sets shorthand `padding: 11px 12px`.
3. Equal specificity → **source order wins** → reserved start padding collapses to **12px**.
4. Absolute joint at `inset-inline-start: 8px` + width **16px** occupies ~8–24px from start; content starts at 12px padding → **overlap**.

**Failure class:** `GEOMETRY_COLLISION` + `MOBILE_SPACING_FAILURE` + `CONTRACT_THRESHOLD_TOO_WEAK`  
**Cause type:** **cascade / insufficient reserved width** (absolute positioning + later padding shorthand override) — not transform/offset.

| Field | Finding |
|-------|---------|
| SURFACE | Settings `#settings` |
| VISIBLE FAILURE | Joint/marker overlaps row line text; geometry too close to chips |
| ROOT CAUSE | Absolute joint + `padding` shorthand defeats ledger `padding-inline-start` |
| WHY CONTRACT PASSED | FRC-07 only checks joint **width** ≥16px in CSS text |
| WHY REAL-DEVICE REVIEW MISSED | Size threshold treated as “visible”; no bbox collision probe |
| REGRESSION SIGNAL | Runtime joint∩text gap ≥ N px; assert computed `padding-inline-start` ≥ joint end + gap |

**SETTINGS ROOT FAILURE: PROVEN**

---

## WORKSPACE — oval meaning (PROVEN)

### What the large oval is

| Layer | Value on live probe |
|-------|---------------------|
| TRUTH DRIVER | `decision_readiness=NEEDS_MORE_EVIDENCE` + uncertainty/sufficiency path that paints void |
| SEMANTIC VARIABLE | Uncertainty / insufficiency **gap between evidence and decision mass** (`merchant_ui_v2_workspace.js`: “Uncertainty / insufficiency void”) |
| GEOMETRY VARIABLE | `.cf2-ws__void` with `data-cf2-void` sized from uncertainty (`large` / `standard` / …); live: **standard**, **288.9×44**, `border-radius: 50% / 42%`, radial wash, inset ring |
| VISIBLE MEANING | Intended: relational void in formation chain evidence → void → mass |

Live attrs: `data-cf2-organism=formation`, `data-cf2-readiness=NEEDS_MORE_EVIDENCE`, `data-cf2-mass=open`, void `aria-hidden="true"` (no merchant label).

### Legibility

Merchant-visible meaning of the oval **depends on knowing** the uncertainty→void mapping. Without explanation it reads as a **decorative capsule / void shape**.

**SEMANTIC_GEOMETRY_NOT_LEGIBLE = YES**

| Field | Finding |
|-------|---------|
| SURFACE | Workspace `#workspace` |
| VISIBLE FAILURE | Large oval reads decorative, not semantic formation gap |
| ROOT CAUSE | Geometry amplified (FRC-03 height/opacity) without merchant-legible coupling; `aria-hidden` |
| WHY CONTRACT PASSED | FRC-03 asserts void **min height** in CSS (≥44px mobile) |
| WHY REVIEW MISSED | “Void present and tall enough” ≠ “void meaning readable” |
| REGRESSION SIGNAL | Semantic-legibility review; optional min contrast/label rule for void role |

**WORKSPACE ROOT FAILURE: PROVEN**

---

## CARTS — incomplete / withheld (PROVEN)

Live: `data-carts-truth=incomplete`, class `cf2-carts is-incomplete`, **2×** `.cf2-carts__object.is-withheld`.

Structure from painter:

```html
<div class="cf2-carts__object is-withheld" aria-hidden="true"></div>
```

- **Empty** children, **no** text in the mass boxes  
- CSS: `min-height: 52px`, dashed start border, `background: rgba(8,32,72,0.02)`, `animation: none`  
- Note below (Arabic): truth incomplete — copy is honest; **geometry is not**

| Ambiguity | Why |
|-----------|-----|
| Loading skeleton | Hollow bars, dashed edge, near-transparent fill, repeated placeholders |
| Broken empty component | Zero content inside “objects”; looks unfinished UI chrome |

Intended meaning (“truth not yet confirmed / withhold queue mass”) is **only** in the note + `data-carts-truth`, not in the shape vocabulary.

| Field | Finding |
|-------|---------|
| SURFACE | Carts `#carts` |
| VISIBLE FAILURE | Withheld queue reads as skeleton / broken empty |
| ROOT CAUSE | `AMBIGUOUS_STATE_EXPRESSION` — empty `aria-hidden` shells reuse object chrome without withheld-state glyph grammar |
| WHY CONTRACT PASSED | Incomplete path exists; FRC-06 targets **detail** white card, not withheld mass legibility |
| WHY REVIEW MISSED | Presence of withheld queue + note counted as pass |
| REGRESSION SIGNAL | Incomplete state must fail if geometry matches loading/skeleton heuristics without distinct withheld grammar |

**CARTS ROOT FAILURE: PROVEN**

---

## COMMUNICATION — empty vs non-empty (PROVEN)

### Non-empty (live)

- Organism `lifecycle-continuum` present  
- Many `.cf2-comms__tick` (live count **80**)  
- List unboxed (`background` transparent, radius 0) — page identity **strong**

### Empty (forced probe of `.cf2-comms__empty` under organism)

From CSS + computed style:

| Property | Computed |
|----------|----------|
| `background` | `rgb(255,255,255)` / `--cf2-surface` |
| `border-radius` | **12px** (`--cf2-r-md`) |
| `border` | 1px surface border + start edge |
| Scaffold | Still painted (`continuumScaffoldHtml`) — organism remnant survives |

Painter empty path: scaffold + `.cf2-comms__empty` title/body (`merchant_ui_v2_comms.js`).

**EMPTY_STATE_GENERIC_COLLAPSE = YES** for the empty copy block (generic white rounded surface card), while dormant ticks partially preserve continuum identity.

| Field | Finding |
|-------|---------|
| SURFACE | Communication `#communication` |
| VISIBLE FAILURE | Empty state collapses copy into generic card; continuum weak vs row state |
| ROOT CAUSE | `.cf2-comms__empty` uses surface + radius card grammar |
| WHY CONTRACT PASSED | FRC-05 asserts scaffold **string** exists; FRC-06 is Carts-only |
| WHY REVIEW MISSED | Non-empty continuum reviewed; empty card not identity-gated |
| REGRESSION SIGNAL | Empty-state page-identity check (no generic surface card; scaffold must dominate) |

**COMMUNICATION ROOT FAILURE: PROVEN**

---

## HOME — rail / satellites (PROVEN)

Live mobile (390):

| Element | Measure |
|---------|---------|
| Primary board | 330×**611.4**, `border-inline-start: **8px** solid navy` |
| Rail stroke area | 8 × 611.4 ≈ **4891 px²** continuous vertical spine |
| Orbit-axis | **14×238** horizontal connector (not the dominant rail) |
| Satellites | **2**, `position: static`, `transform: none`, **width 100%**, mobile CSS `max-width: none` |

Mobile CSS forces all satellite distances to full width — **kills asymmetric orbit**. Satellites read as **stacked text/monitor blocks**, not relational orbit.

| Field | Finding |
|-------|---------|
| SURFACE | Home `#home` |
| VISIBLE FAILURE | Long navy start-edge dominates tall board; satellites lack orbital relationship |
| ROOT CAUSE | `HIERARCHY_TOO_STRONG` (full-height 8px spine) + `RELATIONSHIP_NOT_VISIBLE` (mobile full-width stack) |
| WHY CONTRACT PASSED | FRC-01/02 assert primary edge **wider than** satellite edge + no 2-col grid in CSS — not live weight or orbit geometry |
| WHY REVIEW MISSED | Edge width threshold + axis presence ≠ relational readability |
| REGRESSION SIGNAL | Relative visual-weight threshold; mobile orbit relationship (non-equal widths / offset) |

**HOME ROOT FAILURE: PROVEN**

---

## SIDEBAR — mobile contextual pattern

### Approved pattern (documented — no implementation)

**MOBILE CONTEXTUAL SIDEBAR (`.cf2-ctx`)**

| Property | Proven |
|----------|--------|
| Overlay | `.cf2-ctx-backdrop.is-open` + `body.is-ctx-open` |
| Panel geometry | `position: fixed`, width **280px** (`min(280px, 82vw)`), inset-inline-start 0, bg `#f7f9fc` |
| Selected-state grammar | `.is-active` / page items in panel |
| Contextual contents | Per page (Home: نظرة عامة/الملخص; Workspace: ما يحتاج قرارك; …) |

Live audit:

| Page | `data-cf2-ctx` | Handle | Open behavior |
|------|----------------|--------|---------------|
| home | on | visible | backdrop + 280px panel |
| workspace | on | visible | same shell geometry |
| carts | off | hidden | page owns filters/list context in-stage |
| communication | off | hidden | same |
| settings | off | hidden | same |

Shell behavior when ctx is **on** is identical. Ctx **off** on carts/comms/settings is intentional (no secondary context drawer), not a broken overlay.

**SIDEBAR PATTERN: APPROVED**  
(Products ownership out of scope.)

---

## Per-surface falsification table

| SURFACE | VISIBLE FAILURE | ROOT CAUSE | WHY CONTRACT PASSED | WHY REVIEW MISSED | REGRESSION SIGNAL | CLASS |
|---------|-----------------|------------|---------------------|-------------------|-------------------|-------|
| Settings | Joint overlaps text | Absolute + padding cascade | FRC-07 width only | No bbox gap | Collision + reserved pad | `GEOMETRY_COLLISION`, `MOBILE_SPACING_FAILURE`, `CONTRACT_THRESHOLD_TOO_WEAK` |
| Workspace | Oval decorative | Void size ≠ meaning | FRC-03 height | No legibility | Semantic-legibility | `SEMANTIC_GEOMETRY_NOT_LEGIBLE`, `CONTRACT_THRESHOLD_TOO_WEAK` |
| Carts | Skeleton / broken | Empty withheld shells | Incomplete path / FRC-06 detail | Note ≠ geometry | Withheld≠skeleton | `AMBIGUOUS_STATE_EXPRESSION`, `REVIEW_EVIDENCE_INSUFFICIENT` |
| Comms | Empty → white card | `.cf2-comms__empty` card CSS | Scaffold string | Non-empty bias | Empty identity | `EMPTY_STATE_GENERIC_COLLAPSE` |
| Home | Rail + stacked sats | 8px spine; mobile 100% width | Edge ratio in CSS | No live weight/orbit | Weight + orbit | `HIERARCHY_TOO_STRONG`, `RELATIONSHIP_NOT_VISIBLE` |

---

## Gate falsification

### Existing gates that failed to detect

| Gate | Blind spot |
|------|------------|
| FRC-01/02 Home | CSS edge width / no 2-col grid — no live mass ratio, no orbit offset |
| FRC-03 Workspace void | Min height only — no meaning/legibility |
| FRC-05 Comms | Scaffold presence in JS — no empty card ban |
| FRC-06 Carts | Detail transparent — withheld mass unchecked |
| FRC-07 Settings | Joint px size — **no collision**, no computed pad reserve |
| FRC-08 mobile hooks | Organism survival strings — not composition safety |
| Real-device review PASS | Local size probes + screenshots without production collision/legibility checklist |
| Config parity / deploy gates | Correct for flags — orthogonal to visual composition |

### Future gate needs (do not implement yet)

1. **Collision detection** (joint/marker vs text/chip bbox)  
2. **Minimum semantic geometry size** (already partial — keep)  
3. **Minimum text/geometry separation**  
4. **Semantic-legibility review** (merchant meaning without explanation)  
5. **Empty-state page-identity check**  
6. **Relative visual-weight threshold** (live)  
7. **Production screenshot evidence requirement**  

**CONTRACT BLIND SPOTS: 7** (FRC-01…08 classes above that miss composition safety; counted as the seven future-need items / major miss classes)  
**REAL-DEVICE GATE BLIND SPOTS: 5** (no collision, no legibility, no empty-identity, no live weight, no prod screenshot mandate)

---

## FINAL REPORT

```
CURRENT SHA: c20627167c759145b65b591bc4df75a8dd6262a3

SURFACES FALSIFIED: 5

SETTINGS ROOT FAILURE: PROVEN
WORKSPACE ROOT FAILURE: PROVEN
CARTS ROOT FAILURE: PROVEN
COMMUNICATION ROOT FAILURE: PROVEN
HOME ROOT FAILURE: PROVEN

SIDEBAR PATTERN: APPROVED

CONTRACT BLIND SPOTS: 7
REAL-DEVICE GATE BLIND SPOTS: 5

ROOT FAILURE CLASSES:
- GEOMETRY_COLLISION
- MOBILE_SPACING_FAILURE
- SEMANTIC_GEOMETRY_NOT_LEGIBLE
- AMBIGUOUS_STATE_EXPRESSION
- EMPTY_STATE_GENERIC_COLLAPSE
- HIERARCHY_TOO_STRONG
- RELATIONSHIP_NOT_VISIBLE
- CONTRACT_THRESHOLD_TOO_WEAK
- REVIEW_EVIDENCE_INSUFFICIENT

SAFE TO DESIGN CONTROLLED PRODUCTION VISUAL FIX: YES

IMPLEMENTATION PERFORMED: NO
PRODUCTION CHANGED: NO

STOP.
```
