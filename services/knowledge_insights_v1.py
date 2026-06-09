# -*- coding: utf-8 -*-
"""
Knowledge Layer v1 — metrics → evidence-based insights (no DB access).
"""
from __future__ import annotations

from typing import Any, Optional

from services.knowledge_metrics_v1 import KnowledgeMetricsBundle
from services.knowledge_types_v1 import (
    CATEGORY_CONVERSION,
    CATEGORY_HESITATION,
    CATEGORY_RECOVERY,
    CATEGORY_STORE_HEALTH,
    CATEGORY_TRAFFIC,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    HESITATION_BUCKETS,
    KnowledgeInsight,
    MIN_CART_SAMPLE,
    MIN_HESITATION_SAMPLE,
    MIN_RECOVERY_SAMPLE,
    SEVERITY_INFO,
    SEVERITY_NOTICE,
    SEVERITY_WARNING,
    confidence_from_sample,
    data_window_payload,
    insufficient_insight,
)


def _dw(metrics: KnowledgeMetricsBundle) -> dict[str, Any]:
    return data_window_payload(
        window_days=metrics.window_days,
        window_start=metrics.window_start,
        window_end=metrics.window_end,
    )


def build_traffic_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    dw = _dw(metrics)
    tables = ["abandoned_carts"]

    if not metrics.visitor_data_available:
        return [
            insufficient_insight(
                insight_key="traffic_visitor_unavailable",
                category=CATEGORY_TRAFFIC,
                title_ar="بيانات الزوار غير متوفرة",
                message_ar=(
                    "CartFlow لا يرى عدد زوار المتجر حالياً — "
                    "لا يمكن قياس حجم الزيارات من هذه البيانات."
                ),
                evidence={
                    "visitor_data_available": False,
                    "cart_count": metrics.cart_count,
                    "note": "visitor_data_unavailable",
                },
                data_window=dw,
                sample_size=metrics.cart_count,
                source_tables=tables,
                recommended_action_ar=(
                    "قد تحتاج إلى مراجعة إعدادات التتبع إذا استمر نقص البيانات."
                ),
            )
        ]

    return []


def build_conversion_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    dw = _dw(metrics)
    insights: list[KnowledgeInsight] = []

    gaps: list[str] = []
    if not metrics.visitor_data_available:
        gaps.append("visitor_data_unavailable")
    if not metrics.checkout_data_available:
        gaps.append("checkout_data_unavailable")

    funnel_evidence: dict[str, Any] = {
        "cart_count": metrics.cart_count,
        "checkout_signal_count": metrics.checkout_signal_count,
        "purchase_count": metrics.purchase_count,
        "gaps": gaps,
    }

    if gaps:
        gap_msgs = []
        if "visitor_data_unavailable" in gaps:
            gap_msgs.append("بيانات الزوار غير متوفرة")
        if "checkout_data_unavailable" in gaps:
            gap_msgs.append("بيانات مرحلة الدفع غير متوفرة")

        insights.append(
            insufficient_insight(
                insight_key="conversion_funnel_gaps",
                category=CATEGORY_CONVERSION,
                title_ar="فجوات في مسار التحويل",
                message_ar=(
                    "مسار التحويل الكامل غير مرئي بالكامل: "
                    + "؛ ".join(gap_msgs)
                    + "."
                ),
                evidence=funnel_evidence,
                data_window=dw,
                sample_size=metrics.cart_count,
                source_tables=["abandoned_carts", "purchase_truth_records"],
                recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
            )
        )

    if metrics.cart_count >= MIN_CART_SAMPLE and metrics.purchase_count > 0:
        rate = round(metrics.purchase_count / max(metrics.cart_count, 1), 4)
        conf = confidence_from_sample(metrics.cart_count, minimum=MIN_CART_SAMPLE)
        insights.append(
            KnowledgeInsight(
                insight_key="conversion_cart_to_purchase",
                category=CATEGORY_CONVERSION,
                severity=SEVERITY_INFO,
                title_ar="تحويل السلة إلى شراء (مرئي)",
                message_ar=(
                    f"سُجّل {metrics.purchase_count} عملية شراء مؤكدة مقابل "
                    f"{metrics.cart_count} سلة في نافذة البيانات."
                ),
                evidence={**funnel_evidence, "cart_to_purchase_rate": rate},
                confidence=conf,
                data_window=dw,
                sample_size=metrics.cart_count,
                source_tables=["abandoned_carts", "purchase_truth_records"],
                recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
            )
        )
    elif metrics.cart_count == 0:
        insights.append(
            insufficient_insight(
                insight_key="conversion_no_carts",
                category=CATEGORY_CONVERSION,
                title_ar="لا توجد سلال في النافذة",
                message_ar="لم تُسجَّل سلات مهجورة في نافذة البيانات الحالية.",
                evidence=funnel_evidence,
                data_window=dw,
                sample_size=0,
                source_tables=["abandoned_carts"],
            )
        )

    return insights


def build_hesitation_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    dw = _dw(metrics)
    total = metrics.hesitation_total
    dist = metrics.hesitation_distribution

    if total < MIN_HESITATION_SAMPLE:
        return [
            insufficient_insight(
                insight_key="hesitation_insufficient_sample",
                category=CATEGORY_HESITATION,
                title_ar="بيانات التردد محدودة",
                message_ar=(
                    f"عدد أسباب التردد المسجّلة ({total}) أقل من الحد الأدنى "
                    f"({MIN_HESITATION_SAMPLE}) لاستنتاج موثوق."
                ),
                evidence={"hesitation_total": total, "distribution": dist},
                data_window=dw,
                sample_size=total,
                source_tables=["cart_recovery_reasons"],
            )
        ]

    top_reason = max(dist.items(), key=lambda kv: kv[1])[0]
    top_count = dist[top_reason]
    conf = confidence_from_sample(total, minimum=MIN_HESITATION_SAMPLE)

    pct = round(100.0 * top_count / total, 1)
    distribution_pct = {
        k: round(100.0 * v / total, 1) for k, v in sorted(dist.items(), key=lambda x: -x[1])
    }

    return [
        KnowledgeInsight(
            insight_key="hesitation_top_reason",
            category=CATEGORY_HESITATION,
            severity=SEVERITY_INFO,
            title_ar="سبب التردد الأبرز",
            message_ar=(
                f"السبب الأكثر تسجيلاً هو «{top_reason}» "
                f"({top_count} من {total} — {pct}%)."
            ),
            evidence={
                "top_reason": top_reason,
                "top_count": top_count,
                "hesitation_total": total,
                "distribution": dist,
                "distribution_pct": distribution_pct,
            },
            confidence=conf,
            data_window=dw,
            sample_size=total,
            source_tables=["cart_recovery_reasons"],
            recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
        ),
        KnowledgeInsight(
            insight_key="hesitation_distribution",
            category=CATEGORY_HESITATION,
            severity=SEVERITY_INFO,
            title_ar="توزيع أسباب التردد",
            message_ar=(
                "توزيع أسباب التردد المسجّلة من الودجت خلال نافذة البيانات."
            ),
            evidence={
                "distribution": dist,
                "distribution_pct": distribution_pct,
                "buckets": sorted(HESITATION_BUCKETS),
            },
            confidence=conf,
            data_window=dw,
            sample_size=total,
            source_tables=["cart_recovery_reasons"],
            recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
        ),
    ]


def build_recovery_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    dw = _dw(metrics)
    activity_total = (
        metrics.recovery_messages_sent
        + metrics.recovery_failed
        + metrics.recovery_ignored
        + metrics.recovery_stopped
    )

    if activity_total < MIN_RECOVERY_SAMPLE:
        return [
            insufficient_insight(
                insight_key="recovery_insufficient_sample",
                category=CATEGORY_RECOVERY,
                title_ar="نشاط الاسترجاع محدود",
                message_ar=(
                    f"عدد أحداث الاسترجاع ({activity_total}) أقل من الحد الأدنى "
                    f"({MIN_RECOVERY_SAMPLE}) لتقييم الفعالية."
                ),
                evidence={
                    "messages_sent": metrics.recovery_messages_sent,
                    "replies": metrics.recovery_replies,
                    "returns": metrics.recovery_returns,
                    "purchases": metrics.recovery_purchases,
                    "ignored": metrics.recovery_ignored,
                    "stopped": metrics.recovery_stopped,
                    "failed": metrics.recovery_failed,
                },
                data_window=dw,
                sample_size=activity_total,
                source_tables=["cart_recovery_logs", "recovery_truth_timeline_events"],
            )
        ]

    conf = confidence_from_sample(activity_total, minimum=MIN_RECOVERY_SAMPLE)
    effectiveness: Optional[float] = None
    if metrics.recovery_messages_sent > 0 and metrics.recovery_purchases > 0:
        effectiveness = round(
            metrics.recovery_purchases / metrics.recovery_messages_sent, 4
        )

    bottlenecks: list[dict[str, Any]] = []
    for key, label, count in (
        ("failed", "failed", metrics.recovery_failed),
        ("ignored", "ignored", metrics.recovery_ignored),
        ("stopped", "stopped", metrics.recovery_stopped),
        ("no_reply", "no_reply", max(0, metrics.recovery_messages_sent - metrics.recovery_replies)),
    ):
        if count > 0:
            bottlenecks.append({"key": key, "label": label, "count": count})
    bottlenecks.sort(key=lambda x: -int(x["count"]))

    insights: list[KnowledgeInsight] = [
        KnowledgeInsight(
            insight_key="recovery_activity_summary",
            category=CATEGORY_RECOVERY,
            severity=SEVERITY_INFO,
            title_ar="ملخص نشاط الاسترجاع",
            message_ar=(
                f"رسائل مُرسَلة: {metrics.recovery_messages_sent}؛ "
                f"ردود: {metrics.recovery_replies}؛ "
                f"عائدون للموقع: {metrics.recovery_returns}؛ "
                f"مشتريات مؤكدة: {metrics.recovery_purchases}."
            ),
            evidence={
                "messages_sent": metrics.recovery_messages_sent,
                "replies": metrics.recovery_replies,
                "returns": metrics.recovery_returns,
                "purchases": metrics.recovery_purchases,
                "ignored": metrics.recovery_ignored,
                "stopped": metrics.recovery_stopped,
                "failed": metrics.recovery_failed,
                "effectiveness_purchase_per_message": effectiveness,
            },
            confidence=conf if effectiveness else CONFIDENCE_LOW,
            data_window=dw,
            sample_size=activity_total,
            source_tables=[
                "cart_recovery_logs",
                "recovery_truth_timeline_events",
                "purchase_truth_records",
            ],
            recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
        )
    ]

    if bottlenecks:
        top = bottlenecks[0]
        insights.append(
            KnowledgeInsight(
                insight_key="recovery_bottleneck",
                category=CATEGORY_RECOVERY,
                severity=SEVERITY_NOTICE if top["key"] == "failed" else SEVERITY_INFO,
                title_ar="عنق زجاجة في الاسترجاع",
                message_ar=(
                    f"أبرز نقطة ضغط مسجّلة: {top['label']} ({top['count']} حدث)."
                ),
                evidence={"bottlenecks": bottlenecks},
                confidence=conf,
                data_window=dw,
                sample_size=activity_total,
                source_tables=["cart_recovery_logs", "recovery_truth_timeline_events"],
                recommended_action_ar="تأكد أن بيانات المتجر تصل بشكل صحيح.",
            )
        )

    return insights


def build_store_health_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    dw = _dw(metrics)
    insights: list[KnowledgeInsight] = []
    signals: list[str] = []

    if metrics.cart_count == 0:
        signals.append("not_enough_cart_data")
    if metrics.carts_with_phone == 0 and metrics.cart_count > 0:
        signals.append("not_enough_phone_data")
    if metrics.recovery_scheduled_active > 0 or metrics.recovery_messages_sent > 0:
        signals.append("recovery_is_running")
    if metrics.purchase_truth_rows > 0:
        signals.append("purchase_truth_exists")
    if metrics.lifecycle_closure_rows > 0:
        signals.append("lifecycle_truth_exists")

    limited = (
        metrics.cart_count < MIN_CART_SAMPLE
        and metrics.hesitation_total < MIN_HESITATION_SAMPLE
        and metrics.recovery_messages_sent < MIN_RECOVERY_SAMPLE
    )
    if limited:
        signals.append("data_too_limited_for_reliable_insight")

    if not signals:
        signals.append("baseline_ok")

    severity = SEVERITY_WARNING if "data_too_limited_for_reliable_insight" in signals else SEVERITY_INFO
    message_parts = []
    if "not_enough_cart_data" in signals:
        message_parts.append("لا توجد سلات كافية في النافذة.")
    if "not_enough_phone_data" in signals:
        message_parts.append("معظم السلات بدون رقم عميل.")
    if "recovery_is_running" in signals:
        message_parts.append("مسار الاسترجاع نشط.")
    if "purchase_truth_exists" in signals:
        message_parts.append("توجد سجلات Purchase Truth.")
    if "lifecycle_truth_exists" in signals:
        message_parts.append("توجد سجلات Lifecycle Truth.")
    if "data_too_limited_for_reliable_insight" in signals:
        message_parts.append("البيانات محدودة لرؤية موثوقة.")

    insights.append(
        KnowledgeInsight(
            insight_key="store_health_overview",
            category=CATEGORY_STORE_HEALTH,
            severity=severity,
            title_ar="صحة بيانات المتجر",
            message_ar=" ".join(message_parts) or "البيانات الأساسية متاحة.",
            evidence={"signals": signals, "metrics": metrics.to_dict()},
            confidence=CONFIDENCE_INSUFFICIENT if limited else CONFIDENCE_LOW,
            data_window=dw,
            sample_size=metrics.cart_count,
            source_tables=metrics.source_tables,
            recommended_action_ar=(
                "تأكد أن بيانات المتجر تصل بشكل صحيح."
                if limited
                else "راقب هذا المؤشر خلال الأيام القادمة."
            ),
        )
    )

    # Traffic trend visibility (cart-based demand proxy only)
    if metrics.cart_count > 0 or metrics.prev_cart_count > 0:
        delta = metrics.cart_count - metrics.prev_cart_count
        trend = "stable"
        if delta > 0:
            trend = "up"
        elif delta < 0:
            trend = "down"
        insights.append(
            KnowledgeInsight(
                insight_key="traffic_cart_demand_trend",
                category=CATEGORY_TRAFFIC,
                severity=SEVERITY_INFO,
                title_ar="اتجاه الطلب (سلات مهجورة)",
                message_ar=(
                    f"سلات الفترة الحالية: {metrics.cart_count}؛ "
                    f"الفترة السابقة: {metrics.prev_cart_count} "
                    f"(اتجاه: {trend}). "
                    "هذا مؤشر طلب من CartFlow وليس عدد زوار."
                ),
                evidence={
                    "cart_count": metrics.cart_count,
                    "prev_cart_count": metrics.prev_cart_count,
                    "trend": trend,
                    "visitor_data_available": False,
                },
                confidence=confidence_from_sample(
                    metrics.cart_count + metrics.prev_cart_count,
                    minimum=MIN_CART_SAMPLE,
                ),
                data_window=dw,
                sample_size=metrics.cart_count,
                source_tables=["abandoned_carts"],
                recommended_action_ar="راقب هذا المؤشر خلال الأيام القادمة.",
            )
        )

    return insights


def build_all_insights(metrics: KnowledgeMetricsBundle) -> list[KnowledgeInsight]:
    out: list[KnowledgeInsight] = []
    out.extend(build_traffic_insights(metrics))
    out.extend(build_conversion_insights(metrics))
    out.extend(build_hesitation_insights(metrics))
    out.extend(build_recovery_insights(metrics))
    out.extend(build_store_health_insights(metrics))
    return out
