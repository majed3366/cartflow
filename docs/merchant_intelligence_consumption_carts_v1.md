# Merchant Intelligence Consumption V1 — Carts Workspace

**Status:** Implemented  
**Authority:** Presentation layer — consumes `merchant_intelligence_v1` only  
**Service basis:** [`merchant_intelligence_service_v1.md`](merchant_intelligence_service_v1.md)

---

## Mission

Transform the Carts page from a raw cart list into a **workspace of merchant understanding**.

The merchant sees **Merchant Intelligence Groups first** — ordered by platform priority — not individual cart rows.

---

## Architectural rule

```
merchant_intelligence_store_v1 (API)
        ↓ read-only
merchant_intelligence_carts_v1.js
        ↓ projection
Carts workspace UI
```

**Forbidden:** Local grouping, local recommendations, bucket→group mapping, urgency heuristics in JS.

**Allowed inputs only:**

| Field | Scope |
|-------|--------|
| `merchant_intelligence_store_v1` | Store bundle — groups, recommendations, priorities |
| `merchant_intelligence_v1` | Per-row bundle — group assignment, recommendation |
| `intelligence_group_key` | Row group membership |

Presentation may read `merchant_explanation_v1` for **display copy** inside expanded groups (what CartFlow did) — not for intelligence derivation.

---

## First screen

On `/dashboard#carts`, the merchant sees:

1. Hero + workspace subtitle (from MI groups summary)
2. **Intelligence group cards** (collapsed `<details>`)
3. Conversation panel (existing PE v2 — unchanged intelligence)

Legacy bucket filter bar is **hidden** in MI mode (`ma-carts--mi-v1`).

---

## Group order

Static platform order in `merchant_intelligence_carts_v1.js` aligned with MI Authority:

1. needs_merchant  
2. waiting_reply  
3. waiting_phone  
4. returned  
5. waiting_purchase  
6. repeated_hesitation  
7. product_hesitation  
8. vip  
9. completed  
10. risk_pattern  
11. no_contact  

Within same rank: higher `group.priority` first.

---

## Group card (collapsed)

Each card shows from MI group object:

- `title_ar` — title  
- `meaning_ar` — meaning  
- `merchant_summary_ar` — summary  
- `affected_carts` — count badge  
- `total_cart_value` — value (when present)  
- `confidence` — confidence label  
- `priority` — priority  
- Recommendation — from `store.recommendations` or row `merchant_intelligence_v1.recommendation` (highest priority in group)  
- CTA — "عرض التفاصيل" (expand — not a derived action)

No timelines. No raw records on the card face.

---

## Expanded group

Order inside group body:

1. **Why this group exists** — `meaning_ar` / `reason`  
2. **What CartFlow already did** — `merchant_explanation_v1.system_did_ar` from representative cart  
3. **Merchant recommendation** — `recommendation.merchant_message_ar` + primary CTA from `cart_detail_projection_v1` (representative cart)  
4. **Representative carts** — queue items from `representative_item.recovery_key`  
5. **Remaining carts** — collapsed `<details>` ("سلات أخرى")

Raw cart rows appear **last**, never first.

---

## Empty states (meaning-first)

| Condition | Message |
|-----------|---------|
| No groups, no rows | لا توجد سلات نشطة — CartFlow يراقب المتجر. |
| No groups, has rows | CartFlow يتابع سلات متجرك — لا يلزم تدخلك الآن. |
| MI store pending | CartFlow يجهّز فهم المتجر… |
| No attention needed | لا توجد سلات تحتاج انتباهك — CartFlow يتابع المتجر. |

---

## Files

| File | Role |
|------|------|
| `static/merchant_intelligence_carts_v1.js` | MI consumption + group render |
| `static/merchant_dashboard_lazy.js` | `renderMiCartsV1Workspace()` wiring |
| `static/merchant_product_polish_v1.css` | Group card styles |
| `templates/merchant_app.html` | Carts shell + script load |
| `services/dashboard_snapshot_normal_carts_slim_v1.py` | Snapshot allowlist for MI fields |

---

## Certification

**Test module:** `tests/test_merchant_intelligence_consumption_carts_v1.py`

| Check | Method |
|-------|--------|
| No local grouping | Grep — no `merchant_cart_primary_bucket` in MI JS |
| No local recommendations | No derived Arabic copy in MI JS |
| Store payload consumed | `merchant_intelligence_store_v1` in render path |
| Priority order | `needs_merchant` before `completed` in `GROUP_ORDER` |
| Representative + collapsed remainder | `splitRepresentative` + `ma-mi-group-more` |
| Story order in expand | why → CartFlow → recommendation → representatives |
| Snapshot MI fields | allowlist includes MI keys |
| Regression | Carts conversation panel still wired |

Run:

```bash
python -m unittest tests.test_merchant_intelligence_consumption_carts_v1 tests.test_merchant_carts_workspace_experience_v1 tests.test_merchant_product_polish_v1 -v
```

---

## Success criterion

> If a merchant sees this page for five seconds, can they describe the state of their store without opening a single cart?

Groups expose **title, meaning, summary, count, value, recommendation** — sufficient for store-state comprehension before drill-down.

---

## Not in scope (this sprint)

- Home / Weekly Brief / Notifications consumption  
- Visual redesign beyond group cards  
- Changes to `merchant_intelligence_v1.py` service  
- Filter bar reimplementation on top of MI groups
