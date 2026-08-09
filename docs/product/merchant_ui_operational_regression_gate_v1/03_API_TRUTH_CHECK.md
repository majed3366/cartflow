# Gate 3 — API Truth

Artifact: `endpoint_truth_probe.json`  
Session: Living Store review cookie · **read-only**

| Endpoint | HTTP | Shape | Notes |
|----------|------|-------|-------|
| `GET /api/dashboard/summary` | **200** | Valid JSON keys incl. `merchant_home_experience_v1`, HES transport | No 5xx |
| `GET /api/cart-workspace/v1/projection` | **200** | `ok`, `projection.zone_b` length **4** | Primary decision: «لا تغيّر سياسة الشحن حتى تتضح الأدلة.» |

Optional carts/setup paths returned 404 in this probe surface (not loaded by V2 Home/Workspace painters).

## UI match

Workspace painted title/mass matched projection `decision_sentence_ar` sample.  
No client parse failures observed (`pageerror` = 0).
