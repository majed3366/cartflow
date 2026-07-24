# -*- coding: utf-8 -*-
"""
Observation Foundation V1 — assemble canonical observations + correlations.

Pure consumer of Product Signal Collection (+ derived repeats).
No UI. No Home. No findings. No AI.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping, Optional

from services.observation_foundation_v1.catalog_v1 import (
    FOUNDATION_VERSION,
    OBS_CART_ADD,
    OBS_HESITATION_REASON,
    OBS_PURCHASE,
    OBS_REPEAT_PURCHASE,
    OBS_REPEAT_VISIT,
    OBS_RETURN_TO_STORE,
    SIGNAL_TO_OBSERVATION_V1,
    observation_catalog_dict_v1,
)
from services.observation_foundation_v1.correlation_v1 import (
    CORR_ABSENT_REASON,
    CORR_BEHAVIOR_REASON,
    CORR_PRODUCT_CUSTOMER_BEHAVIOR,
    CORR_PRODUCT_INTEREST_CONVERSION,
    CORR_REASON_RETURN,
    CORR_REASON_STRENGTH,
    CORR_REPEAT_RETURN_NO_PURCHASE,
    CORR_RETURN_PURCHASE,
    STATEMENT_CAPABILITIES_V1,
    correlation_model_dict_v1,
)
from services.observation_foundation_v1.flag_v1 import observation_foundation_v1_enabled


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _product_key(signal: Mapping[str, Any]) -> str:
    return (
        _norm(signal.get("product_key"))
        or _norm(signal.get("stable_identity_key"))
        or _norm(signal.get("canonical_product_id"))
        or _norm(signal.get("sku"))
        or _norm(signal.get("product_id"))
        or ""
    )


def _customer_key(signal: Mapping[str, Any]) -> str:
    return (
        _norm(signal.get("customer_key"))
        or _norm(signal.get("customer_id"))
        or _norm(signal.get("phone_hash"))
        or _norm(signal.get("recovery_key"))
        or _norm(signal.get("session_id"))
        or ""
    )


def _reason_token(signal: Mapping[str, Any]) -> str:
    raw = (
        _norm(signal.get("reason_code"))
        or _norm(signal.get("hesitation_reason"))
        or _norm(signal.get("reason"))
        or _norm((signal.get("payload") or {}).get("reason") if isinstance(signal.get("payload"), Mapping) else "")
        or _norm(signal.get("evidence_ref_id"))
    )
    return raw.lower()


def observations_from_signals_v1(
    signals: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Map durable product signals → canonical observations (+ derived repeats)."""
    out: list[dict[str, Any]] = []
    returns_by_customer: dict[str, int] = defaultdict(int)
    purchases_by_customer: dict[str, int] = defaultdict(int)

    for sig in signals:
        if not isinstance(sig, Mapping):
            continue
        stype = _norm(sig.get("signal_type"))
        otype = SIGNAL_TO_OBSERVATION_V1.get(stype)
        if not otype:
            continue
        pk = _product_key(sig)
        ck = _customer_key(sig)
        obs = {
            "schema": FOUNDATION_VERSION,
            "observation_type": otype,
            "product_key": pk,
            "customer_key": ck,
            "session_id": _norm(sig.get("session_id")),
            "observed_at": sig.get("observed_at"),
            "source_signal_type": stype,
            "evidence_ref_type": _norm(sig.get("evidence_ref_type")),
            "evidence_ref_id": _norm(sig.get("evidence_ref_id")),
            "reason_token": _reason_token(sig) if otype == OBS_HESITATION_REASON else "",
            "derived": False,
        }
        out.append(obs)
        if otype == OBS_RETURN_TO_STORE and ck:
            returns_by_customer[ck] += 1
        if otype == OBS_PURCHASE and ck:
            purchases_by_customer[ck] += 1

    for ck, n in returns_by_customer.items():
        if n >= 2:
            out.append(
                {
                    "schema": FOUNDATION_VERSION,
                    "observation_type": OBS_REPEAT_VISIT,
                    "product_key": "",
                    "customer_key": ck,
                    "session_id": "",
                    "observed_at": None,
                    "source_signal_type": "derived:return_count",
                    "evidence_ref_type": "derived",
                    "evidence_ref_id": f"returns:{n}",
                    "reason_token": "",
                    "derived": True,
                    "count": n,
                }
            )
    for ck, n in purchases_by_customer.items():
        if n >= 2:
            out.append(
                {
                    "schema": FOUNDATION_VERSION,
                    "observation_type": OBS_REPEAT_PURCHASE,
                    "product_key": "",
                    "customer_key": ck,
                    "session_id": "",
                    "observed_at": None,
                    "source_signal_type": "derived:purchase_count",
                    "evidence_ref_type": "derived",
                    "evidence_ref_id": f"purchases:{n}",
                    "reason_token": "",
                    "derived": True,
                    "count": n,
                }
            )
    return out


def correlations_from_observations_v1(
    observations: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit Product→Behavior→Reason→Return→Purchase correlations."""
    by_product: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for obs in observations:
        if not isinstance(obs, Mapping):
            continue
        pk = _norm(obs.get("product_key"))
        if pk:
            by_product[pk].append(obs)

    correlations: list[dict[str, Any]] = []

    for pk, items in by_product.items():
        types = {_norm(o.get("observation_type")) for o in items}
        reasons = [
            _norm(o.get("reason_token"))
            for o in items
            if _norm(o.get("observation_type")) == OBS_HESITATION_REASON
            and _norm(o.get("reason_token"))
        ]
        reason_counts = Counter(reasons)
        adds = sum(1 for o in items if o.get("observation_type") == OBS_CART_ADD)
        purchases = sum(1 for o in items if o.get("observation_type") == OBS_PURCHASE)
        returns = sum(
            1 for o in items if o.get("observation_type") == OBS_RETURN_TO_STORE
        )
        evidence_refs = [
            {
                "observation_type": o.get("observation_type"),
                "evidence_ref_type": o.get("evidence_ref_type"),
                "evidence_ref_id": o.get("evidence_ref_id"),
            }
            for o in items
            if o.get("evidence_ref_id")
        ]

        # Product → customer behavior
        if OBS_CART_ADD in types or OBS_RETURN_TO_STORE in types:
            correlations.append(
                {
                    "correlation_kind": CORR_PRODUCT_CUSTOMER_BEHAVIOR,
                    "product_key": pk,
                    "chain": ["product", "customer_behavior"],
                    "counts": {"cart_add": adds, "return": returns, "purchase": purchases},
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": None,
                }
            )

        # Behavior → reason
        if reasons and (OBS_CART_ADD in types or OBS_RETURN_TO_STORE in types):
            correlations.append(
                {
                    "correlation_kind": CORR_BEHAVIOR_REASON,
                    "product_key": pk,
                    "chain": ["customer_behavior", "reason"],
                    "reason_counts": dict(reason_counts),
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": None,
                }
            )

        # Reason → return
        if reasons and OBS_RETURN_TO_STORE in types:
            correlations.append(
                {
                    "correlation_kind": CORR_REASON_RETURN,
                    "product_key": pk,
                    "chain": ["reason", "return"],
                    "reason_counts": dict(reason_counts),
                    "counts": {"return": returns},
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": None,
                }
            )

        # Return → purchase
        if OBS_RETURN_TO_STORE in types:
            correlations.append(
                {
                    "correlation_kind": CORR_RETURN_PURCHASE,
                    "product_key": pk,
                    "chain": ["return", "purchase"],
                    "counts": {"return": returns, "purchase": purchases},
                    "has_purchase_after_return_signal": purchases > 0,
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": None,
                }
            )

        # Interest vs conversion
        if adds >= 1:
            correlations.append(
                {
                    "correlation_kind": CORR_PRODUCT_INTEREST_CONVERSION,
                    "product_key": pk,
                    "chain": ["product", "customer_behavior", "purchase"],
                    "counts": {"cart_add": adds, "purchase": purchases},
                    "interest_without_purchase": adds >= 2 and purchases == 0,
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": "high_interest_low_conversion"
                    if adds >= 2 and purchases == 0
                    else None,
                }
            )

        # Reason strength compare (shipping vs price)
        if len(reason_counts) >= 1:
            def _reason_family(token: str) -> str:
                t = token.lower()
                if any(
                    x in t
                    for x in (
                        "ship",
                        "delivery",
                        "shipping",
                        "شحن",
                        "توصيل",
                    )
                ):
                    return "shipping"
                if t in {"price", "cost", "expensive"} or any(
                    x in t for x in ("price", "سعر", "غالي")
                ):
                    # exclude shipping_cost / delivery_cost (shipping family wins)
                    if "ship" in t or "delivery" in t or "شحن" in t or "توصيل" in t:
                        return "shipping"
                    return "price"
                return "other"

            shipping = sum(
                c for r, c in reason_counts.items() if _reason_family(r) == "shipping"
            )
            price = sum(
                c for r, c in reason_counts.items() if _reason_family(r) == "price"
            )
            if shipping + price >= 1:
                correlations.append(
                    {
                        "correlation_kind": CORR_REASON_STRENGTH,
                        "product_key": pk,
                        "chain": ["reason"],
                        "reason_counts": dict(reason_counts),
                        "compare": {"shipping": shipping, "price": price},
                        "stronger": (
                            "shipping"
                            if shipping > price
                            else ("price" if price > shipping else "tie")
                        ),
                        "evidence_refs": evidence_refs[:20],
                        "statement_capability": "shipping_stronger_than_price"
                        if shipping > price
                        else None,
                    }
                )

        # Repeat return without purchase
        if returns >= 2 and purchases == 0:
            correlations.append(
                {
                    "correlation_kind": CORR_REPEAT_RETURN_NO_PURCHASE,
                    "product_key": pk,
                    "chain": ["return", "purchase"],
                    "counts": {"return": returns, "purchase": purchases},
                    "evidence_refs": evidence_refs[:20],
                    "statement_capability": "repeated_return_without_purchase",
                }
            )

        # Absent quality evidence (only when hesitation observations exist)
        if OBS_HESITATION_REASON in types:
            quality_tokens = ("quality", "جودة", "defect", "broken")
            quality_hits = sum(
                c
                for r, c in reason_counts.items()
                if any(t in r for t in quality_tokens)
            )
            if quality_hits == 0 and sum(reason_counts.values()) >= 1:
                correlations.append(
                    {
                        "correlation_kind": CORR_ABSENT_REASON,
                        "product_key": pk,
                        "chain": ["reason"],
                        "absent_family": "quality",
                        "reason_counts": dict(reason_counts),
                        "evidence_refs": evidence_refs[:20],
                        "statement_capability": "no_quality_issue_evidence",
                    }
                )

    return correlations


def assemble_observation_foundation_v1(
    store_slug: str,
    *,
    signals: Optional[list[Mapping[str, Any]]] = None,
    limit: int = 500,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """
    Assemble Observation Foundation package for a store.

    When ``signals`` is None, loads from Product Signal Collection.
    """
    if not observation_foundation_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": FOUNDATION_VERSION,
            "store_slug": _norm(store_slug),
            "ui": False,
        }

    slug = _norm(store_slug)
    loaded = list(signals) if signals is not None else []
    if signals is None and slug:
        try:
            from services.observation_foundation_v1.durable_signals_bridge_v1 import (  # noqa: PLC0415
                load_observation_input_signals_v1,
            )

            loaded = load_observation_input_signals_v1(slug, limit=limit)
        except Exception:  # noqa: BLE001
            loaded = []

    observations = observations_from_signals_v1(loaded)
    correlations = correlations_from_observations_v1(observations)
    caps_ready = sorted(
        {
            c.get("statement_capability")
            for c in correlations
            if c.get("statement_capability")
        }
    )

    return {
        "ok": True,
        "enabled": True,
        "schema": FOUNDATION_VERSION,
        "store_slug": slug,
        "ui": False,
        "intelligence": False,
        "observation_model": observation_catalog_dict_v1(),
        "correlation_model": correlation_model_dict_v1(),
        "observations": observations,
        "correlations": correlations,
        "counts": {
            "signals_in": len(loaded),
            "observations": len(observations),
            "correlations": len(correlations),
            "statement_capabilities_ready": len(caps_ready),
        },
        "statement_capabilities_ready": caps_ready,
        "statement_capabilities_defined": [
            s["capability_id"] for s in STATEMENT_CAPABILITIES_V1
        ],
    }


__all__ = [
    "assemble_observation_foundation_v1",
    "correlations_from_observations_v1",
    "observations_from_signals_v1",
]
