# -*- coding: utf-8 -*-
"""
PI-F6 production verification helper — Product Identity Foundation V1.

Usage (from app host with DB configured):
  python scripts/_verify_product_identity_foundation_v1.py --store <slug>

Exits 0 when authenticity gates pass for the store sample.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default="demo")
    args = parser.parse_args()
    slug = (args.store or "").strip()

    from services.business_findings_engine_v1 import run_business_findings_engine_v1
    from services.product_data.product_identity_authenticity_v1 import (
        is_fixture_loaded_from,
        sanitize_findings_package_for_merchant_v1,
        text_has_forbidden_product_placeholder,
    )

    report: dict = {"store_slug": slug, "checks": {}, "ok": True}

    pkg = run_business_findings_engine_v1(
        store_slug=slug, load_db=True, demo_fixture=False, window_days=14
    )
    loaded = (pkg.get("evidence") or {}).get("loaded_from")
    report["checks"]["evidence_loaded_from"] = loaded
    report["checks"]["not_fixture"] = not is_fixture_loaded_from(loaded)
    if is_fixture_loaded_from(loaded):
        report["ok"] = False

    safe = sanitize_findings_package_for_merchant_v1(pkg, admit_review_fixtures=False)
    blob = json.dumps(safe, ensure_ascii=False)
    forbidden = text_has_forbidden_product_placeholder(blob)
    report["checks"]["no_placeholder_in_merchant_package"] = not forbidden
    if forbidden:
        report["ok"] = False

    try:
        from database import SessionLocal
        from models import CartLineSnapshot
        from sqlalchemy import func

        db = SessionLocal()
        try:
            n = (
                db.query(func.count(CartLineSnapshot.id))
                .filter(CartLineSnapshot.store_slug == slug)
                .scalar()
            )
            sample = (
                db.query(CartLineSnapshot.name, CartLineSnapshot.product_id)
                .filter(CartLineSnapshot.store_slug == slug)
                .order_by(CartLineSnapshot.id.desc())
                .limit(5)
                .all()
            )
            report["checks"]["snapshot_count"] = int(n or 0)
            report["checks"]["snapshot_sample"] = [
                {"name": r[0], "product_id": r[1]} for r in sample
            ]
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        report["checks"]["db_sample_error"] = type(exc).__name__

    out = _ROOT / "PRODUCT_IDENTITY_FOUNDATION_PROD_VERIFY_V1.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
