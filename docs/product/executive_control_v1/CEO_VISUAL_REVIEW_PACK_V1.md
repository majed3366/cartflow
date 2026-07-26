# CEO Visual Review Pack V1 — Executive Control

**Status:** PENDING PRODUCTION DEPLOY + CERTIFIED SESSION  
**Branch:** `fix/executive-control-merchant-parity-v1` (`590a142`)

## 30-second questions (acceptance)

After a certified Living Store session (`CONSISTENT` + `CEO_REVIEW_SAFE=TRUE` + `store_slug=demo`), the merchant must answer in ≤30s:

1. How is my store?
2. What is the most important issue?
3. Which product is affected?
4. What should I do first?
5. Where are the operational details?

## Expected executive shape (Living Store)

- **حالة المتجر:** مستقر مع فرصة تستحق الانتباه (not “لا توجد مشكلات حرجة”)
- **أهم قرار اليوم:** product-specific (e.g. راجع مسار شراء Raven)
- **أهم منتج:** Raven / TrueSound / Horizon as evidence supports
- **السلال:** operational count + “لا يحتاج إجراءً فردياً الآن.” vs systemic Workspace action
- **التواصل:** constrained when contact missing — never “طبيعي” then

## Screenshots to attach after pack script

- `prod_cert_identity.png`
- `prod_desktop_home.png` / `prod_mobile_home.png`
- `prod_desktop_workspace.png` / `prod_mobile_workspace.png`
- `prod_desktop_products.png` / `prod_mobile_products.png`
- `prod_desktop_carts.png` / `prod_mobile_carts.png`
- `prod_desktop_communication.png` / `prod_mobile_communication.png`

## Run

```bash
python scripts/_executive_control_prod_ceo_pack_v1.py
```
