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
