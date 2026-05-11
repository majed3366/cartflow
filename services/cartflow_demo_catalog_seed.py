# -*- coding: utf-8 -*-
"""
يملأ ‎cf_product_catalog_json‎ لمتاجر التجربة ‎demo / demo2‎ عند الفراغ حتى تعمل طبقة ذكاء المنتج في الإنتاج.
لا يستبدل كتالوجاً غير فارغ — لتجنّب مسح إعدادات التاجر.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("cartflow")


def demo_store_catalog_needs_seed(cf_product_catalog_json: Any) -> bool:
    if not isinstance(cf_product_catalog_json, str) or not cf_product_catalog_json.strip():
        return True
    try:
        data = json.loads(cf_product_catalog_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    prods = data.get("products")
    return not isinstance(prods, list) or len(prods) == 0


def seed_demo_store_product_catalog_if_empty() -> int:
    """
    يحدّث صفوف ‎Store‎ ذات ‎zid_store_id ∈ {demo, demo2}‎ فقط.
    يعيد عدد الصفوف التي تمّ تحديثها.
    """
    from extensions import db
    from models import Store
    from services.demo_sandbox_catalog import merchant_catalog_json_string

    updated = 0
    try:
        db.create_all()
        rows = (
            db.session.query(Store)
            .filter(Store.zid_store_id.in_(("demo", "demo2")))
            .all()
        )
        for st in rows:
            if not demo_store_catalog_needs_seed(getattr(st, "cf_product_catalog_json", None)):
                continue
            slug = (st.zid_store_id or "").strip()
            nav = "/demo/store2" if slug == "demo2" else "/demo/store"
            st.cf_product_catalog_json = merchant_catalog_json_string(nav_base=nav)
            updated += 1
            log.info(
                "[DEMO CATALOG SEED] zid_store_id=%s store_pk=%s json_len=%s",
                slug,
                getattr(st, "id", None),
                len(st.cf_product_catalog_json or ""),
            )
        if updated:
            db.session.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("demo catalog seed failed: %s", exc, exc_info=True)
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return 0
    return updated
