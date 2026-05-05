# -*- coding: utf-8 -*-
"""ترقية ‎DB‎ اختيارية: ‎stores.whatsapp_support_url‎ + جدول ‎abandonment_reason_logs‎."""
from __future__ import annotations

import logging
from typing import Any

import models  # noqa: F401  # تسجيل ‎ORM‎ بما فيه ‎AbandonmentReasonLog‎
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

log = logging.getLogger("cartflow")

_store_abandonment_schema_ensured = False
_recovery_reason_widget_cols_ensured = False
_recovery_reason_rejection_cols_ensured = False


def _ensure_recovery_reason_rejection_columns(db: Any) -> None:
    """أعمدة ‎user_rejected_help / rejection_timestamp‎ لمسار ‎no_help‎ السلوكي."""
    global _recovery_reason_rejection_cols_ensured
    if _recovery_reason_rejection_cols_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("cart_recovery_reasons"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        ts_sql_type = (
            "TIMESTAMP(0) WITH TIME ZONE"
            if dialect == "postgresql"
            else "DATETIME"
        )
        cols = {c["name"] for c in insp.get_columns("cart_recovery_reasons")}
        if "user_rejected_help" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN IF NOT EXISTS user_rejected_help BOOLEAN "
                        "DEFAULT FALSE NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN user_rejected_help BOOLEAN DEFAULT 0 NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        cols = {
            c["name"]
            for c in inspect(db.engine).get_columns("cart_recovery_reasons")
        }
        if "rejection_timestamp" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN IF NOT EXISTS "
                        "rejection_timestamp " + ts_sql_type
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN "
                        "rejection_timestamp " + ts_sql_type
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        _recovery_reason_rejection_cols_ensured = True
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("recovery_reason_rejection_schema: %s", e)


def ensure_recovery_reason_widget_schema(db: Any) -> None:
    """
    أعمدة ‎source / created_at‎ على ‎cart_recovery_reasons‎ (ودجت الطبقة ‎D‎).
    """
    global _recovery_reason_widget_cols_ensured
    if _recovery_reason_widget_cols_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("cart_recovery_reasons"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        created_sql_type = (
            "TIMESTAMP(0) WITH TIME ZONE"
            if dialect == "postgresql"
            else "DATETIME"
        )
        cols = {c["name"] for c in insp.get_columns("cart_recovery_reasons")}
        if "source" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN IF NOT EXISTS source VARCHAR(32) DEFAULT 'widget'"
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons "
                        "ADD COLUMN source VARCHAR(32) DEFAULT 'widget'"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        cols = {
            c["name"]
            for c in inspect(db.engine).get_columns("cart_recovery_reasons")
        }
        if "created_at" not in cols:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN IF NOT EXISTS "
                        "created_at " + created_sql_type
                    )
                else:
                    stmt = (
                        "ALTER TABLE cart_recovery_reasons ADD COLUMN created_at "
                        + created_sql_type
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            try:
                db.session.execute(
                    text(
                        "UPDATE cart_recovery_reasons SET created_at = updated_at "
                        "WHERE created_at IS NULL"
                    )
                )
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
        _recovery_reason_widget_cols_ensured = True
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("recovery_reason_widget_schema: %s", e)


def _ensure_reason_subcategory_columns(db: Any) -> None:
    """إضافة ‎sub_category‎ عند الترقية (جدول سابق بلا العمود). تُنادى بشكل idempotent."""
    try:
        db.create_all()
        for tname, stmt in (
            (
                "cart_recovery_reasons",
                "ALTER TABLE cart_recovery_reasons ADD COLUMN sub_category VARCHAR(64)",
            ),
            (
                "abandonment_reason_logs",
                "ALTER TABLE abandonment_reason_logs ADD COLUMN sub_category VARCHAR(64)",
            ),
        ):
            insp = inspect(db.engine)
            if not insp.has_table(tname):
                continue
            col_names = {c["name"] for c in insp.get_columns(tname)}
            if "sub_category" in col_names:
                continue
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget sub_category: %s", e)


def _ensure_recovery_reason_customer_phone_column(db: Any) -> None:
    """عمود ‎customer_phone‎ على ‎cart_recovery_reasons‎ (اختبار/مسار الواتساب)."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("cart_recovery_reasons"):
            return
        col_names = {c["name"] for c in insp.get_columns("cart_recovery_reasons")}
        if "customer_phone" in col_names:
            return
        stmt = (
            "ALTER TABLE cart_recovery_reasons "
            "ADD COLUMN customer_phone VARCHAR(100)"
        )
        db.session.execute(text(stmt))
        db.session.commit()
    except (OSError, SQLAlchemyError, IntegrityError):
        db.session.rollback()
        log.debug("schema_widget customer_phone: column add skipped or failed")


def ensure_cart_recovery_reason_phone_schema(db: Any) -> None:
    """يُصدَّر للاستدعاء من ‎main‎ قبل استعلام ‎CartRecoveryReason‎."""
    _ensure_recovery_reason_customer_phone_column(db)


def ensure_cart_recovery_reason_rejection_schema(db: Any) -> None:
    """يُصدَّر للاستدعاء من ‎main‎ و‎cart-recovery/reason‎ قبل تحديث أعلام الرفض."""
    _ensure_recovery_reason_rejection_columns(db)


def _ensure_store_reason_templates_json_column(db: Any) -> None:
    """عمود ‎reason_templates_json‎ على ‎stores‎."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "reason_templates_json" in existing:
            return
        text_sql = "TEXT"
        try:
            if dialect == "postgresql":
                stmt = (
                    "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                    f"reason_templates_json {text_sql}"
                )
            else:
                stmt = (
                    f"ALTER TABLE stores ADD COLUMN reason_templates_json {text_sql}"
                )
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget reason_templates_json: %s", e)


def _ensure_store_trigger_templates_json_column(db: Any) -> None:
    """عمود ‎trigger_templates_json‎ على ‎stores‎ — قوالب حسب سبب التردد للاسترجاع."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "trigger_templates_json" in existing:
            return
        text_sql = "TEXT"
        try:
            if dialect == "postgresql":
                stmt = (
                    "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                    f"trigger_templates_json {text_sql}"
                )
            else:
                stmt = (
                    f"ALTER TABLE stores ADD COLUMN trigger_templates_json {text_sql}"
                )
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget trigger_templates_json: %s", e)


def _ensure_store_whatsapp_recovery_template_columns(db: Any) -> None:
    """أعمدة قوالب واتساب الاسترجاع على ‎stores‎ — تُستدعى دائماً (فحص أعمدة ‎idempotent‎)."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        text_sql = "TEXT"
        for col in (
            "template_price",
            "template_shipping",
            "template_quality",
            "template_delivery",
            "template_warranty",
            "template_other",
        ):
            if col in existing:
                continue
            try:
                if dialect == "postgresql":
                    stmt = (
                        f"ALTER TABLE stores ADD COLUMN IF NOT EXISTS {col} {text_sql}"
                    )
                else:
                    stmt = f"ALTER TABLE stores ADD COLUMN {col} {text_sql}"
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget store recovery templates: %s", e)


def _ensure_store_template_control_columns(db: Any) -> None:
    """أعمدة ‎template_mode / template_tone / template_custom_text‎ على ‎stores‎."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "template_mode" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS template_mode "
                        "VARCHAR(32) DEFAULT 'preset' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN template_mode "
                        "VARCHAR(32) DEFAULT 'preset' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "template_tone" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS template_tone "
                        "VARCHAR(32) DEFAULT 'friendly' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN template_tone "
                        "VARCHAR(32) DEFAULT 'friendly' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "template_custom_text" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "template_custom_text TEXT"
                    )
                else:
                    stmt = "ALTER TABLE stores ADD COLUMN template_custom_text TEXT"
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget template control: %s", e)


def _ensure_store_exit_intent_template_columns(db: Any) -> None:
    """أعمدة ‎exit_intent_*‎ لرسالة الخروج قبل السلة."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "exit_intent_template_mode" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "exit_intent_template_mode VARCHAR(32) DEFAULT 'preset' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN exit_intent_template_mode "
                        "VARCHAR(32) DEFAULT 'preset' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "exit_intent_template_tone" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "exit_intent_template_tone VARCHAR(32) DEFAULT 'friendly' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN exit_intent_template_tone "
                        "VARCHAR(32) DEFAULT 'friendly' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "exit_intent_custom_text" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "exit_intent_custom_text TEXT"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN exit_intent_custom_text TEXT"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget exit intent template: %s", e)


def _ensure_store_widget_customization_columns(db: Any) -> None:
    """أعمدة تخصيص مظهر الودجيت (‎widget_*‎) على ‎stores‎."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "widget_name" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS widget_name "
                        "VARCHAR(255) DEFAULT 'مساعد المتجر' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN widget_name VARCHAR(255) "
                        "DEFAULT 'مساعد المتجر' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "widget_primary_color" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "widget_primary_color VARCHAR(16) DEFAULT '#6C5CE7' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN widget_primary_color "
                        "VARCHAR(16) DEFAULT '#6C5CE7' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
        if "widget_style" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS widget_style "
                        "VARCHAR(16) DEFAULT 'modern' NOT NULL"
                    )
                else:
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN widget_style "
                        "VARCHAR(16) DEFAULT 'modern' NOT NULL"
                    )
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget widget customization: %s", e)


def _ensure_abandoned_cart_vip_mode_column(db: Any) -> None:
    """عمود ‎vip_mode‎ على ‎abandoned_carts‎ — ‎False‎ = سلوك عادي."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("abandoned_carts"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("abandoned_carts")}
        if "vip_mode" in existing:
            return
        try:
            if dialect in ("postgresql", "postgres"):
                stmt = (
                    "ALTER TABLE abandoned_carts ADD COLUMN IF NOT EXISTS "
                    "vip_mode BOOLEAN NOT NULL DEFAULT FALSE"
                )
            else:
                stmt = (
                    "ALTER TABLE abandoned_carts ADD COLUMN vip_mode "
                    "BOOLEAN NOT NULL DEFAULT 0"
                )
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget abandoned_carts vip_mode: %s", e)


def _ensure_abandoned_cart_recovery_session_id_column(db: Any) -> None:
    """عمود ‎recovery_session_id‎ على ‎abandoned_carts‎ (‎session_id‎ من الويدجت عند الترك)."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("abandoned_carts"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("abandoned_carts")}
        if "recovery_session_id" in existing:
            return
        try:
            if dialect in ("postgresql", "postgres"):
                stmt = (
                    "ALTER TABLE abandoned_carts ADD COLUMN IF NOT EXISTS "
                    "recovery_session_id VARCHAR(512)"
                )
            else:
                stmt = (
                    "ALTER TABLE abandoned_carts ADD COLUMN recovery_session_id "
                    "VARCHAR(512)"
                )
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget abandoned_carts recovery_session_id: %s", e)


def _ensure_store_recovery_delay_minutes_column(db: Any) -> None:
    """عمود ‎recovery_delay_minutes‎ على ‎stores‎ (اختياري)."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "recovery_delay_minutes" in existing:
            return
        try:
            if dialect in ("postgresql", "postgres"):
                stmt = (
                    "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                    "recovery_delay_minutes INTEGER"
                )
            else:
                stmt = "ALTER TABLE stores ADD COLUMN recovery_delay_minutes INTEGER"
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget recovery_delay_minutes: %s", e)


def _ensure_store_vip_cart_threshold_column(db: Any) -> None:
    """عتبة السلة المميزة (‎vip_cart_threshold‎) على ‎stores‎ — ‎NULL‎ = معطّل."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        existing = {c["name"] for c in insp.get_columns("stores")}
        if "vip_cart_threshold" not in existing:
            try:
                if dialect == "postgresql":
                    stmt = (
                        "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                        "vip_cart_threshold INTEGER"
                    )
                else:
                    stmt = "ALTER TABLE stores ADD COLUMN vip_cart_threshold INTEGER"
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget vip_cart_threshold: %s", e)


def _ensure_store_vip_offer_columns(db: Any) -> None:
    """إعدادات عروض VIP للوحة فقط (‎vip_offer_*‎)."""
    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        stmts_sqlite = [
            "ALTER TABLE stores ADD COLUMN vip_offer_enabled INTEGER DEFAULT 0",
            "ALTER TABLE stores ADD COLUMN vip_offer_type VARCHAR(32)",
            "ALTER TABLE stores ADD COLUMN vip_offer_value VARCHAR(500)",
        ]
        stmts_pg = [
            (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "vip_offer_enabled BOOLEAN NOT NULL DEFAULT FALSE"
            ),
            (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "vip_offer_type VARCHAR(32)"
            ),
            (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "vip_offer_value VARCHAR(500)"
            ),
        ]
        col_names = ("vip_offer_enabled", "vip_offer_type", "vip_offer_value")
        stmts = stmts_pg if dialect in ("postgresql", "postgres") else stmts_sqlite
        for name, stmt in zip(col_names, stmts):
            existing = {c["name"] for c in insp.get_columns("stores")}
            if name in existing:
                continue
            try:
                db.session.execute(text(stmt))
                db.session.commit()
            except (OSError, SQLAlchemyError, IntegrityError):
                db.session.rollback()
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget vip_offer: %s", e)


def ensure_store_widget_schema(db: Any) -> None:
    """يُنادى من مسارات ‎API‎ (لا يعتمد على ‎main‎)."""
    _ensure_store_recovery_delay_minutes_column(db)
    _ensure_reason_subcategory_columns(db)
    ensure_recovery_reason_widget_schema(db)
    _ensure_recovery_reason_customer_phone_column(db)
    _ensure_recovery_reason_rejection_columns(db)
    _ensure_store_whatsapp_recovery_template_columns(db)
    _ensure_store_trigger_templates_json_column(db)
    _ensure_store_reason_templates_json_column(db)
    _ensure_store_template_control_columns(db)
    _ensure_store_exit_intent_template_columns(db)
    _ensure_store_widget_customization_columns(db)
    _ensure_store_vip_cart_threshold_column(db)
    _ensure_store_vip_offer_columns(db)
    _ensure_abandoned_cart_vip_mode_column(db)
    _ensure_abandoned_cart_recovery_session_id_column(db)
    global _store_abandonment_schema_ensured
    if _store_abandonment_schema_ensured:
        return
    try:
        db.create_all()
        insp = inspect(db.engine)
        if insp.has_table("stores"):
            existing = {c["name"] for c in insp.get_columns("stores")}
            if "whatsapp_support_url" not in existing:
                try:
                    db.session.execute(
                        text(
                            "ALTER TABLE stores ADD COLUMN whatsapp_support_url VARCHAR(2048)"
                        )
                    )
                    db.session.commit()
                except (OSError, SQLAlchemyError, IntegrityError):
                    db.session.rollback()
            existing = {c["name"] for c in insp.get_columns("stores")}
            if "store_whatsapp_number" not in existing:
                try:
                    db.session.execute(
                        text(
                            "ALTER TABLE stores ADD COLUMN store_whatsapp_number VARCHAR(64)"
                        )
                    )
                    db.session.commit()
                except (OSError, SQLAlchemyError, IntegrityError):
                    db.session.rollback()
        _store_abandonment_schema_ensured = True
    except (OSError, SQLAlchemyError) as e:
        db.session.rollback()
        log.debug("schema_widget: %s", e)
