# -*- coding: utf-8 -*-
"""Normalize operational truth + bound findings as composition inputs."""
from __future__ import annotations

from typing import Any, Mapping


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def counters_from_summary_payload_v1(
    summary: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
) -> dict[str, Any] | None:
    """
    Prefer light counters already on Home summary — avoid second DB scan.
    """
    if not isinstance(summary, Mapping):
        return None
    store = summary.get("merchant_store_cart_counts")
    if not isinstance(store, Mapping):
        return None
    if "no_phone_total" not in store and "waiting_total" not in store:
        return None
    slug = _norm(store_slug) or _norm(summary.get("store_slug"))
    return {
        "store_slug": slug,
        "no_phone_total": _as_int(store.get("no_phone_total")),
        "waiting_total": _as_int(store.get("waiting_total")),
        "active_total": _as_int(store.get("active_total")),
        "engaged_total": _as_int(store.get("engaged_total")),
        "available": True,
        "source_truth_types": ["merchant_store_cart_counts", "summary_payload"],
    }


def load_store_counter_inputs_v1(store_slug: str) -> dict[str, Any]:
    slug = _norm(store_slug)
    out: dict[str, Any] = {
        "store_slug": slug,
        "no_phone_total": 0,
        "waiting_total": 0,
        "active_total": 0,
        "engaged_total": 0,
        "available": False,
        "source_truth_types": [],
    }
    if not slug:
        return out
    try:
        from services.dashboard_store_context import (  # noqa: PLC0415
            dashboard_canonical_store_row,
        )
        from services.dashboard_counter_totals_v1 import (  # noqa: PLC0415
            build_merchant_cart_counter_totals,
        )

        store_row = dashboard_canonical_store_row(slug)
        if store_row is None:
            return out
        payload = build_merchant_cart_counter_totals(store_row)
        counts = payload.counts.to_counts_dict()
        out.update(
            {
                "no_phone_total": _as_int(counts.get("no_phone_total")),
                "waiting_total": _as_int(counts.get("waiting_total")),
                "active_total": _as_int(counts.get("active_total")),
                "engaged_total": _as_int(counts.get("engaged_total")),
                "available": True,
                "source_truth_types": ["merchant_store_cart_counts"],
            }
        )
    except Exception:  # noqa: BLE001
        pass
    return out


def load_bound_finding_inputs_v1(store_slug: str) -> list[dict[str, Any]]:
    slug = _norm(store_slug)
    if not slug:
        return []
    try:
        from services.merchant_experience_business_findings_binding_v1 import (  # noqa: PLC0415
            PAGE_DECISION,
            PAGE_HOME,
            load_bound_findings_v1,
        )
    except Exception:  # noqa: BLE001
        return []

    try:
        bound = load_bound_findings_v1(slug, mark_displayed=False)
    except Exception:  # noqa: BLE001
        return []

    by_surface = bound.get("by_surface") if isinstance(bound, Mapping) else {}
    if not isinstance(by_surface, Mapping):
        by_surface = {}
    pool = list(by_surface.get(PAGE_DECISION) or [])
    if not pool:
        pool = list(bound.get("findings") or [])
    if not pool:
        pool = list(by_surface.get(PAGE_HOME) or [])

    out: list[dict[str, Any]] = []
    for c in pool:
        if isinstance(c, Mapping):
            out.append(dict(c))
    return out


def extract_product_identity_v1(contract: Mapping[str, Any]) -> tuple[str, str]:
    """Return (product_id, product_name_ar). Empty id means unidentified."""
    subject = contract.get("subject") if isinstance(contract.get("subject"), Mapping) else {}
    sid = _norm(
        contract.get("product_id")
        or contract.get("entity_id")
        or contract.get("subject_id")
        or subject.get("id")
    )
    name = _norm(
        contract.get("product_name_ar")
        or contract.get("product_name")
        or contract.get("subject_label_ar")
        or subject.get("name_ar")
    )
    return sid, name


__all__ = [
    "counters_from_summary_payload_v1",
    "extract_product_identity_v1",
    "load_bound_finding_inputs_v1",
    "load_store_counter_inputs_v1",
]
