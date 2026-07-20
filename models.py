# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Index, UniqueConstraint
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
    # Zid OAuth Authorization header value (distinct from access_token / X-Manager-Token)
    zid_authorization_token = Column(Text, nullable=True)
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


class ProviderRetryLedger(Base):
    """
    Durable, restart-safe retry ledger for outbound provider sends.

    Provider Reliability Governance V1 — PR-4 (retries are durable), PR-7 (temporary
    failure must not become silent failure), PR-RT-5 (retry state never lives only in
    process memory). One row per (correlation_key, provider, step). This is the
    system of record for retry intent; live re-dispatch activation is gated by
    ``PROVIDER_RETRY_ACTIVE`` (foundation default: record-only, no behavior change).
    """

    __tablename__ = "provider_retry_ledger"

    id = Column(Integer, primary_key=True)
    correlation_key = Column(String(512), nullable=False, index=True)
    provider = Column(String(32), nullable=False, default="twilio", index=True)
    store_slug = Column(String(255), nullable=True, index=True)
    session_id = Column(String(512), nullable=True)
    cart_id = Column(String(255), nullable=True)
    customer_phone = Column(String(100), nullable=True)
    step = Column(Integer, nullable=False, default=0, index=True)
    attempt = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="pending", index=True)
    last_failure_class = Column(String(64), nullable=True)
    last_disposition = Column(String(32), nullable=True)
    last_error = Column(String(512), nullable=True)
    next_attempt_at = Column(DateTime, nullable=True, index=True)
    retry_after_until = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "correlation_key", "provider", "step", name="uq_provider_retry_ledger_key"
        ),
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


class CartLineSnapshot(Base):
    """
    Immutable cart line capture from widget Product Identity ``lines[]``.
    Insert-only historical rows — never update name/price on existing snapshots.
    """

    __tablename__ = "cart_line_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "store_slug",
            "session_id",
            "cart_id",
            "capture_source",
            "content_hash",
            name="uq_cart_line_snapshot_dedup",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=False, default="", index=True)
    recovery_key = Column(String(512), nullable=True, index=True)
    product_id = Column(String(128), nullable=True, index=True)
    variant_id = Column(String(128), nullable=True)
    sku = Column(String(128), nullable=True)
    name = Column(String(200), nullable=True)
    unit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    captured_at = Column(DateTime, nullable=False, index=True)
    capture_source = Column(String(64), nullable=False, index=True)
    capture_confidence = Column(String(16), nullable=False)
    content_hash = Column(String(64), nullable=False)


class ProductCatalogEntry(Base):
    """
    Canonical mutable product catalog entry (current truth).
    Historical cart lines remain in ``cart_line_snapshots`` (immutable).
    """

    __tablename__ = "product_catalog_entries"
    __table_args__ = (
        UniqueConstraint(
            "store_slug",
            "stable_identity_key",
            name="uq_product_catalog_identity",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    stable_identity_key = Column(String(256), nullable=False, index=True)
    identity_tier = Column(String(8), nullable=False, index=True)
    product_id = Column(String(128), nullable=True, index=True)
    variant_id = Column(String(128), nullable=True)
    sku = Column(String(128), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    category = Column(String(128), nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=False, default="SAR")
    capture_confidence = Column(String(16), nullable=False)
    catalog_source = Column(String(64), nullable=False, index=True)
    first_seen_at = Column(DateTime, nullable=False)
    last_synced_at = Column(DateTime, nullable=False)


class ProductHesitationMapping(Base):
    """
    Immutable Product ↔ Hesitation Reason link (Hesitation Mapping v1).

    Records the historical fact that a canonical product (``stable_identity_key``)
    was present in a cart/session when a hesitation ``reason`` was captured.
    Insert-only history — never overwritten, never reclassified. No intelligence,
    scoring, or blame attribution lives here.
    """

    __tablename__ = "product_hesitation_mappings"
    __table_args__ = (
        UniqueConstraint(
            "dedup_hash",
            name="uq_product_hesitation_dedup",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=False, default="", index=True)
    recovery_key = Column(String(512), nullable=True, index=True)
    stable_identity_key = Column(String(256), nullable=False, index=True)
    identity_tier = Column(String(8), nullable=False)
    product_id = Column(String(128), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    reason = Column(String(64), nullable=False, index=True)
    sub_reason = Column(String(64), nullable=True, index=True)
    mapping_confidence = Column(String(16), nullable=False)
    mapping_source = Column(String(32), nullable=False, default="reason_capture")
    captured_at = Column(DateTime, nullable=False, index=True)
    dedup_hash = Column(String(64), nullable=False)


class ProductPurchaseMapping(Base):
    """
    Immutable Product ↔ Purchase link (Purchase Mapping v1).

    Records the historical fact that a canonical product was present in a
    cart/session when Purchase Truth confirmed a purchase. Insert-only history —
    never overwritten or reclassified. No intelligence, attribution scoring,
    or ranking lives here.
    """

    __tablename__ = "product_purchase_mappings"
    __table_args__ = (
        UniqueConstraint(
            "dedup_hash",
            name="uq_product_purchase_dedup",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, index=True)
    cart_id = Column(String(255), nullable=False, default="", index=True)
    recovery_key = Column(String(512), nullable=True, index=True)
    order_id = Column(String(255), nullable=True, index=True)
    stable_identity_key = Column(String(256), nullable=False, index=True)
    product_id = Column(String(128), nullable=True, index=True)
    name = Column(String(200), nullable=True)
    quantity = Column(Integer, nullable=True)
    unit_price = Column(Float, nullable=True)
    purchase_confidence = Column(String(16), nullable=False)
    purchase_source = Column(String(128), nullable=False, index=True)
    purchased_at = Column(DateTime, nullable=False, index=True)
    dedup_hash = Column(String(64), nullable=False)


class ProductSignalEvent(Base):
    """
    Immutable Product Signal Collection V1 row — atomic product fact.

    Insert-only history of what happened about a Product Identity. No scoring,
    ranking, recommendations, or presentation fields.
    """

    __tablename__ = "product_signal_events"
    __table_args__ = (
        UniqueConstraint(
            "dedup_hash",
            name="uq_product_signal_dedup",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    session_id = Column(String(512), nullable=False, default="", index=True)
    cart_id = Column(String(255), nullable=False, default="", index=True)
    recovery_key = Column(String(512), nullable=True, index=True)
    stable_identity_key = Column(String(256), nullable=False, index=True)
    identity_tier = Column(String(8), nullable=False, default="")
    product_id = Column(String(128), nullable=True, index=True)
    signal_family = Column(String(64), nullable=False, index=True)
    signal_type = Column(String(64), nullable=False, index=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    source = Column(String(128), nullable=False, index=True)
    evidence_ref_type = Column(String(64), nullable=True)
    evidence_ref_id = Column(String(128), nullable=True)
    dedup_hash = Column(String(64), nullable=False)


class ProductMetricValue(Base):
    """
    Product Metrics Foundation V1 materialization — measurable count facts.

    Deterministic aggregates from product_signal_events only. No trends,
    scores, recommendations, or presentation fields.
    """

    __tablename__ = "product_metric_values"
    __table_args__ = (
        UniqueConstraint(
            "store_slug",
            "stable_identity_key",
            "metric_key",
            "window_code",
            "window_start_key",
            "window_end_key",
            name="uq_product_metric_value_grain",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    stable_identity_key = Column(String(256), nullable=False, default="", index=True)
    metric_key = Column(String(64), nullable=False, index=True)
    metric_family = Column(String(64), nullable=False, index=True)
    window_code = Column(String(16), nullable=False, default="all", index=True)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    # Empty-string sentinels for unique constraint when window bounds are null.
    window_start_key = Column(String(32), nullable=False, default="")
    window_end_key = Column(String(32), nullable=False, default="")
    value = Column(Integer, nullable=False, default=0)
    source_signal_type = Column(String(64), nullable=False, default="")
    computation_version = Column(String(32), nullable=False, default="pmf_v1_count")
    content_hash = Column(String(64), nullable=False, default="")
    computed_at = Column(DateTime, nullable=False, index=True)


class ProductTrendValue(Base):
    """
    Product Trends Foundation V1 materialization — temporal change facts only.

    Compares Product Metrics across adjacent windows. No ranking, health,
    recommendations, or presentation fields.
    """

    __tablename__ = "product_trend_values"
    __table_args__ = (
        UniqueConstraint(
            "store_slug",
            "stable_identity_key",
            "metric_key",
            "trend_window",
            "as_of_key",
            name="uq_product_trend_value_grain",
        ),
    )

    id = Column(Integer, primary_key=True)
    store_slug = Column(String(255), nullable=False, index=True)
    stable_identity_key = Column(String(256), nullable=False, default="", index=True)
    metric_key = Column(String(64), nullable=False, index=True)
    metric_family = Column(String(64), nullable=False, default="", index=True)
    trend_window = Column(String(16), nullable=False, index=True)
    as_of = Column(DateTime, nullable=False, index=True)
    as_of_key = Column(String(32), nullable=False, default="")
    current_value = Column(Integer, nullable=False, default=0)
    previous_value = Column(Integer, nullable=False, default=0)
    delta_abs = Column(Integer, nullable=False, default=0)
    trend_direction = Column(String(32), nullable=False, index=True)
    computation_version = Column(String(32), nullable=False, default="ptf_v1_delta")
    content_hash = Column(String(64), nullable=False, default="")
    computed_at = Column(DateTime, nullable=False, index=True)


class ProductEvidenceBundle(Base):
    """
    Product Evidence Assembly V1 — governed evidence bundle header.

    Assembled from Metrics + Trends only. No confidence, ranking, or guidance.
    """

    __tablename__ = "product_evidence_bundles"
    __table_args__ = (
        UniqueConstraint(
            "store_slug",
            "subject_type",
            "subject_id",
            "assembly_window",
            "as_of_key",
            "bundle_version",
            name="uq_product_evidence_bundle_grain",
        ),
    )

    id = Column(Integer, primary_key=True)
    evidence_bundle_id = Column(String(64), nullable=False, unique=True, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    subject_type = Column(String(32), nullable=False, index=True)
    subject_id = Column(String(256), nullable=False, index=True)
    bundle_version = Column(String(32), nullable=False, default="pea_v1")
    assembled_at = Column(DateTime, nullable=False, index=True)
    assembly_window = Column(String(16), nullable=False, index=True)
    as_of = Column(DateTime, nullable=False, index=True)
    as_of_key = Column(String(32), nullable=False, default="")
    source_count = Column(Integer, nullable=False, default=0)
    fingerprint = Column(String(64), nullable=False, default="")
    computation_version = Column(String(32), nullable=False, default="pea_v1_assemble")


class ProductEvidenceItem(Base):
    """
    Product Evidence Assembly V1 — single factual evidence item with lineage.
    """

    __tablename__ = "product_evidence_items"
    __table_args__ = (
        UniqueConstraint(
            "evidence_bundle_id",
            "evidence_item_id",
            name="uq_product_evidence_item_id",
        ),
    )

    id = Column(Integer, primary_key=True)
    evidence_bundle_id = Column(String(64), nullable=False, index=True)
    evidence_item_id = Column(String(64), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    subject_type = Column(String(32), nullable=False, default="")
    subject_id = Column(String(256), nullable=False, default="")
    metric_key = Column(String(64), nullable=False, index=True)
    metric_value = Column(Integer, nullable=True)
    trend_direction = Column(String(32), nullable=True)
    trend_window = Column(String(16), nullable=False, default="")
    source_layer = Column(String(32), nullable=False, index=True)
    source_record_id = Column(String(128), nullable=False, default="")
    observed_from = Column(DateTime, nullable=True)
    observed_to = Column(DateTime, nullable=True)
    lineage_json = Column(Text, nullable=False, default="{}")
    content_hash = Column(String(64), nullable=False, default="")
    assembled_at = Column(DateTime, nullable=False, index=True)


class EvidenceConfidenceEvaluation(Base):
    """
    Evidence Confidence Foundation V1 — quality evaluation of an evidence bundle.

    Evaluates assembled evidence only. No recommendations, health, or ranking.
    """

    __tablename__ = "evidence_confidence_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "confidence_id",
            name="uq_evidence_confidence_id",
        ),
        UniqueConstraint(
            "evidence_bundle_id",
            "confidence_version",
            "evaluator_version",
            "as_of_key",
            name="uq_evidence_confidence_grain",
        ),
    )

    id = Column(Integer, primary_key=True)
    confidence_id = Column(String(64), nullable=False, index=True)
    evidence_bundle_id = Column(String(64), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    subject_type = Column(String(32), nullable=False, default="")
    subject_id = Column(String(256), nullable=False, default="")
    confidence_level = Column(String(32), nullable=False, index=True)
    confidence_score = Column(Integer, nullable=False, default=0)
    confidence_version = Column(String(32), nullable=False, default="ecf_v1")
    evaluator_version = Column(String(32), nullable=False, default="ecf_v1_eval")
    evaluated_at = Column(DateTime, nullable=False, index=True)
    as_of = Column(DateTime, nullable=False, index=True)
    as_of_key = Column(String(32), nullable=False, default="")
    completeness = Column(Integer, nullable=False, default=0)
    freshness = Column(Integer, nullable=False, default=0)
    consistency = Column(Integer, nullable=False, default=0)
    source_diversity = Column(Integer, nullable=False, default=0)
    sample_size = Column(Integer, nullable=False, default=0)
    missing_sources_json = Column(Text, nullable=False, default="[]")
    conflicting_signals = Column(Boolean, nullable=False, default=False)
    confidence_notes_json = Column(Text, nullable=False, default="[]")
    factors_json = Column(Text, nullable=False, default="{}")
    content_hash = Column(String(64), nullable=False, default="")


class DashboardSnapshot(Base):
    """
    Precomputed merchant dashboard payload — read-only on API hot path
    (Reliability Foundation: dashboard snapshot layer).
    """

    __tablename__ = "dashboard_snapshots"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    snapshot_type = Column(String(64), nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    generated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    expires_at = Column(DateTime, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active", index=True)
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


class DashboardSnapshotArchive(Base):
    """
    Cold storage for historical dashboard snapshot versions moved off the hot table.
    Latest per (store_slug, snapshot_type) always remains in dashboard_snapshots.
    """

    __tablename__ = "dashboard_snapshots_archive"

    id = Column(Integer, primary_key=True)
    source_snapshot_id = Column(Integer, nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    store_slug = Column(String(255), nullable=False, index=True)
    snapshot_type = Column(String(64), nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    generated_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    archived_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class MovementSnapshot(Base):
    """
    Hot read model for customer movement — one row per recovery_key (shadow Phase 1).
    Materialized from durable signals; not yet consumed on dashboard hot paths.
    """

    __tablename__ = "movement_snapshots"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, nullable=True, index=True)
    store_slug = Column(String(255), nullable=False)
    recovery_key = Column(String(512), nullable=False, unique=True)
    cart_id = Column(String(255), nullable=True)
    session_id = Column(String(512), nullable=True)

    provider_sent = Column(Boolean, default=False, nullable=False)
    provider_sent_at = Column(DateTime, nullable=True)

    reply_received = Column(Boolean, default=False, nullable=False)
    reply_at = Column(DateTime, nullable=True)

    continuation_started = Column(Boolean, default=False, nullable=False)
    continuation_at = Column(DateTime, nullable=True)

    returned_to_site = Column(Boolean, default=False, nullable=False)
    returned_at = Column(DateTime, nullable=True)

    passive_return_visit_count = Column(Integer, default=0, nullable=False)
    passive_return_last_at = Column(DateTime, nullable=True)

    purchase_detected = Column(Boolean, default=False, nullable=False, index=True)
    purchase_at = Column(DateTime, nullable=True)
    purchase_truth_id = Column(Integer, nullable=True)

    last_movement_type = Column(String(64), nullable=True)
    last_movement_at = Column(DateTime, nullable=True, index=True)

    movement_active = Column(Boolean, default=True, nullable=False, index=True)
    movement_version = Column(Integer, default=0, nullable=False)

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

    __table_args__ = (
        Index(
            "ix_movement_snapshots_merchant_recovery_key",
            "merchant_id",
            "recovery_key",
        ),
        Index(
            "ix_movement_snapshots_store_slug_updated_at",
            "store_slug",
            "updated_at",
        ),
    )


class SimulationRun(Base):
    """
    Store Reality Simulator V1 — orchestration run (Phase 2).
    Hybrid persistence: run row + JSON for config/accounting/checkpoint/progress.
    Does not store derived Knowledge / dashboard / attribution truth.
    """

    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(String(64), nullable=False, unique=True, index=True)
    store_slug = Column(String(255), nullable=False, default="demo", index=True)
    scenario_ids_json = Column(Text, nullable=False, default="[]")
    seed = Column(Integer, nullable=False, default=0)
    start_date = Column(DateTime, nullable=False)
    duration_days = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="created", index=True)
    current_day = Column(DateTime, nullable=True)
    current_step = Column(Integer, nullable=False, default=0)
    simulated_now = Column(DateTime, nullable=True)
    config_json = Column(Text, nullable=False, default="{}")
    accounting_json = Column(Text, nullable=False, default="{}")
    checkpoint_json = Column(Text, nullable=False, default="{}")
    progress_json = Column(Text, nullable=False, default="{}")
    errors_json = Column(Text, nullable=False, default="[]")
    warnings_json = Column(Text, nullable=False, default="[]")
    # Phase 3 Reality Engine artifacts (hot metadata — not merchant dashboard truth)
    scale_profile = Column(String(32), nullable=True)
    manifest_json = Column(Text, nullable=True)
    reality_score_json = Column(Text, nullable=True)
    validation_report_json = Column(Text, nullable=True)
    plan_summary_json = Column(Text, nullable=True)
    throttle_state_json = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True)
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


class SimulationEventLedger(Base):
    """
    Cold planned/executed simulation events — archive-ready.
    Must not be scanned by merchant dashboard hot paths.
    """

    __tablename__ = "simulation_event_ledger"

    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(String(64), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, default="demo", index=True)
    simulated_event_id = Column(String(128), nullable=False)
    event_index = Column(Integer, nullable=False, default=0)
    event_type = Column(String(64), nullable=False, index=True)
    support = Column(String(32), nullable=False, default="supported")
    status = Column(String(32), nullable=False, default="planned", index=True)
    scenario_id = Column(String(128), nullable=True)
    scenario_version = Column(String(32), nullable=True)
    scenario_revision = Column(Integer, nullable=False, default=1)
    simulated_at = Column(DateTime, nullable=True, index=True)
    payload_json = Column(Text, nullable=False, default="{}")
    result_json = Column(Text, nullable=False, default="{}")
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

    __table_args__ = (
        UniqueConstraint(
            "simulation_run_id",
            "simulated_event_id",
            name="uq_simulation_event_ledger_run_event",
        ),
        Index(
            "ix_simulation_event_ledger_run_status",
            "simulation_run_id",
            "status",
        ),
    )


class SimulationRunArchive(Base):
    """Archived simulation run blob — restore/replay without hot-path pollution."""

    __tablename__ = "simulation_run_archives"

    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(String(64), nullable=False, unique=True, index=True)
    store_slug = Column(String(255), nullable=False, default="demo")
    archive_json = Column(Text, nullable=False, default="{}")
    archived_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SimulationRowIndex(Base):
    """
    Tagged row index for simulation_run_id cleanup isolation.
    Phase 3+ registers operational rows; cleanup deletes only indexed rows.
    """

    __tablename__ = "simulation_row_index"

    id = Column(Integer, primary_key=True)
    simulation_run_id = Column(String(64), nullable=False, index=True)
    store_slug = Column(String(255), nullable=False, default="demo", index=True)
    table_name = Column(String(128), nullable=False, index=True)
    row_pk = Column(String(128), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "simulation_run_id",
            "table_name",
            "row_pk",
            name="uq_simulation_row_index_run_table_pk",
        ),
        Index(
            "ix_simulation_row_index_run_table",
            "simulation_run_id",
            "table_name",
        ),
    )
