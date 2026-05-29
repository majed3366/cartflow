# -*- coding: utf-8 -*-
"""
Bulk in-memory customer phone resolution for merchant normal-carts batch reads.

Replaces per-row _merchant_normal_batch_resolve_customer_phone_raw loop on the
dashboard hot path. Preserves resolution priority/order; no per-row DB access.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# Pre-optimization structural baseline (hot-path audit, 2026-05-29).
AUDIT_BASELINE_PHONE_RESOLUTION_DB_QUERIES_PER_CHECK = 150

_loop_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "phone_resolution_loop_count", default=0
)
_fallback_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "phone_resolution_fallback_count", default=0
)
_db_query_count: contextvars.ContextVar[int] = contextvars.ContextVar(
    "phone_resolution_db_query_count", default=0
)


def phone_resolution_prof_reset() -> None:
    _loop_count.set(0)
    _fallback_count.set(0)
    _db_query_count.set(0)


def phone_resolution_prof_record_loop(n: int = 1) -> None:
    _loop_count.set(int(_loop_count.get()) + max(0, int(n)))


def phone_resolution_prof_record_fallback() -> None:
    _fallback_count.set(int(_fallback_count.get()) + 1)


def phone_resolution_prof_record_db(n: int = 1) -> None:
    _db_query_count.set(int(_db_query_count.get()) + max(0, int(n)))


def phone_resolution_prof_snapshot() -> dict[str, int]:
    return {
        "phone_resolution_loop_count": int(_loop_count.get()),
        "phone_resolution_fallback_count": int(_fallback_count.get()),
        "phone_resolution_db_queries_after": int(_db_query_count.get()),
    }


def build_phone_resolution_comparison(
    *,
    avg_total_dashboard_queries: float,
    avg_loop_count: float,
    avg_fallback_count: float,
    avg_db_queries_after: float,
) -> dict[str, Any]:
    before_db = float(AUDIT_BASELINE_PHONE_RESOLUTION_DB_QUERIES_PER_CHECK)
    after_db = round(float(avg_db_queries_after), 2)
    return {
        "phone_resolution_db_queries_before": int(
            AUDIT_BASELINE_PHONE_RESOLUTION_DB_QUERIES_PER_CHECK
        ),
        "before_baseline_per_dashboard_check": {
            "phone_resolution_db_queries": int(AUDIT_BASELINE_PHONE_RESOLUTION_DB_QUERIES_PER_CHECK),
            "source": "hot_path_audit_pre_phone_bulk_prefetch",
        },
        "after_avg_per_dashboard_check": {
            "phone_resolution_db_queries": after_db,
            "phone_resolution_loop_count": round(float(avg_loop_count), 2),
            "phone_resolution_fallback_count": round(float(avg_fallback_count), 2),
            "total_dashboard_queries": round(float(avg_total_dashboard_queries), 2),
        },
        "delta_per_dashboard_check": {
            "phone_resolution_db_queries_removed": round(before_db - after_db, 2),
        },
        "per_row_db_eliminated": (
            round(float(avg_loop_count), 2) > 0
            and after_db <= 0
            and round(float(avg_fallback_count), 2) <= 0
        ),
    }


@dataclass
class _SentLogPhoneIndex:
    by_session: dict[str, str]
    by_cart: dict[str, str]


def _sent_log_rank(lg: Any) -> tuple[datetime, int]:
    sent = getattr(lg, "sent_at", None)
    if sent is None:
        sent = datetime.min.replace(tzinfo=timezone.utc)
    elif sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    else:
        sent = sent.astimezone(timezone.utc)
    return (sent, int(getattr(lg, "id", 0) or 0))


def _build_sent_log_phone_index(logs: list[Any], sent_statuses: frozenset[str]) -> _SentLogPhoneIndex:
    best_sess: dict[str, tuple[datetime, int, str]] = {}
    best_cart: dict[str, tuple[datetime, int, str]] = {}
    for lg in logs or ():
        stl = str((getattr(lg, "status", None) or "")).strip().lower()
        if stl not in sent_statuses:
            continue
        ph = _strip_phone(getattr(lg, "phone", None))
        if not ph:
            continue
        rank = _sent_log_rank(lg)
        ls = (getattr(lg, "session_id", None) or "").strip()
        if ls:
            prev = best_sess.get(ls)
            if prev is None or rank > (prev[0], prev[1]):
                best_sess[ls] = (rank[0], rank[1], ph)
        lc = (getattr(lg, "cart_id", None) or "").strip()
        if lc:
            prev = best_cart.get(lc)
            if prev is None or rank > (prev[0], prev[1]):
                best_cart[lc] = (rank[0], rank[1], ph)
    return _SentLogPhoneIndex(
        by_session={k: v[2] for k, v in best_sess.items()},
        by_cart={k: v[2] for k, v in best_cart.items()},
    )


def _build_peer_phone_by_session(peers: list[Any]) -> dict[str, list[tuple[datetime, str]]]:
    out: dict[str, list[tuple[datetime, str]]] = {}
    for peer in peers or ():
        if bool(getattr(peer, "vip_mode", False)):
            continue
        sid = (getattr(peer, "recovery_session_id", None) or "").strip()
        if not sid:
            continue
        ph = _strip_phone(getattr(peer, "customer_phone", None))
        if not ph:
            continue
        t = getattr(peer, "last_seen_at", None)
        if t is None:
            ts = datetime.min.replace(tzinfo=timezone.utc)
        elif t.tzinfo is None:
            ts = t.replace(tzinfo=timezone.utc)
        else:
            ts = t.astimezone(timezone.utc)
        out.setdefault(sid, []).append((ts, ph))
    for sid in out:
        out[sid].sort(key=lambda x: x[0], reverse=True)
    return out


def _strip_phone(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    return s[:100] if s else ""


def _map_verified_phone_from_batch(
    *,
    abandon_event_phone: Optional[str],
    recovery_key: str,
    reason_row: Any,
    mem_phone_by_rk: dict[str, str],
    mem_src_by_rk: dict[str, str],
) -> tuple[Optional[str], str]:
    from services.cf_test_phone_override import (  # noqa: PLC0415
        phone_matches_cartflow_demo_test_customer_phone,
    )

    ep = _strip_phone(abandon_event_phone)
    dbp = (
        _strip_phone(getattr(reason_row, "customer_phone", None))
        if reason_row is not None
        else ""
    )
    rk = (recovery_key or "").strip()
    mem = _strip_phone(mem_phone_by_rk.get(rk, ""))
    mem_src = mem_src_by_rk.get(rk, "customer_profile") if mem else "customer_profile"

    candidates: list[tuple[str, str]] = [
        (dbp, "customer_profile"),
        (ep, "abandoned_cart"),
        (mem, mem_src),
    ]

    def _is_demo_line(p: str) -> bool:
        return bool(p) and phone_matches_cartflow_demo_test_customer_phone(p)

    non_demo_exists = any(bool(p) and not _is_demo_line(p) for p, _ in candidates)
    for p, src in candidates:
        if not p:
            continue
        if non_demo_exists and _is_demo_line(p):
            continue
        return p, src
    return None, "none"


def _resolve_phone_from_batch_index(
    ac: Any,
    dash_store: Any,
    batch: Any,
    *,
    mem_phone_by_rk: dict[str, str],
    mem_src_by_rk: dict[str, str],
    sent_idx: _SentLogPhoneIndex,
    peer_by_session: dict[str, list[tuple[datetime, str]]],
    verified_sources: frozenset[str],
    extended_sources: frozenset[str],
    sent_statuses: frozenset[str],
) -> str:
    from main import (  # noqa: PLC0415
        _abandoned_ids_for_recovery_scope_rows,
        _normal_recovery_merchant_normalized_digits,
        _normal_recovery_phone_normalized_equals_merchant,
        _recovery_key_from_store_and_session,
    )

    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    zid = (getattr(ac, "zid_cart_id", None) or "").strip() or None
    cz = (zid or "").strip()[:255]
    if not sid:
        return ""

    slug_base = (getattr(batch, "slug", None) or "").strip()
    slug = slug_base if slug_base else (
        (str(getattr(dash_store, "zid_store_id", None) or "").strip()[:255] or "demo")
    )
    rk = _recovery_key_from_store_and_session(slug, sid)
    reason_row = batch.reason_store_by_session.get(
        sid
    ) or batch.reason_any_by_session.get(sid)
    store_obj = batch.store_row_for_cart(ac)
    merchant_digits = _normal_recovery_merchant_normalized_digits(store_obj)

    def _hit(ph: Optional[str], src: str) -> tuple[Optional[str], str]:
        got = _strip_phone(ph)
        if not got:
            return None, "none"
        if _normal_recovery_phone_normalized_equals_merchant(got, merchant_digits):
            return None, "none"
        return got, src

    col_phone = _strip_phone(getattr(ac, "customer_phone", None)) or None
    phone, src = _map_verified_phone_from_batch(
        abandon_event_phone=col_phone,
        recovery_key=rk,
        reason_row=reason_row,
        mem_phone_by_rk=mem_phone_by_rk,
        mem_src_by_rk=mem_src_by_rk,
    )
    if phone and _normal_recovery_phone_normalized_equals_merchant(phone, merchant_digits):
        phone, src = None, "none"
    if phone and src in verified_sources | extended_sources:
        return phone.strip()

    if cz:
        ac_z = batch.zid_first_ac.get(cz)
        if ac_z is not None:
            out = _hit(getattr(ac_z, "customer_phone", None), "abandoned_cart_zid")
            if out[0]:
                ext_p, ext_s = out
                if ext_s in verified_sources | extended_sources:
                    return ext_p.strip()

    if sid and slug:
        rr = batch.reason_store_by_session.get(sid)
        out = _hit(
            getattr(rr, "customer_phone", None) if rr else None,
            "cart_recovery_reason_session",
        )
        if out[0]:
            ext_p, ext_s = out
            if ext_s in verified_sources | extended_sources:
                return ext_p.strip()

    if sid:
        rr2 = batch.reason_any_by_session.get(sid)
        out = _hit(
            getattr(rr2, "customer_phone", None) if rr2 else None,
            "cart_recovery_reason_any_store",
        )
        if out[0]:
            ext_p, ext_s = out
            if ext_s in verified_sources | extended_sources:
                return ext_p.strip()

    ph_sess = sent_idx.by_session.get(sid)
    if ph_sess:
        out = _hit(ph_sess, "cart_recovery_log_sent")
        if out[0]:
            ext_p, ext_s = out
            if ext_s in verified_sources | extended_sources:
                return ext_p.strip()
    if cz:
        ph_cart = sent_idx.by_cart.get(cz)
        if ph_cart:
            out = _hit(ph_cart, "cart_recovery_log_sent")
            if out[0]:
                ext_p, ext_s = out
                if ext_s in verified_sources | extended_sources:
                    return ext_p.strip()

    ac_ids = _abandoned_ids_for_recovery_scope_rows(
        sid, cz if cz else None, batch.scope_ab_rows
    )
    if ac_ids:
        for aid_ml in ac_ids:
            ml_ph = batch.ml_phone_by_ac_id.get(int(aid_ml))
            out = _hit(ml_ph, "message_log_whatsapp")
            if out[0]:
                ext_p, ext_s = out
                if ext_s in verified_sources | extended_sources:
                    return ext_p.strip()

    for _ts, peer_ph in (peer_by_session.get(sid) or [])[:48]:
        out = _hit(peer_ph, "abandoned_cart_session_peer")
        if out[0]:
            ext_p, ext_s = out
            if ext_s in verified_sources | extended_sources:
                return ext_p.strip()

    return ""


def build_cust_phone_by_ac_bulk(
    full_rows: list[Any],
    dash_store: Any,
    batch: Any,
) -> dict[int, str]:
    """
    Build abandoned_cart_id -> customer phone map with one in-memory pass.
    No per-row DB access.
    """
    from main import (  # noqa: PLC0415
        _NORMAL_RECOVERY_EXTENDED_PHONE_SOURCES,
        _NORMAL_RECOVERY_SENT_LOG_STATUSES,
        _VERIFIED_WA_RECOVERY_PHONE_SOURCES,
    )
    from services.recovery_message_context_v1 import recovery_key_from_parts  # noqa: PLC0415
    from services.recovery_session_phone import (  # noqa: PLC0415
        get_recovery_customer_phone,
        get_recovery_phone_resolution_source,
    )

    slug = (getattr(batch, "slug", None) or "").strip()
    mem_phone_by_rk: dict[str, str] = {}
    mem_src_by_rk: dict[str, str] = {}
    for ac in full_rows:
        sid = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
        zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
        if not slug or not sid:
            continue
        try:
            rk = recovery_key_from_parts(store_slug=slug, session_id=sid, cart_id=zid)
        except Exception:  # noqa: BLE001
            rk = ""
        if not rk or rk in mem_phone_by_rk:
            continue
        mp = get_recovery_customer_phone(rk)
        if mp:
            mem_phone_by_rk[rk] = mp
            mem_src_by_rk[rk] = get_recovery_phone_resolution_source(rk)

    sent_idx = _build_sent_log_phone_index(
        list(getattr(batch, "logs", None) or []),
        _NORMAL_RECOVERY_SENT_LOG_STATUSES,
    )
    peer_by_session = _build_peer_phone_by_session(
        list(getattr(batch, "peers_non_vip", None) or [])
    )

    cust_map: dict[int, str] = {}
    phone_resolution_prof_record_loop(len(full_rows))
    for ac in full_rows:
        aid = int(getattr(ac, "id", 0) or 0)
        if not aid:
            continue
        cust_map[aid] = _resolve_phone_from_batch_index(
            ac,
            dash_store,
            batch,
            mem_phone_by_rk=mem_phone_by_rk,
            mem_src_by_rk=mem_src_by_rk,
            sent_idx=sent_idx,
            peer_by_session=peer_by_session,
            verified_sources=_VERIFIED_WA_RECOVERY_PHONE_SOURCES,
            extended_sources=_NORMAL_RECOVERY_EXTENDED_PHONE_SOURCES,
            sent_statuses=_NORMAL_RECOVERY_SENT_LOG_STATUSES,
        ).strip()
    return cust_map


__all__ = [
    "AUDIT_BASELINE_PHONE_RESOLUTION_DB_QUERIES_PER_CHECK",
    "build_cust_phone_by_ac_bulk",
    "build_phone_resolution_comparison",
    "phone_resolution_prof_record_db",
    "phone_resolution_prof_record_fallback",
    "phone_resolution_prof_record_loop",
    "phone_resolution_prof_reset",
    "phone_resolution_prof_snapshot",
]
