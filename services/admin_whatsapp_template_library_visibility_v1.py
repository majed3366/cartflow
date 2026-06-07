# -*- coding: utf-8 -*-
"""Admin visibility for WhatsApp template library — read-only architecture."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.merchant_whatsapp_template_library_v1 import (
    TemplateLibraryVersion,
    approval_state_label_ar,
    list_library_versions,
    resolve_active_version_key,
    resolve_fallback_chain,
    resolve_sendable_template_key,
    template_library_summary_for_api,
)


@dataclass
class AdminLibraryVersionRow:
    template_key: str
    logical_key: str
    template_version: str
    reason_tag: Optional[str]
    approval_state: str
    approval_state_ar: str
    active_version: bool
    fallback_template_key: Optional[str]
    fallback_chain: list[str]
    enabled: bool

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "template_key": self.template_key,
            "logical_key": self.logical_key,
            "template_version": self.template_version,
            "reason_tag": self.reason_tag,
            "approval_state": self.approval_state,
            "approval_state_ar": self.approval_state_ar,
            "active_version": self.active_version,
            "fallback_template_key": self.fallback_template_key,
            "fallback_chain": self.fallback_chain,
            "enabled": self.enabled,
        }


def build_admin_library_version_row(ver: TemplateLibraryVersion) -> AdminLibraryVersionRow:
    chain = resolve_fallback_chain(ver.logical_key)
    return AdminLibraryVersionRow(
        template_key=ver.template_key,
        logical_key=ver.logical_key,
        template_version=ver.template_version,
        reason_tag=ver.reason_tag,
        approval_state=ver.approval_state,
        approval_state_ar=approval_state_label_ar(ver.approval_state),
        active_version=ver.active_version,
        fallback_template_key=ver.fallback_template_key,
        fallback_chain=chain,
        enabled=ver.enabled,
    )


def list_admin_library_version_rows(
    *,
    logical_key: Optional[str] = None,
) -> list[AdminLibraryVersionRow]:
    return [
        build_admin_library_version_row(v)
        for v in list_library_versions(logical_key=logical_key)
    ]


def admin_library_operations_schema() -> list[dict[str, str]]:
    """Part I — future admin ops fields."""
    return [
        {"field": "template_version", "label_ar": "إصدار القالب"},
        {"field": "template_state", "label_ar": "حالة القالب"},
        {"field": "fallback_chain", "label_ar": "سلسلة الاحتياط"},
        {"field": "policy_adjustment_reason", "label_ar": "سبب تعديل السياسة"},
        {"field": "timing_guardrail_events", "label_ar": "أحداث حماية التوقيت"},
        {"field": "selected_template", "label_ar": "القالب المختار"},
        {"field": "sendable_template_key", "label_ar": "قالب قابل للإرسال (سياسة)"},
    ]


def admin_template_library_api_payload(
    *,
    logical_key: Optional[str] = None,
) -> dict[str, Any]:
    rows = list_admin_library_version_rows(logical_key=logical_key)
    logical_keys = sorted({r.logical_key for r in rows})
    active_map = {lk: resolve_active_version_key(lk) for lk in logical_keys}
    sendable_map = {
        lk: resolve_sendable_template_key(lk) for lk in logical_keys
    }
    return {
        "ok": True,
        **template_library_summary_for_api(),
        "admin_operations_schema": admin_library_operations_schema(),
        "active_version_by_logical_key": active_map,
        "sendable_template_by_logical_key": sendable_map,
        "rows": [r.to_api_dict() for r in rows],
    }
