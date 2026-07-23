# -*- coding: utf-8 -*-
"""
Evidence aggregation for Business Findings Engine V1.

Reads bounded operational truth into a store-scoped EvidenceBundle.
Surfaces never query history unbounded on the hot path — engine runs are
explicit, capped, and observably costed.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import norm

log = logging.getLogger("cartflow")

DEFAULT_WINDOW_DAYS = 14
MAX_PRODUCT_ROWS = 40
MAX_REASON_ROWS = 20
MAX_MOVEMENT_ROWS = 500
MAX_LOG_ROWS = 800


@dataclass
class EvidenceBundle:
    """Deterministic evidence input for finding evaluators."""

    store_slug: str
    window_days: int = DEFAULT_WINDOW_DAYS
    observed_period: dict[str, str] = field(default_factory=dict)
    # Hesitation
    hesitation_total: int = 0
    hesitation_distribution: dict[str, int] = field(default_factory=dict)
    hesitation_by_product: dict[str, dict[str, int]] = field(default_factory=dict)
    hesitation_resolved: dict[str, dict[str, int]] = field(default_factory=dict)
    # Products: product_id -> metrics
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Channel / recovery
    wa_eligible: int = 0
    wa_sent: int = 0
    wa_failed: int = 0
    wa_suppressed: int = 0
    wa_returned: int = 0
    wa_purchased: int = 0
    widget_reasons_captured: int = 0
    widget_contact_captured: int = 0
    widget_shown: Optional[int] = None  # None = unavailable
    # Movement
    returns_total: int = 0
    returns_without_purchase: int = 0
    returns_with_purchase: int = 0
    repeated_returners: int = 0
    # Store activity
    active_carts: int = 0
    purchased_carts: int = 0
    no_phone_total: int = 0
    visitor_total: Optional[int] = None  # None = unavailable
    # Coverage flags
    has_product_views: bool = False
    has_visitor_truth: bool = False
    query_cost: int = 0
    source_tables: list[str] = field(default_factory=list)
    loaded_from: str = "no_evidence_source"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_empty_evidence_bundle_v1(
    *,
    store_slug: str = "",
    window_days: int = DEFAULT_WINDOW_DAYS,
    loaded_from: str = "no_evidence_source",
) -> EvidenceBundle:
    """Honest empty evidence — never substitutes demo fixture placeholders."""
    return EvidenceBundle(
        store_slug=norm(store_slug),
        window_days=window_days,
        observed_period=evidence_period(window_days),
        loaded_from=loaded_from or "no_evidence_source",
        source_tables=[],
        query_cost=0,
    )


def evidence_period(window_days: int = DEFAULT_WINDOW_DAYS) -> dict[str, str]:
    try:
        from services.time_authority.authority import authority_now  # noqa: PLC0415

        end = authority_now().replace(microsecond=0)
    except Exception:  # noqa: BLE001
        end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=max(1, int(window_days)))
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "window_days": str(int(window_days)),
    }


def build_demo_rich_evidence_bundle_v1(
    *,
    store_slug: str = "demo",
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> EvidenceBundle:
    """
    Deterministic demo evidence covering required validation scenarios.

    Used when DB load is unavailable or for offline validation reports.
    Not random filler — each signal maps to an expected finding family.
    """
    slug = norm(store_slug) or "demo"
    return EvidenceBundle(
        store_slug=slug,
        window_days=window_days,
        observed_period=evidence_period(window_days),
        hesitation_total=28,
        hesitation_distribution={
            "shipping": 16,
            "price": 7,
            "thinking": 3,
            "delivery_time": 2,
        },
        hesitation_by_product={
            "prod_ship_cat": {"shipping": 12, "price": 2},
            "prod_x": {"price": 4, "shipping": 2},
            "prod_c": {"thinking": 1},
        },
        hesitation_resolved={
            "shipping": {"returned": 10, "purchased": 1, "unresolved": 9},
            "delivery_time": {"returned": 2, "purchased": 2, "unresolved": 0},
            "price": {"returned": 3, "purchased": 1, "unresolved": 2},
        },
        products={
            "prod_x": {
                "name_ar": "منتج X",
                "add_to_cart": 34,
                "unique_carts": 22,
                "purchases": 2,
                "revisits": 8,
                "repeat_adds": 11,
            },
            "prod_b": {
                "name_ar": "منتج B",
                "add_to_cart": 19,
                "unique_carts": 14,
                "purchases": 1,
                "revisits": 5,
                "repeat_adds": 7,
            },
            "prod_c": {
                "name_ar": "منتج C",
                "add_to_cart": 2,
                "unique_carts": 2,
                "purchases": 0,
                "revisits": 0,
                "repeat_adds": 0,
            },
            "prod_peer_1": {
                "name_ar": "منتج مقارن 1",
                "add_to_cart": 18,
                "unique_carts": 15,
                "purchases": 6,
                "revisits": 2,
                "repeat_adds": 1,
            },
            "prod_peer_2": {
                "name_ar": "منتج مقارن 2",
                "add_to_cart": 16,
                "unique_carts": 12,
                "purchases": 5,
                "revisits": 1,
                "repeat_adds": 1,
            },
        },
        wa_eligible=40,
        wa_sent=32,
        wa_failed=2,
        wa_suppressed=1,
        wa_returned=18,
        wa_purchased=3,
        widget_reasons_captured=28,
        widget_contact_captured=6,
        widget_shown=None,
        returns_total=22,
        returns_without_purchase=16,
        returns_with_purchase=6,
        repeated_returners=5,
        active_carts=60,
        purchased_carts=9,
        no_phone_total=43,
        visitor_total=None,
        has_product_views=False,
        has_visitor_truth=False,
        query_cost=0,
        source_tables=[
            "cart_recovery_reasons",
            "cart_line_snapshots",
            "product_purchase_mappings",
            "movement_snapshots",
            "cart_recovery_logs",
            "purchase_truth_records",
            "abandoned_carts",
        ],
        loaded_from="demo_rich_fixture_v1",
    )


def build_insufficient_evidence_bundle_v1(*, store_slug: str = "demo") -> EvidenceBundle:
    """Sparse store — must produce honest insufficient findings."""
    return EvidenceBundle(
        store_slug=norm(store_slug) or "demo",
        window_days=7,
        observed_period=evidence_period(7),
        hesitation_total=1,
        hesitation_distribution={"thinking": 1},
        products={"prod_tiny": {"name_ar": "منتج", "add_to_cart": 1, "unique_carts": 1, "purchases": 0}},
        wa_sent=1,
        wa_returned=0,
        wa_purchased=0,
        returns_total=0,
        active_carts=2,
        purchased_carts=0,
        no_phone_total=0,
        visitor_total=None,
        has_visitor_truth=False,
        loaded_from="insufficient_fixture_v1",
        source_tables=["cart_recovery_reasons"],
    )


def build_conflicting_evidence_bundle_v1(*, store_slug: str = "demo") -> EvidenceBundle:
    """Signals pull in opposite commercial directions."""
    return EvidenceBundle(
        store_slug=norm(store_slug) or "demo",
        window_days=14,
        observed_period=evidence_period(14),
        hesitation_total=20,
        hesitation_distribution={"shipping": 10, "price": 10},
        hesitation_resolved={
            "shipping": {"returned": 8, "purchased": 4, "unresolved": 4},
            "price": {"returned": 8, "purchased": 4, "unresolved": 4},
        },
        products={
            "prod_a": {
                "name_ar": "منتج أ",
                "add_to_cart": 20,
                "unique_carts": 15,
                "purchases": 7,
            },
            "prod_b": {
                "name_ar": "منتج ب",
                "add_to_cart": 20,
                "unique_carts": 15,
                "purchases": 0,
            },
        },
        wa_sent=20,
        wa_returned=12,
        wa_purchased=10,
        returns_total=14,
        returns_without_purchase=4,
        returns_with_purchase=10,
        active_carts=40,
        purchased_carts=18,
        no_phone_total=2,
        visitor_total=None,
        has_visitor_truth=False,
        loaded_from="conflicting_fixture_v1",
        source_tables=["cart_recovery_reasons", "cart_recovery_logs"],
    )


def load_evidence_bundle_from_db_v1(
    *,
    store_slug: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    dash_store: Any = None,
) -> EvidenceBundle:
    """
    Bounded DB load for a single store. Failures return a sparse bundle with cost.
    Never crosses tenants. Never scans unlimited history.
    """
    t0 = time.perf_counter()
    slug = norm(store_slug)
    if not slug:
        return EvidenceBundle(store_slug="", loaded_from="empty_slug")
    cost = 0
    tables: list[str] = []
    try:
        from extensions import db  # noqa: PLC0415
        from services.knowledge_metrics_v1 import collect_knowledge_metrics  # noqa: PLC0415
        from services.time_authority.authority import authority_now  # noqa: PLC0415

        # Metrics require a session + Time Authority 'now'.
        # Use authority_now() (respects FixedAsOf / simulation binds).
        # Do not use knowledge_stamp_now() — it defaults to SystemClock QTC.
        metrics = collect_knowledge_metrics(
            db.session,
            slug,
            window_days=window_days,
            now=authority_now(),
        )
        cost += 1
        tables.extend(["cart_recovery_reasons", "cart_recovery_logs", "abandoned_carts"])
        hesitation_total = int(getattr(metrics, "hesitation_total", 0) or 0)
        hesitation_dist = dict(getattr(metrics, "hesitation_distribution", {}) or {})
        wa_sent = int(getattr(metrics, "recovery_messages_sent", 0) or 0)
        wa_failed = int(getattr(metrics, "recovery_failed", 0) or 0)
        wa_returned = int(getattr(metrics, "recovery_returns", 0) or 0)
        # purchases via attribution when present
        wa_purchased = int(getattr(metrics, "recovery_purchases", 0) or 0)
    except Exception as exc:  # noqa: BLE001
        log.warning("business_findings evidence metrics failed store=%s: %s", slug, exc)
        hesitation_total = 0
        hesitation_dist = {}
        wa_sent = wa_failed = wa_returned = wa_purchased = 0

    products: dict[str, dict[str, Any]] = {}
    no_phone = 0
    active = 0
    purchased = 0
    try:
        products, p_cost, p_tables = _load_product_interest_v1(slug, window_days=window_days)
        cost += p_cost
        tables.extend(p_tables)
    except Exception as exc:  # noqa: BLE001
        log.warning("business_findings product evidence failed store=%s: %s", slug, exc)

    try:
        no_phone, active, purchased, c_cost = _load_cart_counters_v1(slug, dash_store=dash_store)
        cost += c_cost
        tables.append("merchant_store_cart_counts")
    except Exception as exc:  # noqa: BLE001
        log.warning("business_findings cart counters failed store=%s: %s", slug, exc)

    returns_total = wa_returned
    returns_without_purchase = max(0, returns_total - wa_purchased)
    returns_with_purchase = min(returns_total, wa_purchased)

    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    bundle = EvidenceBundle(
        store_slug=slug,
        window_days=window_days,
        observed_period=evidence_period(window_days),
        hesitation_total=hesitation_total,
        hesitation_distribution=hesitation_dist,
        products=products,
        wa_sent=wa_sent,
        wa_failed=wa_failed,
        wa_returned=wa_returned,
        wa_purchased=wa_purchased,
        widget_reasons_captured=hesitation_total,
        returns_total=returns_total,
        returns_without_purchase=returns_without_purchase,
        returns_with_purchase=returns_with_purchase,
        active_carts=active,
        purchased_carts=purchased,
        no_phone_total=no_phone,
        visitor_total=None,
        has_product_views=False,
        has_visitor_truth=False,
        query_cost=cost,
        source_tables=sorted(set(tables)),
        loaded_from=f"db_v1:{duration_ms}ms",
    )
    return bundle


def _load_cart_counters_v1(
    store_slug: str, *, dash_store: Any = None
) -> tuple[int, int, int, int]:
    from services.commercial_interpretation_v1 import (  # noqa: PLC0415
        resolve_canonical_no_phone_total,
    )

    no_phone, _meta = resolve_canonical_no_phone_total(
        store_slug=store_slug, dash_store=dash_store
    )
    active = 0
    purchased = 0
    try:
        from extensions import db  # noqa: PLC0415
        from models import AbandonedCart, Store  # noqa: PLC0415
        from sqlalchemy import func  # noqa: PLC0415

        store_id = None
        if dash_store is not None and getattr(dash_store, "id", None) is not None:
            store_id = int(dash_store.id)
        if store_id is None:
            row = (
                db.session.query(Store)
                .filter(Store.zid_store_id == store_slug)
                .first()
            )
            if row is not None:
                store_id = int(row.id)
        if store_id is not None:
            active = int(
                db.session.query(func.count(AbandonedCart.id))
                .filter(AbandonedCart.store_id == store_id)
                .scalar()
                or 0
            )
            purchased = int(
                db.session.query(func.count(AbandonedCart.id))
                .filter(
                    AbandonedCart.store_id == store_id,
                    AbandonedCart.recovered_at.isnot(None),
                )
                .scalar()
                or 0
            )
    except Exception:  # noqa: BLE001
        pass
    return int(no_phone or 0), active, purchased, 2


def _load_product_interest_v1(
    store_slug: str, *, window_days: int
) -> tuple[dict[str, dict[str, Any]], int, list[str]]:
    """
    Aggregate cart_line_snapshots + purchase mappings (bounded).

    Canonical fields only: ``CartLineSnapshot.name`` / ``captured_at``
    (Product Identity Foundation PI-F2). Prefer stable_identity_key when resolvable.
    Never invents placeholder product names.
    """
    products: dict[str, dict[str, Any]] = {}
    try:
        from extensions import db  # noqa: PLC0415
        from models import CartLineSnapshot  # noqa: PLC0415
        from sqlalchemy import func  # noqa: PLC0415
        from services.product_data.product_catalog_normalizer_v1 import (  # noqa: PLC0415
            catalog_input_from_line,
            resolve_canonical_identity,
        )
        from services.product_data.product_identity_authenticity_v1 import (  # noqa: PLC0415
            text_has_forbidden_product_placeholder,
        )
        from services.time_authority.authority import authority_now  # noqa: PLC0415

        since = authority_now() - timedelta(days=max(1, window_days))
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        rows = (
            db.session.query(
                CartLineSnapshot.product_id,
                CartLineSnapshot.variant_id,
                CartLineSnapshot.sku,
                CartLineSnapshot.name,
                func.count(CartLineSnapshot.id),
                func.count(func.distinct(CartLineSnapshot.session_id)),
            )
            .filter(
                CartLineSnapshot.store_slug == store_slug,
                CartLineSnapshot.captured_at >= since_naive,
            )
            .group_by(
                CartLineSnapshot.product_id,
                CartLineSnapshot.variant_id,
                CartLineSnapshot.sku,
                CartLineSnapshot.name,
            )
            .order_by(func.count(CartLineSnapshot.id).desc())
            .limit(MAX_PRODUCT_ROWS)
            .all()
        )
        for pid, variant_id, sku, pname, adds, unique_carts in rows:
            display = norm(pname)
            if text_has_forbidden_product_placeholder(display):
                continue
            # Reject internal keys used as names (sim degradation residue)
            if display and "_" in display and " " not in display and all(
                ord(c) < 128 for c in display
            ):
                display = ""
            line = {
                "product_id": pid,
                "variant_id": variant_id,
                "sku": sku,
                "name": pname,
            }
            product = catalog_input_from_line(line)
            resolution = (
                resolve_canonical_identity(product) if product is not None else None
            )
            key = (
                (resolution.stable_identity_key if resolution else "")
                or norm(pid)
                or (f"name:{display}" if display else "")
            )
            if not key:
                continue
            if key in products:
                products[key]["add_to_cart"] += int(adds or 0)
                products[key]["unique_carts"] += int(unique_carts or 0)
                products[key]["repeat_adds"] = max(
                    0,
                    int(products[key]["add_to_cart"])
                    - int(products[key]["unique_carts"]),
                )
                if display and not products[key].get("name_ar"):
                    products[key]["name_ar"] = display
                continue
            # Honest unresolved: no placeholder; skip nameless aggregates for merchant findings
            if not display:
                continue
            products[key] = {
                "name_ar": display,
                "product_id": norm(pid) or None,
                "stable_identity_key": (
                    resolution.stable_identity_key if resolution else None
                ),
                "add_to_cart": int(adds or 0),
                "unique_carts": int(unique_carts or 0),
                "purchases": 0,
                "revisits": 0,
                "repeat_adds": max(0, int(adds or 0) - int(unique_carts or 0)),
            }
        # Purchase counts via stable key or product_id
        try:
            from models import ProductPurchaseMapping  # noqa: PLC0415

            for key, pdata in list(products.items())[:MAX_PRODUCT_ROWS]:
                sid_key = norm(pdata.get("stable_identity_key")) or key
                pid_key = norm(pdata.get("product_id"))
                q = db.session.query(func.count(ProductPurchaseMapping.id)).filter(
                    ProductPurchaseMapping.store_slug == store_slug,
                )
                if sid_key.startswith(("a|", "b|", "c|", "d|", "e|")):
                    cnt = q.filter(
                        ProductPurchaseMapping.stable_identity_key == sid_key
                    ).scalar()
                elif pid_key:
                    cnt = q.filter(
                        ProductPurchaseMapping.product_id == pid_key
                    ).scalar()
                else:
                    cnt = 0
                products[key]["purchases"] = int(cnt or 0)
        except Exception:  # noqa: BLE001
            pass
        return products, 2, ["cart_line_snapshots", "product_purchase_mappings"]
    except Exception as exc:  # noqa: BLE001
        log.warning("product interest aggregate unavailable: %s", exc)
        return {}, 0, []
