# -*- coding: utf-8 -*-
"""عرض تجاري خفيف لحالات الاسترجاع العادي — بدون مفاتيح تقنية في الواجهة."""
from __future__ import annotations

# خرائط حالة تقريبية داخلية (لا تُعرض للتاجر) → نصوص أعمال
_COARSE_TO_BUSINESS_STATE_AR: dict[str, str] = {
    "pending": "تحتاج متابعة",
    "sent": "تم التواصل",
    "replied": "العميل رد",
    "clicked": "تفاعل مع الرابط",
    "returned": "العميل عاد",
    "ignored": "لم تُستكمل",
    "stopped": "توقفت المتابعة",
    "converted": "تم الاسترجاع",
    "blocked": "تحتاج مراجعة",
}


def merchant_business_state_label_ar(coarse: str) -> str:
    k = (coarse or "").strip().lower()
    return _COARSE_TO_BUSINESS_STATE_AR.get(k, "تحتاج متابعة")


def merchant_next_action_hint_ar(
    *,
    coarse: str,
    has_phone: bool,
    is_dormant_case: bool,
) -> str:
    """إرشاد قصير للتاجر فقط — لا يصف طوابير أو محركات."""
    if is_dormant_case:
        return "حالة سابقة — يمكنك الرجوع إليها عند الحاجة دون إجراء مطلوب الآن."
    if not has_phone:
        return "أضف رقم العميل من إعدادات المتجر أو من بيانات الطلب ليكمل المسار."
    cr = (coarse or "").strip().lower()
    if cr == "pending":
        return "ستُرسل رسالة المتابعة تلقائياً وفق التوقيت الذي ضبطته."
    if cr == "sent":
        return "راقب الرد؛ عند الحاجة راجع المحادثة من واتساب المتجر."
    if cr in ("replied", "clicked", "returned"):
        return "تابع بخطوة بيع لطيفة أو أجب على استفسار العميل."
    if cr == "blocked":
        return "راجع بيانات العميل أو الربط ثم أعد المحاولة."
    if cr in ("converted", "stopped", "ignored"):
        return "لا يتطلب إجراءاً إضافياً من هذه الشاشة."
    return "راقب النتيجة من تقاريرك اليومية."


def merchant_history_case_note_ar(*, dormant_sales: bool) -> str:
    """نص للحالات السابقة دون مصطلحات تشغيل أو «خامل»."""
    if dormant_sales:
        return "لم يُكمل العميل المسار بعد آخر تواصل — نُظهرها هنا كمرجع."
    return "حالة سابقة للرجوع إليها عند الحاجة."
