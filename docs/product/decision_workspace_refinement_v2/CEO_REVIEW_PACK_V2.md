# Decision Workspace Refinement V2 — CEO Review Pack

**Status:** Awaiting CEO visual review after production deploy.  
**Date (UTC):** 2026-07-28  
**Scope:** Refine only — no new features / engines / architecture expansion.

---

## Mission

Workspace = **Executive Decision Room**.

Merchant leaves with:

1. one trusted decision  
2. one execution methodology  
3. one measurable verification path  

Never another report.

---

## What changed (R1–R7)

| ID | Change |
|----|--------|
| **R1** | Conversation face: chained labels (ما يحدث → لماذا → ولذلك → جاهزية → … → كيف يتحقق) |
| **R2** | CartFlow owns analysis/readiness/validation; merchant owns judgement/execution — no investigate/diagnose CTAs |
| **R3** | Methodology on card: readiness → where → how → avoid → commitment → verify |
| **R4** | `execution_domain` internal / platform / business; routing follows domain |
| **R5** | No `#workspace` loops; no fixed Products dump; business may have no in-app href |
| **R6** | Soft/investigative openers stripped; filler reduced |
| **R7** | Page question answers: what / why / ready / where / how CartFlow verifies |

---

## Acceptance checklist (CEO)

- [ ] Feels like an executive meeting  
- [ ] Never feels like a BI report  
- [ ] CartFlow performs the analysis  
- [ ] Merchant performs the business decision  
- [ ] Execution destination is logical  
- [ ] No circular navigation  
- [ ] Language is diagnostic / methodological  
- [ ] Execution methodology is explicit  
- [ ] Continues Home (diagnostic primary)

---

## Production artifacts

Screenshots after deploy:

- `prod_desktop_workspace.png` / `prod_desktop_home.png`  
- `prod_mobile_workspace.png` / `prod_mobile_home.png`  

Script: `scripts/_gate2a_decision_workspace_prod_shots_v1.py` (or refinement V2 shot script if present).

---

## STOP

No polishing after deployment.  
**Await CEO visual review.**
