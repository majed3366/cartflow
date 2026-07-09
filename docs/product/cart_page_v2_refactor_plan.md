# Cart Page V2 — Refactor Plan

**Date (UTC):** 2026-07-09  
**Status:** Implementation roadmap only — no code in this document  
**Blueprint:** [`cart_page_v2_blueprint.md`](cart_page_v2_blueprint.md)  
**Constitution:** [`cart_page_product_constitution.md`](cart_page_product_constitution.md)  
**Action rules:** [`cart_page_action_governance.md`](cart_page_action_governance.md)

---

## Roadmap principles

| Rule | Meaning |
|------|---------|
| Independently deployable | Each phase ships behind a flag or additive path; production stays usable if the phase is reverted |
| No workflow breakage | Archive, reopen, contact, VIP interrupt, completed history, and normal-carts polling keep working |
| No big-bang rewrite | Replace one attention band or decision surface at a time |
| Preserve operational truth | No changes to Lifecycle Truth classification, Purchase Truth, recovery scheduling, WhatsApp send, or Snapshot builder semantics |
| UI ≠ truth | Presentation and CTA governance may change; `customer_lifecycle_*`, archive DB rows, and snapshot/hot-slice truth stay authoritative |
| Snapshot-safe | Prefer additive payload fields + read-time presentation; do not require snapshot rebuild for rollback |
| LGE-compatible | Interactive expand/select changes stay presentation-only until Lifecycle Governance Engine owns them |

**Global feature flag (recommended):** `CARTFLOW_CARTS_V2_UI=0|1` (or equivalent). Default off until a phase is validated. Phases may also use narrower flags listed below.

**Hard non-goals for all phases:** Changing `classify_customer_lifecycle_state_v1`, recovery due-scanner, archive DB write semantics, snapshot change-gate rules, or merchant decision *truth* keys — only how they are shown and which CTA is primary.

---

## Phase 0 — Primary action projection (additive, no visible redesign)

| Field | Content |
|-------|---------|
| **Goal** | Attach a governed **primary_action** (and optional demoted secondary) to each normal-carts row from [`cart_page_action_governance.md`](cart_page_action_governance.md), without changing the Cart UI yet. Unlocks later phases. |
| **Files affected** | New small mapper module under `services/` (e.g. cart page action projection); attach hook near existing normal-carts enrichment (`main.py` / batch attach path); snapshot slim allowlist if the field must survive snapshot storage; unit tests only |
| **UI impact** | None (payload additive; UI ignores field until later phases) |
| **Risk level** | Low |
| **Regression risk** | Low — additive JSON only; snapshot size slight increase if slim-listed |
| **Validation checklist** | [ ] Every lifecycle/VIP/archive variant maps to exactly one primary from the allowed vocabulary [ ] Purchased → No action; archived → Reopen; automatic → Wait [ ] No change to archive/reopen API behavior [ ] Snapshot read still serves normal-carts [ ] Flag off: zero UI difference |
| **Rollback strategy** | Stop attaching the field; remove slim allowlist entry if needed; redeploy. No data migration. |

**Deploy note:** Ship first. Do not enable UI consumption yet.

**Status (2026-07-09):** Implemented — `services/cart_page_primary_action_v1.py`; field `cart_page_primary_action_v1` on rows; flag `CARTFLOW_CARTS_V2_PRIMARY_ACTION` (default `1`). Consumed by Phase 1 CTAs and Phase 2 Attention Verdict.

---

## Phase 1 — One-primary CTA enforcement (panel + completed)

| Field | Content |
|-------|---------|
| **Goal** | Enforce constitution §2/§4 on the **existing** case panel and completed/archive rows: one primary CTA; Archive/Reopen demoted so they never compete with Wait/Contact. |
| **Files affected** | `static/merchant_dashboard_lazy.js` (primary/secondary action HTML, archived compact panel, `cartRowTableDisplay`); possibly small CSS for demoted dismiss control; tests under `tests/test_carts_archive_reopen_regression_v1.py` / action governance tests |
| **UI impact** | Same layout; Contact or Wait narrative is sole primary; Archive moves to overflow/demoted control; Reopen remains sole primary on archived rows |
| **Risk level** | Medium |
| **Regression risk** | Medium — merchants who used Archive as a second visible button must still reach dismiss via demoted control; contact/reopen must not disappear |
| **Validation checklist** | [ ] Wait states: no Archive twin beside Wait [ ] Contact executable: one Contact CTA; Archive not co-primary [ ] Archived: Reopen only as primary [ ] Purchased: no Reopen [ ] Archive API + reopen API still succeed [ ] Poll/archive truth overlay still holds (`merchant_archive_truth_overlay`) [ ] Desktop + mobile panel |
| **Rollback strategy** | Feature flag off restores previous secondary button placement; no server rollback required if Phase 0 field unused by old UI |

**Depends on:** Phase 0 recommended (can hardcode mapping in JS temporarily — prefer Phase 0).

**Status (2026-07-09):** **Implemented + Production Verified** — UI consumes `cart_page_primary_action_v1` via `resolveCartPagePrimaryAction` in `static/merchant_dashboard_lazy.js`. Exactly one primary CTA (`data-cf-primary-action`); Archive demoted (`data-cf-lifecycle-secondary="archive"`, label «إغلاق الحالة»); Reopen primary on archived compact + completed table; archived visual wins over stale projection after optimistic archive. No lifecycle/archive API or truth changes. Commits: `4ba3700`, `2451a26`. Prod verify: `scripts/_cart_page_v2_phase1_prod_verify.py` → PASS (Wait primary, Archive secondary, Reopen primary, archive/reopen APIs, no console fatals).

---

## Phase 2 — Attention verdict band (replace hero / duplicate summaries)

| Field | Content |
|-------|---------|
| **Goal** | Introduce Blueprint **Section 1** (attention verdict) as the top product statement; hide or stop rendering decorative hero title/purpose and competing MPL/queue-sub triples when V2 flag is on. |
| **Files affected** | `templates/merchant_app.html` (host node for verdict); `static/merchant_dashboard_lazy.js` and/or small new presentation JS; optional read of store counts already on normal-carts; CSS for verdict band only |
| **UI impact** | Top of Carts shows one merchant-language verdict instead of «السلال» + purpose + multiple summaries |
| **Risk level** | Medium |
| **Regression risk** | Medium — merchants lose familiar hero chrome; empty/loading copy must remain honest |
| **Validation checklist** | [ ] Verdict answers Q1+Q4 only [ ] No second summary competing above the fold [ ] Loading/empty states still clear [ ] VIP interrupt (current banner) still visible above or with verdict [ ] Flag off: legacy hero/summaries restored |
| **Rollback strategy** | Flag off; leave host node empty/hidden |

**Does not change:** Filter logic, MI groups, panel, archive APIs.

**Status (2026-07-09):** **Implemented + Production Verified + Hotfixed** — `#ma-carts-attention-verdict-v1` after VIP alerts; counts from `cart_page_primary_action_v1` via `resolveCartPagePrimaryAction` (needs you = Contact + Follow up + Review; calm = Wait / empty). Hides `#ma-carts-hero`, `#ma-carts-queue-sub`, `#ma-carts-product-language-v1` when `CARTFLOW_CARTS_V2_UI` on (default `1`). Flag: `services/cart_page_v2_ui_flag_v1.py` → `data-carts-v2-ui` on `#page-carts`. Story cards, filters, counters, archive/reopen unchanged. Commit: `13ffe5c`. Prod verify: `scripts/_cart_page_v2_phase2_prod_verify.py` → PASS (verdict visible desktop+mobile, duplicates removed, filters/stories/archive/reopen OK, no console fatals).

**Deploy note:** Deploy polling hit unauthenticated `/dashboard` redirect, but static assets were live and manual production verification passed.

**Hotfix (2026-07-09):** MI pending no longer blanks the cart body under Attention Verdict — `renderMiCartsV1Pending(rows)` keeps a visible pending message in `#ma-carts-groups-v2`, passes real rows into the verdict when available, and does not hide `#ma-carts-queue-empty` from the verdict renderer. Commit: `00f54f5`. Prod verify: `scripts/_cart_page_v2_phase2_hotfix_prod_verify.py` → PASS.

**Hotfix (2026-07-09) — desktop layout:** **Desktop layout regression fixed + Production Verified.** After workspace expansion, PE v2 `grid-template-columns: 360px 1fr` left verdict + story cards in a narrow side column. Carts desktop override uses `minmax(480px, 1.2fr) minmax(360px, 0.8fr)` (`merchant_product_polish_v1.css` + `merchant_workspace_expansion_v1.css`); verdict/pending drop `max-width: 1080px` so they fill the queue column. Mobile single-column unchanged. CSS/layout only. Commit: `ef8adb7`. Prod verify: `scripts/_cart_page_v2_desktop_layout_prod_verify.py` → PASS (queue ~658px vs prior 360px track; verdict/stories/filters/archive/reopen OK; mobile no overflow).

**Hotfix (2026-07-09) — Attention Verdict freshness:** **Attention Verdict Freshness Consistency — Production Verified.** Cache/sessionStorage and thin/partial/unconfirmed-empty keep paths no longer present row-derived counts as final. Verdict shows calm «جارٍ تحديث الصورة...» (data-verdict-freshness=pending) until a successful live/snapshot apply; then recomputes final. Build bump ui-setup-v8e-verdict-freshness-v1. UI-only; no truth/API changes. Commit: b263924. Prod verify: scripts/_cart_page_v2_verdict_freshness_prod_verify.py → PASS (desktop+mobile converge automatic; pending visible; partial not stale-final; archive/reopen OK).

### Phase 2.6 — Rendering State Controller V1

| Field | Content |
|-------|---------|
| **Goal** | One merchant-visible rendering owner (`CartPageRenderingStateController`); Verdict / MI / Pending / Empty / Stories become paint-only |
| **Files affected** | `static/cart_page_rendering_state_controller_v1.js`, `static/merchant_dashboard_lazy.js`, `templates/merchant_app.html`, `services/merchant_setup_render_build.py` |
| **UI impact** | Same merchant outcomes; unified ownership of pending/final/cached/refreshing/failed |
| **Risk level** | Medium (architecture) |
| **Does not change** | Snapshot Truth, Lifecycle Truth, Primary Action Projection, Archive/Reopen, Recovery |
| **Out of scope** | Phase 3 automatic band |

**Status (2026-07-09):** **Implemented + Production Verified** — RSC owns composition via `CACHE_HYDRATED` / `FETCH_*` / `APPLY_*` / `ROWS_PATCHED`; last-good MI preserved on keep/cache; presenters paint from plan. Build `ui-setup-v8f-rsc-v1`. Commit: `bbf1163`. Tests: `tests/test_cart_page_rendering_state_controller_v1.py`. Design: `docs/architecture/rendering_state_controller_v1.md`. Prod verify: `scripts/_cart_page_v2_rsc_v1_prod_verify.py` → PASS (desktop+mobile converge `automatic`; one rendering state; no conflicting pending messages on refresh; last-good stories kept; cache→final; stories/filters OK; archive/reopen OK; build `ui-setup-v8f-rsc-v1`; no console fatals). Screenshots: `scripts/_cart_page_v2_rsc_v1_prod_verify_out/01_desktop_final.png`, `02_mobile_final.png`.

### Phase 2.6.1 — RSC V1.1 Merchant-visible Refresh Policy

| Field | Content |
|-------|---------|
| **Goal** | Separate internal operational fetches from merchant-visible Refreshing |
| **Rule** | Never `FINAL → REFRESHING` for token/pending/keep/background sync; only boot / explicit refresh / no trusted state / hard failure without last-good |
| **Files** | `static/cart_page_rendering_state_controller_v1.js`, `static/merchant_dashboard_lazy.js`, build bump |
| **Out of scope** | Phase 3 |

**Status (2026-07-09):** **Implemented + Production Verified** — `SOFT_REVALIDATE` + silent reason policy; build `ui-setup-v8g-rsc-v1_1`. Commit: `03a2546`. Investigation: `docs/product/rsc_stability_investigation_v1.md`. Prod verify: `scripts/_cart_page_v2_rsc_v1_1_prod_verify.py` → PASS (soft token/pending poll no pending flash; stories kept; no repeated refreshing over ~12s hold; desktop+mobile converge final; archive/reopen OK; no console fatals). Screenshots: `scripts/_cart_page_v2_rsc_v1_1_prod_verify_out/01_desktop_stable_final.png`, `02_mobile_stable_final.png`.

---

## Phase 3 — CartFlow automatic band| Field | Content |
|-------|---------|
| **Goal** | Add Blueprint **Section 2**: calm aggregate of Wait-primary carts (“CartFlow is following N carts”). Reduces urge to open every row. |
| **Files affected** | Presentation JS/CSS; counts derived from Phase 0 primary_action on existing rows (client-side OK); no truth service changes |
| **UI impact** | New calm band under verdict; does not remove story cards yet |
| **Risk level** | Low |
| **Regression risk** | Low — additive band; avoid implying Contact |
| **Validation checklist** | [ ] Band only counts Wait primaries [ ] No CTA that invents work [ ] Hidden when zero active carts [ ] Does not duplicate full cart list [ ] Flag off removes band |
| **Rollback strategy** | Flag off / stop rendering band |

---

## Phase 4 — Critical interrupt alignment (VIP)

| Field | Content |
|-------|---------|
| **Goal** | Align existing VIP alert with Blueprint **Section 0**: one sentence + one primary (**Follow up manually** / Contact), never Archive as interrupt CTA; omit section when empty. |
| **Files affected** | VIP banner render path in `merchant_dashboard_lazy.js` / template slot `#ma-cart-alerts-root`; CSS only as needed |
| **UI impact** | VIP banner copy/CTA clarity; remove decorative-only chrome if present |
| **Risk level** | Medium |
| **Regression risk** | Medium — VIP merchants must still reach manual contact; do not enable auto-WhatsApp against VIP policy |
| **Validation checklist** | [ ] Interrupt absent when no VIP must-act [ ] Single primary CTA matches governance [ ] Archive not on interrupt face [ ] Link/scroll to that cart in Section 4/list still works [ ] Flag off: previous VIP banner |
| **Rollback strategy** | Flag off |

**Constraint:** Do not change VIP lane recovery suppression logic — presentation/CTA only.

---

## Phase 5 — Carts-to-decide queue (split attention list)

| Field | Content |
|-------|---------|
| **Goal** | Blueprint **Section 4**: show action-needed carts (Contact / Follow up manually / Review) first; demote pure Wait carts out of the decision queue (they live in Section 2). Keep selection → panel wiring. |
| **Files affected** | `static/merchant_intelligence_carts_v1.js`, `static/merchant_dashboard_lazy.js` (workspace render/order/filter of rows fed to MI/stories); tests for consumption ordering |
| **UI impact** | Decision list shorter and prioritized; automatic carts no longer dominate the queue |
| **Risk level** | Medium–High |
| **Regression risk** | High if Wait carts become undiscoverable — must remain reachable via automatic band or explicit “show automatic” control |
| **Validation checklist** | [ ] Every Contact/Follow up/Review cart appears in decide list [ ] Wait-only carts not mixed as “needs you” [ ] Story/group copy cannot say Contact when members are Wait [ ] Selecting a cart still opens panel [ ] Archive/reopen still available per Phase 1 rules [ ] Snapshot poll does not reshuffle into contradiction [ ] Flag off: previous MI/story ordering |
| **Rollback strategy** | Flag off restores previous `renderMiCartsV1Workspace` / story ordering |

**Preserve:** MI/value-story *data* generation; only consumption/order/visibility changes.

---

## Phase 6 — Case decision surface (panel restructure)

| Field | Content |
|-------|---------|
| **Goal** | Blueprint **Section 5**: fixed order Happening → Why → CartFlow did → Your decision; timeline closed by default; one primary control (Phase 1 rules). |
| **Files affected** | `static/merchant_dashboard_lazy.js` (conversation/panel HTML); `static/merchant_pe_v2.css` (layout only); projection consumers of `cart_detail_projection_v1` / explanation fields (read-only) |
| **UI impact** | Panel content order and density; mobile panel parity |
| **Risk level** | Medium |
| **Regression risk** | Medium — merchants used to long open timelines; primary actions must remain obvious |
| **Validation checklist** | [ ] Q1–Q5 order on face [ ] Timeline collapsed by default [ ] Primary matches Phase 0 field [ ] Desktop + mobile parity [ ] No dual CTAs [ ] Flag off: previous panel HTML |
| **Rollback strategy** | Flag off |

**Forbidden in this phase:** Changing `cart_detail_projection_v1` truth inputs; explanation algorithm changes.

---

## Phase 7 — Recent change band

| Field | Content |
|-------|---------|
| **Goal** | Blueprint **Section 3**: 0–3 decision-relevant deltas; omit when empty. |
| **Files affected** | Presentation JS; prefer existing movement/visibility fields already on normal-carts (`customer_movement_*` or equivalent). **No new truth engine** in this phase. If inputs insufficient, ship “omit always” behind flag until data is adequate — do not invent events. |
| **UI impact** | Optional band between automatic and decide list |
| **Risk level** | Medium |
| **Regression risk** | Medium if noisy or wrong deltas create false urgency |
| **Validation checklist** | [ ] Section omitted when no deltas [ ] Max 3 lines [ ] No lifetime history dump [ ] Does not override Section 1 verdict [ ] Flag off removes band |
| **Rollback strategy** | Flag off |

**If blocked on data quality:** Skip deploy of UI; keep Phase 7 as no-op until movement signals are trustworthy — do not weaken Snapshot/Lifecycle to force it.

---

## Phase 8 — History doorway + demote recovered-from-attention

| Field | Content |
|-------|---------|
| **Goal** | Blueprint **Section 6**: single low-emphasis entry to completed/archive; remove or disable recovered filter chip from active attention path when V2 on; completed tab remains the history surface. |
| **Files affected** | `templates/merchant_app.html` / carts presentation (doorway link); `static/merchant_app.js` filter bar visibility; completed page unchanged functionally |
| **UI impact** | Less history noise on active Carts; clearer path to مكتملة |
| **Risk level** | Medium |
| **Regression risk** | Medium — merchants who used «تم الاسترداد» chip on Carts need the doorway/completed tab |
| **Validation checklist** | [ ] Completed/purchased still on completed tab [ ] Reopen still on archived [ ] Active decide list excludes pure history [ ] Flag off restores recovered chip if it was shown |
| **Rollback strategy** | Flag off |

---

## Phase 9 — Chrome removal & consistency lock

| Field | Content |
|-------|---------|
| **Goal** | Remove remaining unjustified chrome under V2 (confidence chips on card face, expand CTA that restates the same lines, non-working filter chips, duplicate evidence blocks). Lock story/row/panel/CTA consistency checks in tests. |
| **Files affected** | `static/merchant_intelligence_carts_v1.js`, filter init in `merchant_app.js` / lazy JS, CSS; contract tests |
| **UI impact** | Cleaner cards; fewer interactive no-ops |
| **Risk level** | Low–Medium |
| **Regression risk** | Low if Phase 5 already split queues; Medium if merchants relied on decorative cues |
| **Validation checklist** | [ ] No filter chip without real set change [ ] No confidence on card face [ ] Contradiction test: story primary == row primary == panel primary [ ] Constitution checklist pass on desktop + mobile [ ] Flag off restores prior chrome if needed |
| **Rollback strategy** | Flag off |

---

## Suggested ship order

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3
                ↓
            Phase 4 (VIP interrupt)
                ↓
            Phase 5 (decide queue)
                ↓
            Phase 6 (panel)
                ↓
            Phase 7 (recent change — defer if data weak)
                ↓
            Phase 8 (history doorway)
                ↓
            Phase 9 (chrome removal + locks)
```

Each arrow is a **separate deploy**. Do not combine High regression phases (5+6+8) in one release.

---

## Cross-phase validation (every deploy)

| Check | Required |
|-------|----------|
| Snapshot normal-carts still serves | Yes |
| Hot-slice + archive truth overlay still correct | Yes |
| `POST .../archive` and `.../reopen` succeed and persist across poll | Yes |
| Lifecycle labels/actions still from lifecycle authority (not reinvented in JS) | Yes |
| No recovery/scheduler/WhatsApp behavior change | Yes |
| Desktop + mobile smoke: open Carts, select cart, primary CTA works | Yes |
| Flag off restores prior Cart UX | Yes |

**Prod probe (after UI-affecting phases):** extend or reuse `scripts/_carts_archive_reopen_prod_truth_verify_v1.py` plus a short V2 attention/CTA checklist — not a substitute for Phase checklists.

---

## Explicitly out of this roadmap

| Out | Why |
|-----|-----|
| Rewriting MI / value-story generation services | Truth/composition ownership stays; V2 is consumption |
| Snapshot builder algorithm changes | Freshness/ownership unchanged |
| Lifecycle state machine changes | Action governance maps *from* lifecycle; does not redefine it |
| LGE full migration | May follow after V2 bands stabilize; not a Cart V2 blocker |
| Big-bang deletion of `merchant_dashboard_lazy.js` | Incremental replacement only |

---

## Definition of done (Cart Page V2)

V2 is done when, with the flag on:

1. Sections 0–6 match the blueprint attention order (3 omitted when empty).  
2. Every visible cart has one primary action; Archive/Reopen never compete.  
3. Story, row, and panel never contradict.  
4. Snapshot + lifecycle + archive operational truth unchanged.  
5. Flag off still restores pre-V2 Cart UX until sunset.

Sunset of the legacy Cart presentation is a **separate** decision after V2 has been default-on in production without rollback.
