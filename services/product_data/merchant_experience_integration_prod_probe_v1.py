# -*- coding: utf-8 -*-
"""MEIF/MEH — production probe GET /dev/merchant-experience."""
from __future__ import annotations

from typing import Any

from services.product_data.merchant_experience_hardening_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_HARDENING_V1,
    merchant_experience_hardening_v1_enabled,
)
from services.product_data.merchant_experience_integration_flag_v1 import (
    ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
    merchant_experience_integration_v1_enabled,
)
from services.product_data.merchant_experience_integration_foundation_v1 import (
    generate_merchant_experience_integration_v1,
)
from services.product_data.merchant_experience_integration_registry_v1 import (
    integration_map_valid_v1,
)
from services.product_data.merchant_experience_integration_types_v1 import (
    MEIF_VERSION_V1,
)

_ALLOWED_STORES = frozenset({"demo"})


def build_merchant_experience_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    map_ok, map_errors = integration_map_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": merchant_experience_integration_v1_enabled(),
        "hardening_enabled": merchant_experience_hardening_v1_enabled(),
        "flag_env": ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1,
        "hardening_flag_env": ENV_MERCHANT_EXPERIENCE_HARDENING_V1,
        "meif_version": MEIF_VERSION_V1,
        "assembly_window": window,
        "page_readiness": {},
        "governed_consumption_pct": 0,
        "legacy_consumption_pct": 0,
        "placeholder_count": 0,
        "duplicate_logic_count": 0,
        "legacy_leakage_count": 0,
        "routing_integrity": False,
        "navigation_integrity": False,
        "trust_warnings": [],
        "integration_failures": [],
        "readiness_score": 0,
        "unresolved_findings": [],
        "capability_gaps": {},
        "hardening_status": "unknown",
        "mev1_high_resolution": {},
        "canonical_fingerprint": "",
        "errors": list(map_errors),
        "registries_valid": bool(map_ok),
        "non_demo_writes": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    report = generate_merchant_experience_integration_v1(slug, assembly_window=window)
    out["as_of"] = report.get("as_of")
    out["canonical_fingerprint"] = report.get("canonical_fingerprint") or ""
    out["errors"].extend(list(report.get("errors") or []))
    audit = report.get("audit") or {}
    hardening = report.get("hardening") or {}
    out["governed_consumption_pct"] = int(audit.get("governed_consumption_pct") or 0)
    out["legacy_consumption_pct"] = int(audit.get("legacy_consumption_pct") or 0)
    out["placeholder_count"] = int(audit.get("placeholder_count") or 0)
    out["duplicate_logic_count"] = int(audit.get("duplicate_logic_count") or 0)
    out["legacy_leakage_count"] = int(
        hardening.get("legacy_leakage_count")
        if hardening.get("legacy_leakage_count") is not None
        else audit.get("legacy_leakage_count")
        or 0
    )
    out["routing_integrity"] = bool(audit.get("routing_integrity"))
    out["navigation_integrity"] = bool(audit.get("navigation_integrity"))
    out["trust_warnings"] = list(audit.get("trust_warnings") or [])
    out["integration_failures"] = list(audit.get("integration_failures") or [])
    out["mev1_high_resolution"] = dict(report.get("mev1_high_resolution") or {})
    out["readiness_score"] = int(hardening.get("readiness_score") or 0)
    out["unresolved_findings"] = list(hardening.get("unresolved_findings") or [])
    out["capability_gaps"] = dict(hardening.get("capability_gaps") or {})
    out["hardening_status"] = str(hardening.get("status") or "absent")
    out["chapter_outcome"] = hardening.get("chapter_outcome")
    out["delta_vs_v2"] = hardening.get("delta_vs_v2")
    out["category_a_resolved"] = list(hardening.get("category_a_resolved") or [])
    pages = report.get("pages") or {}
    out["page_readiness"] = {
        pid: {
            "ready": bool(p.get("ready")),
            "governed_consumption": bool(p.get("governed_consumption")),
            "placeholder_eliminated": bool(p.get("placeholder_eliminated")),
            "trust_labeling": bool(p.get("trust_labeling")),
            "legacy_consumption": bool(p.get("legacy_consumption")),
        }
        for pid, p in pages.items()
    }
    out["navigation"] = report.get("navigation") or {}
    out["operational_state"] = report.get("operational_state") or {}
    out["sample_home"] = (pages.get("home") or {}).get("sections")
    out["sample_home_meta"] = {
        "suppress_setup_theatre": (pages.get("home") or {}).get("suppress_setup_theatre"),
        "chronology_cue": (pages.get("home") or {}).get("chronology_cue"),
        "trust_labeling": (pages.get("home") or {}).get("trust_labeling"),
    }
    out["sample_carts"] = {
        "forbid_please_wait": (pages.get("carts") or {}).get("forbid_please_wait"),
        "durable_cart_count": (pages.get("carts") or {}).get("durable_cart_count"),
        "status_message_ar": (pages.get("carts") or {}).get("status_message_ar"),
        "attention_answered": (pages.get("carts") or {}).get("attention_answered"),
    }

    highs = out["mev1_high_resolution"]
    highs_ok = all(bool(v) for v in highs.values()) if highs else False
    hardening_ok = (
        out["hardening_status"] in {"hardened", "hardened_with_leakage"}
        and out["legacy_leakage_count"] == 0
        and out["readiness_score"] >= 80
    )
    out["ok"] = bool(
        report.get("ok")
        and out["registries_valid"]
        and out["governed_consumption_pct"] == 100
        and out["navigation_integrity"]
        and out["routing_integrity"]
        and highs_ok
        and hardening_ok
        and "store_not_allowlisted" not in out["errors"]
        and not out["integration_failures"]
    )
    return out


__all__ = ["build_merchant_experience_prod_probe_v1"]
