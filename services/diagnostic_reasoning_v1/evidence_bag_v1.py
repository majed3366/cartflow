# -*- coding: utf-8 -*-
"""
Bounded evidence bag loader — off-path only.

Caps rows and window. Never join unbounded history on Home.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.cause_registry_v1 import (
    SIGNAL_DELIVERY,
    SIGNAL_DELIVERY_TIME,
    SIGNAL_INTEREST,
    SIGNAL_NO_PHONE,
    SIGNAL_PAYMENT,
    SIGNAL_PAYMENT_FRICTION,
    SIGNAL_PRICE,
    SIGNAL_SHIPPING,
    SIGNAL_SHIPPING_COST,
    SIGNAL_SHIPPING_STAGE,
)
from services.diagnostic_reasoning_v1.contract_v1 import (
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
    FAMILY_PAYMENT_FRICTION,
)
from services.diagnostic_reasoning_v1.compose_v1 import DEFAULT_WINDOW_DAYS

# Hard caps — performance protection.
MAX_REASON_ROWS = 200
MAX_BAGS = 8


def _normalize_reason(raw: str) -> str:
    t = (raw or "").strip().lower()
    aliases = {
        "shipping_cost": SIGNAL_SHIPPING_COST,
        "shipping": SIGNAL_SHIPPING,
        "delivery_time": SIGNAL_DELIVERY_TIME,
        "delivery": SIGNAL_DELIVERY,
        "payment": SIGNAL_PAYMENT,
        "payment_friction": SIGNAL_PAYMENT_FRICTION,
        "price": SIGNAL_PRICE,
        "price_high": SIGNAL_PRICE,
        "شحن": SIGNAL_SHIPPING,
        "توصيل": SIGNAL_DELIVERY,
    }
    return aliases.get(t, t)


def build_evidence_bags_from_reason_counts_v1(
    *,
    store_slug: str,
    reason_counts: Mapping[str, int],
    product_name_ar: str = "",
    product_id: str = "",
    no_phone: int = 0,
    interest_without_purchase: bool = False,
    shipping_stage_observed: bool = False,
    sample_n: Optional[int] = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> list[dict[str, Any]]:
    """Pure builder for tests and orchestrator (no DB)."""
    signals: dict[str, int] = {}
    for k, v in (reason_counts or {}).items():
        nk = _normalize_reason(str(k))
        if not nk:
            continue
        try:
            n = max(0, int(v))
        except (TypeError, ValueError):
            n = 0
        if n:
            signals[nk] = signals.get(nk, 0) + n
    total = int(sample_n if sample_n is not None else sum(signals.values()))
    bags: list[dict[str, Any]] = []

    # Shipping-stage family when stage observed or shipping-family signals present.
    ship_family = (
        shipping_stage_observed
        or signals.get(SIGNAL_SHIPPING, 0) > 0
        or signals.get(SIGNAL_SHIPPING_COST, 0) > 0
        or signals.get(SIGNAL_DELIVERY, 0) > 0
        or signals.get(SIGNAL_DELIVERY_TIME, 0) > 0
    )
    if ship_family:
        ship_signals = dict(signals)
        if shipping_stage_observed or (
            signals.get(SIGNAL_SHIPPING, 0) > 0
            and signals.get(SIGNAL_SHIPPING_COST, 0) <= 0
        ):
            ship_signals[SIGNAL_SHIPPING_STAGE] = max(
                1, ship_signals.get(SIGNAL_SHIPPING_STAGE, 0)
            )
        bags.append(
            {
                "diagnostic_family": FAMILY_CHECKOUT_AFTER_SHIPPING,
                "subject_type": "product" if product_id or product_name_ar else "store",
                "subject_id": product_id or "store",
                "product_name_ar": product_name_ar,
                "product_identity_ok": bool(product_id or product_name_ar),
                "signals": ship_signals,
                "sample_n": total,
                "minimum_sample": 3,
                "recurrence_days": min(7, window_days),
                "observation_refs": [
                    f"reason_counts:{k}:{v}" for k, v in list(ship_signals.items())[:12]
                ],
            }
        )

    if interest_without_purchase or (
        total >= 2 and not ship_family and signals.get(SIGNAL_PRICE, 0) == 0
    ):
        bags.append(
            {
                "diagnostic_family": FAMILY_INTEREST_WITHOUT_PURCHASE,
                "subject_type": "product" if product_id or product_name_ar else "store",
                "subject_id": product_id or "store",
                "product_name_ar": product_name_ar,
                "product_identity_ok": bool(product_id or product_name_ar),
                "signals": {**signals, SIGNAL_INTEREST: max(1, signals.get(SIGNAL_INTEREST, 0))},
                "sample_n": total,
                "minimum_sample": 3,
                "recurrence_days": min(7, window_days),
                "observation_refs": ["capability:interest_without_purchase"],
            }
        )

    if signals.get(SIGNAL_PAYMENT, 0) > 0 or signals.get(SIGNAL_PAYMENT_FRICTION, 0) > 0:
        bags.append(
            {
                "diagnostic_family": FAMILY_PAYMENT_FRICTION,
                "subject_type": "product" if product_id else "store",
                "subject_id": product_id or "store",
                "product_name_ar": product_name_ar,
                "product_identity_ok": bool(product_id or product_name_ar),
                "signals": signals,
                "sample_n": total,
                "minimum_sample": 3,
                "recurrence_days": min(7, window_days),
                "observation_refs": ["signal:payment"],
            }
        )

    if no_phone > 0:
        bags.append(
            {
                "diagnostic_family": FAMILY_CONTACT_FOLLOWUP_BLOCKED,
                "subject_type": "store",
                "subject_id": "store",
                "product_name_ar": "",
                "product_identity_ok": False,
                "signals": {SIGNAL_NO_PHONE: int(no_phone)},
                "sample_n": int(no_phone),
                "minimum_sample": 1,
                "recurrence_days": 1,
                "observation_refs": [f"no_phone:{no_phone}"],
            }
        )

    return bags[:MAX_BAGS]


def _bags_from_publication_v1(
    publication: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Synthesize bounded bags from merchant publication / situations (no history scan)."""
    pub = publication if isinstance(publication, Mapping) else {}
    bags: list[dict[str, Any]] = []
    home_prod = (
        pub.get("home_product_situation")
        if isinstance(pub.get("home_product_situation"), Mapping)
        else {}
    )
    primary = (
        pub.get("primary_executive_decision")
        if isinstance(pub.get("primary_executive_decision"), Mapping)
        else {}
    )
    product_name = str(
        home_prod.get("product_name_ar")
        or home_prod.get("subject_ar")
        or pub.get("primary_subject")
        or primary.get("subject_ar")
        or ""
    ).strip()
    product_id = str(
        home_prod.get("situation_id") or product_name or "store"
    ).strip()
    kind = str(home_prod.get("situation_kind") or "").strip()
    action = str(
        pub.get("primary_action") or primary.get("action_ar") or ""
    )
    text = " ".join(
        [
            kind,
            action,
            str(home_prod.get("statement_ar") or ""),
            str(home_prod.get("title_ar") or ""),
        ]
    )

    if kind == "shipping_friction" or "شحن" in text or "shipping" in text.lower():
        bags.extend(
            build_evidence_bags_from_reason_counts_v1(
                store_slug=str(pub.get("store_slug") or ""),
                reason_counts={SIGNAL_SHIPPING: 1},
                product_name_ar=product_name,
                product_id=product_id,
                shipping_stage_observed=True,
                sample_n=1,
            )
        )
    if kind == "interest_without_purchase" or "اهتمام" in text:
        bags.extend(
            build_evidence_bags_from_reason_counts_v1(
                store_slug=str(pub.get("store_slug") or ""),
                reason_counts={},
                product_name_ar=product_name,
                product_id=product_id,
                interest_without_purchase=True,
                sample_n=2,
            )
        )

    cc = pub.get("communication_condition") if isinstance(pub.get("communication_condition"), Mapping) else {}
    sc = pub.get("store_condition") if isinstance(pub.get("store_condition"), Mapping) else {}
    if cc.get("constrained") or "تواصل" in str(sc.get("summary_ar") or ""):
        bags.extend(
            build_evidence_bags_from_reason_counts_v1(
                store_slug=str(pub.get("store_slug") or ""),
                reason_counts={},
                no_phone=max(1, int(cc.get("no_phone") or 1)),
            )
        )
    return bags[:MAX_BAGS]


def load_bounded_evidence_bags_v1(
    store_slug: str,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    dash_store: Any = None,
    publication: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Load capped reason rows for a store. Off-path only.

    Uses LIMIT MAX_REASON_ROWS — never unbounded history.
    """
    slug = (store_slug or "").strip()
    if not slug:
        return []

    reason_counts: Counter[str] = Counter()
    no_phone = 0
    product_name = ""
    product_id = ""
    interest = False
    shipping_stage = False

    pub = publication if isinstance(publication, Mapping) else {}
    home_prod = (
        pub.get("home_product_situation")
        if isinstance(pub.get("home_product_situation"), Mapping)
        else {}
    )
    if home_prod:
        product_name = str(
            home_prod.get("product_name_ar") or home_prod.get("subject_ar") or ""
        ).strip()
        product_id = str(home_prod.get("situation_id") or product_name or "").strip()
        kind = str(home_prod.get("situation_kind") or "")
        if kind == "interest_without_purchase":
            interest = True
        if kind == "shipping_friction":
            shipping_stage = True

    try:
        from extensions import db
        from models import CartRecoveryReason

        since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            days=max(1, int(window_days))
        )
        # store_id column may hold slug or numeric — try slug match first.
        q = (
            db.session.query(CartRecoveryReason.reason)
            .filter(CartRecoveryReason.store_id == slug)
            .filter(CartRecoveryReason.created_at >= since)
            .order_by(CartRecoveryReason.created_at.desc())
            .limit(MAX_REASON_ROWS)
        )
        for (reason,) in q.all():
            reason_counts[_normalize_reason(str(reason or ""))] += 1
    except Exception:  # noqa: BLE001
        pass

    # no_phone from publication communication_condition / cart counts if present
    cc = pub.get("communication_condition") if isinstance(pub, Mapping) else None
    if isinstance(cc, Mapping) and cc.get("constrained"):
        no_phone = max(no_phone, 1)
    sc = pub.get("store_condition") if isinstance(pub, Mapping) else None
    if isinstance(sc, Mapping) and "تواصل" in str(sc.get("summary_ar") or ""):
        no_phone = max(no_phone, 1)

    if not reason_counts and shipping_stage:
        # Stage observation without subtype rows — still emit bag for honest insufficiency.
        reason_counts[SIGNAL_SHIPPING] = 1

    bags = build_evidence_bags_from_reason_counts_v1(
        store_slug=slug,
        reason_counts=dict(reason_counts),
        product_name_ar=product_name,
        product_id=product_id,
        no_phone=no_phone,
        interest_without_purchase=interest,
        shipping_stage_observed=shipping_stage,
        window_days=window_days,
    )
    if not bags:
        bags = _bags_from_publication_v1(pub)
    # Always merge publication-derived contact/shipping bags when absent.
    if bags and not any(
        b.get("diagnostic_family") == FAMILY_CHECKOUT_AFTER_SHIPPING for b in bags
    ):
        extra = _bags_from_publication_v1(pub)
        for b in extra:
            if b.get("diagnostic_family") not in {
                x.get("diagnostic_family") for x in bags
            }:
                bags.append(b)
    return bags[:MAX_BAGS]


__all__ = [
    "MAX_BAGS",
    "MAX_REASON_ROWS",
    "build_evidence_bags_from_reason_counts_v1",
    "load_bounded_evidence_bags_v1",
]
