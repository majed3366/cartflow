# -*- coding: utf-8 -*-
"""
Products V1 compose — one bounded read model. No ranker. No N+1.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.live_reality_lab_v1.gate_v1 import is_live_reality_lab_tenant
from services.product_data.product_identity_authenticity_v1 import (
    text_has_forbidden_product_placeholder,
)
from services.product_data.product_read_model_contract_v1 import (
    KNOWN_UNKNOWNS,
    PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED,
    visit_field_label,
)
from services.products_commercial_truth_v1.contract_v1 import (
    ATTENTION_INSUFFICIENT,
    ATTENTION_LABEL_AR,
    ATTENTION_MONITORING,
    ATTENTION_NEEDS,
    ATTENTION_OWNER,
    ATTENTION_STABLE,
    CARTS_WITHOUT_PURCHASE_AR,
    COMMERCIAL_STATUS_OWNER,
    EXPOSURE_LAB_SYNTHETIC,
    EXPOSURE_NONE_RECORDED,
    EXPOSURE_NOT_STORED,
    EXPOSURE_HEADING_AR,
    EXPOSURE_UNAVAILABLE_AR,
    KICKER_AR,
    LAB_VISIT_HEADING_AR,
    LAB_VISIT_NOTE_AR,
    LAB_VISIT_NOT_REAL_AR,
    LAYER_SCHEMA,
    LAYER_VERSION,
    MAX_PRODUCTS,
    MISSING_NAME_IDENTITY_AR,
    MISSING_NAME_TITLE_AR,
    NO_RELIABLE_VISIT_AR,
    NOTE_AR,
    PRESENTATION_DEGRADED,
    PRESENTATION_INSUFFICIENT,
    PRESENTATION_NEUTRAL,
    PRESENTATION_STRONG,
    PRODUCT_READ_MODEL_SCHEMA,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
    QUESTION_AR,
    READ_MODEL_OWNER,
    REASON_NOUN_AR,
    SIGNAL_HEADING_AR,
    STORE_CONTEXT_BODY_AR,
    STORE_CONTEXT_CTA_AR,
    VISIT_FIELD_CLASS_LAB_ONLY,
    VISIT_FIELD_NAME,
)


def _norm(value: Any, *, max_len: int = 200) -> str:
    return str(value or "").strip()[:max_len]


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _money_ar(amount: float, currency: str = "SAR") -> str:
    whole = int(round(amount))
    if abs(amount - whole) < 0.005:
        num = str(whole)
    else:
        num = f"{amount:.2f}"
    suffix = "ر.س" if currency in {"SAR", "ر.س", ""} else currency
    return f"{num} {suffix}"


def _name_ok(name: str) -> bool:
    n = _norm(name)
    if not n:
        return False
    if text_has_forbidden_product_placeholder(n):
        return False
    return True


def _attention(
    *,
    missing_name: bool,
    named: bool,
    cart_count: int,
    purchase_count: int,
    purchase_known: bool,
    hesitation_n: int,
) -> str:
    if missing_name or not named:
        return ATTENTION_INSUFFICIENT
    if purchase_known and cart_count > 0 and purchase_count == 0:
        return ATTENTION_NEEDS
    if purchase_known and purchase_count > 0:
        return ATTENTION_STABLE
    if hesitation_n > 0:
        return ATTENTION_MONITORING
    return ATTENTION_INSUFFICIENT


def _hesitation_line(counts: Mapping[str, int]) -> str:
    parts: list[str] = []
    for key, n in counts.items():
        if n <= 0:
            continue
        noun = REASON_NOUN_AR.get(key) or key
        parts.append(f"{noun} ({n})")
        if len(parts) >= 2:
            break
    if not parts:
        return ""
    return "أسباب تردد مسجّلة على هذا المنتج: " + "، ".join(parts) + "."


def _top_hesitation(counts: Mapping[str, int]) -> tuple[str, int] | None:
    best: tuple[str, int] | None = None
    for key, raw in counts.items():
        n = _as_int(raw)
        if n <= 0:
            continue
        if best is None or n > best[1]:
            best = (_norm(key).lower(), n)
    return best


def _presentation_kind(
    *,
    missing_name: bool,
    named: bool,
    cart_count: int,
    purchase_count: int,
    hesitation_n: int,
) -> str:
    if missing_name or not named:
        return PRESENTATION_DEGRADED
    if hesitation_n > 0 or purchase_count > 0:
        return PRESENTATION_STRONG
    if cart_count > 0:
        return PRESENTATION_NEUTRAL
    return PRESENTATION_INSUFFICIENT


def _strongest_signal(
    *,
    hes: Mapping[str, int],
    cart_count: int,
    cart_value: float,
    purchase_count: int,
    purchase_known: bool,
    currency: str,
) -> str:
    top = _top_hesitation(hes)
    if top:
        noun = REASON_NOUN_AR.get(top[0]) or top[0]
        return f"{noun} تكرر في {top[1]} أسباب تردد مسجّلة لهذا المنتج."
    if purchase_known and cart_count > 0 and purchase_count == 0:
        if cart_value > 0:
            return (
                f"توجد {cart_count} سلال بقيمة {_money_ar(cart_value, currency)} "
                "دون مشتريات مسجّلة."
            )
        return CARTS_WITHOUT_PURCHASE_AR
    return ""


def _load_from_db(store_slug: str, store: Any, *, lab_tenant: bool) -> dict[str, Any]:
    from services.products_commercial_truth_v1.load_consolidated_v1 import (
        load_products_read_model_v1,
    )

    return load_products_read_model_v1(store_slug, store, lab_tenant=lab_tenant)


def _card_from_facts(
    item: Mapping[str, Any],
    *,
    lab_tenant: bool,
    carts: Mapping[str, Any],
    purchases: Mapping[str, Any],
    hesitation: Mapping[str, Any],
    visits: Optional[Mapping[str, int]],
) -> dict[str, Any]:
    pid = _norm(item.get("product_id"))
    raw_name = _norm(item.get("name"))
    missing = bool(item.get("missing_name")) or not _name_ok(raw_name)
    named = _name_ok(raw_name) and not missing
    cart = carts.get(pid) or {}
    purch = purchases.get(pid)
    # Successful bounded mapping query ⇒ absent rows are a real zero, not unknown.
    purchase_known = True
    purchase_count = _as_int((purch or {}).get("purchase_count"))
    revenue = _as_float((purch or {}).get("revenue"))
    cart_count = _as_int(cart.get("cart_count"))
    cart_value = _as_float(cart.get("cart_value"))
    hes = dict(hesitation.get(pid) or {})
    hesitation_n = sum(_as_int(v) for v in hes.values())
    attention = _attention(
        missing_name=missing,
        named=named,
        cart_count=cart_count,
        purchase_count=purchase_count,
        purchase_known=purchase_known,
        hesitation_n=hesitation_n,
    )
    unknown: list[str] = list(KNOWN_UNKNOWNS)
    currency = _norm(item.get("currency")) or "SAR"
    title = raw_name if named else MISSING_NAME_TITLE_AR
    identity = raw_name if named else MISSING_NAME_IDENTITY_AR
    price = item.get("price")
    evidence: list[str] = []
    if cart_count > 0 and purchase_count == 0 and purchase_known:
        evidence.append(CARTS_WITHOUT_PURCHASE_AR)
    hes_line = _hesitation_line(hes)
    if hes_line:
        evidence.append(hes_line)
    signal_ar = _strongest_signal(
        hes=hes,
        cart_count=cart_count,
        cart_value=cart_value,
        purchase_count=purchase_count,
        purchase_known=purchase_known,
        currency=currency,
    )
    kind = _presentation_kind(
        missing_name=missing,
        named=named,
        cart_count=cart_count,
        purchase_count=purchase_count,
        hesitation_n=hesitation_n,
    )
    exposure: dict[str, Any]
    if lab_tenant and visits is not None:
        n = _as_int(visits.get(pid))
        if n > 0:
            exposure = {
                "state": EXPOSURE_LAB_SYNTHETIC,
                "count": n,
                "heading_ar": LAB_VISIT_HEADING_AR,
                "value_ar": str(n),
                "note_ar": LAB_VISIT_NOT_REAL_AR,
                "label_ar": f"{LAB_VISIT_HEADING_AR}: {n}. {LAB_VISIT_NOT_REAL_AR}",
                VISIT_FIELD_NAME: n,
                "truth_class": VISIT_FIELD_CLASS_LAB_ONLY,
            }
        else:
            exposure = {
                "state": EXPOSURE_NONE_RECORDED,
                "count": None,
                "heading_ar": EXPOSURE_HEADING_AR,
                "value_ar": EXPOSURE_UNAVAILABLE_AR,
                "note_ar": None,
                "label_ar": EXPOSURE_UNAVAILABLE_AR,
                "truth_class": visit_field_label(lab_tenant=True),
            }
    else:
        exposure = {
            "state": EXPOSURE_NOT_STORED,
            "count": None,
            "heading_ar": EXPOSURE_HEADING_AR,
            "value_ar": EXPOSURE_UNAVAILABLE_AR,
            "note_ar": None,
            "label_ar": EXPOSURE_UNAVAILABLE_AR,
            "truth_class": visit_field_label(lab_tenant=False),
        }
    cart_value_ar = _money_ar(cart_value, currency) if cart_count else None
    revenue_ar = _money_ar(revenue, currency) if purchase_count else None
    return {
        "product_id": pid,
        "product_name": title,
        "product_identity": identity,
        "missing_name": missing,
        "name_is_merchant_title": named,
        "price": float(price) if price is not None else None,
        "price_ar": _money_ar(float(price), currency) if price is not None else None,
        "currency": currency,
        "cart_count": cart_count,
        "cart_value": cart_value,
        "cart_value_ar": cart_value_ar,
        "purchases": purchase_count,
        "purchase_known": True,
        "revenue": revenue,
        "revenue_ar": revenue_ar,
        "hesitation_reason_counts": hes,
        "hesitation_ar": hes_line or None,
        "signal_ar": signal_ar or None,
        "signal_heading_ar": SIGNAL_HEADING_AR if signal_ar else None,
        "presentation_kind": kind,
        "exposure": exposure,
        "commercial_attention_state": attention,
        "attention_label_ar": ATTENTION_LABEL_AR[attention],
        "evidence_ar": evidence,
        "unknown_fields": sorted(unknown),
        "attribution_boundary": "product" if hesitation_n else None,
        "product_scoped_shipping_claim": False,
    }


def compose_products_commercial_truth_v1(
    *,
    store_slug: str = "",
    store: Any = None,
    preloaded: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bounded product commercial truth. preloaded is tests/capture only."""
    slug = _norm(store_slug or getattr(store, "store_id", "") or "", max_len=191)
    lab_tenant = is_live_reality_lab_tenant(store_slug=slug, store=store)
    if preloaded is not None:
        blob = dict(preloaded)
        query_count = 0
        n_plus_one = 0
    else:
        blob = _load_from_db(slug, store, lab_tenant=lab_tenant)
        ceiling = QUERY_COUNT_LAB if lab_tenant else QUERY_COUNT_NORMAL
        query_count = int(blob.get("query_count") or ceiling)
        n_plus_one = 0
    catalog = list(blob.get("catalog") or [])
    carts = dict(blob.get("carts") or {})
    purchases = dict(blob.get("purchases") or {})
    hesitation = dict(blob.get("hesitation") or {})
    visits = blob.get("visits")
    if not lab_tenant:
        visits = None
    elif visits is not None and not isinstance(visits, Mapping):
        visits = {}
    seen: set[str] = set()
    cards: list[dict[str, Any]] = []
    for item in catalog[:MAX_PRODUCTS]:
        pid = _norm(item.get("product_id"))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        cards.append(
            _card_from_facts(
                item,
                lab_tenant=lab_tenant,
                carts=carts,
                purchases=purchases,
                hesitation=hesitation,
                visits=visits if isinstance(visits, Mapping) or visits is None else None,
            )
        )
    for pid in list(carts.keys()):
        if pid in seen or len(cards) >= MAX_PRODUCTS:
            continue
        seen.add(pid)
        cards.append(
            _card_from_facts(
                {"product_id": pid, "name": "", "missing_name": True, "price": None},
                lab_tenant=lab_tenant,
                carts=carts,
                purchases=purchases,
                hesitation=hesitation,
                visits=visits if isinstance(visits, Mapping) or visits is None else None,
            )
        )
    # Readability order from cart/purchase facts — not a mission ranker.
    rank = {
        ATTENTION_NEEDS: 0,
        ATTENTION_STABLE: 1,
        ATTENTION_MONITORING: 2,
        ATTENTION_INSUFFICIENT: 3,
    }
    cards.sort(
        key=lambda c: (
            rank.get(c["commercial_attention_state"], 9),
            -int(c.get("cart_count") or 0),
            str(c.get("product_name") or ""),
        )
    )
    groups: dict[str, list[dict[str, Any]]] = {}
    for card in cards:
        groups.setdefault(card["presentation_kind"], []).append(card)
    kind_label = {
        PRESENTATION_STRONG: "",
        PRESENTATION_NEUTRAL: "",
        PRESENTATION_INSUFFICIENT: "بيانات غير كافية",
        PRESENTATION_DEGRADED: "هوية غير مكتملة",
    }
    group_list = []
    for key in (
        PRESENTATION_STRONG,
        PRESENTATION_NEUTRAL,
        PRESENTATION_INSUFFICIENT,
        PRESENTATION_DEGRADED,
    ):
        rows = groups.get(key) or []
        if rows:
            group_list.append(
                {
                    "id": key,
                    "label_ar": kind_label[key],
                    "count": len(rows),
                    "product_ids": [r["product_id"] for r in rows],
                }
            )
    primary = next(
        (c for c in cards if c.get("presentation_kind") == PRESENTATION_STRONG),
        cards[0] if cards else None,
    )
    named_n = sum(1 for c in cards if c.get("name_is_merchant_title"))
    return {
        "ok": True,
        "schema": LAYER_SCHEMA,
        "layer_version": LAYER_VERSION,
        "read_model_schema": PRODUCT_READ_MODEL_SCHEMA,
        "store_slug": slug,
        "lab_tenant": lab_tenant,
        "read_model_owner": READ_MODEL_OWNER,
        "attention_owner": ATTENTION_OWNER,
        "commercial_status_owner": COMMERCIAL_STATUS_OWNER,
        "frontend_ranking": 0,
        "frontend_fixtures": 0,
        "query_delta": query_count,
        "n_plus_one": n_plus_one,
        "product_scoped_shipping_claim_allowed": PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED,
        "real_merchant_visit_ingestion": False,
        "unique_visitor_claim": 0,
        "question_ar": QUESTION_AR,
        "kicker_ar": KICKER_AR,
        "note_ar": NOTE_AR,
        "performance_debt_id": "PRODUCTS_READ_MODEL_QUERY_FANOUT_V1",
        "store_context": {
            "attribution_boundary": "store",
            "body_ar": STORE_CONTEXT_BODY_AR,
            "cta_ar": STORE_CONTEXT_CTA_AR,
            "href": "#workspace",
        },
        "primary": primary,
        "products": cards,
        "groups": group_list,
        "counts": {
            "products": len(cards),
            "named": named_n,
            "missing_name": len(cards) - named_n,
        },
        "visit_field_label": visit_field_label(lab_tenant=lab_tenant),
    }


__all__ = ["compose_products_commercial_truth_v1"]
