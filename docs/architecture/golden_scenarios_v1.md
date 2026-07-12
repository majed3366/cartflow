# Cart Workspace Golden Scenarios V1

**Status:** Constitutional engineering scenarios — permanent  
**Date (UTC):** 2026-07-12  
**Version:** v1  
**Runtime:** `services/cart_workspace/golden_scenarios_v1.py`  
**Authority:** Cart Workspace Product Foundation + Engineering Spec + Implementation Constitution  

Every future Cart Workspace sprint **must** pass GS-01…GS-10.

These scenarios exercise the shadow pipeline only. They do **not** activate the merchant surface (`CARTFLOW_CART_WORKSPACE_V1` remains default OFF).

---

## Catalogue

| ID | Title | Parity topic | Expected projection posture |
|----|-------|--------------|-----------------------------|
| **GS-01** | Normal hesitation | Waiting | Quiet; Do Not Admit (R01) |
| **GS-02** | Customer reply | Customer Reply | Quiet; Do Not Admit (R04) — automation answers |
| **GS-03** | VIP | VIP | Zone A card; Admit R07; Override active |
| **GS-04** | Discount request | Customer Reply / exception | Zone B card; Admit R06; one Action |
| **GS-05** | Purchase completed | Purchase | Quiet; R11; Zone D rollup ≥1; journey completed |
| **GS-06** | Missing phone | Missing Phone | Quiet; Do Not Admit (R09) — Status ≠ Decision |
| **GS-07** | Duplicate webhook | Duplicate Event | One open Decision only; second step Do Not Admit |
| **GS-08** | Provider outage | Provider Failure | Quiet; R12; CartFlow owns Execution |
| **GS-09** | Merchant inactive | Merchant Inactivity | One open Decision retained; no re-Admit |
| **GS-10** | Recovery completed | Recovery Completed | Admit then purchase → Quiet; open=0; Zone D bump |

---

## Invariants proven

- Decision identity stable (no duplicate cards on refresh fingerprint)
- Ownership transitions only via Admit / completion gates
- Admission binary only
- Zones derived from open Decisions + rollups
- Quiet = success when A+B empty

---

## How to run

```text
pytest tests/test_cart_workspace_golden_scenarios_v1.py -q
GET /dev/cart-workspace-golden          # ENV=development
GET /dev/cart-workspace-projection?golden=GS-03
```

---

## Amendment

Adding/changing a golden scenario requires:

1. Product impact check (does expected posture change Product Truth?)  
2. Update this catalogue + `golden_scenarios_v1.py`  
3. Sprint regression green  

---

**End of Golden Scenarios V1.**
