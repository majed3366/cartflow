# -*- coding: utf-8 -*-
"""
طبقة ذكاء المنتج v1 — قواعد فقط، بلا ذكاء اصطناعي، بلا منتجات أو أسعار وهمية.

معزولة عن الجدولة ومسار واتساب الرئيسي؛ تُستهلك من مسار الاستمرار فقط.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from models import AbandonedCart, Store

from services.cartflow_merchant_offer_settings import merchant_offer_settings_from_store_row
from services.cartflow_merchant_offer_settings import product_catalog_from_store_row
from services.recovery_product_context import (
    infer_category_from_product_name,
    line_items_from_abandoned_cart,
    recovery_product_context_from_abandoned_cart,
    resolved_category_label,
    _item_category,
    _item_display_name,
    _item_unit_price,
)

log = logging.getLogger("cartflow")

# Bumped when cheaper diagnostics change — grep in prod logs to confirm this revision is live.
CHEAPER_DIAG_BUILD = "cheaper-diag-info-v2"

FALLBACK_CHEAPER_MESSAGE_AR = (
    "أفهمك 👍\n"
    "نقدر نساعدك بخيار أنسب حسب ميزانيتك."
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    product_id: str
    name: str
    price: float
    category: str
    url: str
    available: bool
    normalized_category: str = ""
    product_family: str = ""
    product_type: str = ""


@dataclass(frozen=True, slots=True)
class ProductIntelligenceSnapshot:
    current_product_id: Optional[str]
    current_product_name: Optional[str]
    current_product_price: Optional[float]
    current_product_category: Optional[str]
    current_product_url: Optional[str]
    current_checkout_url: str
    cart_total: Optional[float]
    alternative: Optional[CatalogEntry]
    cart_products: tuple[CatalogEntry, ...]
    alternative_score: Optional[float] = None
    fallback_reason: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CheaperAlternativeResult:
    entry: Optional[CatalogEntry]
    cheaper_candidate_score: float
    fallback_reason: str


def _norm_bucket(label: str) -> str:
    return (label or "").strip().lower()


def _line_item_id(it: dict[str, Any]) -> str:
    for k in ("id", "product_id", "variant_id", "sku"):
        v = it.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:128]
    prod = it.get("product")
    if isinstance(prod, dict):
        for k in ("id", "sku"):
            v = prod.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()[:128]
    return ""


def _line_item_url(it: dict[str, Any]) -> str:
    u = it.get("url") or it.get("product_url") or it.get("link")
    if not u and isinstance(it.get("product"), dict):
        u = it["product"].get("url") or it["product"].get("permalink")
    if u is None:
        return ""
    return str(u).strip()[:2048]


def _nested_product(it: dict[str, Any]) -> dict[str, Any]:
    p = it.get("product")
    return p if isinstance(p, dict) else {}


def _line_item_meta(it: dict[str, Any], key: str) -> str:
    v = it.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        v = _nested_product(it).get(key)
    if v is None:
        return ""
    return str(v).strip()[:120]


def _entry_from_line_item(it: dict[str, Any]) -> Optional[CatalogEntry]:
    name = _item_display_name(it)
    price = _item_unit_price(it)
    if not name or price is None or price <= 0:
        return None
    cat = _item_category(it) or infer_category_from_product_name(name)
    cat_s = (cat or "")[:120]
    nc = _line_item_meta(it, "normalized_category") or _norm_bucket(cat_s)
    fam = (_line_item_meta(it, "product_family") or "")[:64]
    ptype = (_line_item_meta(it, "product_type") or "")[:64]
    return CatalogEntry(
        product_id=_line_item_id(it) or name[:64],
        name=name[:300],
        price=float(price),
        category=cat_s,
        url=_line_item_url(it),
        available=True,
        normalized_category=nc[:120],
        product_family=fam[:64],
        product_type=ptype[:64],
    )


def _entries_from_catalog_dict(catalog: dict[str, Any]) -> list[CatalogEntry]:
    out: list[CatalogEntry] = []
    prods = catalog.get("products") if isinstance(catalog.get("products"), list) else []
    for p in prods:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()[:128]
        name = str(p.get("name") or "").strip()[:300]
        try:
            price = float(p.get("price"))
        except (TypeError, ValueError):
            continue
        if not name or price <= 0:
            continue
        avail = p.get("available")
        available = avail is not False
        if not available:
            continue
        cat = str(p.get("category") or "").strip()[:120]
        nc_raw = p.get("normalized_category")
        nc = str(nc_raw).strip()[:120] if isinstance(nc_raw, str) and nc_raw.strip() else _norm_bucket(cat)
        fam_raw = p.get("product_family")
        fam = str(fam_raw).strip()[:64] if isinstance(fam_raw, str) else ""
        pt_raw = p.get("product_type")
        pt = str(pt_raw).strip()[:64] if isinstance(pt_raw, str) else ""
        url = str(p.get("url") or "").strip()[:2048]
        out.append(
            CatalogEntry(
                product_id=pid or name[:64],
                name=name,
                price=round(price, 2),
                category=cat,
                url=url,
                available=True,
                normalized_category=nc,
                product_family=fam,
                product_type=pt,
            )
        )
    return out


_RAW_TO_CANON: dict[str, str] = {
    _norm_bucket("إلكترونيات"): "electronics",
    "electronics": "electronics",
    "electronic": "electronics",
    _norm_bucket("ساعات"): "watches",
    "watches": "watches",
    "watch": "watches",
    _norm_bucket("عطور"): "beauty",
    "perfume": "beauty",
    "perfumes": "beauty",
    "fragrance": "beauty",
    _norm_bucket("العناية والتجميل"): "beauty",
    _norm_bucket("الموضة والأزياء"): "fashion",
    _norm_bucket("أزياء"): "fashion",
    "ازياء": "fashion",
    "fashion": "fashion",
    "apparel": "fashion",
    _norm_bucket("المنزل والمعيشة"): "home",
    "home": "home",
}


def _canon_for_category_label(label: str) -> str:
    b = _norm_bucket(label)
    if not b:
        return ""
    return _RAW_TO_CANON.get(b, b)


def _canon_for_infer_label(infer_label: str) -> str:
    b = _norm_bucket(infer_label)
    if not b:
        return ""
    return _RAW_TO_CANON.get(b, b)


_TYPE_NEEDLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "headphones",
        (
            "سماعة",
            "headphone",
            "earbud",
            "airpod",
            "anc",
            "true",
            "sound",
            "soundstick",
            "truesound",
        ),
    ),
    (
        "watch",
        ("ساعة", "watch", "horizon", "pulse sport", "حزام", "band"),
    ),
    ("perfume", ("عطر", "oud", "musk", "perfume", "amber", "velvet")),
    ("charger", ("شاحن", "charger", "usb", "watt", "محول")),
    ("wallet", ("محفظة", "wallet")),
    ("apparel", ("هودي", "hoodie", "قميص", "جاكيت")),
)


def _infer_product_type_family(name: str) -> str:
    n = (name or "").strip().lower()
    if not n:
        return ""
    for fam, needles in _TYPE_NEEDLES:
        for nd in needles:
            if nd in n:
                return fam
    return ""


_SPLIT_TOKENS = re.compile(r"[\s,|;،]+")


def _name_tokens(name: str) -> set[str]:
    raw = _SPLIT_TOKENS.split((name or "").lower())
    out: set[str] = set()
    for p in raw:
        t = re.sub(r"[^\w\u0600-\u06FF]", "", p)
        if len(t) >= 2:
            out.add(t)
    return out


def _token_jaccard(a: str, b: str) -> float:
    sa, sb = _name_tokens(a), _name_tokens(b)
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return float(inter) / float(union) if union else 0.0


def _category_canon_frozenset(
    *,
    explicit_category: str,
    normalized_category: str,
    product_name: str,
) -> frozenset[str]:
    s: set[str] = set()
    for lab in (explicit_category, normalized_category):
        c = _canon_for_category_label(lab)
        if c:
            s.add(c)
    inf = infer_category_from_product_name(product_name or "")
    ic = _canon_for_infer_label(inf)
    if ic:
        s.add(ic)
    return frozenset(s)


def _primary_category_canons(
    primary: CatalogEntry,
    recovery_category_label: Optional[str],
) -> frozenset[str]:
    s: set[str] = set()
    if recovery_category_label and recovery_category_label.strip():
        s.add(_canon_for_category_label(recovery_category_label))
    s.update(
        _category_canon_frozenset(
            explicit_category=primary.category,
            normalized_category=primary.normalized_category or _norm_bucket(primary.category),
            product_name=primary.name,
        )
    )
    return frozenset(x for x in s if x)


def _candidate_category_canons(e: CatalogEntry) -> frozenset[str]:
    return _category_canon_frozenset(
        explicit_category=e.category,
        normalized_category=e.normalized_category or _norm_bucket(e.category),
        product_name=e.name,
    )


def _price_epsilon(primary_price: float) -> float:
    return max(0.01, abs(float(primary_price)) * 1e-6)


def _is_strictly_lower_price(candidate: float, primary: float) -> bool:
    if primary <= 0:
        return False
    return float(candidate) + _price_epsilon(primary) < float(primary)


def _cheaper_candidate_score(primary: CatalogEntry, cand: CatalogEntry) -> float:
    score = 25.0
    pf = (primary.product_family or "").strip()
    cf = (cand.product_family or "").strip()
    if pf and cf and pf == cf:
        score += 40.0
    else:
        pt_p = (primary.product_type or "").strip() or _infer_product_type_family(primary.name)
        pt_c = (cand.product_type or "").strip() or _infer_product_type_family(cand.name)
        if pt_p and pt_c and pt_p == pt_c:
            score += 22.0
    score += _token_jaccard(primary.name, cand.name) * 20.0
    if primary.price > 0:
        ratio = min(1.0, max(0.0, float(cand.price) / float(primary.price)))
        score += ratio * 25.0
    if cand.available:
        score += 5.0
    return round(score, 4)


def _log_alt_rejected(
    *,
    primary: CatalogEntry,
    cand: CatalogEntry,
    primary_canons: frozenset[str],
    reason: str,
    score_val: float,
) -> None:
    msg = (
        "[ALTERNATIVE REJECTED] product_id=%s category=%s original_price=%s "
        "candidate_price=%s rejection_reason=%s score=%s"
    )
    args = (
        (cand.product_id or "")[:64],
        (cand.category or "")[:80],
        primary.price,
        cand.price,
        reason,
        score_val,
    )
    dbg = (
        "[CHEAPER REJECTED] primary_id=%s candidate_id=%s candidate_name=%s "
        "primary_canons=%s candidate_canons=%s primary_price=%s candidate_price=%s "
        "rejection_reason=%s"
    )
    pc = ",".join(sorted(primary_canons))[:160]
    cc = ",".join(sorted(_candidate_category_canons(cand)))[:160]
    dbg_args = (
        (primary.product_id or "")[:64],
        (cand.product_id or "")[:64],
        (cand.name or "")[:80],
        pc,
        cc,
        primary.price,
        cand.price,
        reason,
    )
    # Always INFO for [CHEAPER REJECTED] so production log pipelines (often INFO+) capture mismatches.
    if reason == "category_mismatch":
        log.debug(msg, *args)
    else:
        log.info(msg, *args)
    log.info(dbg, *dbg_args)


def select_cheaper_alternative(
    *,
    primary: CatalogEntry,
    cart_entries: list[CatalogEntry],
    catalog_entries: list[CatalogEntry],
    recovery_category_label: Optional[str],
) -> CheaperAlternativeResult:
    """
    نفس الفئة (إشارات متعددة + تطبيع)، سعر أقل آمن، متاح فقط، ترتيب بالدرجة.
    """
    if primary.price <= 0:
        log.info(
            "[CHEAPER FALLBACK REASON] reason=invalid_primary_price primary_id=%s price=%s",
            (primary.product_id or "")[:64],
            primary.price,
        )
        return CheaperAlternativeResult(None, 0.0, "invalid_primary_price")

    primary_canons = _primary_category_canons(primary, recovery_category_label)
    if not primary_canons:
        log.info(
            "[PRODUCT MATCH] skip: no category signal primary_id=%s",
            primary.product_id[:32] if primary.product_id else "",
        )
        log.info(
            "[CHEAPER FALLBACK REASON] reason=no_category_signal primary_id=%s "
            "primary_category=%s primary_norm_category=%s recovery_category_label=%s",
            (primary.product_id or "")[:64],
            (primary.category or "")[:120],
            (primary.normalized_category or "")[:120],
            (recovery_category_label or "")[:120],
        )
        return CheaperAlternativeResult(None, 0.0, "no_category_signal")

    pool = cart_entries + catalog_entries
    log.info(
        "[CHEAPER MATCH DEBUG] phase=select diag_build=%s primary_id=%s primary_name=%s "
        "primary_category=%s primary_norm_category=%s primary_price=%s "
        "primary_family=%s primary_type=%s recovery_category_label=%s "
        "primary_canons=%s pool_size=%s cart_tail=%s catalog=%s",
        CHEAPER_DIAG_BUILD,
        (primary.product_id or "")[:64],
        (primary.name or "")[:80],
        (primary.category or "")[:120],
        (primary.normalized_category or "")[:120],
        primary.price,
        (primary.product_family or "")[:64],
        (primary.product_type or "")[:64],
        (recovery_category_label or "")[:120],
        ",".join(sorted(primary_canons))[:160],
        len(pool),
        len(cart_entries),
        len(catalog_entries),
    )

    scored: list[tuple[CatalogEntry, float]] = []
    seen_keys: set[str] = set()
    for e in pool:
        if e.product_id == primary.product_id and e.name == primary.name:
            _log_alt_rejected(
                primary=primary,
                cand=e,
                primary_canons=primary_canons,
                reason="same_line_as_primary",
                score_val=-1.0,
            )
            continue
        key = f"{e.product_id}|{e.name}"
        if key in seen_keys:
            _log_alt_rejected(
                primary=primary,
                cand=e,
                primary_canons=primary_canons,
                reason="duplicate_candidate",
                score_val=-1.0,
            )
            continue
        seen_keys.add(key)
        cand_canons_pre = _candidate_category_canons(e)
        log.info(
            "[CHEAPER CANDIDATE] product_id=%s name=%s price=%s category=%s "
            "normalized_category=%s available=%s product_family=%s product_type=%s "
            "candidate_canons=%s",
            (e.product_id or "")[:64],
            (e.name or "")[:80],
            e.price,
            (e.category or "")[:120],
            (e.normalized_category or "")[:120],
            e.available,
            (e.product_family or "")[:64],
            (e.product_type or "")[:64],
            ",".join(sorted(cand_canons_pre))[:160],
        )
        if not e.available:
            _log_alt_rejected(
                primary=primary,
                cand=e,
                primary_canons=primary_canons,
                reason="unavailable",
                score_val=-1.0,
            )
            continue
        cand_canons = cand_canons_pre
        if not (primary_canons & cand_canons):
            _log_alt_rejected(
                primary=primary,
                cand=e,
                primary_canons=primary_canons,
                reason="category_mismatch",
                score_val=-1.0,
            )
            continue
        if not _is_strictly_lower_price(e.price, primary.price):
            _log_alt_rejected(
                primary=primary,
                cand=e,
                primary_canons=primary_canons,
                reason="price_not_lower",
                score_val=-1.0,
            )
            continue
        sc = _cheaper_candidate_score(primary, e)
        scored.append((e, sc))
        log.info(
            "[ALTERNATIVE SCORE] product_id=%s category=%s original_price=%s "
            "candidate_price=%s rejection_reason=n/a score=%s",
            (e.product_id or "")[:64],
            (e.category or "")[:80],
            primary.price,
            e.price,
            sc,
        )

    log.info(
        "[PRODUCT MATCH] primary_canons=%s primary_price=%s eligible_scored=%s",
        ",".join(sorted(primary_canons))[:120],
        primary.price,
        len(scored),
    )
    if not scored:
        log.info(
            "[CHEAPER FALLBACK REASON] reason=no_eligible_cheaper_in_category primary_id=%s "
            "primary_price=%s primary_canons=%s pool_size=%s scored_count=0",
            (primary.product_id or "")[:64],
            primary.price,
            ",".join(sorted(primary_canons))[:160],
            len(pool),
        )
        return CheaperAlternativeResult(None, 0.0, "no_eligible_cheaper_in_category")

    best_entry, best_score = max(
        scored,
        key=lambda t: (t[1], t[0].price, t[0].name),
    )
    log.info(
        "[ALTERNATIVE SELECTED] id=%s price=%s (primary=%s) score=%s",
        best_entry.product_id[:48],
        best_entry.price,
        primary.price,
        best_score,
    )
    try:
        pdiff = f"{float(primary.price) - float(best_entry.price):.2f}"
    except (TypeError, ValueError):
        pdiff = ""
    log.info(
        "[CHEAPER SELECTED] product_id=%s name=%s price=%s primary_id=%s primary_price=%s "
        "price_difference=%s score=%s url_present=%s",
        (best_entry.product_id or "")[:64],
        (best_entry.name or "")[:120],
        best_entry.price,
        (primary.product_id or "")[:64],
        primary.price,
        pdiff,
        best_score,
        "1" if (best_entry.url or "").strip() else "0",
    )
    return CheaperAlternativeResult(best_entry, float(best_score), "")


def _cart_total_from_abandoned(ac: AbandonedCart, entries: list[CatalogEntry]) -> Optional[float]:
    raw = getattr(ac, "cart_value", None)
    if raw is not None:
        try:
            v = float(raw)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if not entries:
        return None
    s = sum(e.price for e in entries)
    return s if s > 0 else None


def _display_sar_amount(price: float) -> str:
    try:
        x = float(price)
    except (TypeError, ValueError):
        return ""
    if x <= 0:
        return ""
    if abs(x - round(x)) < 0.001:
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def build_product_intelligence_snapshot(
    ac: AbandonedCart,
    store: Optional[Store],
) -> ProductIntelligenceSnapshot:
    from services.behavioral_recovery.link_tracking import build_recovery_tracking_url

    line_dicts = line_items_from_abandoned_cart(ac)
    cart_entries: list[CatalogEntry] = []
    for d in line_dicts:
        e = _entry_from_line_item(d)
        if e:
            cart_entries.append(e)

    primary: Optional[CatalogEntry] = cart_entries[0] if cart_entries else None
    recovery_ctx = recovery_product_context_from_abandoned_cart(ac)
    rc_cat = resolved_category_label(recovery_ctx)

    catalog: dict[str, Any] = (
        product_catalog_from_store_row(store) if store is not None else {"products": []}
    )
    catalog_entries = _entries_from_catalog_dict(catalog)

    store_id = getattr(store, "id", None) if store is not None else None
    raw_prod_count = (
        len(catalog.get("products"))
        if isinstance(catalog.get("products"), list)
        else 0
    )
    log.info(
        "[CHEAPER MATCH DEBUG] phase=snapshot diag_build=%s store_id=%s line_dicts=%s "
        "cart_entries_built=%s catalog_raw_products=%s catalog_entries_available=%s "
        "recovery_category=%s primary_mapped=%s primary_id=%s primary_category=%s "
        "primary_price=%s",
        CHEAPER_DIAG_BUILD,
        store_id,
        len(line_dicts),
        len(cart_entries),
        raw_prod_count,
        len(catalog_entries),
        (rc_cat or "")[:120],
        "1" if primary is not None else "0",
        (primary.product_id if primary else "")[:64],
        (primary.category if primary else "")[:120],
        primary.price if primary else "",
    )
    if primary is None and line_dicts:
        log.info(
            "[CHEAPER FALLBACK REASON] reason=no_primary_cart_line line_items=%s "
            "(first line missing name/price)",
            len(line_dicts),
        )

    alt: Optional[CatalogEntry] = None
    alt_score: Optional[float] = None
    fb_reason: Optional[str] = None
    if primary is not None:
        pick = select_cheaper_alternative(
            primary=primary,
            cart_entries=cart_entries[1:],
            catalog_entries=catalog_entries,
            recovery_category_label=rc_cat,
        )
        alt = pick.entry
        if pick.entry is not None:
            alt_score = pick.cheaper_candidate_score
            log.info(
                "[CHEAPER MATCH DEBUG] phase=post_select select_returned_alt=1 "
                "matched_product_id=%s matched_price=%s",
                (pick.entry.product_id or "")[:64],
                pick.entry.price,
            )
        else:
            fb_reason = pick.fallback_reason or None
            log.info(
                "[CHEAPER MATCH DEBUG] phase=post_select select_returned_alt=0 "
                "fallback_reason_from_select=%s",
                (fb_reason or "")[:80],
            )
        if alt is None and recovery_ctx.cheaper_alternative_name:
            pprice = primary.price
            oprice = recovery_ctx.cheaper_alternative_price
            oname = (recovery_ctx.cheaper_alternative_name or "").strip()
            if (
                oname
                and oprice is not None
                and oprice > 0
                and _is_strictly_lower_price(float(oprice), pprice)
                and line_dicts
                and len(line_dicts) >= 2
            ):
                for d in line_dicts[1:]:
                    e2 = _entry_from_line_item(d)
                    if (
                        e2
                        and e2.name == oname
                        and abs(e2.price - float(oprice)) < 0.02
                    ):
                        alt = e2
                        alt_score = _cheaper_candidate_score(primary, e2)
                        fb_reason = None
                        log.info(
                            "[ALTERNATIVE SELECTED] source=cart_line id=%s score=%s",
                            e2.product_id[:48],
                            alt_score,
                        )
                        log.info(
                            "[CHEAPER SELECTED] source=cart_context_recovery product_id=%s "
                            "name=%s price=%s primary_id=%s score=%s",
                            (e2.product_id or "")[:64],
                            (e2.name or "")[:120],
                            e2.price,
                            (primary.product_id or "")[:64],
                            alt_score,
                        )
                        break

    zid = (getattr(ac, "zid_cart_id", None) or "").strip()
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    checkout = (
        build_recovery_tracking_url(zid, sid) or (getattr(ac, "cart_url", None) or "").strip()
    )

    cart_total = _cart_total_from_abandoned(ac, cart_entries)

    if primary is not None and alt is None:
        rsn = (fb_reason or "no_alternative").strip() or "no_alternative"
        log.info(
            "[FALLBACK USED] product_id=%s category=%s original_price=%s "
            "candidate_price=n/a rejection_reason=%s score=0",
            (primary.product_id or "")[:64],
            (primary.category or "")[:80],
            primary.price,
            rsn,
        )
        log.info(
            "[CHEAPER FALLBACK REASON] reason=final_snapshot_no_alternative detail=%s "
            "primary_id=%s catalog_entries=%s",
            rsn[:120],
            (primary.product_id or "")[:64],
            len(catalog_entries),
        )

    if primary is not None:
        mp = (alt.name if alt else "").strip()[:300]
        op = (primary.name or "").strip()[:300]
        diff_s = ""
        if alt is not None:
            try:
                diff_s = f"{float(primary.price) - float(alt.price):.2f}"
            except (TypeError, ValueError):
                diff_s = ""
        log.info(
            "[REAL PRODUCT MATCH] matched_product=%s original_product=%s "
            "price_difference=%s fallback_used=%s",
            mp[:200],
            op[:200],
            diff_s,
            "true" if alt is None else "false",
        )

    snap = ProductIntelligenceSnapshot(
        current_product_id=primary.product_id if primary else None,
        current_product_name=primary.name if primary else None,
        current_product_price=primary.price if primary else None,
        current_product_category=primary.category if primary else None,
        current_product_url=primary.url if primary and primary.url else None,
        current_checkout_url=checkout,
        cart_total=cart_total,
        alternative=alt,
        cart_products=tuple(cart_entries),
        alternative_score=alt_score,
        fallback_reason=(fb_reason if alt is None else None),
    )

    log.info(
        "[PRODUCT CONTEXT] product_id=%s name=%s price=%s category=%s "
        "cart_lines=%s alt=%s cart_total=%s",
        (snap.current_product_id or "")[:64],
        (snap.current_product_name or "")[:80],
        snap.current_product_price,
        (snap.current_product_category or "")[:64],
        len(cart_entries),
        bool(alt),
        cart_total,
    )
    return snap


def _reason_matches_trigger(reason_tag: str, trigger: str) -> bool:
    rt = (reason_tag or "").strip().lower()
    tr = (trigger or "").strip().lower()
    if not tr:
        return False
    if tr == "price":
        return rt == "price" or rt.startswith("price_")
    if tr == "shipping":
        return rt in ("shipping", "delivery") or rt.startswith("ship")
    if tr == "quality":
        return rt == "quality" or rt.startswith("quality_")
    return tr in rt or rt == tr


def _continuation_intent_for_offer(contextual_intent: str) -> str:
    return (contextual_intent or "").strip().lower()


def decide_merchant_offer_line(
    store: Optional[Store],
    *,
    reason_tag: str,
    contextual_intent: str,
    action: str,
    cart_total: Optional[float],
    first_seen_at: Optional[datetime],
    has_real_alternative: bool,
) -> tuple[str, bool]:
    """
    يرجع (سطر عربي للعرض، هل يُسمح باحتساب استخدام).
    """
    if store is None:
        log.info("[OFFER DECISION] skip: no store")
        return "", False
    settings = merchant_offer_settings_from_store_row(store)
    if not settings.get("offer_enabled") or not settings.get("enable_discount_offers"):
        log.info("[OFFER DECISION] skip: offers disabled")
        return "", False
    code = str(settings.get("discount_code") or "").strip()
    if not code:
        log.info("[OFFER DECISION] skip: empty discount_code")
        return "", False

    if not _reason_matches_trigger(reason_tag, str(settings.get("offer_trigger_reason") or "")):
        log.info(
            "[OFFER DECISION] skip: reason mismatch tag=%s trigger=%s",
            reason_tag,
            settings.get("offer_trigger_reason"),
        )
        return "", False

    min_tot = settings.get("offer_min_cart_total")
    if min_tot is not None:
        try:
            need = float(min_tot)
            ct = float(cart_total) if cart_total is not None else 0.0
            if ct < need:
                log.info(
                    "[OFFER DECISION] skip: cart_total %s < min %s",
                    cart_total,
                    need,
                )
                return "", False
        except (TypeError, ValueError):
            return "", False

    delay_m = int(settings.get("offer_delay_minutes") or 0)
    if delay_m > 0 and first_seen_at is not None:
        now = datetime.now(timezone.utc)
        fs = first_seen_at
        if fs.tzinfo is None:
            fs = fs.replace(tzinfo=timezone.utc)
        age_min = (now - fs).total_seconds() / 60.0
        if age_min < delay_m:
            log.info(
                "[OFFER DECISION] skip: delay not elapsed (%.1f < %s)",
                age_min,
                delay_m,
            )
            return "", False

    max_uses = settings.get("offer_max_uses")
    if max_uses is not None:
        try:
            cap = int(max_uses)
            used = int(getattr(store, "cf_offer_applications_count", 0) or 0)
            if used >= cap:
                log.info("[OFFER DECISION] skip: max_uses reached %s/%s", used, cap)
                return "", False
        except (TypeError, ValueError):
            pass

    ci = _continuation_intent_for_offer(contextual_intent)
    allow_intents = frozenset(
        {
            "wants_cheaper_alternative",
            "yes_to_cheaper_alternative",
            "asks_price_detail",
            "ready_for_checkout",
            "confirmation_generic",
            "asks_shipping_detail",
            "asks_delivery_detail",
        }
    )
    allow_actions = frozenset(
        {
            "send_cheaper_alternative",
            "explain_price",
            "send_checkout_link",
            "resend_checkout_link",
            "explain_shipping",
            "explain_delivery",
        }
    )
    if ci not in allow_intents and (action or "") not in allow_actions:
        log.info("[OFFER DECISION] skip: intent/action not targeted")
        return "", False

    if ci in ("ready_for_checkout", "confirmation_generic") and has_real_alternative:
        log.info("[OFFER DECISION] skip: checkout path with alternative context")
        return "", False

    parts = [f"كود الخصم: {code}"]
    pct = settings.get("discount_percent")
    if pct is not None:
        try:
            p = int(pct)
            if 1 <= p <= 35:
                parts.append(f"({p}٪)")
        except (TypeError, ValueError):
            pass
    line = " — ".join(parts)
    log.info(
        "[OFFER DECISION] allow reason=%s intent=%s action=%s line=%s",
        reason_tag,
        contextual_intent,
        action,
        line[:120],
    )
    return f"\n\n{line}", True


def build_intelligence_continuation_vars(
    ac: AbandonedCart,
    store: Optional[Store],
    *,
    reason_tag: str,
    contextual_intent: str,
    action: str,
) -> dict[str, str]:
    snap = build_product_intelligence_snapshot(ac, store)
    ship = os.getenv("CARTFLOW_SHIPPING_ESTIMATE_AR") or (
        "حسب المدينة — غالباً ٣–٧ أيام عمل"
    )
    ship = str(ship).strip()

    checkout = snap.current_checkout_url or "رابط المتجر"
    alt = snap.alternative
    has_real = bool(alt and alt.name.strip())

    offer_line, offer_apply = decide_merchant_offer_line(
        store,
        reason_tag=reason_tag,
        contextual_intent=contextual_intent,
        action=action,
        cart_total=snap.cart_total,
        first_seen_at=getattr(ac, "first_seen_at", None),
        has_real_alternative=has_real,
    )
    if offer_apply:
        log.info("[OFFER APPLIED] preview=%s", offer_line.strip()[:100])

    vars_map: dict[str, str] = {
        "checkout_url": checkout,
        "alternative_product_name": alt.name if alt else "",
        "alternative_checkout_url": (alt.url if alt and alt.url else checkout),
        "alternative_product_price_display": _display_sar_amount(alt.price)
        if alt
        else "",
        "current_product_name_display": (snap.current_product_name or "").strip()[:300],
        "shipping_estimate": ship,
        "cheaper_reply_mode": "real" if has_real else "fallback",
        "has_price_context": "1"
        if snap.current_product_price is not None
        else "0",
        "current_product_price_display": ""
        if snap.current_product_price is None
        else f"{snap.current_product_price:.2f}",
        "merchant_offer_line": offer_line,
        "merchant_offer_applied": "1" if offer_apply else "0",
        "cheaper_candidate_score": ""
        if snap.alternative_score is None
        else f"{snap.alternative_score:.4f}",
        "cheaper_fallback_reason": (snap.fallback_reason or "")
        if not has_real
        else "",
    }
    log.info(
        "[CHEAPER MATCH DEBUG] phase=continuation_vars diag_build=%s cheaper_reply_mode=%s "
        "has_real_alternative=%s alternative_url_len=%s cheaper_fallback_reason=%s",
        CHEAPER_DIAG_BUILD,
        vars_map.get("cheaper_reply_mode", ""),
        "1" if has_real else "0",
        len((vars_map.get("alternative_checkout_url") or "")),
        (vars_map.get("cheaper_fallback_reason") or "")[:120],
    )
    return vars_map


def record_merchant_offer_use(store: Optional[Store]) -> None:
    if store is None:
        return
    try:
        n = int(getattr(store, "cf_offer_applications_count", 0) or 0)
        store.cf_offer_applications_count = n + 1
        log.info("[OFFER APPLIED] cf_offer_applications_count=%s", n + 1)
    except (TypeError, ValueError):
        pass


def resolve_store_for_abandoned_cart(ac: Optional[AbandonedCart]) -> Optional[Store]:
    if ac is None:
        return None
    raw = getattr(ac, "store_id", None)
    if raw is None:
        return None
    try:
        from unittest.mock import MagicMock as _MagicMock
    except ImportError:
        _MagicMock = ()  # type: ignore[assignment]
    if isinstance(raw, _MagicMock):
        return None
    try:
        from extensions import db

        return db.session.get(Store, int(raw))
    except (TypeError, ValueError, RuntimeError):
        return None
