# -*- coding: utf-8 -*-
"""كاش في الذاكرة لإعدادات الودجيت العامة — مسار المتجر لا ينتظر ‎connection pool‎."""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from extensions import db
from models import CartRecoveryLog

log = logging.getLogger("cartflow")

_SENT_STATUSES_FOR_READY = frozenset({"sent_real", "mock_sent"})
_REFRESH_THROTTLE_SEC = 8.0
_AFTER_STEP1_MAX_KEYS = 500

_lock = threading.RLock()

_store_snapshots: Dict[str, Dict[str, Any]] = {}
_ready_after_step1: Dict[str, bool] = {}

_per_slug_busy: Set[str] = set()
_per_slug_last_schedule: Dict[str, float] = {}
_refresh_fail_until_mono: Dict[str, float] = {}

_signals_installed = False
_REFRESH_FAILURE_COOLDOWN_SEC = 60.0


def normalize_store_slug(store_slug: str) -> str:
    return (store_slug or "").strip()[:255]


def _composite_ready_key(store_slug: str, session_id: str) -> str:
    ss = normalize_store_slug(store_slug)
    sid = (session_id or "").strip()[:512]
    return f"{ss}\x00{sid}"


def _trim_after_step1_map() -> None:
    global _ready_after_step1
    if len(_ready_after_step1) <= _AFTER_STEP1_MAX_KEYS:
        return
    for i, key in enumerate(list(_ready_after_step1.keys())):
        if i >= _AFTER_STEP1_MAX_KEYS // 2:
            break
        _ready_after_step1.pop(key, None)


def install_cart_recovery_ready_signals_once() -> None:
    """يُحمَّل مرة — يحدِّث كاش ‎after_step1‎ بعد إدراج / تحديث ‎CartRecoveryLog‎."""

    global _signals_installed

    def _hydrate_ready_from_recovery_log_target(target: Any) -> None:
        try:
            ss = normalize_store_slug(str(getattr(target, "store_slug", "") or ""))
            sid = (str(getattr(target, "session_id", "") or "")).strip()[:512]
            if not ss or not sid:
                return
            step = getattr(target, "step", None)
            st_raw = getattr(target, "status", None)
            st = str(st_raw) if st_raw is not None else ""
            ck = _composite_ready_key(ss, sid)
            with _lock:
                if step == 1 and st in _SENT_STATUSES_FOR_READY:
                    _trim_after_step1_map()
                    _ready_after_step1[ck] = True
                else:
                    _ready_after_step1.pop(ck, None)
        except Exception:  # noqa: BLE001
            return

    def _mapper_listener(mapper: Any, connection: Any, target: Any) -> None:  # noqa: ARG001
        _hydrate_ready_from_recovery_log_target(target)

    with _lock:
        if _signals_installed:
            return
        event.listen(CartRecoveryLog, "after_insert", _mapper_listener)
        event.listen(CartRecoveryLog, "after_update", _mapper_listener)
        _signals_installed = True


def note_after_step1_from_recovery_log_attrs(
    *, store_slug: str, session_id: str, step: Optional[int], status: str
) -> None:
    """استدعاء صريح بعد ‎commit‎ ناجحة (اختصار يطابق المنطق أعلاه)."""

    ss = normalize_store_slug(store_slug)
    sid = (session_id or "").strip()[:512]
    ck = _composite_ready_key(ss, sid)
    st = str(status or "").strip()
    try:
        sp_i = int(step) if step is not None else None  # type: ignore[arg-type]
    except (TypeError, ValueError):
        sp_i = None
    with _lock:
        if sp_i == 1 and st in _SENT_STATUSES_FOR_READY:
            _trim_after_step1_map()
            _ready_after_step1[ck] = True
        else:
            _ready_after_step1.pop(ck, None)


def build_snapshot_from_store_row(store_row: Optional[Any]) -> Dict[str, Any]:
    from services.cartflow_widget_public_bundle import (
        merge_widget_template_bundle_from_store_row,
    )
    from services.vip_cart import merchant_vip_threshold_int

    tpl = merge_widget_template_bundle_from_store_row(store_row)
    wa: Optional[str] = None
    if store_row is not None:
        w = getattr(store_row, "whatsapp_support_url", None)
        if isinstance(w, str) and w.strip():
            wa = w.strip()[:2048]
    return {
        "template_bundle": tpl,
        "whatsapp_url": wa,
        "vip_threshold": merchant_vip_threshold_int(store_row),
    }


def _public_payload_keys_from_dashboard_row(sess: Any, row: Any) -> List[str]:
    from models import Store

    keys: List[str] = []
    zs = getattr(row, "zid_store_id", None)
    if isinstance(zs, str) and zs.strip():
        keys.append(zs.strip()[:255])
    try:
        top = sess.query(Store.id).order_by(Store.id.desc()).limit(1).scalar()
        rid = getattr(row, "id", None)
        if (
            top is not None
            and rid is not None
            and int(top) == int(rid)  # type: ignore[arg-type]
        ):
            keys.extend(["demo", "default", "cartflow-default-recovery"])
    except Exception:  # noqa: BLE001
        pass
    seen: Set[str] = set()
    out: List[str] = []
    for k in keys:
        kk = normalize_store_slug(k)
        if not kk:
            continue
        if kk in seen:
            continue
        seen.add(kk)
        out.append(kk)
    return out


def update_from_dashboard_store_row(store_row: Any) -> None:
    """استدعَ بعد ثبات إعدادات الودجيت في القاعدة (‎لوحة‎)."""

    if store_row is None:
        return
    snap = build_snapshot_from_store_row(store_row)
    sess = db.session
    ks = _public_payload_keys_from_dashboard_row(sess, store_row)
    with _lock:
        for k in ks:
            _store_snapshots[k] = snap
            _refresh_fail_until_mono.pop(k, None)
    log.info(
        "[WIDGET CONFIG CACHE UPDATED_FROM_DASHBOARD] keys=%s",
        ",".join(ks[:12]) + ("..." if len(ks) > 12 else ""),
    )


def get_snapshot(norm_slug: str) -> Optional[Dict[str, Any]]:
    with _lock:
        got = _store_snapshots.get(norm_slug)
        return dict(got) if isinstance(got, dict) else None


def ready_after_step1_memory(store_slug: str, session_id: str) -> bool:
    ck = _composite_ready_key(store_slug, session_id)
    with _lock:
        return bool(_ready_after_step1.get(ck))


def _is_vip_from_threshold(cart_total: Optional[float], threshold: Optional[int]) -> bool:
    if threshold is None:
        return False
    if threshold < 1:
        return False
    if cart_total is None:
        return False
    try:
        total = float(cart_total)
    except (TypeError, ValueError):
        return False
    return total >= float(threshold)


def ready_http_payload(norm_slug: str, session_id: str, snap: Optional[Dict[str, Any]]):
    """جسم ‎GET /ready‎ — ‎snap‎ فارغ ⇒ قوالب الافتراضي الآمن."""

    aft = ready_after_step1_memory(norm_slug, session_id)
    if snap is None:
        tpl = build_snapshot_from_store_row(None)["template_bundle"]
        return {"ok": True, "after_step1": aft, **tpl}
    tpl = snap.get("template_bundle") or {}
    return {"ok": True, "after_step1": aft, **dict(tpl)}


def public_http_payload(
    norm_slug: str, cart_total: Optional[float], snap: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    ct_out: Optional[float] = None
    is_vip_pub = False
    vip_eval = False
    if cart_total is not None:
        vip_eval = True
        try:
            ct_out = float(cart_total)
        except (TypeError, ValueError):
            ct_out = None
    if snap is None:
        tpl = build_snapshot_from_store_row(None)["template_bundle"]
        return {
            "ok": True,
            "whatsapp_url": None,
            "cart_total": ct_out,
            "is_vip": False,
            "vip_from_cart_total": vip_eval,
            **tpl,
        }
    tpl = snap.get("template_bundle") or {}
    vip_th = snap.get("vip_threshold")
    th_int: Optional[int] = None
    if isinstance(vip_th, int):
        th_int = vip_th
    elif vip_th is not None:
        try:
            th_int = int(vip_th)
        except (TypeError, ValueError):
            th_int = None
    if ct_out is not None:
        is_vip_pub = _is_vip_from_threshold(ct_out, th_int)
    wa = snap.get("whatsapp_url")
    if wa is not None and not (isinstance(wa, str) and wa.strip()):
        wa = None
    return {
        "ok": True,
        "whatsapp_url": wa,
        "cart_total": ct_out,
        "is_vip": is_vip_pub,
        "vip_from_cart_total": vip_eval,
        **dict(tpl),
    }


def _load_snapshot_from_db(norm_slug: str) -> Dict[str, Any]:
    """قراءة فقط من الجداول الموجودة — بدون ‎DDL‎ ولا ‎create_all‎ (مسار خلفية/اختبار)."""

    from services.cartflow_widget_public_store import store_row_for_widget_public_session

    Maker = sessionmaker(bind=db.engine)
    sess = Maker()
    try:
        row = store_row_for_widget_public_session(sess, norm_slug)
        return build_snapshot_from_store_row(row)
    finally:
        sess.close()


def _release_refresh_busy(norm_slug: str) -> None:
    with _lock:
        _per_slug_busy.discard(norm_slug)


def _run_refresh_impl(norm_slug: str) -> bool:
    """يُحدِّث الكاش عند النجاح. عند الخطأ: كتم + تبريد ‎60s‎ دون طوفان إعادة المحاولة."""

    try:
        snap_new = _load_snapshot_from_db(norm_slug)
    except Exception as exc:  # noqa: BLE001
        mono = time.monotonic()
        with _lock:
            _refresh_fail_until_mono[norm_slug] = mono + _REFRESH_FAILURE_COOLDOWN_SEC
        log.warning(
            "[WIDGET CONFIG REFRESH FAILURE_SUPPRESSED] store_slug=%s err=%s",
            norm_slug[:80],
            exc,
        )
        return False
    with _lock:
        _store_snapshots[norm_slug] = snap_new
        _refresh_fail_until_mono.pop(norm_slug, None)
    log.info("[WIDGET CONFIG CACHE REFRESH_SUCCESS] store_slug=%s", norm_slug[:80])
    return True


def maybe_schedule_background_refresh(
    norm_slug: str, background_tasks: Optional[Any]
) -> None:
    """جدولة تحديث من القاعدة خارج مسار الاستجابة — قيد واحد لكل ‎store_slug‎ + خنق زمني."""

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    slug = normalize_store_slug(norm_slug)
    if not slug:
        return
    mono = time.monotonic()
    with _lock:
        fail_until = float(_refresh_fail_until_mono.get(slug) or 0.0)
        if mono < fail_until:
            log.info(
                "[WIDGET CONFIG REFRESH THROTTLED] store_slug=%s cooldown_remaining_s=%.1f",
                slug[:80],
                max(0.0, fail_until - mono),
            )
            return
        if slug in _per_slug_busy:
            return
        last = float(_per_slug_last_schedule.get(slug) or 0.0)
        if mono - last < _REFRESH_THROTTLE_SEC:
            return
        _per_slug_last_schedule[slug] = mono
        _per_slug_busy.add(slug)
    log.info("[WIDGET CONFIG CACHE REFRESH_SCHEDULED] store_slug=%s", slug[:80])

    def _job() -> None:
        try:
            _run_refresh_impl(slug)
        finally:
            _release_refresh_busy(slug)

    try:
        if background_tasks is not None:
            background_tasks.add_task(_job)
            return
    except Exception:  # noqa: BLE001
        _release_refresh_busy(slug)
        raise

    threading.Thread(target=_job, daemon=True).start()


def warmup_snapshot_sync_pytest(norm_slug: str) -> None:
    """في ‎pytest‎ فقط — يملأ الكاش قبل الاستجابة حتى لا تتلاشى المنطولة مقابل الافتراضي."""

    slug = normalize_store_slug(norm_slug)
    if not slug or not os.environ.get("PYTEST_CURRENT_TEST"):
        return
    _run_refresh_impl(slug)

