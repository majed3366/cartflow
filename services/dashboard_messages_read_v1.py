# -*- coding: utf-8 -*-
"""
Messages read model — bounded DB phase, then release, then compose.

INV-ADM-05 / INV-ADM-06: do not hold a QueuePool checkout across
timeline/lifecycle/message composition or JSON assembly.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.db_lifecycle_v1.unit_of_work import close_request_uow_if_clean


def compose_messages_payload(
    *,
    message_history_rows: Sequence[Mapping[str, Any]],
    refresh_state: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Pure compose from materialized row dicts. No DB."""
    rows = list(message_history_rows or ())
    last_send_ar = "—"
    if rows:
        last_send_ar = str(rows[0].get("time_ar") or "—")
    out: dict[str, Any] = {
        "merchant_message_history_rows": rows,
        "merchant_wa_last_send_ar": last_send_ar,
    }
    if refresh_state:
        out.update(dict(refresh_state))
    return out


def release_messages_db_phase() -> bool:
    """HTTP boundary only: return the connection before encode (INV-ADM-05)."""
    return close_request_uow_if_clean(reason="messages_read_db_phase")


def compose_messages_after_db_phase(
    message_history_rows: Sequence[Mapping[str, Any]],
    refresh_state: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Release the scoped session, then compose. HTTP route only — not shared helpers."""
    release_messages_db_phase()
    return compose_messages_payload(
        message_history_rows=message_history_rows,
        refresh_state=refresh_state,
    )


__all__ = [
    "compose_messages_after_db_phase",
    "compose_messages_payload",
    "release_messages_db_phase",
]
