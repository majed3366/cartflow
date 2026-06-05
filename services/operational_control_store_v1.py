# -*- coding: utf-8 -*-
"""
Durable persistence for operational controls v1.

Singleton DB row (id=1) shared across workers; in-process cache in
operational_control_v1.py reloads when updated_at changes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger(__name__)

SNAPSHOT_ROW_ID = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x)[:255] for x in raw if x is not None and str(x).strip()]
    if isinstance(raw, str) and raw.strip():
        try:
            val = json.loads(raw)
            if isinstance(val, list):
                return [str(x)[:255] for x in val if x is not None and str(x).strip()]
        except (ValueError, TypeError):
            pass
    return []


def load_durable_operational_control() -> tuple[Optional[dict[str, Any]], Optional[datetime]]:
    """
    Read singleton snapshot from DB.

    Returns (state_dict, updated_at) or (None, None) when unavailable/empty.
    """
    try:
        from extensions import db
        from models import OperationalControlSnapshot
        from schema_operational_control import ensure_operational_control_schema

        ensure_operational_control_schema(db)
        row = db.session.get(OperationalControlSnapshot, SNAPSHOT_ROW_ID)
        if row is None:
            return None, None
        return {
            "platform_wa_paused": bool(row.platform_wa_paused),
            "platform_schedule_paused": bool(row.platform_schedule_paused),
            "platform_continuation_paused": bool(row.platform_continuation_paused),
            "provider_paused": bool(row.provider_paused),
            "provider_id": (row.provider_id or None),
            "paused_stores": set(_json_list(row.paused_stores_json)),
            "paused_reasons": set(_json_list(row.paused_reasons_json)),
        }, row.updated_at
    except SQLAlchemyError as exc:
        log.warning("operational control durable load failed: %s", exc)
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None, None
    except Exception as exc:  # noqa: BLE001
        log.warning("operational control durable load error: %s", exc)
        return None, None


def persist_durable_operational_control(state: Any) -> Optional[datetime]:
    """Upsert singleton snapshot from OperationalControlState-like object."""
    try:
        from extensions import db
        from models import OperationalControlSnapshot
        from schema_operational_control import ensure_operational_control_schema

        ensure_operational_control_schema(db)
        now = _utc_now()
        row = db.session.get(OperationalControlSnapshot, SNAPSHOT_ROW_ID)
        if row is None:
            row = OperationalControlSnapshot(id=SNAPSHOT_ROW_ID)
            db.session.add(row)
        row.platform_wa_paused = bool(getattr(state, "platform_wa_paused", False))
        row.platform_schedule_paused = bool(
            getattr(state, "platform_schedule_paused", False)
        )
        row.platform_continuation_paused = bool(
            getattr(state, "platform_continuation_paused", False)
        )
        row.provider_paused = bool(getattr(state, "provider_paused", False))
        pid = getattr(state, "provider_id", None)
        row.provider_id = (str(pid)[:32] if pid else None)
        row.paused_stores_json = json.dumps(
            sorted(getattr(state, "paused_stores", set()) or []),
            ensure_ascii=False,
        )
        row.paused_reasons_json = json.dumps(
            sorted(getattr(state, "paused_reasons", set()) or []),
            ensure_ascii=False,
        )
        row.updated_at = now
        db.session.commit()
        return now
    except SQLAlchemyError as exc:
        log.warning("operational control durable persist failed: %s", exc)
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("operational control durable persist error: %s", exc)
        return None


def reset_durable_operational_control_for_tests() -> None:
    """Delete durable snapshot — tests only."""
    try:
        from extensions import db
        from models import OperationalControlSnapshot
        from schema_operational_control import (
            ensure_operational_control_schema,
            reset_operational_control_schema_guard_for_tests,
        )

        reset_operational_control_schema_guard_for_tests()
        ensure_operational_control_schema(db)
        row = db.session.get(OperationalControlSnapshot, SNAPSHOT_ROW_ID)
        if row is not None:
            db.session.delete(row)
            db.session.commit()
    except SQLAlchemyError:
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
