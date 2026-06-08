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
    # مصدر الربط (مثلاً zid_dev لمتجر التطوير في زد) — يُملأ عبر OAuth فقط
    integration_source = Column(String(64), nullable=True, index=True)
    connected_at = Column(DateTime, nullable=True)
    # تثبيت ودجت واجهة زد (Partner Custom Snippet + تحقق متجر)
    widget_installation_status = Column(String(32), nullable=True)
    widget_installed_at = Column(DateTime, nullable=True)
    widget_last_seen_at = Column(DateTime, nullable=True)
    widget_install_error = Column(Text, nullable=True)
    # Storefront runtime truth gate (beacon + verification status)
    widget_last_runtime_slug = Column(String(255), nullable=True)
    widget_last_beacon_json = Column(Text, nullable=True)
    widget_runtime_truth_status = Column(String(32), nullable=True)
    widget_runtime_truth_json = Column(Text, nullable=True)
    widget_runtime_truth_at = Column(DateTime, nullable=True)
    # إعدادات الاسترجاع (لاحقاً) — بدون واجهة بعد
    recovery_delay = Column(Integer, default=2, nullable=False)
    recovery_delay_unit = Column(
        String(20), default="minutes", nullable=False
    )
    recovery_attempts = Column(Integer, default=1, nullable=False)
    # دقائق التهدئة قبل إرسال واتساب الاسترجاع؛ ‎NULL‎ = استخدام ‎config_system + recovery_delay‎ كما سابقاً.
    recovery_delay_minutes = Column(Integer, nullable=True)
    # فترة الانتظار بعد الإرسال الأول قبل المحاولة الثانية (استرجاع عادي)؛ ‎NULL‎ = افتراضي آمن في الكود.
    second_attempt_delay_minutes = Column(Integer, nullable=True)
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
    # إعدادات واتساب من لوحة التاجر (قراءة/حفظ فقط في v1)
    whatsapp_recovery_enabled = Column(Boolean, default=True, nullable=False)
    whatsapp_provider_mode = Column(String(32), nullable=True)
    whatsapp_mode = Column(String(32), default="cartflow_managed", nullable=True)
    whatsapp_onboarding_journey = Column(String(64), nullable=True)
    whatsapp_onboarding_journey_status = Column(String(32), nullable=True)
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
    # تفضيلات VIP من لوحة التاجر (عرض/حفظ v1 — لا تغيّر مسار الكشف التشغيلي وحده)
    vip_enabled = Column(Boolean, default=True, nullable=False)
    vip_notify_enabled = Column(Boolean, default=True, nullable=False)
    vip_note = Column(Text, nullable=True)
    # تفضيلات عامة من لوحة التاجر (عرض/حفظ فقط — لا تغيّر التشغيل)
    settings_notify_vip = Column(Boolean, default=True, nullable=False)
    settings_notify_recovery_success = Column(Boolean, default=True, nullable=False)
    settings_notify_whatsapp_failure = Column(Boolean, default=True, nullable=False)
    widget_enabled = Column(Boolean, default=True, nullable=False)
    widget_display_name = Column(String(255), nullable=True)
    merchant_automation_mode = Column(String(32), default="manual", nullable=False)
    # عروض VIP (لوحة التحكم فقط؛ غير مستخدمة في وقت الإرسال بعد)
    vip_offer_enabled = Column(Boolean, default=False, nullable=False)
    vip_offer_type = Column(String(32), nullable=True)
    vip_offer_value = Column(String(500), nullable=True)
    # ظهور واجهة استعادة الودجيت للعميل فقط؛ التتبع و VIP يبقيان يعملين
    cartflow_widget_enabled = Column(Boolean, default=True, nullable=False)
    cartflow_widget_delay_value = Column(Integer, default=0, nullable=False)
    cartflow_widget_delay_unit = Column(String(20), default="minutes", nullable=False)
    # إعدادات مشغّل ظهور الودجيت (JSON) — طبقة تحكم تاجرية؛ القيم الافتراضية في الكود عند الفراغ
    cf_widget_trigger_settings_json = Column(Text, nullable=True)
    # كتالوج خفيف (JSON) لطبقة ذكاء المنتج — بدون مخزون وهمي؛ اختياري
    cf_product_catalog_json = Column(Text, nullable=True)
    # عروض التاجر لمسار الاستمرار (JSON) — قواعد فقط؛ لا إنشاء خصومات تلقائياً
    cf_merchant_offer_settings_json = Column(Text, nullable=True)
    # عدد مرات إرفاق عرض التاجر في رد الاستمرار (لـ offer_max_uses)
    cf_offer_applications_count = Column(Integer, default=0, nullable=False)
    # حساب التاجر المالك (اختياري — متاجر demo/قديمة بدون ربط)
    merchant_user_id = Column(
        Integer, ForeignKey("merchant_users.id"), nullable=True, index=True
    )
    identity_aliases = relationship(
        "StoreIdentityAlias",
        backref="store",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class StoreIdentityAlias(Base):
    """
    Platform-agnostic alias → CartFlow Store row.

    All storefront slugs, OAuth ids, and dashboard keys resolve through this table.
    """

    __tablename__ = "store_identity_aliases"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    alias_kind = Column(String(64), nullable=False, index=True)
    alias_value = Column(String(255), nullable=False, unique=True, index=True)
    platform = Column(String(32), nullable=True, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MerchantUser(Base):
    __tablename__ = "merchant_users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    merchant_name = Column(String(255), nullable=False)
    primary_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    # SaaS plan (marketplace-first — no billing engine in Phase 1)
    current_plan = Column(String(32), default="starter", nullable=False)
    plan_status = Column(String(32), default="active", nullable=False)
    plan_source = Column(String(32), default="manual", nullable=False)
    plan_started_at = Column(DateTime, nullable=True)
    plan_expires_at = Column(DateTime, nullable=True)
    trial_started_at = Column(DateTime, nullable=True)
    trial_expires_at = Column(DateTime, nullable=True)
    billing_interval = Column(String(32), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MerchantSubscriptionAuditLog(Base):
    """Append-only audit trail for admin subscription changes."""

    __tablename__ = "merchant_subscription_audit_logs"

    id = Column(Integer, primary_key=True)
    merchant_user_id = Column(
        Integer, ForeignKey("merchant_users.id"), nullable=False, index=True
    )
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    admin_source = Column(String(128), nullable=False, default="admin_session")
    action = Column(String(64), nullable=False)
    old_plan = Column(String(32), nullable=True)
    new_plan = Column(String(32), nullable=True)
    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)
    old_plan_expires_at = Column(DateTime, nullable=True)
    new_plan_expires_at = Column(DateTime, nullable=True)
    old_trial_expires_at = Column(DateTime, nullable=True)
    new_trial_expires_at = Column(DateTime, nullable=True)
    old_billing_interval = Column(String(32), nullable=True)
    new_billing_interval = Column(String(32), nullable=True)
    old_plan_started_at = Column(DateTime, nullable=True)
    new_plan_started_at = Column(DateTime, nullable=True)
    old_trial_started_at = Column(DateTime, nullable=True)
    new_trial_started_at = Column(DateTime, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


class MerchantPasswordResetToken(Base):
    __tablename__ = "merchant_password_reset_tokens"

    id = Column(Integer, primary_key=True)
    merchant_user_id = Column(
        Integer, ForeignKey("merchant_users.id"), nullable=False, index=True
    )
    token_hash = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


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
    # جلسة الاسترجاع من الواجهة (‎session_id‎ عند ترك السلة من الويدجت/المتجر)
    recovery_session_id = Column(String(512), nullable=True, index=True)
    # سلة عالية القيمة (VIP): لا استرجاع تلقائي للعميل — متابعة يدوية
    vip_mode = Column(Boolean, default=False, nullable=False)
    # دورة حياة عرض لوحة VIP فقط: abandoned / contacted / closed / converted
    vip_lifecycle_status = Column(String(32), nullable=True)

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


class RecoverySchedule(Base):
    """
    جدولة استرجاع دائمة — تنجو من إعادة تشغيل الخادم (Reliability Program v1).
    مفتاح المحاولة: ‎recovery_key + step + multi_slot_index‎.
    """

    __tablename__ = "recovery_schedules"

    id = Column(Integer, primary_key=True)
    recovery_key = Column(String(512), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=True, index=True)
    reason_tag = Column(String(128), nullable=True)
    customer_phone = Column(String(100), nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    due_at = Column(DateTime, nullable=False, index=True)
    effective_delay_seconds = Column(Float, nullable=False)
    delay_source = Column(String(128), nullable=False, default="unknown")
    status = Column(String(64), nullable=False, default="scheduled", index=True)
    step = Column(Integer, nullable=False, default=1)
    multi_slot_index = Column(Integer, nullable=False, default=-1)
    sequential_attempt_index = Column(Integer, nullable=True)
    context_json = Column(Text, nullable=True)
    last_error = Column(String(512), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class MerchantCartLifecycleArchive(Base):
    """Merchant manual / auto archive for normal-cart lifecycle (dashboard only)."""

    __tablename__ = "merchant_cart_lifecycle_archives"

    id = Column(Integer, primary_key=True)
    recovery_key = Column(String(512), nullable=False, unique=True, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    abandoned_cart_id = Column(Integer, nullable=True, index=True)
    is_archived = Column(Boolean, default=True, nullable=False, index=True)
    archive_source = Column(String(64), nullable=False, default="manual")
    archived_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    reopened_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


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
    recovery_key = Column(String(512), nullable=True, index=True)
    reason_tag = Column(String(64), nullable=True)
    context_status = Column(String(32), nullable=True, index=True)
    context_json = Column(Text, nullable=True)
    message_type = Column(String(64), nullable=True)
    source = Column(String(64), nullable=True)
    provider = Column(String(32), nullable=True)
    provider_message_sid = Column(String(128), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    sent_at = Column(DateTime, nullable=True)


class WhatsAppDeliveryTruth(Base):
    """
    Lightweight delivery truth by provider message SID (v1).
    Provider acceptance (queued) ≠ delivered_to_customer.
    """

    __tablename__ = "whatsapp_delivery_truth"

    id = Column(Integer, primary_key=True)
    provider = Column(String(32), nullable=False, default="twilio", index=True)
    message_sid = Column(String(128), nullable=False, unique=True, index=True)
    customer_phone = Column(String(100), nullable=True)
    store_slug = Column(String(255), nullable=True, index=True)
    session_id = Column(String(512), nullable=True, index=True)
    cart_id = Column(String(255), nullable=True)
    recovery_key = Column(String(512), nullable=True, index=True)
    send_status = Column(String(64), nullable=True)
    delivery_status = Column(String(64), nullable=True)
    read_status = Column(String(64), nullable=True)
    provider_error = Column(String(512), nullable=True)
    truth_level = Column(String(64), nullable=False, default="unknown", index=True)
    last_event_time = Column(DateTime, nullable=False)
    raw_last_payload = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RecoveryTruthTimelineEvent(Base):
    """
    Append-only proven transitions for one recovery_key (dashboard truth / debug).
    """

    __tablename__ = "recovery_truth_timeline_events"

    id = Column(Integer, primary_key=True)
    recovery_key = Column(String(512), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=True, index=True)
    cart_id = Column(String(255), nullable=True, index=True)
    status = Column(String(64), nullable=False, index=True)
    source = Column(String(128), nullable=False, default="")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )


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


class MerchantFollowupAction(Base):
    """
    تنبيه/إجراء للتاجر بعد نية إيجابية من العميل (مثل رد واتساب).
    لا يُرسل للعميل تلقائياً من هذا الصف؛ للقراءة من لوحة/ـAPI لاحقاً.
    """

    __tablename__ = "merchant_followup_actions"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    abandoned_cart_id = Column(
        Integer, ForeignKey("abandoned_carts.id"), nullable=True, index=True
    )
    customer_phone = Column(String(100), nullable=False, index=True)
    status = Column(String(64), nullable=False, index=True)
    reason = Column(String(64), nullable=False, index=True)
    inbound_message = Column(String(512), nullable=True)
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


class LifecycleClosureRecord(Base):
    """
    Durable terminal lifecycle closure — survives process restart.
    One row per recovery_key (canonical closure status).
    """

    __tablename__ = "lifecycle_closure_records"

    id = Column(Integer, primary_key=True)
    recovery_key = Column(String(512), nullable=False, unique=True, index=True)
    closure_status = Column(String(64), nullable=False, index=True)
    closure_reason = Column(String(128), nullable=False)
    closure_source = Column(String(128), nullable=False)
    closure_time = Column(DateTime, nullable=False)
    store_slug = Column(String(255), nullable=True, index=True)
    session_id = Column(String(512), nullable=True, index=True)
    cart_id = Column(String(255), nullable=True, index=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PurchaseTruthRecord(Base):
    """
    Durable purchase evidence — survives process restart.
    One row per recovery_key when purchase is verified.
    """

    __tablename__ = "purchase_truth_records"

    id = Column(Integer, primary_key=True)
    recovery_key = Column(String(512), nullable=False, unique=True, index=True)
    purchase_detected = Column(Boolean, default=True, nullable=False)
    purchase_time = Column(DateTime, nullable=False)
    purchase_source = Column(String(128), nullable=False, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=True, index=True)
    customer_phone = Column(String(100), nullable=True)
    evidence_detail = Column(String(512), nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class OperationalControlSnapshot(Base):
    """
    Durable platform operational controls — singleton row (id=1).
    Survives process restart and is shared across workers.
    """

    __tablename__ = "operational_control_snapshots"

    id = Column(Integer, primary_key=True)
    platform_wa_paused = Column(Boolean, default=False, nullable=False)
    platform_schedule_paused = Column(Boolean, default=False, nullable=False)
    platform_continuation_paused = Column(Boolean, default=False, nullable=False)
    provider_paused = Column(Boolean, default=False, nullable=False)
    provider_id = Column(String(32), nullable=True)
    paused_stores_json = Column(Text, nullable=False, default="[]")
    paused_reasons_json = Column(Text, nullable=False, default="[]")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DbReadyOperationalSnapshot(Base):
    """
    Lightweight DB ready timing snapshot — singleton row (id=1).
    Survives restart; used by Admin Operations dashboard health.
    """

    __tablename__ = "db_ready_operational_snapshots"

    id = Column(Integer, primary_key=True)
    last_duration_ms = Column(Float, default=0.0, nullable=False)
    worst_duration_ms = Column(Float, default=0.0, nullable=False)
    avg_duration_ms = Column(Float, default=0.0, nullable=False)
    sample_count = Column(Integer, default=0, nullable=False)
    last_stage = Column(String(64), nullable=True)
    last_trace_id = Column(String(16), nullable=True)
    last_lock_wait_ms = Column(Float, default=0.0, nullable=False)
    last_query_count = Column(Integer, default=0, nullable=False)
    last_sql_ms = Column(Float, default=0.0, nullable=False)
    last_success = Column(Boolean, default=True, nullable=False)
    last_failure_message = Column(String(255), nullable=True)
    status = Column(String(16), nullable=False, default="healthy")
    last_top_substage = Column(String(64), nullable=True)
    last_top_substage_queries = Column(Integer, default=0, nullable=False)
    last_top_substage_sql_ms = Column(Float, default=0.0, nullable=False)
    last_top_substage_elapsed_ms = Column(Float, default=0.0, nullable=False)
    top_substages_json = Column(Text, nullable=False, default="[]")
    stage_classifications_json = Column(Text, nullable=False, default="[]")
    startup_warm_status = Column(String(16), nullable=False, default="not_started")
    startup_warm_duration_ms = Column(Float, default=0.0, nullable=False)
    startup_warm_error = Column(String(255), nullable=True)
    last_request_cached_verification = Column(Boolean, nullable=True)
    restart_startup_at = Column(DateTime, nullable=True)
    restart_warm_completed_at = Column(DateTime, nullable=True)
    restart_first_dashboard_at = Column(DateTime, nullable=True)
    restart_first_dashboard_duration_ms = Column(Float, default=0.0, nullable=False)
    restart_first_dashboard_cached_verification = Column(Boolean, nullable=True)
    restart_first_dashboard_heavy_warm = Column(Boolean, nullable=True)
    restart_first_dashboard_used_safe_path = Column(Boolean, nullable=True)
    restart_survival_result = Column(String(8), nullable=False, default="pending")
    restart_survival_timing = Column(String(64), nullable=False, default="unknown")
    restart_survival_protected = Column(Boolean, nullable=True)
    restart_survival_reason = Column(String(64), nullable=True)
    restart_survival_evaluated_at = Column(DateTime, nullable=True)
    last_seen_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
