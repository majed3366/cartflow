# -*- coding: utf-8 -*-
"""Part 6 — chronological operational timeline (newest first)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.admin_operational_control.context import OperationalControlContext


def _parse_iso(iso: str) -> datetime | None:
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    except Exception:
        return None


def _time_label_ar(iso: str) -> str:
    ts = _parse_iso(iso)
    if ts is None:
        return "—"
    return ts.astimezone(timezone.utc).strftime("%H:%M")


def build_admin_operational_timeline(ctx: OperationalControlContext) -> dict[str, Any]:
    from services.admin_operational_health import (  # noqa: PLC0415
        get_operational_timeline_source_events,
    )

    events: list[dict[str, Any]] = []

    for ev in get_operational_timeline_source_events():
        events.append(ev)

    for item in (ctx.admin_summary.get("admin_operational_hints_ar") or [])[:3]:
        if not item:
            continue
        events.append(
            {
                "recorded_at_utc": ctx.generated_at_utc,
                "kind": "hint",
                "message_ar": str(item)[:200],
            }
        )

    for v in (ctx.issues or []):
        if v.active:
            events.append(
                {
                    "recorded_at_utc": ctx.generated_at_utc,
                    "kind": "active_issue",
                    "message_ar": f"خطر نشط: {v.problem_ar}",
                }
            )

    def sort_key(e: dict[str, Any]) -> datetime:
        ts = _parse_iso(str(e.get("recorded_at_utc") or ""))
        return ts or datetime.min.replace(tzinfo=timezone.utc)

    events.sort(key=sort_key, reverse=True)

    items: list[dict[str, Any]] = []
    for ev in events[:25]:
        iso = str(ev.get("recorded_at_utc") or "")
        items.append(
            {
                "time_ar": _time_label_ar(iso),
                "message_ar": str(ev.get("message_ar") or "—")[:240],
                "kind": str(ev.get("kind") or "event"),
            }
        )

    if not items:
        items.append(
            {
                "time_ar": "—",
                "message_ar": "لا أحداث مسجّلة بعد في هذه العملية",
                "kind": "empty",
            }
        )

    return {"items": items}
