# Evidence Asset Registry V1

**Status:** Permanent ID registry for Landing Evidence Library.  
**Date (UTC):** 2026-07-29  
**Library:** `library/EV-XXX/`  

IDs are permanent. Do not renumber. Retire via `retirement_history` in meta.json.

---

## Registry

| Evidence ID | Name | Landing Section(s) | Candidate file | Status | Scenario |
|-------------|------|--------------------|----------------|--------|----------|
| EV-001 | Hero Dashboard Preview | LP-02 | `library/EV-001/candidate.png` | Ready After Fresh Capture | SCN-HOME-01 |
| EV-002 | Widget Introduction | LP-06 | `library/EV-002/candidate.png` | Ready After Fresh Capture | SCN-WIDGET-01 |
| EV-003 | Widget Hesitation | LP-06 | `library/EV-003/candidate.png` | Ready After Fresh Capture | SCN-WIDGET-02 |
| EV-004 | Widget Reason Selection | LP-06 | `library/EV-004/candidate.png` | Ready After Fresh Capture | SCN-WIDGET-03 |
| EV-005 | WhatsApp Journey | LP-07 | — | Requires Operational Verification | SCN-WA-01 |
| EV-006 | Customer Reply | LP-07 | — | Requires Operational Verification | SCN-WA-02 |
| EV-007 | Merchant Follow-up | LP-07 | — | Requires Operational Verification | SCN-WA-03 |
| EV-008 | Purchase Completion | LP-07,08,12 | — | Ready After Fresh Capture | SCN-PUR-01 |
| EV-009 | Customer Return | LP-07,08 | — | Ready After Fresh Capture | SCN-RET-01 |
| EV-010 | Home Dashboard | LP-08 | `library/EV-010/candidate.png` | Ready After Fresh Capture | SCN-HOME-01 |
| EV-011 | Attention Queue | LP-08,10 | `library/EV-011/candidate.png` | Ready After Fresh Capture | SCN-HOME-01 |
| EV-012 | Knowledge Card | LP-09 | `library/EV-012/candidate.png` | Requires Reality Validation | SCN-KNOW-01 |
| EV-013 | Insufficient Evidence | LP-09,12 | `library/EV-013/candidate.png` | Ready After Fresh Capture | SCN-KNOW-02 |
| EV-014 | Decision Surface | LP-10,08 | `library/EV-014/candidate.png` | Ready After Fresh Capture | SCN-DEC-01 |
| EV-015 | Mobile Dashboard | LP-08 | `library/EV-015/candidate.png` | Ready After Fresh Capture | SCN-HOME-01 |
| EV-016 | Mobile Widget | LP-06 | `library/EV-016/candidate.png` | Ready After Fresh Capture | SCN-WIDGET-02 |
| EV-017 | Signup Flow | LP-15,01 | — | Ready After Fresh Capture | SCN-CTA-01 |
| EV-018 | Login Flow | LP-15,01 | — | Ready After Fresh Capture | SCN-CTA-02 |
| EV-019 | Integration Readiness Text | LP-13 | text (no image) | **Production Ready** | SCN-INT-01 |
| EV-020 | Contact Method | LP-16 | text/mailto | **Production Ready** | SCN-LEG-01 |
| EV-021 | Privacy Page | LP-16 | — | **Blocked** | SCN-LEG-02 |
| EV-022 | Terms Page | LP-16 | — | **Blocked** | SCN-LEG-03 |

---

## Rejected references (not IDs)

| Path | Reason |
|------|--------|
| `library/_rejected_ineligible/widget_settings.png` | Settings ≠ widget evidence |
| `library/_rejected_ineligible/whatsapp_settings.png` | Settings ≠ WA journey |

---

## Storyboard peak coverage

| Peak | Required IDs | Coverage |
|------|--------------|----------|
| Hero preview | EV-001 | Candidate |
| First product evidence | EV-002…004, EV-016 | Candidates (retake) |
| WA evidence | EV-005…007 | Missing |
| Dashboard climax | EV-010,011,015 | Candidates |
| Knowledge discovery | EV-012,013 | Candidate + RV |
| Decision | EV-014 | Candidate |
| CTA | EV-017,018 | Path only |
| Legal | EV-021,022 | Blocked |

---

## Reusability (later surfaces)

Approved Production Ready assets may later support: Pricing · Features · Widget page · WhatsApp page · Knowledge page · Docs · Investor decks — **only** while status remains Production Ready and not Outdated.
