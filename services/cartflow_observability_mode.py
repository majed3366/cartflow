# -*- coding: utf-8 -*-
"""
Central observability knob: ‎CARTFLOW_OBSERVABILITY_MODE‎ (‎off‎ | ‎basic‎ | ‎debug‎).

‎off‎ افتراضي — يطبِّق أيضاً سياسات التشغيل على وسوم التشخيص القديمة.

لا يؤثر على منطق الاسترداد أو الـ‎API‎؛ قراءة ‎ENV‎ وسجلات فقط.
"""

from __future__ import annotations

import logging
import os
from typing import Final, Literal

log = logging.getLogger("cartflow")

_MODE_ENV = "CARTFLOW_OBSERVABILITY_MODE"

_OFF_TRUTHY: Final = frozenset({"0", "false", "no", "off"})
_ON_TRUTHY: Final = frozenset({"1", "true", "yes", "on"})


def _strip_lower(raw: str | None) -> str:
    return (raw or "").strip().lower()


def observability_mode() -> Literal["off", "basic", "debug"]:
    raw = _strip_lower(os.getenv(_MODE_ENV))
    if raw in ("", "off"):
        return "off"
    if raw in ("basic", "standard", "summary"):
        return "basic"
    if raw in ("debug", "deep", "verbose", "diag", "diagnostics"):
        return "debug"
    if raw:
        log.warning(
            "[CARTFLOW_OBSERVABILITY] invalid_%s=%r defaulting_to=off",
            _MODE_ENV,
            (os.getenv(_MODE_ENV) or "")[:80],
        )
    return "off"


def observability_request_sql_audit_active() -> bool:
    """عداد الاستعلامات لكل طلب + مستمع ‎SQL‎؛ يفعِّل مع ‎basic‎ أو ‎debug‎ ما لم يفرض التعطيل."""
    om = observability_mode()
    if om == "off":
        return False
    lg = _strip_lower(os.getenv("CARTFLOW_DB_REQUEST_AUDIT"))
    if lg in _OFF_TRUTHY:
        return False
    return om in ("basic", "debug")


def observability_middleware_verbose_db_request_logs() -> bool:
    """سطور ‎[DB REQUEST START/END/COUNT]‎ — ‎debug‎ فقط."""
    return observability_request_sql_audit_active() and observability_mode() == "debug"


def observability_db_audit_leak_and_nesting_warnings() -> bool:
    """تحذيرات التداخل / تسرب الجلسة — ‎debug‎ فقط لتقليل الضوضاء."""
    return observability_request_sql_audit_active() and observability_mode() == "debug"


def observability_dashboard_route_endpoint_profile_enabled() -> bool:
    """‎[DASHBOARD PROFILE]‎ لكل نقطة طرفية — ‎debug‎."""
    return observability_mode() == "debug"


def observability_emit_dashboard_shell_profile() -> bool:
    """‎[DASHBOARD SHELL PROFILE]‎ — ‎debug‎."""
    return observability_mode() == "debug"


def observability_emit_dashboard_section_profile() -> bool:
    """‎[DASHBOARD SECTION PROFILE]‎ — ‎basic‎ أو ‎debug‎."""
    return observability_mode() in ("basic", "debug")


def observability_emit_normal_carts_aggregate_profile() -> bool:
    """‎[NORMAL CARTS PROFILE]‎ — ‎basic‎ أو ‎debug‎."""
    return observability_mode() in ("basic", "debug")


def observability_emit_cart_event_profile() -> bool:
    """‎[CART EVENT PROFILE]‎ — ‎basic‎ أو ‎debug‎."""
    return observability_mode() in ("basic", "debug")


def observability_emit_pre_cart_event_profile() -> bool:
    """‎[PRE CART EVENT PROFILE]‎ خطوات دقيقة لـ‎cart-event‎ — ‎debug‎ فقط."""
    return observability_mode() == "debug"


def observability_emit_cart_sync_profile() -> bool:
    """‎[CART SYNC PROFILE]‎ — ‎debug‎ فقط."""
    return observability_mode() == "debug"


def observability_cartflow_session_consistency_log_enabled() -> bool:
    """خطوط ‎[CARTFLOW SESSION]‎ مع ‎CARTFLOW_SESSION_CONSISTENCY_LOG=1‎ — يُكمَد بـ‎basic/debug‎."""
    if observability_mode() == "off":
        return False
    return _strip_lower(os.getenv("CARTFLOW_SESSION_CONSISTENCY_LOG")) in _ON_TRUTHY


def observability_normal_carts_subprofiler_enabled() -> bool:
    """‎[NORMAL CARTS SUBPROFILE/TOP]‎ — ‎debug‎ ما لم يفرض الإيقاف صراحة."""
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_NORMAL_CARTS_SUBPROFILE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_dashboard_summary_subprofiler_enabled() -> bool:
    """‎[DASHBOARD SUMMARY SUBPROFILE/TOP]‎."""
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_DASHBOARD_SUMMARY_SUBPROFILE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_stall_trace_enabled() -> bool:
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_STALL_TRACE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_merchant_dashboard_batch_reads_trace_enabled() -> bool:
    """‎MERCHANT_BATCH_READS_*‎ خطوات دقيقة."""
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_MERCHANT_BATCH_READS_TRACE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_peers_sql_explain_enabled() -> bool:
    """شرح ‎SQL‎ للـpeers؛ يفرض أيضاً المتغير التاريخي لتجنب تسرب الـ‎IN‎ literals عرضياً."""
    if observability_mode() != "debug":
        return False
    return _strip_lower(os.getenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG")) in _ON_TRUTHY


def observability_lightweight_alert_list_trace_enabled() -> bool:
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_LIGHTWEIGHT_ALERT_LIST_TRACE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_stale_meta_trace_enabled() -> bool:
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_STALE_META_TRACE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_queued_followup_schema_inspection_enabled() -> bool:
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_QUEUED_FOLLOWUP_SCHEMA_INSPECTION"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_queue_readiness_log_enabled() -> bool:
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_QUEUE_READINESS_LOG"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_provider_readiness_diag_enabled() -> bool:
    """خطوط ‎[CARTFLOW PROVIDER]‎ وما شابها عند تشغيل المسار."""
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_PROVIDER_READINESS_LOG"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_structured_health_dashboard_log_enabled() -> bool:
    """
    سجلات صحة مهيّأة بوضوح — تعمل في ‎basic‎ أو ‎debug‎ عند ‎CARTFLOW_STRUCTURED_HEALTH_LOG=1‎
    (‎off‎ يطفئها مهما كانت المتغيرات الفرعية).
    """
    if observability_mode() == "off":
        return False
    return _strip_lower(os.getenv("CARTFLOW_STRUCTURED_HEALTH_LOG")) in _ON_TRUTHY


def observability_wa_readiness_step_profiler_enabled() -> bool:
    """خطوط ‎[WA READINESS STEP/TOP]‎."""
    if observability_mode() != "debug":
        return False
    v = _strip_lower(os.getenv("CARTFLOW_WA_READINESS_STEP_PROFILE"))
    if v in _OFF_TRUTHY:
        return False
    return True


def observability_diag_log(logger: logging.Logger, level: int, fmt: str, *args: object) -> None:
    """سجل واحد — بدون ‎print‎ مزدوج."""
    try:
        logger.log(level, fmt, *args)
    except Exception:  # noqa: BLE001
        pass

