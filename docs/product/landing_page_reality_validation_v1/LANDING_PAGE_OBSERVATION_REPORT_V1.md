# Landing Page Observation Report V1

**Status:** Living report — refresh after telemetry deploy + as merchant sessions accumulate  
**Date opened (UTC):** 2026-07-29  
**Production URL:** https://smartreplyai.net/  
**Telemetry:** `POST /api/landing/event` · summary `GET /api/landing/summary`

---

## 0. Sample provenance

| Class | Included in merchant conclusions? | Notes |
|-------|-----------------------------------|-------|
| Merchant anonymous sessions | **Yes** | Opaque `session_key` |
| Agent / lab probes | **No** | Labeled below |
| Bot / crawler (if identifiable later) | **No** | Exclude when detected |

### Lab / technical probe log

| When (UTC) | Actor | Result |
|------------|-------|--------|
| 2026-07-29 | Agent probe | `GET https://smartreplyai.net/` → **HTTP 200**, HTML ~22KB, title/hero/sections present |
| 2026-07-29 | Agent probe | `HEAD /` → **405** (method not allowed; GET is the contract — not a merchant defect) |
| 2026-07-29 | Deploy | Branch `feat/landing-page-reality-validation-v1` @ `7918de1` pushed to origin — **merge to `main` required** for Railway to serve telemetry JS + `/api/landing/event` |

---

## 1. Technical observations (complete)

| Check | Result | Evidence |
|-------|--------|----------|
| Public deploy | **Pass** | Host responds 200 on `GET /` |
| Routing `/` | **Pass** | Serves marketing HTML |
| CTAs `/signup` `/login` | **Pass** | Present in HTML; routes exist outside landing |
| Critical layout break | **None observed** in lab GET | Visual polish out of scope |
| Mobile viewport meta | **Present** | `width=device-width, initial-scale=1.0` |
| Landing JS load (pre-RV) | N/A historically | Telemetry script added in RV deploy |
| Knowledge section on live | **Absent** | No `#knowledge` / LP-09 node |
| Evidence assets on live | Settings crops still in `#components` | Conflicts Evidence Production rejection list (structural) |

### Performance / rendering (lab)

No production performance regression tooling run in this pack. No merchant-reported loading failure at open. Revisit if `page_exit` clusters near `landing_opened` with zero scroll.

---

## 2. Behavioural aggregates

> Refresh with:
>
> ```bash
> curl -sH "X-CartFlow-Admin: $CARTFLOW_ADMIN_PASSWORD" \
>   "https://smartreplyai.net/api/landing/summary?hours=168"
> ```

### Window snapshot

| Metric | Value | As-of (UTC) |
|--------|------:|-------------|
| Window hours | 168 | — |
| Distinct sessions (`session_key`) | _pending post-deploy_ | — |
| `landing_opened` | _pending_ | — |
| `hero_visible` | _pending_ | — |
| `hero_cta_clicked` | _pending_ | — |
| `signup_clicked` | _pending_ | — |
| `login_clicked` | _pending_ | — |
| `problem_section_viewed` | _pending_ | — |
| `widget_section_viewed` | _pending_ | — |
| `whatsapp_section_viewed` | _pending_ | — |
| `dashboard_section_viewed` | _pending_ | — |
| `knowledge_section_viewed` | **0 expected** while LP-09 absent | structural |
| `faq_section_viewed` | _pending_ | — |
| `footer_reached` | _pending_ | — |
| `scroll_25` / `50` / `75` / `100` | _pending_ | — |
| Device mix (opens) | _pending_ | — |

### Derived (fill when counts > 0)

| Derived | Formula | Value |
|---------|---------|------:|
| Hero CTA rate | hero_cta / landing_opened | — |
| Signup rate | signup_clicked / landing_opened | — |
| Login rate | login_clicked / landing_opened | — |
| Reach Widget | widget_section_viewed / landing_opened | — |
| Reach Dashboard | dashboard_section_viewed / landing_opened | — |
| Reach Knowledge | knowledge / opened | **0** (section missing) |
| Deep scroll (75%+) | scroll_75 / opened | — |
| Full scroll | scroll_100 / opened | — |
| Bounce proxy | opened with no scroll_25 and quick page_exit | — |

---

## 3. Answers to observation questions

| Question | Current answer | Evidence class |
|----------|----------------|----------------|
| Hero — value in first seconds? | **Insufficient merchant sample** | Need `hero_visible` + CTA / early exit pattern |
| Story — where stop? | **Pending** scroll ladder | scroll_* + last section_viewed |
| Widget — continue after? | **Pending**; live Widget is inside `#components` (settings shot) | widget → whatsapp/dashboard/faq rates |
| Dashboard — increases engagement? | **Pending**; mapped to `#visibility` | dashboard_section_viewed vs later scroll |
| Knowledge — reached? | **No — section not on live page** | CX-RV-01 structural |
| Why not Knowledge? | Implementation gap vs approved IA/Hi-Fi | DOM audit |
| Which CTA? | **Pending** | hero_cta vs signup(final) vs login |
| Scroll depth? | **Pending** | scroll_* distribution |
| Ignored sections? | **Pending** | low view rates |
| Technical mobile issues? | None from lab GET | Revisit with device_distribution |

---

## 4. Decision status

| Field | Value |
|-------|-------|
| Decision | **PENDING — observation window open** |
| Eligible options later | Approve V1 · Minor Revision V2 · Major Revision V2 |
| Structural lean (not closed) | Missing LP-09 + live ≠ Hi-Fi already justify **Major Revision V2** backlog items; merchant scroll proof still required before closing Approve vs Minor |

Do not close Approve V1 on lab probes alone.

---

## 5. Update log

| Date (UTC) | Change |
|------------|--------|
| 2026-07-29 | Report opened; technical probe; telemetry instrumentation shipped for production deploy |
