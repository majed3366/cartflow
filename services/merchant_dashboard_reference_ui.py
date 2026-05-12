# -*- coding: utf-8 -*-
"""عرض لوحة التاجر المرجعية — دوال عرض فقط دون استعلامات ثقيلة."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

_WEEKDAYS_AR = (
    "الاثنين",
    "الثلاثاء",
    "الأربعاء",
    "الخميس",
    "الجمعة",
    "السبت",
    "الأحد",
)


def merchant_ar_weekday_date_header(now_utc: datetime) -> str:
    """عنوان تاريخ عربي بسيط للشريط العلوي (يوم + تاريخ رقمي)."""
    d = now_utc
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    else:
        d = d.astimezone(timezone.utc)
    wd = _WEEKDAYS_AR[int(d.weekday())]
    return f"{wd}، {int(d.day)} {int(d.month)} {int(d.year)}"


def merchant_relative_time_arabic(
    dt: Optional[datetime],
    *,
    now_utc: datetime,
) -> str:
    if dt is None:
        return "—"
    a = dt
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    else:
        a = a.astimezone(timezone.utc)
    n = now_utc if now_utc.tzinfo else now_utc.replace(tzinfo=timezone.utc)
    sec = int((n - a).total_seconds())
    if sec < 45:
        return "الآن"
    if sec < 3600:
        m = max(1, sec // 60)
        return f"منذ {m} دقيقة"
    if sec < 86400:
        h = sec // 3600
        if h == 1:
            return "منذ ساعة"
        return f"منذ {h} ساعة"
    days = sec // 86400
    if days == 1:
        return "منذ يوم"
    return f"منذ {days} أيام"


def merchant_reason_chip_class_and_label(reason_tag: str) -> tuple[str, str]:
    """فئة الشارة + النص التجاري (مع رمز) — بدون كشف وسوم خام."""
    k = (reason_tag or "").strip().lower()
    if k in ("price", "price_high"):
        return ("c-price", "💰 السعر مرتفع")
    if k in ("shipping", "delivery"):
        return ("c-shipping", "🚚 تكلفة الشحن")
    if k == "thinking":
        return ("c-thinking", "🤔 يفكر في القرار")
    if k in ("warranty", "quality", "human_support"):
        return ("c-trust", "🔒 الثقة بالمتجر")
    return ("c-other", "💭 أخرى")


def merchant_coarse_to_status_row(
    coarse: str,
    *,
    has_phone: bool,
) -> tuple[str, str, bool]:
    """
    (فئة صف الحالة، نص الشارة، هل الخطوة التالية عاجلة)
    coarse = مفتاح داخلي من مسار الاسترجاع — لا يُعرض للتاجر.
    """
    c = (coarse or "").strip().lower()
    if c == "converted":
        return ("s-recovered", "تم الاسترداد", False)
    if c == "sent":
        return ("s-sent", "رسالة أُرسلت", False)
    if c in ("pending", "replied", "clicked", "returned"):
        return ("s-waiting", "جارٍ المتابعة", False)
    if c == "blocked":
        return ("s-attention", "يحتاج متابعة", True)
    if c in ("ignored", "stopped"):
        urgent = not has_phone
        return ("s-inactive", "لا متابعة", urgent)
    return ("s-waiting", "جارٍ المتابعة", False)


def merchant_reason_panel_rows_from_counts(
    counts: dict[str, int],
) -> tuple[list[dict], str]:
    """
    من مجموعات أسباب (مفاتيح داخلية) → صفوف لوحة النسب + سطر ملاحظة.
    """
    label_and_color: list[tuple[str, str, str]] = [
        ("💰 السعر مرتفع", "price", "#3b82f6"),
        ("🚚 تكلفة الشحن", "shipping", "#8b5cf6"),
        ("🤔 يفكر في القرار", "thinking", "#ec4899"),
        ("🔒 الثقة بالمتجر", "trust", "#f97316"),
        ("💭 أخرى", "other", "#94a3b8"),
    ]
    trust_keys = frozenset({"warranty", "quality", "human_support"})
    bucket: dict[str, int] = {
        "price": 0,
        "shipping": 0,
        "thinking": 0,
        "trust": 0,
        "other": 0,
    }
    for raw_k, n in counts.items():
        k = (raw_k or "").strip().lower()
        v = int(n or 0)
        if k in ("price", "price_high"):
            bucket["price"] += v
        elif k in ("shipping", "delivery"):
            bucket["shipping"] += v
        elif k == "thinking":
            bucket["thinking"] += v
        elif k in trust_keys:
            bucket["trust"] += v
        else:
            bucket["other"] += v
    total = sum(bucket.values())
    rows: list[dict[str, object]] = []
    if total <= 0:
        return (
            rows,
            "لا توجد بيانات كافية عن أسباب التردد لهذه الفترة بعد.",
        )
    for lbl, bkey, color in label_and_color:
        cnt = int(bucket.get(bkey, 0))
        pct = min(100.0, round(100.0 * float(cnt) / float(total), 1))
        rows.append(
            {
                "label_ar": lbl,
                "count_pct": pct,
                "fill_color": color,
            }
        )
    p = int(bucket.get("price", 0))
    sh = int(bucket.get("shipping", 0))
    combo = min(100.0, round(100.0 * float(p + sh) / float(total), 1)) if total else 0.0
    insight = (
        f"💡 السعر والشحن معاً يسببان {combo:.0f}٪ من التردد — راجع إعدادات الشحن وعروض الخصم"
        if (p + sh) > 0
        else "💡 راجع تجربة الشراء والأسعار لتحسين التحويل."
    )
    return rows, insight


def merchant_vip_avatar_letter(index_zero_based: int) -> str:
    letters = ("أ", "ب", "ج", "د", "هـ", "و")
    if 0 <= index_zero_based < len(letters):
        return letters[index_zero_based]
    return "VIP"
