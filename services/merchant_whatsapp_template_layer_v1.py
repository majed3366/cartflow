# -*- coding: utf-8 -*-
"""Merchant WhatsApp template customization layer — architecture only (no send/runtime)."""
from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from services.merchant_whatsapp_reason_mapping_v1 import REASON_TO_TEMPLATE_KEY
from services.merchant_whatsapp_template_registry_v1 import (
    MERCHANT_EDITABLE_TEMPLATE_KEYS,
    TEMPLATE_REGISTRY,
    TemplateRegistryEntry,
    get_registry_entry,
    meta_status_label_ar,
)

_MAX_CONTENT_CHARS = 65535
_schema_once = False


def parse_whatsapp_template_overrides_column(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Parse Store.whatsapp_template_overrides_json → {TEMPLATE_KEY: {enabled, custom_content}}."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        data = raw
    else:
        s = str(raw).strip()
        if not s:
            return {}
        try:
            data = json.loads(s)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for key, entry in data.items():
        tk = (key or "").strip().upper()
        if tk not in MERCHANT_EDITABLE_TEMPLATE_KEYS:
            continue
        if not isinstance(entry, dict):
            continue
        enabled = bool(entry.get("enabled", True))
        content_raw = entry.get("custom_content")
        if content_raw is None:
            content_raw = entry.get("content")
        custom_content = (
            str(content_raw).strip()[:_MAX_CONTENT_CHARS]
            if content_raw is not None
            else ""
        )
        row: Dict[str, Any] = {"enabled": enabled}
        if custom_content:
            row["custom_content"] = custom_content
        out[tk] = row
    return out


def _effective_content(
    entry: TemplateRegistryEntry,
    override: Optional[Dict[str, Any]],
) -> str:
    if override:
        custom = str(override.get("custom_content") or "").strip()
        if custom:
            return custom
    return entry.default_content


def _is_customized(
    entry: TemplateRegistryEntry,
    override: Optional[Dict[str, Any]],
) -> bool:
    if not override:
        return False
    custom = str(override.get("custom_content") or "").strip()
    return bool(custom and custom != entry.default_content)


def _effective_enabled(
    entry: TemplateRegistryEntry,
    override: Optional[Dict[str, Any]],
) -> bool:
    if override and "enabled" in override:
        return bool(override.get("enabled"))
    return entry.enabled


def build_merchant_template_row(
    entry: TemplateRegistryEntry,
    override: Optional[Dict[str, Any]],
) -> dict[str, Any]:
    customized = _is_customized(entry, override)
    return {
        "template_key": entry.template_key,
        "reason_tag": entry.reason_tag,
        "display_name_ar": entry.display_name_ar,
        "template_type": entry.template_type,
        "enabled": _effective_enabled(entry, override),
        "default_content": entry.default_content,
        "effective_content": _effective_content(entry, override),
        "is_customized": customized,
        "customization_state_ar": "مخصص" if customized else "افتراضي",
        "merchant_editable": entry.merchant_editable,
        "customization_plan_tier": entry.customization_plan_tier,
        "future_meta_template_name": entry.future_meta_template_name,
        "future_meta_status": entry.future_meta_status,
        "future_meta_status_ar": meta_status_label_ar(entry.future_meta_status),
        "mapping_locked": True,
    }


def merchant_whatsapp_template_layer_for_api(
    store: Optional[Any],
) -> dict[str, Any]:
    """Merchant-facing template layer — editable reason templates only in UI."""
    ensure_whatsapp_template_overrides_schema(None)
    overrides = parse_whatsapp_template_overrides_column(
        getattr(store, "whatsapp_template_overrides_json", None) if store else None
    )
    merchant_rows: list[dict[str, Any]] = []
    for tk in sorted(MERCHANT_EDITABLE_TEMPLATE_KEYS):
        entry = TEMPLATE_REGISTRY[tk]
        merchant_rows.append(build_merchant_template_row(entry, overrides.get(tk)))

    system_rows: list[dict[str, Any]] = []
    for tk, entry in TEMPLATE_REGISTRY.items():
        if entry.merchant_editable:
            continue
        system_rows.append(build_merchant_template_row(entry, None))

    return {
        "whatsapp_template_registry_version": "v1",
        "whatsapp_template_layer_architecture_only": True,
        "whatsapp_template_runtime_unchanged": True,
        "whatsapp_template_merchant_rows": merchant_rows,
        "whatsapp_template_system_rows": system_rows,
        "whatsapp_template_reason_mapping": [
            {
                "reason_tag": reason,
                "template_key": tk,
                "display_name_ar": (
                    get_registry_entry(tk).display_name_ar
                    if get_registry_entry(tk)
                    else reason
                ),
                "mapping_locked": True,
            }
            for reason, tk in REASON_TO_TEMPLATE_KEY.items()
            if reason != "unknown"
        ],
        "whatsapp_template_plan_alignment": {
            "starter": "قوالب افتراضية فقط — بدون تعديل (معمارية فقط)",
            "growth": "تعديل الصياغة وتفعيل/تعطيل لكل سبب",
            "pro": "مكتبة قوالب متقدمة (مستقبل)",
            "enforcement": False,
        },
    }


def whatsapp_template_fields_for_api(store: Optional[Any]) -> dict[str, Any]:
    layer = merchant_whatsapp_template_layer_for_api(store)
    overrides = parse_whatsapp_template_overrides_column(
        getattr(store, "whatsapp_template_overrides_json", None) if store else None
    )
    return {
        **layer,
        "whatsapp_template_overrides": overrides,
    }


def apply_whatsapp_template_layer_from_body(
    row: Any,
    body: Mapping[str, Any],
) -> None:
    """Persist merchant overrides — only editable template keys; no mapping changes."""
    ensure_whatsapp_template_overrides_schema(None)
    base = parse_whatsapp_template_overrides_column(
        getattr(row, "whatsapp_template_overrides_json", None)
    )

    restore_keys = body.get("whatsapp_template_restore_defaults")
    if isinstance(restore_keys, list):
        for raw_key in restore_keys:
            tk = str(raw_key or "").strip().upper()
            if tk in MERCHANT_EDITABLE_TEMPLATE_KEYS:
                base.pop(tk, None)

    incoming = body.get("whatsapp_template_overrides")
    if isinstance(incoming, dict):
        for raw_key, entry in incoming.items():
            tk = str(raw_key or "").strip().upper()
            if tk not in MERCHANT_EDITABLE_TEMPLATE_KEYS:
                continue
            if not isinstance(entry, dict):
                continue
            prev = dict(base.get(tk, {}))
            if "enabled" in entry:
                prev["enabled"] = bool(entry.get("enabled"))
            if "custom_content" in entry:
                raw_content = entry.get("custom_content")
                if raw_content is None or not str(raw_content).strip():
                    prev.pop("custom_content", None)
                else:
                    prev["custom_content"] = str(raw_content).strip()[
                        :_MAX_CONTENT_CHARS
                    ]
            if prev.get("custom_content") or "enabled" in prev:
                base[tk] = prev
            elif tk in base:
                base[tk] = prev

    row.whatsapp_template_overrides_json = (
        json.dumps(base, ensure_ascii=False) if base else None
    )


def ensure_store_whatsapp_template_overrides_column(db: Any) -> None:
    from sqlalchemy.exc import IntegrityError

    try:
        db.create_all()
        insp = inspect(db.engine)
        if not insp.has_table("stores"):
            return
        cols = {c["name"] for c in insp.get_columns("stores")}
        if "whatsapp_template_overrides_json" in cols:
            return
        dialect = getattr(getattr(db.engine, "dialect", None), "name", "") or ""
        col_type = "TEXT"
        if dialect in ("postgresql", "postgres"):
            stmt = (
                "ALTER TABLE stores ADD COLUMN IF NOT EXISTS "
                "whatsapp_template_overrides_json TEXT"
            )
        else:
            stmt = (
                f"ALTER TABLE stores ADD COLUMN whatsapp_template_overrides_json "
                f"{col_type}"
            )
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except (OSError, SQLAlchemyError, IntegrityError):
            db.session.rollback()
    except SQLAlchemyError:
        db.session.rollback()


def ensure_whatsapp_template_overrides_schema(db: Any) -> None:
    global _schema_once
    if _schema_once:
        return
    if db is None:
        from extensions import db as ext_db

        db = ext_db
    ensure_store_whatsapp_template_overrides_column(db)
    _schema_once = True


def reset_whatsapp_template_overrides_schema_guard_for_tests() -> None:
    global _schema_once
    _schema_once = False
