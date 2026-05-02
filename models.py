# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import relationship

from extensions import (
    Base,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    # يُعاد ملؤه بعد ‎OAuth‎ عند التأكد من ‎zid_store_id‎ من الاستجابة
    zid_store_id = Column(String(128), unique=True, nullable=True, index=True)
    access_token = Column(Text, default="")
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    # إعدادات الاسترجاع (لاحقاً) — بدون واجهة بعد
    recovery_delay = Column(Integer, default=2, nullable=False)
    recovery_delay_unit = Column(
        String(20), default="minutes", nullable=False
    )
    recovery_attempts = Column(Integer, default=1, nullable=False)
    # دقائق التهدئة قبل إرسال واتساب الاسترجاع؛ ‎NULL‎ = استخدام ‎config_system + recovery_delay‎ كما سابقاً.
    recovery_delay_minutes = Column(Integer, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    abandoned_carts = relationship(
        "AbandonedCart", backref="store", lazy="dynamic"
    )
    message_logs = relationship("MessageLog", backref="store", lazy="dynamic")
    recovery_events = relationship("RecoveryEvent", backref="store", lazy="dynamic")
    # اختياري: رابط واتساب الدعم للعميل (ودجت السبب) — ‎VARCHAR(2048)‎ عند الترقية
    whatsapp_support_url = Column(String(2048), nullable=True)
    # اختياري: رقم واتساب المتجر (تحضير لمصدر إرسال مستقبلي؛ غير مستخدم حالياً في الإرسال)
    store_whatsapp_number = Column(String(64), nullable=True)
    # قوالب واتساب استرجاع قابلة للتهيئة من لوحة التحكم — فارغ = القالب الافتراضي المدمج
    template_price = Column(Text, nullable=True)
    template_shipping = Column(Text, nullable=True)
    template_quality = Column(Text, nullable=True)
    template_delivery = Column(Text, nullable=True)
    template_warranty = Column(Text, nullable=True)
    template_other = Column(Text, nullable=True)
    # قوالب مشغّل الاسترجاع (‎reason_tag‎ → ‎enabled‎ + ‎message‎) كـ JSON
    trigger_templates_json = Column(Text, nullable=True)
    # قوالب سبب الاسترجاع (تفعيل/تعطيل لكل سبب + نص) — لوحة التحكم ‎reason_templates‎
    reason_templates_json = Column(Text, nullable=True)
    # واجهة الودجت: نمط الرسائل (قيمة افتراضية = سلوك النظام الحالي)
    template_mode = Column(String(32), default="preset", nullable=False)
    template_tone = Column(String(32), default="friendly", nullable=False)
    template_custom_text = Column(Text, nullable=True)
    # رسالة الخروج قبل السلة (منفصلة عن قوالب واتساب وعن نص اكتشاف المنتجات)
    exit_intent_template_mode = Column(String(32), default="preset", nullable=False)
    exit_intent_template_tone = Column(String(32), default="friendly", nullable=False)
    exit_intent_custom_text = Column(Text, nullable=True)
    # تخصيص مظهر الودجيت (واجهة فقط؛ لا تأثير على منطق الاسترجاع)
    widget_name = Column(String(255), default="مساعد المتجر", nullable=False)
    widget_primary_color = Column(String(16), default="#6C5CE7", nullable=False)
    widget_style = Column(String(16), default="modern", nullable=False)
    # عتبة سلة مميزة (ريال سعودي)؛ ‎NULL‎ = معطّل — تحضير لمسار VIP لاحقاً
    vip_cart_threshold = Column(Integer, nullable=True)


class AbandonedCart(Base):
    __tablename__ = "abandoned_carts"

    id = Column(Integer, primary_key=True)
    store_id = Column(
        Integer, ForeignKey("stores.id"), nullable=True, index=True
    )
    zid_cart_id = Column(String(255), unique=True, nullable=False, index=True)
    customer_name = Column(String(500), nullable=True)
    customer_phone = Column(String(100), nullable=True)
    customer_email = Column(String(500), nullable=True)
    cart_value = Column(Float, nullable=True)
    cart_url = Column(String(2048), nullable=True)
    status = Column(String(50), default="detected", nullable=False)
    raw_payload = Column(Text, nullable=True)
    first_seen_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    recovered_at = Column(DateTime, nullable=True)

    message_logs = relationship("MessageLog", backref="abandoned_cart", lazy="dynamic")

    @staticmethod
    def set_raw(obj: "AbandonedCart", data: Any) -> None:
        if isinstance(data, (dict, list)):
            obj.raw_payload = json.dumps(data, ensure_ascii=False)[:65000]
        else:
            obj.raw_payload = (str(data) or "")[:65000]


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True)
    store_id = Column(
        Integer, ForeignKey("stores.id"), nullable=False, index=True
    )
    abandoned_cart_id = Column(
        Integer, ForeignKey("abandoned_carts.id"), nullable=True, index=True
    )
    channel = Column(String(50), default="whatsapp", nullable=False)
    phone = Column(String(100), default="", nullable=False)
    message = Column(Text, default="")
    status = Column(String(50), default="pending", nullable=False)
    provider_response = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ObjectionTrack(Base):
    """متابعة اختيار ‎objection‎ من الودجيت (سعر/جودة)."""
    __tablename__ = "objection_tracks"

    id = Column(Integer, primary_key=True)
    # عمود ‎SQL‎ ‎:type‎ — ‎"price"‎ / ‎"quality"‎
    object_type = Column("type", String(20), nullable=False, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # حقول اختيارية (تُملأ من ‎/dev/create-test-objection‎ فقط؛ ‎/track/objection‎ يتركها ‎None‎)
    customer_name = Column(String(500), nullable=True)
    customer_phone = Column(String(100), nullable=True)
    cart_url = Column(String(2048), nullable=True)
    customer_type = Column(String(20), nullable=True)
    last_activity_at = Column(DateTime, nullable=True)


class AbandonmentReasonLog(Base):
    __tablename__ = "abandonment_reason_logs"

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    reason = Column(String(32), nullable=False, index=True)
    sub_category = Column(String(64), nullable=True, index=True)
    custom_text = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class CartRecoveryReason(Base):
    """
    آخر سبب اختيار لكل ‎(store_slug, session_id)‎ — يُستعمل لاحقاً لتخصيص رسائل الاسترجاع.
    """

    __tablename__ = "cart_recovery_reasons"

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    # وسوم الطبقة ‎D‎ للودجت (مثل ‎price_high‎) أطول من ‎slug‎ القديم
    reason = Column(String(64), nullable=False, index=True)
    # اختياري: رقم واتساب للعميل (من ‎POST /api/cart-recovery/reason‎) لمسار الإرسال
    customer_phone = Column(String(100), nullable=True)
    sub_category = Column(String(64), nullable=True, index=True)
    custom_text = Column(Text, nullable=True)
    source = Column(String(32), default="widget", nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_rejected_help = Column(Boolean, default=False, nullable=False)
    rejection_timestamp = Column(DateTime, nullable=True)


class CartRecoveryLog(Base):
    """تسجيل محاولات الاسترجاع (وهمي/تخطٍ) دون الاعتماد على واتساب حقيقي."""
    __tablename__ = "cart_recovery_logs"

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=True, index=True)
    phone = Column(String(100), nullable=True)
    message = Column(Text, default="", nullable=False)
    status = Column(String(50), nullable=False, index=True)
    step = Column(Integer, nullable=True, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    sent_at = Column(DateTime, nullable=True)


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id = Column(Integer, primary_key=True)
    store_id = Column(
        Integer, ForeignKey("stores.id"), nullable=True, index=True
    )
    abandoned_cart_id = Column(
        Integer, ForeignKey("abandoned_carts.id"), nullable=True, index=True
    )
    event_type = Column(String(128), default="webhook", nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
