# -*- coding: utf-8 -*-
"""
Gate 1 — Home Slim Transport V1.

Home summary may carry only lightweight executive teaser inputs + HES package.
Heavy MEIF / ORV / Daily Brief / Pulse / ACF payloads are stripped or never attached.
"""
from __future__ import annotations

from typing import Any, Mapping

ENV_HOME_SLIM_TRANSPORT_V1 = "CARTFLOW_HOME_SLIM_TRANSPORT_V1"

# Keys removed from /api/dashboard/summary when slim transport is on.
HEAVY_SUMMARY_KEYS_V1 = (
    "merchant_experience_integration_v1",
    "observation_reality_validation_v1",
    "merchant_daily_brief_v1",
    "merchant_pulse_v1",
    "commerce_signals_v1",
    "home_adaptive_cognition_v1",
    "adaptive_cognition_v1",
)


def home_slim_transport_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    import os

    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_HOME_SLIM_TRANSPORT_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return default


def _abandoned_count(summary: Mapping[str, Any]) -> int:
    if _as_int(summary.get("merchant_nav_badge_abandoned")):
        return _as_int(summary.get("merchant_nav_badge_abandoned"))
    counts = summary.get("merchant_store_cart_counts")
    if isinstance(counts, Mapping):
        for key in ("active_total", "abandoned", "waiting_send"):
            n = _as_int(counts.get(key))
            if n:
                return n
    return _as_int(str(summary.get("merchant_kpi_abandoned_fmt") or "0").replace(",", ""))


def _wa_sent_count(summary: Mapping[str, Any]) -> int:
    return _as_int(str(summary.get("merchant_kpi_wa_sent_fmt") or "0").replace(",", ""))


def extract_home_teaser_inputs_v1(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Build constitutional teaser inputs from light summary fields and any
    already-attached fat packages (which will be stripped after extract).
    """
    src = summary if isinstance(summary, Mapping) else {}
    abandoned = _abandoned_count(src)
    wa_sent = _wa_sent_count(src)

    decisions_count = 0
    decisions_title = ""
    meif = src.get("merchant_experience_integration_v1")
    if isinstance(meif, Mapping):
        pages = meif.get("pages") if isinstance(meif.get("pages"), Mapping) else {}
        home = pages.get("home") if isinstance(pages, Mapping) else {}
        sections = (
            home.get("sections") if isinstance(home, Mapping) and isinstance(home.get("sections"), Mapping) else {}
        )
        decisions = list((sections or {}).get("merchant_decisions") or [])
        decisions_count = len(decisions)
        if decisions and isinstance(decisions[0], Mapping):
            decisions_title = str(
                decisions[0].get("title_ar")
                or decisions[0].get("merchant_summary")
                or decisions[0].get("title")
                or ""
            ).strip()
        carts_page = pages.get("carts") if isinstance(pages, Mapping) else {}
        if isinstance(carts_page, Mapping):
            abandoned = max(
                abandoned,
                _as_int(carts_page.get("durable_cart_count")),
            )
        comm = pages.get("communication") if isinstance(pages, Mapping) else {}
        if isinstance(comm, Mapping):
            cops = (
                comm.get("operational_truth")
                if isinstance(comm.get("operational_truth"), Mapping)
                else {}
            )
            wa_sent = max(wa_sent, _as_int((cops or {}).get("mock_whatsapp_sent")))
            schedules = _as_int((cops or {}).get("recovery_schedules"))
        else:
            schedules = 0
    else:
        schedules = 0

    obs_count = 0
    obs_top: dict[str, str] | None = None
    orv = src.get("observation_reality_validation_v1")
    if isinstance(orv, Mapping):
        findings = [f for f in list(orv.get("findings") or []) if isinstance(f, Mapping)]
        named = [
            f
            for f in findings
            if str(f.get("product_name_ar") or "").strip()
            and str(f.get("statement_ar") or "").strip()
        ]
        obs_count = len(named)
        if named:
            obs_top = {
                "product_name_ar": str(named[0].get("product_name_ar") or "").strip(),
                "statement_ar": str(named[0].get("statement_ar") or "").strip(),
            }

    return {
        "schema": "home_teaser_inputs_v1",
        "health": {
            "watching": abandoned > 0,
            "abandoned_carts": abandoned,
        },
        "decisions": {
            "count": decisions_count,
            "top_title_ar": decisions_title,
        },
        "observations": {
            "count": obs_count,
            "top": obs_top,
        },
        "carts": {"count": abandoned},
        "communication": {
            "sent": wa_sent,
            "schedules": schedules,
            "activity": (wa_sent + schedules) > 0,
        },
    }


def strip_heavy_home_summary_payload_v1(summary: dict[str, Any]) -> dict[str, Any]:
    """Remove page-owned heavy packages from the Home summary transport."""
    if not isinstance(summary, dict):
        return summary
    for key in HEAVY_SUMMARY_KEYS_V1:
        summary.pop(key, None)
    # Keep a minimal home experience stub (slug only) — drop Daily Brief embed.
    home = summary.get("merchant_home_experience_v1")
    if isinstance(home, dict):
        summary["merchant_home_experience_v1"] = {
            "ok": bool(home.get("ok", True)),
            "store_slug": str(home.get("store_slug") or "").strip(),
            "slim_transport": True,
            "version": home.get("version") or "slim_transport_v1",
        }
    summary["home_slim_transport_v1"] = True
    return summary


def minimal_home_experience_stub_v1(store_slug: str) -> dict[str, Any]:
    return {
        "ok": True,
        "store_slug": str(store_slug or "").strip(),
        "slim_transport": True,
        "version": "slim_transport_v1",
    }


__all__ = [
    "ENV_HOME_SLIM_TRANSPORT_V1",
    "HEAVY_SUMMARY_KEYS_V1",
    "extract_home_teaser_inputs_v1",
    "home_slim_transport_v1_enabled",
    "minimal_home_experience_stub_v1",
    "strip_heavy_home_summary_payload_v1",
]
