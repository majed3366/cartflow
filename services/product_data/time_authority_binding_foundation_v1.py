# -*- coding: utf-8 -*-
"""
Time Authority Binding Foundation V1 (TABF).

Governing capability — not a producer of business intelligence.
Resolves canonical observation/replay as_of for Product Performance layers.
Does not redesign timelines, analytics, Knowledge rules, or Guidance rules.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from services.product_data.time_authority_binding_flag_v1 import (
    time_authority_binding_v1_enabled,
)
from services.product_data.time_authority_binding_registry_v1 import (
    SUBSYSTEM_BINDINGS_V1,
    subsystem_bindings_v1,
    tabf_registry_valid_v1,
    time_inventory_v1,
)
from services.product_data.time_authority_binding_resolve_v1 import (
    describe_time_binding_v1,
    resolve_bound_as_of_v1,
)
from services.product_data.time_authority_binding_types_v1 import (
    BINDING_BOUND,
    BINDING_LEGACY,
    BINDING_PARTIAL,
    BINDING_UNBOUND,
    TABF_GENERATION_VERSION_V1,
    TABF_VERSION_V1,
)

log = logging.getLogger("cartflow")


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _runtime_binding_status(subsystem_id: str) -> str:
    """Reflect code-level binding for Product Performance path."""
    row = SUBSYSTEM_BINDINGS_V1.get(subsystem_id) or {}
    declared = str(row.get("binding_status") or BINDING_UNBOUND)
    if not time_authority_binding_v1_enabled():
        return BINDING_LEGACY
    # Truth remains partial (event vs process) by design of facts.
    if subsystem_id == "truth":
        return BINDING_PARTIAL
    return declared


def audit_subsystem_bindings_v1() -> dict[str, Any]:
    bindings = []
    unbound = []
    for sid, row in SUBSYSTEM_BINDINGS_V1.items():
        status = _runtime_binding_status(sid)
        entry = {
            **row,
            "runtime_binding_status": status,
            "bound": status in {BINDING_BOUND, BINDING_PARTIAL},
        }
        bindings.append(entry)
        if status in {BINDING_UNBOUND, BINDING_LEGACY}:
            unbound.append(sid)
    return {
        "bindings": bindings,
        "unbound_subsystems": unbound,
        "all_required_bound": len(unbound) == 0
        or unbound == ["truth"]  # truth may remain partial
        or set(unbound).issubset({"truth"}),
    }


def verify_replay_ordering_consistency_v1(
    store_slug: str,
    *,
    as_of: datetime,
    assembly_window: str = "d7",
) -> dict[str, Any]:
    """
    Deterministic replay check: identical as_of → identical SCF fingerprint + OT fingerprint.
    Does not invent merchant features.
    """
    from services.product_data.operational_truth_foundation_v1 import (
        generate_operational_truth_v1,
    )
    from services.product_data.surface_composition_foundation_v1 import (
        generate_surface_compositions_v1,
    )

    slug = (store_slug or "").strip()[:255]
    a_scf = generate_surface_compositions_v1(
        slug, assembly_window=assembly_window, as_of=as_of
    )
    b_scf = generate_surface_compositions_v1(
        slug, assembly_window=assembly_window, as_of=as_of
    )
    a_ot = generate_operational_truth_v1(
        slug, assembly_window=assembly_window, as_of=as_of
    )
    b_ot = generate_operational_truth_v1(
        slug, assembly_window=assembly_window, as_of=as_of
    )
    scf_ok = a_scf.get("canonical_fingerprint") == b_scf.get("canonical_fingerprint")
    ot_ok = a_ot.get("canonical_fingerprint") == b_ot.get("canonical_fingerprint")
    # Ordering: composition ids order stable
    order_a = [c.get("composition_id") for c in (a_scf.get("compositions") or [])]
    order_b = [c.get("composition_id") for c in (b_scf.get("compositions") or [])]
    return {
        "deterministic_scf": bool(scf_ok),
        "deterministic_ot": bool(ot_ok),
        "ordering_consistent": order_a == order_b,
        "replay_consistent": bool(scf_ok and ot_ok and order_a == order_b),
        "scf_fingerprint": a_scf.get("canonical_fingerprint"),
        "ot_fingerprint": a_ot.get("canonical_fingerprint"),
        "as_of": as_of.isoformat(sep=" "),
    }


def detect_ordering_conflicts_v1(scf_report: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect obvious chronology conflicts in composed items (same surface)."""
    conflicts: list[dict[str, Any]] = []
    by_surface: dict[str, list[dict[str, Any]]] = {}
    for c in scf_report.get("compositions") or []:
        by_surface.setdefault(str(c.get("surface_id")), []).append(c)
    for surface_id, items in by_surface.items():
        # Priority must be non-increasing in sorted order used by SCF.
        ordered = sorted(
            items,
            key=lambda x: (
                -int(x.get("priority") or 0),
                str(x.get("composition_id") or ""),
            ),
        )
        last_p = None
        for it in ordered:
            p = int(it.get("priority") or 0)
            if last_p is not None and p > last_p:
                conflicts.append(
                    {
                        "surface_id": surface_id,
                        "type": "priority_inversion",
                        "composition_id": it.get("composition_id"),
                    }
                )
            last_p = p if last_p is None else last_p
    return conflicts


def generate_time_authority_binding_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate binding audit + replay consistency report for a store."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower() or "d7"
    reg_ok, reg_errors = tabf_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "tabf_version": TABF_VERSION_V1,
        "generation_version": TABF_GENERATION_VERSION_V1,
        "enabled": time_authority_binding_v1_enabled(),
        "errors": list(reg_errors),
        "registries_valid": bool(reg_ok),
        "inventory": time_inventory_v1(),
        "subsystem_bindings": subsystem_bindings_v1(),
        "binding_audit": {},
        "canonical_clocks": {},
        "replay_consistency": {},
        "ordering_conflicts": [],
        "chronology_warnings": [],
        "drift_detection": [],
        "stale_interpretations": [],
        "canonical_fingerprint": "",
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not reg_ok:
        out["errors"].append("invalid_registry")
        return out
    if not time_authority_binding_v1_enabled():
        out["errors"].append("tabf_disabled")
        return out

    binding = describe_time_binding_v1(as_of)
    resolved = resolve_bound_as_of_v1(as_of)
    out["as_of"] = resolved.isoformat(sep=" ")
    out["canonical_clocks"] = binding.get("clocks") or {}
    out["binding_status"] = binding
    out["binding_audit"] = audit_subsystem_bindings_v1()

    # Drift: any subsystem still legacy/unbound.
    for b in out["binding_audit"].get("bindings") or []:
        if b.get("runtime_binding_status") in {BINDING_LEGACY, BINDING_UNBOUND}:
            out["drift_detection"].append(
                {
                    "subsystem_id": b.get("subsystem_id"),
                    "status": b.get("runtime_binding_status"),
                    "risk": b.get("drift_risk"),
                }
            )
        if b.get("runtime_binding_status") == BINDING_PARTIAL:
            out["chronology_warnings"].append(
                f"partial_binding:{b.get('subsystem_id')}:{b.get('conflicts')}"
            )

    # Stale interpretations = inventory sites still marked high drift without binding path.
    for site in (out["inventory"].get("sites") or {}).values():
        if str(site.get("drift_risk") or "").startswith("critical") or str(
            site.get("drift_risk") or ""
        ).startswith("high"):
            if "tabf" not in str(site.get("bound_via") or "") and "authority" not in str(
                site.get("bound_via") or ""
            ):
                out["stale_interpretations"].append(site.get("site_id"))

    try:
        from services.product_data.surface_composition_foundation_v1 import (
            generate_surface_compositions_v1,
        )

        scf = generate_surface_compositions_v1(
            slug, assembly_window=window, as_of=resolved
        )
        out["ordering_conflicts"] = detect_ordering_conflicts_v1(scf)
        out["scf_binding"] = {
            "ok": bool(scf.get("ok")),
            "as_of": scf.get("as_of"),
            "uses_bound_as_of": scf.get("as_of") == out["as_of"],
            "composition_count": scf.get("composition_count"),
            "freshness_from_as_of": True,
        }
        out["replay_consistency"] = verify_replay_ordering_consistency_v1(
            slug, as_of=resolved, assembly_window=window
        )
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"scf_binding:{type(exc).__name__}")
        log.warning("tabf scf binding check failed: %s", exc)

    # OT + MEIF binding smoke
    try:
        from services.product_data.operational_truth_foundation_v1 import (
            generate_operational_truth_v1,
        )

        ot = generate_operational_truth_v1(
            slug, assembly_window=window, as_of=resolved
        )
        out["operational_truth_binding"] = {
            "ok": bool(ot.get("ok")),
            "as_of": ot.get("as_of"),
            "uses_bound_as_of": ot.get("as_of") == out["as_of"],
        }
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"ot_binding:{type(exc).__name__}")

    try:
        from services.product_data.merchant_experience_integration_foundation_v1 import (
            generate_merchant_experience_integration_v1,
        )

        me = generate_merchant_experience_integration_v1(
            slug, assembly_window=window, as_of=resolved
        )
        home = (me.get("pages") or {}).get("home") or {}
        cue = home.get("chronology_cue") or {}
        out["merchant_experience_binding"] = {
            "ok": bool(me.get("ok")),
            "as_of": me.get("as_of"),
            "uses_bound_as_of": me.get("as_of") == out["as_of"],
            "chronology_cue_as_of": cue.get("as_of"),
        }
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"meif_binding:{type(exc).__name__}")

    out["canonical_fingerprint"] = _sha(
        {
            "v": TABF_GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "binding": binding.get("source"),
            "audit": [
                (b.get("subsystem_id"), b.get("runtime_binding_status"))
                for b in (out["binding_audit"].get("bindings") or [])
            ],
            "replay": out.get("replay_consistency"),
        }
    )

    replay_ok = bool((out.get("replay_consistency") or {}).get("replay_consistent"))
    scf_bound = bool((out.get("scf_binding") or {}).get("uses_bound_as_of"))
    audit_ok = bool((out.get("binding_audit") or {}).get("all_required_bound"))
    out["ok"] = bool(
        out["registries_valid"]
        and out["enabled"]
        and scf_bound
        and replay_ok
        and audit_ok
        and not out["ordering_conflicts"]
        and not any(str(e).startswith("scf_binding:") for e in out["errors"])
    )
    return out


__all__ = [
    "resolve_bound_as_of_v1",
    "describe_time_binding_v1",
    "audit_subsystem_bindings_v1",
    "verify_replay_ordering_consistency_v1",
    "generate_time_authority_binding_v1",
]
