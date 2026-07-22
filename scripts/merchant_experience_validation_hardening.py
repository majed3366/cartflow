# -*- coding: utf-8 -*-
"""
Merchant Experience Reality Validation — Hardening run (MEH V1).

Compares V1 (28) / V2 (72) / Hardening readiness using MEIF+MEH packages.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "architecture" / "merchant_experience_validation_hardening"
V1 = 28
V2 = 72


def _http_json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=180) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body) if body else {"http_error": exc.code}
        except json.JSONDecodeError:
            return {"http_error": exc.code}
    except URLError as exc:
        return {"error": str(exc)}


def _bootstrap() -> None:
    db_path = Path(tempfile.gettempdir()) / "cartflow_meh_v1.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass
    os.environ["DATABASE_URL"] = "sqlite:///" + str(db_path).replace("\\", "/")
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_EXPERIENCE_HARDENING_V1", "1")
    os.environ.setdefault("CARTFLOW_SURFACE_COMPOSITION_V1", "1")
    os.environ.setdefault("CARTFLOW_MERCHANT_PRESENTATION_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_GUIDANCE_ROUTING_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1", "1")
    os.environ.setdefault("CARTFLOW_KNOWLEDGE_FOUNDATION_V1", "1")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prod-only", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    prod = _http_json(
        "https://smartreplyai.net/dev/merchant-experience?store=demo&assembly_window=d7"
    )
    evidence: dict = {
        "lab": "merchant_experience_validation_hardening",
        "compared_to": {"v1": V1, "v2": V2},
        "production_probe": prod,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if args.prod_only:
        score = int(prod.get("readiness_score") or 0)
        evidence["score"] = {
            "readiness_score": score,
            "v1": V1,
            "v2": V2,
            "delta_vs_v2": score - V2,
            "chapter_outcome": prod.get("chapter_outcome"),
            "unresolved_findings": prod.get("unresolved_findings"),
            "legacy_leakage_count": prod.get("legacy_leakage_count"),
            "hardening_status": prod.get("hardening_status"),
            "materially_improved_vs_v2": score >= V2 + 8,
        }
    else:
        _bootstrap()
        import models  # noqa: F401
        from extensions import db, init_database
        from models import AbandonedCart, Store

        init_database()
        db.create_all()
        if db.session.query(Store).filter_by(zid_store_id="demo").first() is None:
            db.session.add(Store(zid_store_id="demo", is_active=True))
            db.session.commit()
        store = db.session.query(Store).filter_by(zid_store_id="demo").first()
        if store and int(
            db.session.query(AbandonedCart)
            .filter_by(store_id=int(store.id))
            .count()
            or 0
        ) == 0:
            for i in range(5):
                db.session.add(
                    AbandonedCart(
                        store_id=int(store.id),
                        zid_cart_id=f"meh-seed-{i}",
                        customer_phone="966500000000",
                        status="waiting",
                    )
                )
            db.session.commit()
        from services.product_data.merchant_experience_integration_foundation_v1 import (
            generate_merchant_experience_integration_v1,
        )

        report = generate_merchant_experience_integration_v1("demo")
        hard = report.get("hardening") or {}
        evidence["meif_hardening"] = {
            "ok": report.get("ok"),
            "hardening": hard,
            "ops": report.get("operational_state"),
        }
        evidence["score"] = {
            "readiness_score": hard.get("readiness_score"),
            "v1": V1,
            "v2": V2,
            "delta_vs_v2": hard.get("delta_vs_v2"),
            "chapter_outcome": hard.get("chapter_outcome"),
            "unresolved_findings": hard.get("unresolved_findings"),
            "legacy_leakage_count": hard.get("legacy_leakage_count"),
            "materially_improved_vs_v2": bool(
                (hard.get("readiness") or {}).get("materially_improved_vs_v2")
            ),
            "dimensions": (hard.get("readiness") or {}).get("dimensions"),
        }

    path = OUT / "meh_evidence.json"
    path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    score = evidence["score"]
    md_lines = [
        "# Merchant Experience Validation — Hardening (MEH V1)",
        "",
        f"**Date (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "**Status:** COMPLETE",
        "",
        "## Comparison",
        "",
        f"| Run | Readiness |",
        f"|-----|----------:|",
        f"| V1 | {V1} |",
        f"| V2 | {V2} |",
        f"| Hardening | **{score.get('readiness_score')}** |",
        f"| Delta vs V2 | **{score.get('delta_vs_v2')}** |",
        "",
        f"- Chapter outcome: **{score.get('chapter_outcome')}**",
        f"- Materially improved vs V2: **{score.get('materially_improved_vs_v2')}**",
        f"- Legacy leakage: **{score.get('legacy_leakage_count')}**",
        "",
        "## Unresolved (Capability Gaps only)",
        "",
        "```json",
        json.dumps(score.get("unresolved_findings") or [], indent=2, default=str),
        "```",
        "",
        "## STOP",
        "",
        "Remaining issues are Capability Gaps — see",
        "`docs/architecture/merchant_experience_capability_gap_register.md`.",
        "",
    ]
    md = "\n".join(md_lines)
    (OUT / "MERCHANT_EXPERIENCE_VALIDATION_HARDENING.md").write_text(md, encoding="utf-8")
    (
        ROOT / "docs" / "product" / "MERCHANT_EXPERIENCE_VALIDATION_HARDENING.md"
    ).write_text(md, encoding="utf-8")
    print(json.dumps(evidence["score"], indent=2, default=str))
    return 0 if score.get("materially_improved_vs_v2") else 1


if __name__ == "__main__":
    sys.exit(main())
