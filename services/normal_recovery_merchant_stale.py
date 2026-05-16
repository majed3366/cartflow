# -*- coding: utf-8 -*-
"""تصنيف «خامل» لعرض التاجر — قراءة فقط؛ بدون حذف أو إخفاء عشوائي."""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog

from services.normal_recovery_merchant_view_config import (
    normal_recovery_merchant_stale_config,
)

log = logging.getLogger("cartflow")


def stale_meta_trace_enabled() -> bool:
    """سجلات ‎[MERCHANT_GROUP_STALE_TRACE]‎ فقط؛ ‎CARTFLOW_STALE_META_TRACE=0‎ يعطّل."""
    v = (os.getenv("CARTFLOW_STALE_META_TRACE") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    try:
        from services.db_request_audit import audit_enabled

        return audit_enabled()
    except Exception:  # noqa: BLE001
        return False


def queued_followup_schema_inspection_enabled() -> bool:
    """
    ‎[QUEUED_FOLLOWUP_SCHEMA_INSPECT]‎ لتأكيد استدعاء ‎db.create_all()‎ داخل ‎_has_recent_queued_followup‎.
    ‎CARTFLOW_QUEUED_FOLLOWUP_SCHEMA_INSPECTION=0‎ يعطّل؛ غير محدّد ⇒ ‎audit_enabled()‎.
    """
    v = (os.getenv("CARTFLOW_QUEUED_FOLLOWUP_SCHEMA_INSPECTION") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    try:
        from services.db_request_audit import audit_enabled

        return audit_enabled()
    except Exception:  # noqa: BLE001
        return False


def _emit_queued_followup_schema_inspect(
    *,
    path: str,
    store_slug_prefix: str,
    grp_len: int,
    cond_count: int,
    create_all_executed: bool,
    q0: Optional[int],
    q_after_create_all: Optional[int],
    q_end: Optional[int],
    caller: str,
) -> None:
    ca = str(bool(create_all_executed)).lower()
    dq_total = "n/a"
    dq_create_all_phase = "n/a"
    if q0 is not None and q_end is not None:
        dq_total = str(max(0, int(q_end) - int(q0)))
    if (
        q0 is not None
        and q_after_create_all is not None
        and bool(create_all_executed)
    ):
        dq_create_all_phase = str(max(0, int(q_after_create_all) - int(q0)))
    line = (
        f"[QUEUED_FOLLOWUP_SCHEMA_INSPECT] caller={caller} path={path}"
        f" store_slug_prefix={(store_slug_prefix or '-')[:64]}"
        f" grp_len={int(grp_len)} recovery_log_cond_count={int(cond_count)}"
        f" db_create_all_executed={ca}"
        f" ddl_note=extensions.db_create_all_maps_to_SQLAlchemy_metadata_create_all_implicit_schema_sync"
        f" queries_delta_total={dq_total}"
        f" queries_delta_through_create_all={dq_create_all_phase}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _peek_audit_query_count() -> Optional[int]:
    try:
        from services.db_request_audit import peek_request_audit_bucket_for_profile

        b = peek_request_audit_bucket_for_profile()
        if b is None:
            return None
        return int(b.get("queries") or 0)
    except Exception:  # noqa: BLE001
        return None


def _emit_merchant_group_stale_trace(
    *,
    pick_index: Optional[int],
    picked_groups_total: Optional[int],
    grp_len: int,
    coarse_in: str,
    path_out: str,
    checker_state: str,
    recovery_log_cond_count: int,
    window_minutes: Optional[int],
    age_minutes: Optional[float],
    stale_flag_out: bool,
    queries_delta_str: str,
    duration_ms: float,
) -> None:
    tot = ""
    if picked_groups_total is not None:
        tot = f" picked_groups_total={int(picked_groups_total)}"
    line = (
        f"[MERCHANT_GROUP_STALE_TRACE] pick_idx={pick_index}{tot}"
        f" grp_len={int(grp_len)} coarse={(coarse_in or '-')[:40]}"
        f" path={path_out}"
        f" checker_state={checker_state}"
        f" recovery_log_conds={int(recovery_log_cond_count)}"
        f" window_minutes={(window_minutes if window_minutes is not None else 'n/a')}"
        f" age_minutes={(round(age_minutes, 2) if age_minutes is not None else 'n/a')}"
        f" stale_flag={str(bool(stale_flag_out)).lower()}"
        f" queries_delta={queries_delta_str}"
        f" duration_ms={round(duration_ms, 3)}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _cart_recovery_log_conds_for_abandoned(ac: AbandonedCart) -> list[Any]:
    """نفس منطق ‎main._cart_recovery_log_filters_for_abandoned_cart‎ (بدون استيراد دائري)."""
    sess = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
    zid = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
    conds: list[Any] = []
    if sess:
        conds.append(CartRecoveryLog.session_id == sess)
    if zid:
        conds.append(CartRecoveryLog.cart_id == zid)
        conds.append(CartRecoveryLog.session_id == zid)
    return conds


def _group_activity_utc(
    grp_sorted: list[AbandonedCart],
    activity_map: dict[int, datetime],
) -> datetime:
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    ts = [
        activity_map.get(int(getattr(ac, "id", 0) or 0), epoch)
        for ac in grp_sorted
        if ac is not None
    ]
    return max(ts) if ts else epoch


def _has_recent_queued_followup(
    grp_sorted: list[AbandonedCart],
    *,
    store_slug: str,
    since_utc: datetime,
) -> bool:
    ins = queued_followup_schema_inspection_enabled()
    q0 = _peek_audit_query_count() if ins else None
    q_after_create_all: Optional[int] = None
    inspect_path = ""
    inspect_slug = ""
    inspect_grp_len = len(grp_sorted) if grp_sorted else 0
    inspect_cond_cnt = 0
    create_all_hit = False

    ss = (store_slug or "").strip()[:255]
    try:
        if not ss or not grp_sorted:
            inspect_path = "early_return_no_slug_or_empty_group"
            return False
        inspect_slug = ss
        ac0 = grp_sorted[0]
        conds = _cart_recovery_log_conds_for_abandoned(ac0)
        inspect_cond_cnt = len(conds)
        if not conds:
            inspect_path = (
                "early_return_no_recovery_log_conds_skip_create_all_and_select"
            )
            return False
        inspect_path = "db_create_all_then_select_recent_queued_recovery_log_first"
        create_all_hit = True
        db.create_all()
        q_after_create_all = _peek_audit_query_count() if ins else None
        row = (
            db.session.query(CartRecoveryLog.id)
            .filter(
                CartRecoveryLog.store_slug == ss,
                CartRecoveryLog.status == "queued",
                CartRecoveryLog.created_at >= since_utc,
                or_(*conds),
            )
            .first()
        )
        return row is not None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        inspect_path = f"{inspect_path or 'during_followup'}|exception_rollback"
        return False
    finally:
        if ins:
            q_end = _peek_audit_query_count()
            _emit_queued_followup_schema_inspect(
                path=(inspect_path or "unknown_exit"),
                store_slug_prefix=inspect_slug or ss,
                grp_len=int(inspect_grp_len),
                cond_count=int(inspect_cond_cnt),
                create_all_executed=bool(create_all_hit),
                q0=q0,
                q_after_create_all=q_after_create_all,
                q_end=q_end,
                caller="merchant_group_stale_meta_via__has_recent_queued_followup",
            )


def merchant_group_stale_meta(
    grp_sorted: list[AbandonedCart],
    *,
    store_slug: str,
    activity_map: dict[int, datetime],
    coarse: str,
    now_utc: Optional[datetime] = None,
    diag_pick_index: Optional[int] = None,
    diag_picked_groups_total: Optional[int] = None,
) -> tuple[bool, dict[str, Any]]:
    """
    خامل تجاري: ‎pending/sent‎ + تجاوز النافذة + لا ‎queued‎ بعد آخر نشاط معنٍ.
    يُمرَّر ‎coarse‎ من محرك اللوحة (نفس ‎_normal_recovery_coarse_status‎).

    diagnostics: ضع ‎diag_pick_index‎ عند ‎stale_meta_trace_enabled()‎ — سطر ‎[MERCHANT_GROUP_STALE_TRACE]‎ فقط؛ لا يغيّر الحساب.
    """
    meta: dict[str, Any] = {
        "stale": False,
        "stale_reason": "",
        "age_minutes": None,
        "last_activity_at": None,
        "merchant_stale_hint_ar": "",
        "merchant_stale_surface": "",
    }
    do_trace = diag_pick_index is not None
    q0: Optional[int] = None
    t0 = 0.0
    path = "unknown"
    stale_result = False
    cr_trim = ""
    grp_len_effective = len(grp_sorted) if grp_sorted else 0
    win_live: Optional[int] = None
    age_eff: Optional[float] = None
    cond_cnt = 0
    checker_state = ""

    try:
        if do_trace:
            q0 = _peek_audit_query_count()
            t0 = time.perf_counter()

        cfg = normal_recovery_merchant_stale_config()
        if not cfg.get("stale_archive_enabled"):
            path = "stale_archive_disabled"
            checker_state = "checker_not_needed_stale_archive_off"
            return False, meta
        if not grp_sorted:
            path = "empty_group"
            checker_state = "checker_not_needed_empty_row_group"
            return False, meta

        cr_trim = (coarse or "").strip().lower()
        if cr_trim not in ("pending", "sent"):
            path = f"coarse_skip:{cr_trim or 'unset'}"
            checker_state = "checker_not_needed_coarse_only_pending_sent"
            return False, meta

        now = now_utc or datetime.now(timezone.utc)
        last_act = _group_activity_utc(grp_sorted, activity_map)
        if last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=timezone.utc)
        else:
            last_act = last_act.astimezone(timezone.utc)
        meta["last_activity_at"] = last_act.isoformat()
        age_min = max(0.0, (now - last_act).total_seconds() / 60.0)
        age_eff = age_min
        meta["age_minutes"] = round(age_min, 1)

        win_live = (
            int(cfg["active_pending_window_minutes"])
            if cr_trim == "pending"
            else int(cfg["active_sent_window_minutes"])
        )
        if age_min <= float(win_live):
            path = "within_active_window"
            checker_state = "checker_not_needed_still_inside_archive_window"
            return False, meta

        cond_cnt = len(_cart_recovery_log_conds_for_abandoned(grp_sorted[0]))
        since = last_act - timedelta(minutes=2)
        hq = _has_recent_queued_followup(
            grp_sorted, store_slug=store_slug, since_utc=since
        )
        if hq:
            path = "queued_followup_present"
            checker_state = "checker_positive_recent_queued_recovery_log_row"
            meta["stale_reason"] = "queued_followup_present"
            return False, meta

        if cond_cnt <= 0:
            checker_state = (
                "checker_negative_no_session_cart_predicate_no_recovery_log_touch"
            )
        else:
            checker_state = (
                "checker_negative_recent_queued_query_no_hit_then_mark_stale"
            )

        meta["stale"] = True
        stale_result = True
        if cr_trim == "pending":
            path = "marked_stale_pending"
            meta["stale_reason"] = "stale_pending_no_activity"
            meta["merchant_stale_surface"] = "expired_waiting"
            meta["merchant_stale_hint_ar"] = (
                "لم يتفاعل العميل بعد — تم نقلها إلى السجل."
            )
        else:
            path = "marked_stale_sent"
            meta["stale_reason"] = "stale_sent_no_customer_signal"
            meta["merchant_stale_surface"] = "stale_active"
            meta["merchant_stale_hint_ar"] = (
                "لم يظهر تفاعل بعد آخر رسالة — تم نقلها إلى السجل."
            )
        return True, meta
    finally:
        if do_trace:
            q1 = _peek_audit_query_count()
            if q0 is None or q1 is None:
                dq_s = "n/a"
            else:
                dq_s = str(max(0, int(q1) - int(q0)))
            elapsed_ms = (time.perf_counter() - float(t0)) * 1000.0
            _emit_merchant_group_stale_trace(
                pick_index=diag_pick_index,
                picked_groups_total=diag_picked_groups_total,
                grp_len=grp_len_effective,
                coarse_in=cr_trim or (coarse or ""),
                path_out=path,
                checker_state=checker_state or "unset",
                recovery_log_cond_count=cond_cnt,
                window_minutes=win_live,
                age_minutes=age_eff,
                stale_flag_out=stale_result,
                queries_delta_str=dq_s,
                duration_ms=elapsed_ms,
            )
