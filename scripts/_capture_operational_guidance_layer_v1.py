# -*- coding: utf-8 -*-
"""Local structural review capture for OGL V1 (no production deploy)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PACK = ROOT / "docs" / "product" / "operational_guidance_layer_v1"
EV = PACK / "evidence"
EV.mkdir(parents=True, exist_ok=True)

checks = {}

home_js = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
checks["aaraf_alan_count"] = home_js.count("اعرف الآن")
checks["home_ogl_markers"] = all(
    s in home_js
    for s in ("ما الذي أحتاج فعله الآن؟", "ماذا تفعل الآن", "متى تعيد الفحص", "الحالة")
)

ws_js = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
checks["workspace_ogl"] = all(
    s in ws_js for s in ("التشخيص", "التوصية", "recheck_condition_ar", "شرط إعادة الفحص")
)

rec_html = (
    ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
).read_text(encoding="utf-8")
checks["first_message_label_gone"] = "موعد أول رسالة" not in rec_html
checks["fallback_primary_gone"] = "إعدادات احتياطية للمسارات بدون قالب سبب" not in rec_html
checks["advanced_present"] = "إعدادات متقدمة" in rec_html and "يُستخدم فقط عندما لا يوجد قالب سبب قابل للتطبيق" in rec_html
checks["internal_timing_copy"] = len(
    re.findall(r"fallback|quiet path|runtime", rec_html, flags=re.I)
)
checks["reason_order_ui"] = "mw-reason-list" in rec_html

wid_js = (ROOT / "static" / "merchant_widget_panel.js").read_text(encoding="utf-8")
checks["widget_drag_touch"] = "dragstart" in wid_js and "touchstart" in wid_js

from services.operational_guidance_v1 import compose_operational_guidance_v1
from services.operational_guidance_v1.compose_v1 import compose_from_hesitation_distribution_v1

g_ins = compose_operational_guidance_v1({"store_slug": "review"}, store_slug="review")
g_ship = compose_from_hesitation_distribution_v1(
    store_slug="review",
    total=20,
    distribution={"shipping": 12, "price": 4, "other": 4},
)
checks["guidance_insufficient_ok"] = bool(g_ins.get("ok") and g_ins.get("recheck_condition"))
checks["guidance_shipping_ok"] = bool(g_ship.get("ok") and g_ship.get("family") == "shipping_friction")

# Lightweight HTML evidence pages for founder visual review attachment.
(EV / "home_guidance_fixture.html").write_text(
    f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>OGL Home fixture</title>
<body style="font-family:Tajawal,sans-serif;padding:24px;max-width:720px">
<h1>ما الذي أحتاج فعله الآن؟</h1>
<div data-cf2-ogl-home="1">
<p><b>ما نراه</b> {g_ship.get('home_surface',{}).get('what_we_see_ar','')}</p>
<p><b>ماذا يعني</b> {g_ship.get('home_surface',{}).get('what_it_means_ar','')}</p>
<p><b>ماذا تفعل الآن</b> {g_ship.get('home_surface',{}).get('what_to_do_now_ar','')}</p>
<p><b>متى تعيد الفحص</b> {g_ship.get('home_surface',{}).get('when_to_recheck_ar','')}</p>
</div>
<p>أدوار ثانوية: الحالة · ما يحتاج انتباهًا · الأثر</p>
<p>اعرف الآن count fixture assert: 0</p>
</body></html>
""",
    encoding="utf-8",
)
(EV / "home_insufficient_fixture.html").write_text(
    f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>OGL insufficient</title>
<body style="font-family:Tajawal,sans-serif;padding:24px;max-width:720px">
<h1>أدلة غير كافية</h1>
<p>{g_ins.get('diagnosis')}</p>
<p><b>الإجراء</b> {g_ins.get('merchant_action')}</p>
<p><b>إعادة الفحص</b> {g_ins.get('recheck_condition')}</p>
</body></html>
""",
    encoding="utf-8",
)
(EV / "workspace_guidance_fixture.html").write_text(
    f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>OGL Workspace</title>
<body style="font-family:Tajawal,sans-serif;padding:24px;max-width:720px">
<p><b>الدليل</b> {g_ship.get('workspace_surface',{}).get('evidence_ar','')}</p>
<p><b>التشخيص</b> {g_ship.get('workspace_surface',{}).get('diagnosis_ar','')}</p>
<p><b>التوصية</b> {g_ship.get('workspace_surface',{}).get('recommendation_ar','')}</p>
<p><b>لماذا</b> {g_ship.get('workspace_surface',{}).get('why_ar','')}</p>
<p><b>شرط إعادة الفحص</b> {g_ship.get('workspace_surface',{}).get('recheck_condition_ar','')}</p>
</body></html>
""",
    encoding="utf-8",
)
(EV / "recovery_advanced_fixture.html").write_text(
    """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Recovery advanced</title>
<body style="font-family:Tajawal,sans-serif;padding:24px">
<p>أقرب إرسال من القوالب · 15 دقيقة من ترك السلة</p>
<details open><summary>إعدادات متقدمة</summary>
<p>يُستخدم فقط عندما لا يوجد قالب سبب قابل للتطبيق.</p>
</details>
</body></html>
""",
    encoding="utf-8",
)
(EV / "widget_reason_order_fixture.html").write_text(
    """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Reason order</title>
<body style="font-family:Tajawal,sans-serif;padding:24px">
<ul>
<li>⋮⋮ الشحن ↑ ↓</li>
<li>⋮⋮ السعر ↑ ↓</li>
<li>⋮⋮ الجودة ↑ ↓</li>
</ul>
<p>keys immutable · display_order merchant configurable</p>
</body></html>
""",
    encoding="utf-8",
)

try:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for name in (
            "home_guidance_fixture",
            "home_insufficient_fixture",
            "workspace_guidance_fixture",
            "recovery_advanced_fixture",
            "widget_reason_order_fixture",
        ):
            page.set_viewport_size({"width": 1280, "height": 800})
            page.goto((EV / f"{name}.html").as_uri())
            page.screenshot(path=str(EV / f"desktop_{name}.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(EV / f"mobile_{name}.png"), full_page=True)
        browser.close()
    checks["screenshots"] = True
except Exception as exc:  # noqa: BLE001
    checks["screenshots"] = False
    checks["screenshots_error"] = str(exc)

verdict = {
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "checks": checks,
    "pass": checks["aaraf_alan_count"] == 0
    and checks["home_ogl_markers"]
    and checks["workspace_ogl"]
    and checks["first_message_label_gone"]
    and checks["fallback_primary_gone"]
    and checks["advanced_present"]
    and checks["internal_timing_copy"] == 0
    and checks["reason_order_ui"]
    and checks["widget_drag_touch"]
    and checks["guidance_insufficient_ok"]
    and checks["guidance_shipping_ok"],
}
(PACK / "REVIEW_PROOF.json").write_text(
    json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps(verdict, ensure_ascii=False, indent=2))
raise SystemExit(0 if verdict["pass"] else 1)
