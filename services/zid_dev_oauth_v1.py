# -*- coding: utf-8 -*-
"""
Zid Partner development-store OAuth activation (read-only marketplace install path).

Gated by ZID_DEV_OAUTH_ENABLED — does not replace merchant dashboard OAuth (signed state).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import Store
from schema_zid_dev_oauth import ensure_store_zid_integration_schema

log = logging.getLogger("cartflow")

ZID_DEV_INTEGRATION_SOURCE = "zid_dev"
_MISSING_CODE_MESSAGE = (
    "Zid callback reached but no authorization code was received."
)


def zid_dev_oauth_enabled() -> bool:
    """Explicit opt-in for Zid development-store activation (not public marketplace)."""
    return (os.getenv("ZID_DEV_OAUTH_ENABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _resolve_deploy_commit_short() -> str:
    for key in (
        "RAILWAY_GIT_COMMIT_SHA",
        "GIT_COMMIT",
        "SOURCE_VERSION",
        "COMMIT_SHA",
    ):
        val = (os.getenv(key) or "").strip()
        if val:
            return val[:7]
    return "unknown"


def zid_dev_oauth_runtime_check_log(*, branch: str) -> None:
    """Temporary runtime branch marker for Zid dev install OAuth verification."""
    enabled = "true" if zid_dev_oauth_enabled() else "false"
    line = (
        f"[ZID DEV CHECK] enabled={enabled} "
        f"commit={_resolve_deploy_commit_short()} branch={branch}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def zid_dev_oauth_log(event: str, **fields: str) -> None:
    parts = [f"[ZID OAUTH DEV] {event}"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def persist_zid_dev_store_from_token_response(
    token_response: dict[str, Any],
) -> Optional[Store]:
    """
    Upsert Store by zid_store_id from OAuth token response (development install only).
    """
    from integrations.zid_client import (
        fetch_zid_store_id_from_profile,
        parse_zid_store_id_from_token,
        persist_oauth_tokens_on_store_row,
    )

    ensure_store_zid_integration_schema(db)
    access = (token_response.get("access_token") or "").strip()
    if not access:
        return None
    zid = parse_zid_store_id_from_token(token_response) or fetch_zid_store_id_from_profile(
        access
    )
    if not zid:
        return None
    row = db.session.query(Store).filter(Store.zid_store_id == zid).first()
    if row is None:
        row = Store(zid_store_id=zid, is_active=True)
        db.session.add(row)
    if not persist_oauth_tokens_on_store_row(row, token_response):
        return None
    now = datetime.now(timezone.utc)
    row.integration_source = ZID_DEV_INTEGRATION_SOURCE
    row.connected_at = now
    row.is_active = True
    db.session.commit()
    return row


def build_zid_dev_store_status_readonly() -> dict[str, Any]:
    """Read-only status for the latest zid_dev-connected store (no token leakage)."""
    ensure_store_zid_integration_schema(db)
    row = (
        db.session.query(Store)
        .filter(Store.integration_source == ZID_DEV_INTEGRATION_SOURCE)
        .order_by(Store.connected_at.desc(), Store.id.desc())
        .first()
    )
    if row is None:
        return {
            "connected": False,
            "zid_store_id": None,
            "integration_source": None,
            "connected_at": None,
            "token_present": False,
            "zid_dev_oauth_enabled": zid_dev_oauth_enabled(),
        }
    connected_at = getattr(row, "connected_at", None)
    if connected_at is not None and connected_at.tzinfo is None:
        connected_at = connected_at.replace(tzinfo=timezone.utc)
    return {
        "connected": bool((row.access_token or "").strip()),
        "zid_store_id": (row.zid_store_id or "").strip() or None,
        "integration_source": (row.integration_source or "").strip() or None,
        "connected_at": connected_at.isoformat() if connected_at else None,
        "token_present": bool((row.access_token or "").strip()),
        "zid_dev_oauth_enabled": zid_dev_oauth_enabled(),
    }
