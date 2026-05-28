# -*- coding: utf-8 -*-
"""Read-only truth report: dashboard template storage vs runtime resolver lookup."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.reason_template_recovery import canonical_reason_template_key
from services.recovery_multi_message import diagnose_multi_message_config
from services.store_reason_templates import parse_reason_templates_column
from services.trigger_templates_dashboard import build_trigger_templates_get_payload


def build_template_truth_report(
    *,
    store_slug: str,
    reason: str,
) -> Dict[str, Any]:
    ss = (store_slug or "").strip()[:255]
    rt = (reason or "").strip()[:64]
    canon = canonical_reason_template_key(rt)
    try:
        from services.dashboard_store_context import dashboard_canonical_store_row
        from services.recovery_store_lookup import resolve_recovery_store_row_canonical

        dash_row = dashboard_canonical_store_row(ss, allow_schema_warm=True)
        runtime_row = resolve_recovery_store_row_canonical(ss, allow_schema_warm=True)
        row = runtime_row or dash_row
        store_found = row is not None
        raw_json = getattr(row, "reason_templates_json", None) if row is not None else None
        parsed = parse_reason_templates_column(raw_json) if row is not None else {}
        entry = parsed.get(canon) if canon else None
        entry_key_found = canon if entry is not None else None
        dashboard_payload = build_trigger_templates_get_payload(dash_row)
        diag = diagnose_multi_message_config(rt, row)
        out: Dict[str, Any] = {
            "ok": True,
            "store_slug": ss,
            "reason": rt,
            "store_found": store_found,
            "store_id": int(getattr(row, "id", 0) or 0) if row is not None else None,
            "store_zid": (getattr(row, "zid_store_id", None) or "").strip() if row is not None else None,
            "raw_reason_templates_json": raw_json,
            "dashboard_trigger_templates_response": dashboard_payload,
            "runtime_lookup_key": canon,
            "template_entry_found": bool(diag.get("template_entry_found")),
            "entry_key_found": entry_key_found,
            "message_count": diag.get("message_count"),
            "messages_array_len": diag.get("messages_array_len"),
            "guided_attempts_keys": diag.get("guided_attempts_keys"),
            "materialized_len": diag.get("materialized_len"),
            "slots_len": diag.get("slots_len"),
            "miss_reason": diag.get("miss_reason"),
            "dashboard_store_id": int(getattr(dash_row, "id", 0) or 0) if dash_row is not None else None,
            "dashboard_store_zid": (getattr(dash_row, "zid_store_id", None) or "").strip() if dash_row is not None else None,
            "runtime_store_id": int(getattr(runtime_row, "id", 0) or 0) if runtime_row is not None else None,
            "runtime_store_zid": (getattr(runtime_row, "zid_store_id", None) or "").strip() if runtime_row is not None else None,
        }
        return out
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": str(exc), "store_slug": ss, "reason": rt}
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return {"ok": False, "error": str(exc), "store_slug": ss, "reason": rt}

