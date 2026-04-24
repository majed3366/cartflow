# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from extensions import db


class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    # يُعاد ملؤه بعد ‎OAuth‎ عند التأكد من ‎zid_store_id‎ من الاستجابة
    zid_store_id = db.Column(db.String(128), unique=True, nullable=True, index=True)
    access_token = db.Column(db.Text, default="")
    refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    abandoned_carts = db.relationship(
        "AbandonedCart", backref="store", lazy="dynamic"
    )
    message_logs = db.relationship("MessageLog", backref="store", lazy="dynamic")
    recovery_events = db.relationship("RecoveryEvent", backref="store", lazy="dynamic")


class AbandonedCart(db.Model):
    __tablename__ = "abandoned_carts"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), nullable=True, index=True
    )
    zid_cart_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(500), nullable=True)
    customer_phone = db.Column(db.String(100), nullable=True)
    customer_email = db.Column(db.String(500), nullable=True)
    cart_value = db.Column(db.Float, nullable=True)
    cart_url = db.Column(db.String(2048), nullable=True)
    status = db.Column(db.String(50), default="detected", nullable=False)
    raw_payload = db.Column(db.Text, nullable=True)
    first_seen_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    recovered_at = db.Column(db.DateTime, nullable=True)

    message_logs = db.relationship("MessageLog", backref="abandoned_cart", lazy="dynamic")

    @staticmethod
    def set_raw(obj: "AbandonedCart", data: Any) -> None:
        if isinstance(data, (dict, list)):
            obj.raw_payload = json.dumps(data, ensure_ascii=False)[:65000]
        else:
            obj.raw_payload = (str(data) or "")[:65000]


class MessageLog(db.Model):
    __tablename__ = "message_logs"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), nullable=False, index=True
    )
    abandoned_cart_id = db.Column(
        db.Integer, db.ForeignKey("abandoned_carts.id"), nullable=True, index=True
    )
    channel = db.Column(db.String(50), default="whatsapp", nullable=False)
    phone = db.Column(db.String(100), default="", nullable=False)
    message = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="pending", nullable=False)
    provider_response = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class ObjectionTrack(db.Model):
    """متابعة اختيار ‎objection‎ من الودجيت (سعر/جودة)."""
    __tablename__ = "objection_tracks"

    id = db.Column(db.Integer, primary_key=True)
    # عمود ‎SQL‎ ‎:type‎ — ‎"price"‎ / ‎"quality"‎
    object_type = db.Column("type", db.String(20), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class RecoveryEvent(db.Model):
    __tablename__ = "recovery_events"

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(
        db.Integer, db.ForeignKey("stores.id"), nullable=True, index=True
    )
    abandoned_cart_id = db.Column(
        db.Integer, db.ForeignKey("abandoned_carts.id"), nullable=True, index=True
    )
    event_type = db.Column(db.String(128), default="webhook", nullable=False)
    payload = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
