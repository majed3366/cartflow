# -*- coding: utf-8 -*-
"""
Commerce Intelligence Synthesis — governed source adapters (cisrc_v1).

No provider-specific tables, raw webhooks, or frontend state.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.product_data.commerce_intelligence_synthesis_types_v1 import (
    KNOWLEDGE_WINDOW_MAP,
    SHIPPING_REASON_TOKENS,
    WINDOW_LENGTH_DAYS,
)
from services.product_data.knowledge_foundation_types_v1 import (
    KNOWLEDGE_TYPE_EVIDENCE_CONFLICT,
    KNOWLEDGE_TYPE_EVIDENCE_GAP,
    KNOWLEDGE_TYPE_METRIC_TREND,
)
from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1
from services.product_data.product_hesitation_mapping_v1 import (
    mapping_count_for_store,
    products_for_reason,
)
from services.product_data.product_purchase_mapping_v1 import (
    purchase_mapping_count,
    purchases_for_product,
)
from services.product_data.time_authority_binding_resolve_v1 import resolve_bound_as_of_v1

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def _in_window(ts: Optional[datetime], start: datetime, end: datetime) -> bool:
    if ts is None:
        return False
    return start <= ts <= end


def load_synthesis_sources_v1(
    store_slug: str,
    *,
    time_window_key: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Load all governed source contracts for one synthesis refresh."""
    slug = (store_slug or "").strip()[:255]
    window = (time_window_key or "d7").strip().lower()
    if window not in WINDOW_LENGTH_DAYS:
        window = "d7"
    anchor = resolve_bound_as_of_v1(as_of)
    days = WINDOW_LENGTH_DAYS[window]
    window_start = anchor - timedelta(days=days)
    knowledge_window = KNOWLEDGE_WINDOW_MAP.get(window, "d7")

    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "time_window_key": window,
        "window_start": window_start.isoformat(sep=" "),
        "window_end": anchor.isoformat(sep=" "),
        "as_of": anchor.isoformat(sep=" "),
        "knowledge_window": knowledge_window,
        "sources": {},
        "rejected_inputs": [],
        "unsupported_input_reasons": {},
        "available_source_domains": [],
        "missing_source_domains": [],
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out

    # --- knowledge (required) ---
    try:
        knowledge = generate_knowledge_v1(
            slug, assembly_window=knowledge_window, as_of=anchor
        )
        if knowledge.get("ok"):
            out["sources"]["knowledge"] = {
                "ok": True,
                "contract_key": "generate_knowledge_v1",
                "statements": list(knowledge.get("statements") or []),
                "statement_count": int(knowledge.get("statement_count") or 0),
                "canonical_fingerprint": knowledge.get("canonical_fingerprint") or "",
                "knowledge_window": knowledge_window,
            }
            out["available_source_domains"].append("knowledge")
        else:
            out["sources"]["knowledge"] = {
                "ok": False,
                "contract_key": "generate_knowledge_v1",
                "statements": [],
                "errors": list(knowledge.get("errors") or ["knowledge_failed"]),
            }
            out["missing_source_domains"].append("knowledge")
            out["rejected_inputs"].append(
                {
                    "source_domain": "knowledge",
                    "reason": "knowledge_not_ok",
                    "detail": knowledge.get("errors") or [],
                }
            )
            out["unsupported_input_reasons"]["knowledge"] = "knowledge_not_ok"
    except Exception as exc:  # noqa: BLE001
        out["sources"]["knowledge"] = {"ok": False, "errors": [type(exc).__name__]}
        out["missing_source_domains"].append("knowledge")
        out["rejected_inputs"].append(
            {
                "source_domain": "knowledge",
                "reason": f"exception:{type(exc).__name__}",
            }
        )
        out["unsupported_input_reasons"]["knowledge"] = f"exception:{type(exc).__name__}"
        out["errors"].append(f"knowledge:{type(exc).__name__}")

    # --- product hesitation (optional) ---
    try:
        shipping_rows: list[dict[str, Any]] = []
        for token in sorted(SHIPPING_REASON_TOKENS):
            for row in products_for_reason(slug, token, limit=200):
                ts = _parse_dt(row.get("captured_at"))
                if not _in_window(ts, window_start, anchor):
                    out["rejected_inputs"].append(
                        {
                            "source_domain": "product_hesitation",
                            "reason": "outside_temporal_window",
                            "record_id": row.get("id"),
                        }
                    )
                    continue
                shipping_rows.append(row)
        total = mapping_count_for_store(slug)
        out["sources"]["product_hesitation"] = {
            "ok": True,
            "contract_key": "product_hesitation_mapping_read_v1",
            "store_mapping_count": int(total),
            "shipping_hesitation_rows": shipping_rows,
            "shipping_hesitation_count": len(shipping_rows),
        }
        if total > 0 or shipping_rows:
            out["available_source_domains"].append("product_hesitation")
        else:
            out["missing_source_domains"].append("product_hesitation")
            out["unsupported_input_reasons"]["product_hesitation"] = "no_mappings"
    except Exception as exc:  # noqa: BLE001
        out["sources"]["product_hesitation"] = {
            "ok": False,
            "errors": [type(exc).__name__],
        }
        out["missing_source_domains"].append("product_hesitation")
        out["rejected_inputs"].append(
            {
                "source_domain": "product_hesitation",
                "reason": f"exception:{type(exc).__name__}",
            }
        )
        out["unsupported_input_reasons"]["product_hesitation"] = (
            f"exception:{type(exc).__name__}"
        )

    # --- product purchase (optional) ---
    try:
        pcount = purchase_mapping_count(slug)
        out["sources"]["product_purchase"] = {
            "ok": True,
            "contract_key": "product_purchase_mapping_read_v1",
            "store_purchase_mapping_count": int(pcount),
        }
        if pcount > 0:
            out["available_source_domains"].append("product_purchase")
        else:
            out["missing_source_domains"].append("product_purchase")
            out["unsupported_input_reasons"]["product_purchase"] = "no_mappings"
    except Exception as exc:  # noqa: BLE001
        out["sources"]["product_purchase"] = {
            "ok": False,
            "errors": [type(exc).__name__],
        }
        out["missing_source_domains"].append("product_purchase")
        out["rejected_inputs"].append(
            {
                "source_domain": "product_purchase",
                "reason": f"exception:{type(exc).__name__}",
            }
        )
        out["unsupported_input_reasons"]["product_purchase"] = (
            f"exception:{type(exc).__name__}"
        )

    # --- commerce signals (optional; force read of governed projection) ---
    try:
        from services.commerce_signals_v1 import (  # noqa: PLC0415
            load_store_commerce_signals_v1,
        )

        signals_report = load_store_commerce_signals_v1(store_slug=slug, force=True)
        signals = list(signals_report.get("signals") or [])
        out["sources"]["commerce_signals"] = {
            "ok": bool(signals_report.get("ok")),
            "contract_key": "load_store_commerce_signals_v1",
            "signals": signals,
            "signal_count": len(signals),
            "enabled": bool(signals_report.get("enabled")),
        }
        if signals:
            out["available_source_domains"].append("commerce_signals")
        else:
            out["missing_source_domains"].append("commerce_signals")
            out["unsupported_input_reasons"]["commerce_signals"] = "no_signals"
    except Exception as exc:  # noqa: BLE001
        out["sources"]["commerce_signals"] = {
            "ok": False,
            "errors": [type(exc).__name__],
        }
        out["missing_source_domains"].append("commerce_signals")
        out["rejected_inputs"].append(
            {
                "source_domain": "commerce_signals",
                "reason": f"exception:{type(exc).__name__}",
            }
        )
        out["unsupported_input_reasons"]["commerce_signals"] = (
            f"exception:{type(exc).__name__}"
        )

    # Deduplicate domain lists while preserving order
    seen_a: set[str] = set()
    avail: list[str] = []
    for d in out["available_source_domains"]:
        if d not in seen_a:
            seen_a.add(d)
            avail.append(d)
    out["available_source_domains"] = avail
    seen_m: set[str] = set()
    miss: list[str] = []
    for d in out["missing_source_domains"]:
        if d not in seen_m and d not in seen_a:
            seen_m.add(d)
            miss.append(d)
    out["missing_source_domains"] = miss

    out["ok"] = "knowledge" in out["available_source_domains"] or bool(
        out["sources"].get("knowledge", {}).get("ok")
    )
    # Knowledge may be ok with empty statements — still a valid source contract.
    if out["sources"].get("knowledge", {}).get("ok"):
        out["ok"] = True
        if "knowledge" not in out["available_source_domains"]:
            out["available_source_domains"].insert(0, "knowledge")
            out["missing_source_domains"] = [
                d for d in out["missing_source_domains"] if d != "knowledge"
            ]
    return out


def knowledge_index_v1(sources: dict[str, Any]) -> dict[str, Any]:
    """Index knowledge statements for rule evaluation."""
    stmts = list((sources.get("sources") or {}).get("knowledge", {}).get("statements") or [])
    by_product: dict[str, dict[str, Any]] = {}
    conflicts = 0
    gaps: list[str] = []
    cart_interest_products: list[str] = []
    purchase_gap_products: list[str] = []
    return_trend_products: list[str] = []
    engagement_trend_count = 0
    purchase_trend_count = 0

    for s in stmts:
        st = str(s.get("subject_type") or "")
        sid = str(s.get("subject_id") or "")
        ktype = str(s.get("knowledge_type") or "")
        metric = str(s.get("metric_key") or "")
        direction = str(s.get("trend_direction") or "")
        gap = str(s.get("gap_key") or "")

        if ktype == KNOWLEDGE_TYPE_EVIDENCE_CONFLICT:
            conflicts += 1
        if ktype == KNOWLEDGE_TYPE_EVIDENCE_GAP and gap:
            gaps.append(gap)

        if st == "product" and sid:
            bucket = by_product.setdefault(
                sid,
                {
                    "trends": [],
                    "gaps": [],
                    "conflicts": 0,
                    "cart_interest": False,
                    "purchase_gap": False,
                    "return_interest": False,
                },
            )
            if ktype == KNOWLEDGE_TYPE_METRIC_TREND:
                bucket["trends"].append({"metric_key": metric, "direction": direction})
                if metric in {
                    "cart_added_count",
                    "cart_synced_count",
                    "checkout_touched_count",
                    "interest_hesitation_count",
                } and direction in {"increasing", "newly_appeared", "stable"}:
                    bucket["cart_interest"] = True
                    if sid not in cart_interest_products:
                        cart_interest_products.append(sid)
                    engagement_trend_count += 1
                if metric == "purchase_count":
                    purchase_trend_count += 1
                if metric == "customer_return_count" and direction in {
                    "increasing",
                    "newly_appeared",
                    "stable",
                }:
                    bucket["return_interest"] = True
                    if sid not in return_trend_products:
                        return_trend_products.append(sid)
            if ktype == KNOWLEDGE_TYPE_EVIDENCE_GAP:
                bucket["gaps"].append(gap)
                if gap in {"purchase_count", "purchases", "purchase_truth"}:
                    bucket["purchase_gap"] = True
                    if sid not in purchase_gap_products:
                        purchase_gap_products.append(sid)
            if ktype == KNOWLEDGE_TYPE_EVIDENCE_CONFLICT:
                bucket["conflicts"] += 1

    return {
        "statement_count": len(stmts),
        "by_product": by_product,
        "conflict_count": conflicts,
        "gaps": gaps,
        "cart_interest_products": cart_interest_products,
        "purchase_gap_products": purchase_gap_products,
        "return_trend_products": return_trend_products,
        "engagement_trend_count": engagement_trend_count,
        "purchase_trend_count": purchase_trend_count,
    }


def purchase_count_for_product_v1(store_slug: str, product_id: str) -> int:
    try:
        return len(purchases_for_product(store_slug, product_id, limit=50))
    except Exception:  # noqa: BLE001
        return 0


__all__ = [
    "load_synthesis_sources_v1",
    "knowledge_index_v1",
    "purchase_count_for_product_v1",
]
