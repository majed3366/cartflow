# -*- coding: utf-8 -*-
"""
Compose Evidence Gaps from insufficient / conflicting diagnostic contracts.

Off-path only. Never called from Home finalize.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.contract_v1 import (
    DIAGNOSIS_STATUS_CONFLICTING,
    DIAGNOSIS_STATUS_INSUFFICIENT,
)
from services.evidence_expansion_v1.contract_v1 import (
    EVIDENCE_EXPANSION_VERSION_V1,
    GAP_STATUS_OPEN,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    empty_evidence_gap_v1,
    validate_evidence_gap_v1,
)
from services.evidence_expansion_v1.observable_registry_v1 import (
    observables_for_family_v1,
)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gap_id(store_slug: str, family: str, diagnostic_id: str) -> str:
    raw = f"{store_slug}|{family}|{diagnostic_id}|{EVIDENCE_EXPANSION_VERSION_V1}"
    return "eg_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _available_from_contract(contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    available: list[dict[str, Any]] = []
    for ref in list(contract.get("observation_refs") or [])[:20]:
        available.append({"kind": "observation_ref", "ref": str(ref)})
    for item in list(contract.get("supporting_evidence") or [])[:12]:
        if isinstance(item, Mapping):
            available.append(
                {
                    "kind": "supporting_score",
                    "cause_key": item.get("cause_key"),
                    "support_n": item.get("support_n"),
                }
            )
    # Stage-level presence
    if contract.get("observation_ar"):
        available.append(
            {
                "kind": "observation_statement",
                "text_ar": str(contract.get("observation_ar") or "")[:240],
            }
        )
    return available


def _competing_causes(contract: Mapping[str, Any]) -> list[str]:
    causes: list[str] = []
    for row in list(contract.get("candidate_causes") or []):
        if not isinstance(row, Mapping):
            continue
        key = str(row.get("cause_key") or "").strip()
        if key and key != "insufficient_evidence":
            causes.append(key)
    # Preserve order, unique
    seen: set[str] = set()
    out: list[str] = []
    for c in causes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    for c in list(contract.get("tied_causes") or []):
        k = str(c or "").strip()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _priority_for(contract: Mapping[str, Any], missing_n: int) -> str:
    status = str(contract.get("diagnosis_status") or "")
    if status == DIAGNOSIS_STATUS_CONFLICTING:
        return PRIORITY_HIGH
    if missing_n >= 4:
        return PRIORITY_HIGH
    return PRIORITY_MEDIUM


def should_open_evidence_gap_v1(contract: Mapping[str, Any] | None) -> bool:
    if not isinstance(contract, Mapping):
        return False
    status = str(contract.get("diagnosis_status") or "")
    return status in {DIAGNOSIS_STATUS_INSUFFICIENT, DIAGNOSIS_STATUS_CONFLICTING}


def compose_evidence_gap_from_diagnostic_v1(
    contract: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Build one Evidence Gap from an insufficient/conflicting diagnostic contract."""
    if not should_open_evidence_gap_v1(contract):
        return None
    family = str(contract.get("diagnostic_family") or "").strip()
    slug = str(contract.get("store_slug") or "").strip()
    dx_id = str(contract.get("diagnostic_id") or "").strip()
    if not (family and slug):
        return None

    future = observables_for_family_v1(family)
    if not future:
        return None

    missing = [
        {
            "observable_key": o["observable_key"],
            "description": o["description"],
            "separates_causes": o["separates_causes"],
            "collected": False,
        }
        for o in future
    ]
    gap = empty_evidence_gap_v1(
        gap_id=_gap_id(slug, family, dx_id or family),
        store_slug=slug,
        diagnostic_family=family,
        diagnostic_id=dx_id,
    )
    gap.update(
        {
            "diagnosis_status": str(contract.get("diagnosis_status") or ""),
            "competing_causes": _competing_causes(contract),
            "evidence_available": _available_from_contract(contract),
            "evidence_missing": missing,
            "possible_future_observables": [
                o["observable_key"] for o in future
            ],
            "priority": _priority_for(contract, len(missing)),
            "gap_status": GAP_STATUS_OPEN,
            # Governance copy only — truncate; never store phones/emails/PII blobs.
            "observation_ar": str(contract.get("observation_ar") or "")[:240],
            "subject_type": str(contract.get("subject_type") or "")[:64],
            "subject_id": str(contract.get("subject_id") or "")[:128],
            "generated_at": _utc_iso(),
            "merchant_safe": False,
            "internal_only": True,
            "reopen_reason": "",
        }
    )
    ok, errors = validate_evidence_gap_v1(gap)
    gap["contract_ok"] = ok
    gap["contract_errors"] = errors
    return gap if ok else gap


__all__ = [
    "compose_evidence_gap_from_diagnostic_v1",
    "should_open_evidence_gap_v1",
]
