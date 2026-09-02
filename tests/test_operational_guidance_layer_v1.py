# -*- coding: utf-8 -*-
"""Operational Guidance Layer V1 + Recovery/Widget order gates."""
from __future__ import annotations

from pathlib import Path

from services.cartflow_widget_trigger_settings import (
    DEFAULT_WIDGET_TRIGGER_CONFIG,
    normalize_widget_trigger_config,
)
from services.operational_guidance_v1 import (
    FAMILY_AUDIT_V1,
    SUPPORTED_FAMILIES_NOW,
    compose_operational_guidance_v1,
    validate_guidance_object_v1,
)
from services.operational_guidance_v1.compose_v1 import (
    compose_from_hesitation_distribution_v1,
    compose_wait_insufficient_v1,
)
from services.operational_guidance_v1.contract_v1 import (
    FAMILY_PRICE_HESITATION,
    FAMILY_SHIPPING_FRICTION,
    FAMILY_WAIT_INSUFFICIENT,
    is_bare_generic_recommendation_ar,
)

ROOT = Path(__file__).resolve().parents[1]


def test_guidance_contract_fields_required():
    g = compose_wait_insufficient_v1(
        store_slug="demo",
        missing_ar="ناقص",
        observe_ar="راقب دون تغيير السعر حتى يكتمل الشرط.",
        unlock_ar="أعد القرار عند وصول أسباب التردد إلى 8.",
    )
    assert g["ok"] is True
    assert validate_guidance_object_v1(g) == []
    assert g["recheck_condition"]
    assert g["merchant_action"]
    assert g["home_surface"]["when_to_recheck_ar"]


def test_bare_generic_rejected():
    assert is_bare_generic_recommendation_ar("راجع")
    assert is_bare_generic_recommendation_ar("راقب")
    assert not is_bare_generic_recommendation_ar(
        "لا تغيّر السعر الآن. راقب أسباب التردد حتى تصل إلى 8."
    )


def test_no_guidance_without_evidence_default():
    g = compose_operational_guidance_v1({"store_slug": "demo"}, store_slug="demo")
    assert g["family"] == FAMILY_WAIT_INSUFFICIENT
    assert g["ok"] is True
    assert "8" in g["recheck_condition"] or "تشخيص" in g["recheck_condition"]


def test_shipping_and_price_families_from_distribution():
    ship = compose_from_hesitation_distribution_v1(
        store_slug="demo",
        total=20,
        distribution={"shipping": 12, "price": 4, "other": 4},
    )
    assert ship["ok"] is True
    assert ship["family"] == FAMILY_SHIPPING_FRICTION
    assert "لا تغيّر" in ship["recommendation"] or "لا تخفّض" in ship["recommendation"]

    price = compose_from_hesitation_distribution_v1(
        store_slug="demo",
        total=20,
        distribution={"price": 14, "shipping": 3, "other": 3},
    )
    assert price["family"] == FAMILY_PRICE_HESITATION
    assert "خصم" in price["recommendation"] or "السعر" in price["recommendation"]


def test_communication_followup_from_teaser():
    g = compose_operational_guidance_v1(
        {
            "store_slug": "demo",
            "home_teaser_inputs_v1": {
                "schema": "home_teaser_inputs_v1",
                "health": {"no_phone": 3},
            },
        },
        store_slug="demo",
    )
    assert g["ok"] is True
    assert g["family"] == "communication_followup"
    assert g["recheck_condition"]


def test_supported_families_audit_complete():
    assert len(SUPPORTED_FAMILIES_NOW) == 5
    for fam in SUPPORTED_FAMILIES_NOW:
        assert FAMILY_AUDIT_V1.get(fam) == "SUPPORTED_NOW"


def test_reason_display_order_corrupt_falls_back():
    cfg = normalize_widget_trigger_config(
        {"reason_display_order": ["price", "price", "bogus", None, "shipping"]}
    )
    order = cfg["reason_display_order"]
    assert order[0] == "price"
    assert "bogus" not in order
    assert len(order) == len(DEFAULT_WIDGET_TRIGGER_CONFIG["reason_display_order"])
    assert len(set(order)) == len(order)
    for k in DEFAULT_WIDGET_TRIGGER_CONFIG["reason_display_order"]:
        assert k in order


def test_reason_display_order_missing_uses_canonical():
    cfg = normalize_widget_trigger_config({})
    assert cfg["reason_display_order"] == list(
        DEFAULT_WIDGET_TRIGGER_CONFIG["reason_display_order"]
    )


def test_home_js_no_aaraf_alan_duplication():
    home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
    assert home.count("اعرف الآن") == 0
    assert "ما الذي أحتاج فعله الآن؟" in home
    assert "what_to_do_now_ar" in home or "ماذا تفعل الآن" in home


def test_recovery_primary_no_first_message_ambiguity():
    html = (
        ROOT / "templates" / "partials" / "merchant_settings_canonical_v1.html"
    ).read_text(encoding="utf-8")
    assert "موعد أول رسالة" not in html
    assert "إعدادات احتياطية للمسارات بدون قالب سبب" not in html
    assert "إعدادات متقدمة" in html
    assert "يُستخدم فقط عندما لا يوجد قالب سبب قابل للتطبيق" in html
    assert "أقرب إرسال من القوالب" in html
    assert "fallback" not in html.lower()
    assert "quiet path" not in html.lower()
    assert "mw-reason-list" in html


def test_widget_panel_has_reason_order_ui():
    js = (ROOT / "static" / "merchant_widget_panel.js").read_text(encoding="utf-8")
    assert "paintReasonOrderUi" in js
    assert "reason_display_order" in js
    assert "touchstart" in js
    assert "dragstart" in js
