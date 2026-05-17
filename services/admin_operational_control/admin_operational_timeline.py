# -*- coding: utf-8 -*-
"""Part 6 — chronological operational timeline (newest first) with severity."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.admin_operational_control.context import OperationalControlContext

_SEVERITY_BY_KIND: dict[str, tuple[str, str]] = {
    "pool": ("risk", "🔴"),
    "cart_event": ("risk", "🔴"),
    "anomaly": ("warning", "🟡"),
    "hint": ("warning", "🟡"),
    "active_issue": ("risk", "🔴"),
    "active_issue_potential": ("warning", "🟡"),
    "stable": ("recovered", "🟢"),
    "recovered": ("recovered", "🟢"),
    "empty": ("warning", "🟡"),
    "critical": ("critical", "🚨"),
}


def _timeline_severity(kind: str, *, tier: str = "") -> dict[str, str]:
    if kind == "active_issue" and tier == "potential":
        sev, emoji = _SEVERITY_BY_KIND["active_issue_potential"]
    elif kind in _SEVERITY_BY_KIND:
        sev, emoji = _SEVERITY_BY_KIND[kind]
    else:
        sev, emoji = "warning", "🟡"
    return {"severity": sev, "severity_emoji": emoji}


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

    for issue in ctx.issues or []:
        if issue.active:
            events.append(
                {
                    "recorded_at_utc": ctx.generated_at_utc,
                    "kind": "active_issue",
                    "tier": issue.tier,
                    "message_ar": f"{issue.problem_ar}",
                }
            )

    def sort_key(e: dict[str, Any]) -> datetime:
        ts = _parse_iso(str(e.get("recorded_at_utc") or ""))
        return ts or datetime.min.replace(tzinfo=timezone.utc)

    events.sort(key=sort_key, reverse=True)

    items: list[dict[str, Any]] = []
    for ev in events[:25]:
        iso = str(ev.get("recorded_at_utc") or "")
        kind = str(ev.get("kind") or "event")
        tier = str(ev.get("tier") or "")
        sev = _timeline_severity(kind, tier=tier)
        items.append(
            {
                "time_ar": _time_label_ar(iso),
                "message_ar": str(ev.get("message_ar") or "—")[:240],
                "kind": kind,
                **sev,
            }
        )

    if not items:
        sev = _timeline_severity("stable")
        items.append(
            {
                "time_ar": "—",
                "message_ar": "لا أحداث مسجّلة بعد في هذه العملية",
                "kind": "empty",
                **sev,
            }
        )

    return {"items": items}
