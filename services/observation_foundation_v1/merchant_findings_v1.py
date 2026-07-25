# -*- coding: utf-8 -*-
"""
Observation Reality Validation — merchant findings (entity-bound).

Every finding must reference a real product display name.
If none can be identified: no finding — honest empty state.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.home_executive_summary_v1.compose_v1 import OBS_EMPTY_AR
from services.observation_foundation_v1.admission_bridge_v1 import (
    ADMISSION_BRIDGE_VERSION_V1,
    admit_observation_candidates_v1,
)
from services.observation_foundation_v1.assemble_v1 import assemble_observation_foundation_v1
from services.observation_foundation_v1.flag_v1 import observation_foundation_v1_enabled

ENV_OBSERVATION_REALITY_VALIDATION_V1 = "CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1"
# Lab-only: never default on in production Home.
ENV_ORV_APPROVED_MASS_V1 = "CARTFLOW_ORV_APPROVED_MASS_V1"

_CAPABILITY_ORDER = (
    "high_interest_low_conversion",
    "shipping_stronger_than_price",
    "repeated_return_without_purchase",
    "no_quality_issue_evidence",
)


def observation_reality_validation_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    import os

    env = environ if environ is not None else os.environ
    if not observation_foundation_v1_enabled(environ=env):
        return False
    raw = str(env.get(ENV_OBSERVATION_REALITY_VALIDATION_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _approved_mass_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    import os

    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_ORV_APPROVED_MASS_V1, "0") or "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}


def project_merchant_observation_findings_v1(
    package: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    product_name_resolver: Any = None,
) -> list[dict[str, Any]]:
    """
    Project evidence-backed capabilities into entity-bound merchant findings
    via Observation Admission Bridge V1 (no silent drops).
    """
    bridge = admit_observation_candidates_v1(
        package,
        store_slug=store_slug,
        product_name_resolver=product_name_resolver,
    )
    if isinstance(package, dict):
        package["_admission_bridge_v1"] = bridge
    return list(bridge.get("admitted") or [])


def _assemble_orv_package_v1(
    store_slug: str,
    *,
    signals: Optional[list[Mapping[str, Any]]] = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Assemble durable foundation only — approved mass off unless lab flag."""
    pkg = assemble_observation_foundation_v1(
        store_slug, signals=signals, environ=environ
    )
    findings = project_merchant_observation_findings_v1(pkg, store_slug=store_slug)
    bridge = pkg.get("_admission_bridge_v1") if isinstance(pkg, dict) else None
    if findings or signals is not None or not _approved_mass_enabled(environ=environ):
        pkg["_orv_findings_cache"] = findings
        pkg["_orv_mass_source"] = "durable_or_provided"
        pkg["_orv_admission_bridge"] = bridge
        return pkg

    # Explicit lab flag only
    from services.observation_foundation_v1.orv_approved_mass_v1 import (  # noqa: PLC0415
        approved_orv_validation_signals_v1,
    )

    durable: list[Any] = []
    try:
        from services.observation_foundation_v1.durable_signals_bridge_v1 import (  # noqa: PLC0415
            load_observation_input_signals_v1,
        )

        durable = list(
            load_observation_input_signals_v1(str(store_slug or "").strip()) or []
        )
    except Exception:  # noqa: BLE001
        durable = []
    merged: list[Mapping[str, Any]] = list(durable) + list(
        approved_orv_validation_signals_v1()
    )
    pkg = assemble_observation_foundation_v1(
        store_slug, signals=merged, environ=environ
    )
    findings = project_merchant_observation_findings_v1(pkg, store_slug=store_slug)
    pkg["_orv_findings_cache"] = findings
    pkg["_orv_mass_source"] = "lab_approved_mass"
    pkg["_orv_admission_bridge"] = pkg.get("_admission_bridge_v1")
    return pkg


def build_observation_reality_validation_v1(
    store_slug: str,
    *,
    signals: Optional[list[Mapping[str, Any]]] = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not observation_reality_validation_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": "observation_reality_validation_v1",
            "findings": [],
            "empty_state_ar": OBS_EMPTY_AR,
            "ui": True,
            "temporary": True,
        }

    pkg = _assemble_orv_package_v1(store_slug, signals=signals, environ=environ)
    findings = list(pkg.pop("_orv_findings_cache", None) or [])
    bridge = pkg.pop("_orv_admission_bridge", None) or pkg.pop("_admission_bridge_v1", None)
    if not findings:
        findings = project_merchant_observation_findings_v1(pkg, store_slug=store_slug)
        bridge = pkg.get("_admission_bridge_v1") or bridge
    mass_source = pkg.pop("_orv_mass_source", None)
    required = list(_CAPABILITY_ORDER)
    present = [f["capability_id"] for f in findings]
    bridge = bridge if isinstance(bridge, dict) else {}
    return {
        "ok": True,
        "enabled": True,
        "schema": "observation_reality_validation_v1",
        "store_slug": store_slug,
        "temporary": True,
        "ui": True,
        "product_intelligence": False,
        "findings": findings,
        "count": len(findings),
        "empty_state_ar": OBS_EMPTY_AR if not findings else "",
        "required_capabilities": required,
        "present_capabilities": present,
        "missing_capabilities": [c for c in required if c not in present],
        "acceptance_all_four": len(present) == 4,
        "foundation_counts": pkg.get("counts") or {},
        "mass_source": mass_source,
        "admission_bridge_version": ADMISSION_BRIDGE_VERSION_V1,
        "admission_reconciliation": bridge.get("reconciliation") or {},
        "suppression_registry": bridge.get("suppressed") or [],
        "suppressed_by_reason": bridge.get("suppressed_by_reason") or {},
        "workspace_decisions": bridge.get("workspace_decisions") or [],
        "eyebrow_ar": "معرفة من الملاحظة",
        "title_ar": "ملاحظات المنتجات",
        "lede_ar": "ملاحظات مرتبطة بمنتجات حقيقية فقط.",
    }


def _resolve_observation_store_slug_v1(store_slug: str) -> str:
    """Use the merchant's own store only — never fall back to demo."""
    return str(store_slug or "").strip()


def attach_observation_reality_validation_to_summary_v1(
    summary: dict[str, Any],
    store_slug: str,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    try:
        slug = _resolve_observation_store_slug_v1(str(store_slug or "").strip())
        if not slug:
            summary["observation_reality_validation_v1"] = {
                "ok": True,
                "enabled": True,
                "schema": "observation_reality_validation_v1",
                "store_slug": "",
                "findings": [],
                "count": 0,
                "empty_state_ar": OBS_EMPTY_AR,
                "ui": True,
                "product_intelligence": False,
                "mass_source": "none_empty_store_slug",
            }
            return summary
        pkg = build_observation_reality_validation_v1(slug, environ=environ)
        summary["observation_reality_validation_v1"] = pkg
    except Exception:  # noqa: BLE001
        summary["observation_reality_validation_v1"] = {
            "ok": False,
            "enabled": True,
            "findings": [],
            "empty_state_ar": OBS_EMPTY_AR,
            "error": "attach_failed",
        }
    return summary


__all__ = [
    "ENV_OBSERVATION_REALITY_VALIDATION_V1",
    "ENV_ORV_APPROVED_MASS_V1",
    "OBS_EMPTY_AR",
    "attach_observation_reality_validation_to_summary_v1",
    "build_observation_reality_validation_v1",
    "observation_reality_validation_v1_enabled",
    "project_merchant_observation_findings_v1",
]
