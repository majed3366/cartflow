# Landing Page Reality Validation V1

**Status:** Observation window OPEN  
**Date (UTC):** 2026-07-29  
**Production URL:** https://smartreplyai.net/  
**Subject:** Publicly deployed `GET /` (`templates/cartflow_landing.html`)

---

## 1. One question

Does the current Landing Page communicate CartFlow's value to real merchants?

All later improvements must be evidence-driven.

---

## 2. Governing authorities (immutable for this phase)

| Authority | Role in validation |
|-----------|-------------------|
| Landing Page Constitution V1 | Claim / truth / evidence laws |
| Landing Page Information Architecture V1 | LP-01…16 intended story |
| Landing Page Copy Architecture V1 | Message objectives (not final copy rewrite gate) |
| Landing Page Storyboard V1 | Scroll journey expectations |
| Landing Page Wireframe V1 | Structure reference |
| Landing Page Visual Direction V1 | Feel reference |
| Landing Page Hi-Fi Figma V1 | Canonical visual reference for future implementation |

This phase **must not reopen** approved governance. It validates **implementation**.

---

## 3. Implementation under validation

| Item | Value |
|------|-------|
| Host | `https://smartreplyai.net` |
| Route | `GET /` → `routes/public.py` → `cartflow_landing.html` |
| CTAs | `/signup`, `/login` (no Demo) |
| Live structure | Older product-story: Hero → think → objections → recovery → visibility → components → FAQ → contact → footer |
| Approved IA structure | LP-01…16 (Widget first evidence → Dashboard climax → Knowledge earns identity) |
| Hi-Fi on production | **No** — Figma is review reference only until formal frontend approval |

### Contradiction log

| ID | Finding | Handling |
|----|---------|----------|
| CX-RV-01 | Live `GET /` does not implement approved LP-01…16 / Hi-Fi Figma V1 | Documented. No silent redesign during validation. Telemetry maps live DOM → closest semantic events. `knowledge_section_viewed` cannot fire (section absent). |
| CX-RV-02 | Live `#components` still uses settings screenshots rejected by Evidence Production | Structural/evidence debt — backlog only; no asset swap redesign in this window unless critical defect. |

---

## 4. Production rules (binding)

### Allowed during validation

- Broken layouts  
- Routing errors  
- Loading failures  
- Accessibility blockers  
- Critical bugs  

### Forbidden during validation

- UX improvements  
- Visual improvements  
- Copy rewrites  
- New sections  
- Removed sections  
- Speculative redesigns  
- Opinion-based optimisation  

---

## 5. Telemetry contract

### Endpoint

| Method | Path | Auth |
|--------|------|------|
| `POST` | `/api/landing/event` | None (anonymous) |
| `GET` | `/api/landing/summary` | `X-CartFlow-Admin: $CARTFLOW_ADMIN_PASSWORD` |

### Client

`static/cartflow_landing_telemetry.js` (loaded by landing footer).

### Allowed events only

```text
landing_opened
hero_visible
hero_cta_clicked
login_clicked
signup_clicked
problem_section_viewed
widget_section_viewed
whatsapp_section_viewed
dashboard_section_viewed
knowledge_section_viewed
faq_section_viewed
footer_reached
scroll_25
scroll_50
scroll_75
scroll_100
page_exit
```

### Privacy

- No names, emails, phones, IPs stored in event rows  
- Opaque `session_key` in `sessionStorage` only  
- Device class: mobile / tablet / desktop / unknown  
- Persist table: `landing_page_events_v1`

### Live DOM → event map

| Event | Live selector / note |
|-------|----------------------|
| `hero_visible` | `#hero` |
| `problem_section_viewed` | `#objections` |
| `dashboard_section_viewed` | `#visibility` |
| `widget_section_viewed` | `#components` widget card |
| `whatsapp_section_viewed` | `#components` WhatsApp card |
| `faq_section_viewed` | `#faq` |
| `footer_reached` | `footer.foot` |
| `knowledge_section_viewed` | **No node** — always absent on current live page |
| `hero_cta_clicked` | Hero primary → `/signup` |
| `signup_clicked` | Any signup CTA (hero / nav / final) |
| `login_clicked` | Login links |

---

## 6. Observation questions (must be answered in reports)

1. **Hero** — Value understood in the first few seconds?  
2. **Story** — Where do merchants stop scrolling?  
3. **Widget** — Do visitors continue after Widget?  
4. **Dashboard** — Does Dashboard increase engagement?  
5. **Knowledge** — Do merchants reach Knowledge? If not, why?  
6. **CTA** — Hero vs Final vs Login vs Signup interaction  
7. **Scroll** — How far do visitors read?  
8. **Reading** — Ignored vs retained sections  
9. **Technical** — Rendering, performance, mobile issues  

---

## 7. Success metrics (observations, not KPI targets)

Report actuals only:

Visitors (approx sessions) · Sessions · Average / distribution of scroll depth · Hero CTA clicks · Signup clicks · Login clicks · Section visibility · Dashboard visibility · Knowledge visibility · CTA completion · Bounce observations · Device distribution · Mobile vs Desktop behaviour  

Learning > passing arbitrary targets.

---

## 8. Sample sufficiency (decision gate)

Decision (Approve / Minor / Major) requires behavioural sample — not lab probes alone.

| Gate | Definition |
|------|------------|
| **Minimum behavioural sample** | ≥ 30 distinct `session_key` with `landing_opened` in a contiguous observation window **or** 14 UTC days of telemetry, whichever comes first for interim review |
| **Lab / agent traffic** | Technical probes allowed; **must be labeled** and excluded from merchant behavioural conclusions |
| **Structural evidence** | May populate Revision Backlog immediately (e.g. missing LP-09) without claiming merchant scroll proof |

---

## 9. Final decision (exactly one)

When sample gate is met, choose exactly one:

1. **Approve V1** — live page communicates value adequately; no story redesign required  
2. **Minor Revision V2** — local evidence-backed fixes (copy density, CTA weight, asset swap) without IA change  
3. **Major Revision V2** — implement approved LP-01…16 / Hi-Fi structure on production  

Decision must cite behavioural and/or structural evidence in `LANDING_PAGE_OBSERVATION_REPORT_V1.md`.

---

## 10. Non-goals

- Optimise from personal opinion  
- Change visual hierarchy without evidence  
- Rewrite copy because it “feels better”  
- Introduce or remove approved sections during the window  
- Conduct speculative redesigns  

---

## 11. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Landing publicly deployed | **Pass** — `https://smartreplyai.net/` returns 200 |
| Behavioural telemetry operational | **Pending merge to `main`** — code on `feat/landing-page-reality-validation-v1` (`7918de1`); verify via summary after Railway deploy |
| Merchant interaction observed | **In progress** — window open; refresh Observation Report as sessions accumulate |
| Reality Validation reports completed | **Pass** — pack files present; behavioural sections update as data arrives |
| Evidence-backed revision backlog | **Pass** — see `REVISION_BACKLOG_V1.md` |
| Next iteration driven by measured behaviour | **Binding rule** — see Revision Rules |

---

## 12. Strategic principle

```text
Observation → Evidence → Decision → Improvement
```

Never:

```text
Opinion → Redesign → Hope
```
