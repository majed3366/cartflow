# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from extensions import db


class Store(db.Model):
    """متجر مرتبط بتثبيت التطبيق عبر ‎Zid OAuth‎."""
    __tablename__ = "stores"

    id = db.Column(db.Integer, primary_key=True)
    zid_store_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    access_token = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AbandonedCart(db.Model):
    __tablename__ = "abandoned_carts"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(500), default="")
    customer_phone = db.Column(db.String(100), default="")
    cart_value = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    generated_message = db.Column(db.Text, default="")
    cart_url = db.Column(db.String(2048), default="")
