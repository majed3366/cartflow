# Home Commercial Intelligence Transition V1 — Validation

**Date (UTC):** 2026-07-19  
**Production URL:** https://smartreplyai.net/dashboard#home  

---

## Success metric

Home is measured by **how many different commercial questions** CartFlow answers with evidence — not carts/events/widgets.

Demo evidence run (`scripts/_validate_home_commercial_intelligence_v1.py`):

| Metric | Result |
|--------|--------|
| Diversity OK | Yes |
| Questions answered | ≥ 4 |
| Dimensions | products, recovery, traffic, contact (and more as available) |
| Contact-only monopoly | **Broken** — Understanding/Opportunity/Learning use non-contact dimensions |

Evidence JSON: `HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json`

---

## Deliverables

1. `COMMERCIAL_QUESTION_REGISTRY_V1.md` + `services/commercial_question_registry_v1.py`  
2. Question→Insight mapping in evidence JSON + registry §4  
3. Evidence flow documented in registry §5  
4. Admission: `services/home_commercial_intelligence_v1.py` (wired in finalize)  
5. Screenshots: require logged-in merchant session (auth wall) — use fixture URLs below  
6. This validation report  

---

## What merchants should see

- Understanding answers a **product / hesitation / traffic** question (not phone count)  
- Opportunity is a **commercial** opportunity, not “N carts with phone”  
- Learning shows **knowledge growth or missing evidence**  
- Priority may still own contact **action** when warranted  
- Health evidence prefers commercial-question coverage over cart tallies  

---

## Fixture URLs

https://smartreplyai.net/dashboard?acf_fixture=attention#home  
https://smartreplyai.net/dashboard?acf_fixture=healthy#home  

---

## STOP

Await Product Review. No new pages. No Home redesign. No AI conclusions.
