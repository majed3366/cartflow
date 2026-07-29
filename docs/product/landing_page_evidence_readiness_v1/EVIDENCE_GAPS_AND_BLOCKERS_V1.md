# Evidence Gaps and Blockers V1

**Status:** Blocker registry for landing publication.  
**Date (UTC):** 2026-07-29  
**Parent:** Landing Page Evidence Readiness V1  

Defines missing proof and reopen gates only — not redesign solutions.

---

## Blocker registry

| Blocker ID | Section | Missing Evidence | Why It Matters | Current Risk | Resolution Owner | Required Action | Gate to Reopen | Status |
|------------|---------|------------------|----------------|--------------|------------------|-----------------|----------------|--------|
| BLK-01 | LP-06 | Publication-safe storefront widget capture (mobile) | Settings PNG would violate Visual Evidence Law | **High** — false product proof | Product + Eng | Execute CAP-02/03 under Capture Plan | Capture approved + eligibility pass | Open |
| BLK-02 | LP-06 | Landing currently points at settings UI | Merchants see admin, not customer tool | High | Product | Retire settings as LP-06 evidence | CAP-02 replaces EI-009 | Open |
| BLK-03 | LP-07 | Journey-grade WA evidence (not settings) | WA-sender mispositioning | High | Product + Ops | CAP-04/05/06 | Ops verify + capture approve | Open |
| BLK-04 | LP-07 | Provider readiness wording (Meta/Twilio) | Overclaiming production WA | High | Ops | Document current gate; disclose | Ops sign-off on ceiling | Open |
| BLK-05 | LP-08 | Landing-grade capture from current Home/Workspace | Stale May 2026 crops misrepresent product | High | Product | CAP-07/08/15 from 2026-07 faces | Freshness check | Open |
| BLK-06 | LP-08 | Face approval for public marketing use | CEO-review surfaces still evolving | Medium | Product | Explicit “landing-safe face” approval | Owner question 12 | Open |
| BLK-07 | LP-09 | Theme Reality Validation for pattern claims | Fabrication / empty-as-intelligence risk | High | Product | RV-LP-01…09 as applicable | RV pass per theme | Open |
| BLK-08 | LP-09 | Knowledge materialisation reliability | Empty Home common without bridge | High | Product | Capture only when painted; disclose empty honesty | CAP-11 + CAP-12 | Open |
| BLK-09 | LP-10 | Traffic vs conversion distinction RV | Claim exceeds safe language | Medium | Product | RV-LP-05 | Validation pass | Open |
| BLK-10 | LP-11 | Organic longitudinal continuity pack | Simulation ≠ multi-week merchant proof | Medium | Product | Keep conceptual/illustrative | E6 continuity (future) | Open — accepted for conceptual |
| BLK-11 | FAQ / LP-06 | Measured storefront performance | Speed claim forbidden without numbers | High | Engineering | Baseline vs enabled Web Vitals study | Perf validation pass | Open |
| BLK-12 | LP-13 | Logo rights + false platform support | Legal + Truth Policy | Medium | Product/Legal | Text states only; no logos | Integration revalidation | Open (logos blocked) |
| BLK-13 | LP-15 | Demo booking path | Cannot offer Demo CTA | Low (correctly deferred) | Product | Build path before claim | Path exists + gate | Open — correctly blocked |
| BLK-14 | LP-15 | Instant activation expectation | Signup ≠ production go-live | Medium | Ops/Product | Disclosure in CTA/onboarding truth | Wording ceiling | Open |
| BLK-15 | LP-16 | Privacy page | Footer trust incomplete | Medium | Legal/Product | Ship real Privacy page | Legal review | Open |
| BLK-16 | LP-16 | Terms page | Footer trust incomplete | Medium | Legal/Product | Ship real Terms page | Legal review | Open |
| BLK-17 | LP-12 | Absolute privacy/security legal approval | Overclaim risk | Medium | Legal | Bound isolation language | Legal OK for absolutes | Open |
| BLK-18 | Cross | Sensitive-data scrub process for captures | PII on public landing | High | Product/Ops | Demo-only + mask phones | Capture governance checklist | Open |
| BLK-19 | LP-06 | Mobile customer journey pack | Mobile-first constitution | High | Product | CAP-02 mobile | Mobile eligibility | Open |
| BLK-20 | Cross | No E6 commercially publishable pack yet | Premature full-page launch risk | High | Product | Close BLK-01…08 as needed per section | Per-section E6 | Open |

---

## Blocker categories covered

| Category | Blocker IDs |
|----------|-------------|
| Missing product capture | BLK-01, BLK-03, BLK-05, BLK-19 |
| Stale UI | BLK-02, BLK-05 |
| Operational readiness | BLK-04, BLK-14 |
| Provider readiness | BLK-04 |
| Reality Validation | BLK-07, BLK-09 |
| Performance measurement | BLK-11 |
| Integration verification | BLK-12 |
| Commercial path | BLK-13, BLK-14 |
| Legal/privacy | BLK-15, BLK-16, BLK-17 |
| Sensitive-data handling | BLK-18 |
| Mobile evidence | BLK-19 |
| Knowledge materialisation | BLK-08 |

---

## Reopen policy

1. Close a blocker only with dated evidence update in this pack or SYSTEM_SUMMARY.  
2. Closing BLK-01 does not auto-close BLK-07.  
3. Conceptual sections (LP-04, LP-11 modality) may proceed without E6 visuals if claims stay conceptual.  
4. No broad redesign prescriptions — proof first.
