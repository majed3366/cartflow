# -*- coding: utf-8 -*-
"""
كتالوج متجر التجربة — بيانات ثابتة واقعية لاختبار ذكاء المنتج والعروض والاستمرار.
لا يستبدل تطبيقاً منفصلاً؛ يُغذّي ‎/demo/store*‎ و‎JSON‎ للمزامنة مع ‎cf_product_catalog_json‎.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

# ترتيب العرض ومسارات ‎/demo/store/product/{n}‎
SANDBOX_PRODUCT_ORDER: Tuple[str, ...] = (
    "hp_pro",
    "earbuds",
    "hp_air",
    "hp_stick",
    "watch_pro",
    "watch_sport",
    "perfume",
    "perfume_velvet",
    "charger",
    "watch_band",
    "wallet",
    "hoodie_essentials",
    "hoodie",
)

# مفتاح الصف → رقم المسار
SANDBOX_PRODUCT_NUM_BY_KEY: Dict[str, int] = {
    k: i + 1 for i, k in enumerate(SANDBOX_PRODUCT_ORDER)
}

# رقم المسار → مفتاح (لـ‎ main._DEMO_BEHAVIORAL_PRODUCT_BY_NUM‎)
SANDBOX_PRODUCT_KEY_BY_NUM: Dict[int, str] = {
    i + 1: k for i, k in enumerate(SANDBOX_PRODUCT_ORDER)
}


def _img(seed: str, w: int = 520, h: int = 520) -> str:
    s = seed.replace(" ", "-")[:40]
    return f"https://picsum.photos/seed/cf-{s}/{w}/{h}"


def product_demo_url(nav_base: str, key: str) -> str:
    """مسار صفحة المنتج في واجهة التجربة (‎/demo/store‎ أو ‎/demo/store2‎)."""
    nb = (nav_base or "/demo/store").rstrip("/") or "/demo/store"
    return f"{nb}/product/{SANDBOX_PRODUCT_NUM_BY_KEY[key]}"


def _p(
    key: str,
    *,
    name: str,
    price: float,
    category: str,
    description: str,
    short: str,
    warranty_info: str,
    shipping_info: str,
    related: Tuple[str, ...],
    cheaper_than: Tuple[str, ...] = (),
    available: bool = True,
    image_seed: str = "",
    product_family: str = "",
    normalized_category: str = "",
) -> Dict[str, Any]:
    seed = image_seed or key
    url_path = product_demo_url("/demo/store", key)
    nc_out = (normalized_category or "").strip() or (category or "").strip()
    out: Dict[str, Any] = {
        "key": key,
        "id": f"demo_{key}",
        "sku": f"DEMO-{key.upper().replace('_', '-')}",
        "name": name,
        "price": float(price),
        "unit_price": float(price),
        "category": category,
        "normalized_category": nc_out,
        "description": description,
        "short": short,
        "warranty_info": warranty_info,
        "shipping_info": shipping_info,
        "url": url_path,
        "product_url": url_path,
        "image": _img(seed),
        "available": available,
        "related_keys": list(related),
        "cheaper_alternative_keys": list(cheaper_than),
    }
    fam = (product_family or "").strip()
    if fam:
        out["product_family"] = fam[:64]
    return out


SANDBOX_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "hp_pro": _p(
        "hp_pro",
        name="TrueSound Pro — سماعة لاسلكية مع عزل ضوضاء",
        price=449.0,
        category="إلكترونيات",
        description=(
            "عزل نشط مريح لساعات الاستماع، صوت واضح في المكالمات، وعلبة شحن "
            "تدوم لعدة أيام بين الشحنات. مناسبة للسفر والعمل."
        ),
        short="فئة عليا — عزل ANC وصوت متوازن.",
        warranty_info="ضمان سنتان ضد عيوب التصنيع.",
        shipping_info="شحن 2–5 أيام عمل حسب المدينة.",
        related=("earbuds", "hp_air", "charger"),
        cheaper_than=("earbuds", "hp_air", "hp_stick"),
        image_seed="ts-pro-hp",
        product_family="truesound_headphones",
    ),
    "earbuds": _p(
        "earbuds",
        name="TrueSound — سماعة لاسلكية",
        price=199.0,
        category="إلكترونيات",
        description=(
            "تجربة صوتية متوازنة، عزل تمريري مريح، وعمر بطارية يناسب اليوم الكامل. "
            "تصنيف متوسط–علوي دون سعر الفئة الراقية."
        ),
        short="خيار متوسط قوي للاستخدام اليومي.",
        warranty_info="ضمان سنة ضد عيوب التصنيع.",
        shipping_info="شحن 2–5 أيام عمل حسب المدينة.",
        related=("hp_pro", "hp_air", "charger"),
        cheaper_than=("hp_air", "hp_stick"),
        image_seed="ts-lite-hp",
        product_family="truesound_headphones",
    ),
    "hp_air": _p(
        "hp_air",
        name="TrueSound Air — سماعة خفيفة",
        price=119.0,
        category="إلكترونيات",
        description=(
            "تصميم مفتوح أخف وزناً للمشي والمكتب. صوت واضح مع ميكروفون مناسب للمكالمات القصيرة."
        ),
        short="مدخل سعري أخف — نفس العائلة الصوتية.",
        warranty_info="ضمان سنة.",
        shipping_info="شحن 2–4 أيام عمل.",
        related=("earbuds", "hp_stick", "charger"),
        cheaper_than=("hp_stick",),
        image_seed="ts-air-hp",
        product_family="truesound_headphones",
    ),
    "hp_stick": _p(
        "hp_stick",
        name="SoundStick — سماعة سلكية مدمجة",
        price=59.0,
        category="إلكترونيات",
        description=(
            "سماعة أذن سلكية بسيطة للحقيبة والسفر. لا بطارية — تعمل مع منفذ سماعات قياسي أو محوّل."
        ),
        short="أقل سعر في فئة السماعات — للميزانيات الحذرة.",
        warranty_info="ضمان 6 أشهر.",
        shipping_info="شحن اقتصادي 3–6 أيام.",
        related=("hp_air", "charger"),
        cheaper_than=(),
        image_seed="soundstick",
        product_family="truesound_headphones",
    ),
    "watch_pro": _p(
        "watch_pro",
        name="Horizon Steel — ساعة يد ستانلس",
        price=1299.0,
        category="ساعات",
        description=(
            "هيكل ستانلس مقاوم للخدوش اليومية، ميناء زجاجياً صلباً، ومقاومة رذاذ ماء للاستعمال العادي. "
            "حزام قابل للتبديل."
        ),
        short="فئة عليا — مظهر رسمي ومتين.",
        warranty_info="ضمان سنتان على الحركة.",
        shipping_info="شحن مؤمّن 2–4 أيام.",
        related=("watch_sport", "watch_band"),
        cheaper_than=("watch_sport",),
        image_seed="horizon-steel",
        product_family="horizon_timepieces",
    ),
    "watch_sport": _p(
        "watch_sport",
        name="Pulse Sport — ساعة رياضية",
        price=449.0,
        category="ساعات",
        description=(
            "وزن خفيف، مقياس نبض بصري، وتتبع نشاط يومي. بطارية تكفي لأيام متعددة."
        ),
        short="نفس فئة الساعات بسعر أقل من الفئة الفاخرة.",
        warranty_info="ضمان 18 شهراً.",
        shipping_info="شحن 2–5 أيام.",
        related=("watch_pro", "watch_band"),
        cheaper_than=(),
        image_seed="pulse-sport",
        product_family="horizon_timepieces",
    ),
    "perfume": _p(
        "perfume",
        name="Amber Oud — عطر مركز",
        price=289.0,
        category="عطور",
        description=(
            "مسار دافئ من العنبر والخشب مع لمسة خفيفة من الورد. ثبات مناسب للمساء."
        ),
        short="خط عطري فاخر نسبياً.",
        warranty_info="لا يُستبدل بعد كسر ختم الاحكام.",
        shipping_info="تغليف حماية — 1–4 أيام عمل.",
        related=("perfume_velvet",),
        cheaper_than=("perfume_velvet",),
        image_seed="amber-oud",
        product_family="studio_scent",
    ),
    "perfume_velvet": _p(
        "perfume_velvet",
        name="Velvet Musk — عطر يومي",
        price=149.0,
        category="عطور",
        description=(
            "مسك ناعم مع حلاوة خفيفة — مناسب للعمل والخروج اليومي دون ثقل."
        ),
        short="بديل أوفر ضمن نفس فئة العطور.",
        warranty_info="لا يُستبدل بعد فتح الاحكام.",
        shipping_info="1–4 أيام عمل.",
        related=("perfume",),
        cheaper_than=(),
        image_seed="velvet-musk",
        product_family="studio_scent",
    ),
    "charger": _p(
        "charger",
        name="Nano 20W — رأس شحن سريع USB‑PD",
        price=75.0,
        category="إلكترونيات",
        description=(
            "رأس مدمج للحقيبة يدعم بروفيل PD حتى 20 واط للهواتف المتوافقة."
        ),
        short="إكسسوار صغير يكمّل السماعات والهاتف.",
        warranty_info="ضمان سنة.",
        shipping_info="شحن 2–4 أيام.",
        related=("earbuds", "hp_pro"),
        cheaper_than=(),
        image_seed="nano-20w",
        product_family="usb_power",
    ),
    "watch_band": _p(
        "watch_band",
        name="Raven — حزام جلد للساعة",
        price=85.0,
        category="إكسسوارات",
        description=(
            "جلد طبيعي مع إبزيم غير بارز. فتحات 20–22 مم لمعظم الوجوه الرياضية والكلاسيكية."
        ),
        short="يُكمل ساعات Horizon و Pulse.",
        warranty_info="ضمان 3 أشهر على الربط.",
        shipping_info="شحن خفيف 1–3 أيام.",
        related=("watch_pro", "watch_sport"),
        cheaper_than=(),
        image_seed="raven-band",
        product_family="horizon_timepieces",
    ),
    "wallet": _p(
        "wallet",
        name="Mira — محفظة سفر نحيفة",
        price=65.0,
        category="إكسسوارات",
        description=(
            "جيوب بطاقات ونقد دون انتفاخ. مناسبة للجيب الأمامي."
        ),
        short="إكسسوار عملي بسعر معقول.",
        warranty_info="6 أشهر على الخياطة.",
        shipping_info="2–4 أيام عمل.",
        related=("hoodie_essentials", "hoodie"),
        cheaper_than=(),
        image_seed="mira-wallet",
        product_family="travel_slg",
    ),
    "hoodie_essentials": _p(
        "hoodie_essentials",
        name="Essentials — هودي قطني خفيف",
        price=89.0,
        category="أزياء",
        normalized_category="الموضة والأزياء",
        description=(
            "قطن مريح بقصة يومية؛ أخف من خط Luxe وبسعر أوضح لنفس فئة الهودي."
        ),
        short="بديل أوفر ضمن نفس فئة الأزياء.",
        warranty_info="ضمان جودة 14 يوماً على العيوب الظاهرة.",
        shipping_info="شحن 2–5 أيام.",
        related=("hoodie", "wallet"),
        cheaper_than=(),
        image_seed="essentials-hoodie",
        product_family="luxe_apparel",
    ),
    "hoodie": _p(
        "hoodie",
        name="Luxe — هودي صوفي",
        price=149.0,
        category="أزياء",
        normalized_category="الموضة والأزياء",
        description=(
            "قطن مريح بقصّة عملية للبرودة الخفيفة. مناسب للعمل الكاجوال."
        ),
        short="فئة أزياء منفصلة عن الإلكترونيات.",
        warranty_info="ضمان جودة 14 يوماً على العيوب الظاهرة.",
        shipping_info="شحن 2–5 أيام.",
        related=("hoodie_essentials", "wallet"),
        cheaper_than=("hoodie_essentials",),
        image_seed="luxe-hoodie",
        product_family="luxe_apparel",
    ),
}


def sandbox_product_js_map(nav_base: str = "/demo/store") -> Dict[str, Any]:
    """خريطة ‎key → حقول السلة/الودجت‎ (نسخة للمتصفح)."""
    nb = (nav_base or "/demo/store").rstrip("/") or "/demo/store"
    out: Dict[str, Any] = {}
    for k in SANDBOX_PRODUCT_ORDER:
        p = SANDBOX_PRODUCTS[k]
        u = product_demo_url(nb, k)
        out[k] = {
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "unit_price": p["unit_price"],
            "category": p["category"],
            "normalized_category": p.get("normalized_category") or (p["category"] or "").strip(),
            "product_family": p.get("product_family", ""),
            "description": p["description"],
            "short": p["short"],
            "warranty_info": p["warranty_info"],
            "shipping_info": p["shipping_info"],
            "url": u,
            "product_url": u,
            "product_num": SANDBOX_PRODUCT_NUM_BY_KEY[k],
            "image": p["image"],
            "available": p["available"],
            "related_keys": list(p["related_keys"]),
            "cheaper_alternative_keys": list(p["cheaper_alternative_keys"]),
        }
    return out


def sandbox_grid_rows(nav_base: str = "/demo/store") -> List[Dict[str, Any]]:
    nb = (nav_base or "/demo/store").rstrip("/") or "/demo/store"
    rows: List[Dict[str, Any]] = []
    for k in SANDBOX_PRODUCT_ORDER:
        p = SANDBOX_PRODUCTS[k]
        rows.append(
            {
                "key": k,
                "num": SANDBOX_PRODUCT_NUM_BY_KEY[k],
                "name": p["name"],
                "category": p["category"],
                "price": p["price"],
                "short": p["short"],
                "image": p["image"],
                "url": product_demo_url(nb, k),
                "available": p.get("available", True),
            }
        )
    return rows


def merchant_catalog_for_intelligence_sync(nav_base: str = "/demo/store") -> Dict[str, Any]:
    """
    شكل ‎product_catalog‎ المتوافق مع ‎normalize_product_catalog‎ — لنسخه في لوحة «العروض الذكية».
    """
    nb = (nav_base or "/demo/store").rstrip("/") or "/demo/store"
    prods: List[Dict[str, Any]] = []
    for k in SANDBOX_PRODUCT_ORDER:
        p = SANDBOX_PRODUCTS[k]
        if not p.get("available", True):
            continue
        row: Dict[str, Any] = {
            "id": p["id"],
            "name": p["name"],
            "price": p["price"],
            "category": p["category"],
            "url": product_demo_url(nb, k),
            "available": True,
        }
        nc = (p.get("normalized_category") or p.get("category") or "").strip()
        if nc:
            row["normalized_category"] = nc[:120]
        fam = (p.get("product_family") or "").strip()
        if fam:
            row["product_family"] = fam[:64]
        prods.append(row)
    return {"version": 1, "products": prods}


def merchant_catalog_json_string(*, indent: int = 2, nav_base: str = "/demo/store") -> str:
    return json.dumps(
        merchant_catalog_for_intelligence_sync(nav_base=nav_base),
        ensure_ascii=False,
        indent=indent,
    )


def demo_template_context_extras(*, nav_base: str = "/demo/store") -> Dict[str, Any]:
    nb = (nav_base or "/demo/store").rstrip("/") or "/demo/store"
    return {
        "demo_catalog_js": sandbox_product_js_map(nav_base=nb),
        "demo_grid_rows": sandbox_grid_rows(nav_base=nb),
        "demo_merchant_catalog_json": merchant_catalog_json_string(nav_base=nb),
        "demo_catalog_nav_base": nb,
    }
