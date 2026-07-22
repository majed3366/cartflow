# -*- coding: utf-8 -*-
"""
Materialize Business Findings — engine run + lifecycle foundation.

This is the ONLY production generation entry for merchant stores.
Home / Decision / Guidance / Knowledge must not call the engine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.business_findings_lifecycle_v1.flag_v1 import (
    business_findings_lifecycle_v1_enabled,
)
from services.business_findings_lifecycle_v1.lifecycle_v1 import advance_state
from services.business_findings_lifecycle_v1.normalize_v1 import (
    normalize_engine_finding_v1,
)
from services.business_findings_lifecycle_v1.persistence_v1 import (
    save_record_fields_v1,
)
from services.business_findings_lifecycle_v1.route_v1 import (
    route_guidance_v1,
    route_knowledge_v1,
    route_operational_truth_v1,
    route_surface_eligible_v1,
)
from services.business_findings_lifecycle_v1.types_v1 import (
    BFL_VERSION_V1,
    LS_DETECTED,
    LS_KNOWLEDGE_ROUTED,
    LS_PERSISTED,
    LS_VALIDATED,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def materialize_business_findings_lifecycle_v1(
    store_slug: str,
    *,
    window_days: int = 14,
    load_db: bool = True,
    demo_fixture: bool = False,
    admit_review_fixtures: bool = False,
    dash_store: Any = None,
    merchant_id: str = "",
) -> dict[str, Any]:
    """
    Detect → Validate → Persist → Knowledge route → OT route → Surface eligible.

    Displayed is set later when a surface consumes the finding.
    """
    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "bfl_version": BFL_VERSION_V1,
        "enabled": business_findings_lifecycle_v1_enabled(),
        "detected": 0,
        "validated": 0,
        "persisted": 0,
        "knowledge_routed": 0,
        "ot_routed": 0,
        "surface_eligible": 0,
        "finding_ids": [],
        "errors": [],
        "stopped_stages": {},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not business_findings_lifecycle_v1_enabled():
        out["errors"].append("bfl_disabled")
        return out

    try:
        from services.business_findings_engine_v1 import run_business_findings_engine_v1
        from services.product_data.product_identity_authenticity_v1 import (
            sanitize_findings_package_for_merchant_v1,
        )
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"import:{type(exc).__name__}")
        return out

    try:
        package = run_business_findings_engine_v1(
            store_slug=slug,
            load_db=bool(load_db) and not demo_fixture,
            demo_fixture=bool(demo_fixture),
            dash_store=dash_store,
            window_days=window_days,
        )
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"engine:{type(exc).__name__}")
        log.warning("bfl materialize engine failed: %s", exc)
        return out

    engine_version = str(package.get("engine_version") or "business_findings_engine_v1")
    raw_findings = [
        f for f in list(package.get("findings") or []) if isinstance(f, dict)
    ]
    out["detected"] = len(raw_findings)

    try:
        package = sanitize_findings_package_for_merchant_v1(
            package,
            admit_review_fixtures=bool(admit_review_fixtures),
        )
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"sanitize:{type(exc).__name__}")
        package = {"findings": []}

    validated = [
        f for f in list(package.get("findings") or []) if isinstance(f, dict)
    ]
    out["validated"] = len(validated)
    as_of = _utc_naive_now()

    for f in validated:
        record = normalize_engine_finding_v1(
            f,
            store_slug=slug,
            merchant_id=merchant_id,
            as_of=as_of,
            engine_version=engine_version,
        )
        ok_v, err_v = advance_state(
            record, LS_VALIDATED, reason="authenticity_sanitize_passed"
        )
        if not ok_v:
            out["errors"].append(f"validate:{record.get('finding_id')}:{err_v}")
            out["stopped_stages"][str(record.get("finding_id"))] = LS_DETECTED
            continue

        ok_p, err_p = advance_state(
            record, LS_PERSISTED, reason="upsert_business_findings"
        )
        if not ok_p:
            out["errors"].append(f"persist_advance:{record.get('finding_id')}:{err_p}")
            continue
        diag = dict(record.get("diagnostics") or {})
        persist = save_record_fields_v1(record)
        if not persist.get("ok"):
            out["errors"].append(
                f"persist:{record.get('finding_id')}:{persist.get('error')}"
            )
            diag["stopped_at"] = LS_VALIDATED
            record["diagnostics"] = diag
            out["stopped_stages"][str(record.get("finding_id"))] = LS_VALIDATED
            continue
        diag["persisted"] = True
        record["diagnostics"] = diag
        out["persisted"] += 1

        # Carry home_eligible / authoritative_surface for surface routing.
        record["home_eligible"] = bool(f.get("home_eligible"))
        record["authoritative_surface"] = str(f.get("authoritative_surface") or "")

        record = route_knowledge_v1(record)
        if record.get("lifecycle_state") == LS_KNOWLEDGE_ROUTED:
            out["knowledge_routed"] += 1
        save_record_fields_v1(record)

        record = route_guidance_v1(record)
        save_record_fields_v1(record)

        record = route_operational_truth_v1(record)
        if (record.get("routing") or {}).get("operational_truth", {}).get("routed"):
            out["ot_routed"] += 1
        save_record_fields_v1(record)

        record = route_surface_eligible_v1(record)
        if (record.get("diagnostics") or {}).get("surface_eligible"):
            out["surface_eligible"] += 1
        save_record_fields_v1(record)

        out["finding_ids"].append(record.get("finding_id"))
        out["stopped_stages"][str(record.get("finding_id"))] = record.get(
            "lifecycle_state"
        )

    fatal = any(
        e.startswith(("engine:", "import:", "bfl_disabled", "store_slug"))
        for e in out["errors"]
    )
    out["ok"] = not fatal
    return out


__all__ = ["materialize_business_findings_lifecycle_v1"]
