# -*- coding: utf-8 -*-
"""
Gate 1 — Home Slim Transport V1 (+ Gate 1-B teaser enrichment).

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


def _fmt_int(summary: Mapping[str, Any], *keys: str) -> int:
    for key in keys:
        if key in summary and summary.get(key) is not None:
            raw = summary.get(key)
            if isinstance(raw, (int, float)):
                return _as_int(raw)
            return _as_int(str(raw or "0").replace(",", ""))
    return 0


def _store_counts(summary: Mapping[str, Any]) -> dict[str, int]:
    counts = summary.get("merchant_store_cart_counts")
    if not isinstance(counts, Mapping):
        stats = summary.get("normal_carts_stats")
        if isinstance(stats, Mapping) and isinstance(
            stats.get("merchant_store_cart_counts"), Mapping
        ):
            counts = stats.get("merchant_store_cart_counts")
        else:
            counts = {}
    src = counts if isinstance(counts, Mapping) else {}
    return {
        "active": _as_int(src.get("active_total")),
        "waiting": _as_int(
            src.get("waiting_total")
            or src.get("waiting_send")
            or src.get("abandoned")
        ),
        "no_phone": _as_int(src.get("no_phone_total") or src.get("canonical_no_phone_total")),
        "archived": _as_int(src.get("archived_total")),
    }


def _kpis(summary: Mapping[str, Any]) -> dict[str, int]:
    kpis = summary.get("kpis") if isinstance(summary.get("kpis"), Mapping) else {}
    return {
        "abandoned_today": _as_int(kpis.get("abandoned_today"))
        or _fmt_int(summary, "merchant_kpi_abandoned_fmt"),
        "recovered_today": _as_int(kpis.get("recovered_today"))
        or _fmt_int(summary, "merchant_kpi_recovered_fmt"),
        "wa_sent_today": _as_int(kpis.get("whatsapp_sent_today"))
        or _fmt_int(summary, "merchant_kpi_wa_sent_fmt"),
    }


def _store_connected(summary: Mapping[str, Any]) -> bool | None:
    for key in ("store_connection", "store_connection_status"):
        conn = summary.get(key)
        if isinstance(conn, Mapping):
            if "store_connected_ok" in conn:
                return bool(conn.get("store_connected_ok"))
            state = str(conn.get("state_key") or conn.get("connection_state") or "").lower()
            if state in {"connected", "ready", "ok"}:
                return True
            if state in {"disconnected", "setup_required", "not_connected", "error"}:
                return False
    return None


def _wa_state(summary: Mapping[str, Any]) -> str:
    card = summary.get("whatsapp_readiness_card")
    if isinstance(card, Mapping):
        return str(card.get("state_key") or "").strip().lower()
    return str(summary.get("wa_state_key") or "").strip().lower()


def extract_home_teaser_inputs_v1(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Build constitutional teaser inputs from light summary fields and any
    already-attached fat packages (which will be stripped after extract).
    """
    src = summary if isinstance(summary, Mapping) else {}
    counts = _store_counts(src)
    kpis = _kpis(src)
    waiting = max(
        counts["waiting"],
        _as_int(src.get("merchant_nav_badge_abandoned")),
        kpis["abandoned_today"],
    )
    active = counts["active"]
    no_phone = counts["no_phone"]
    wa_sent = kpis["wa_sent_today"]
    recovered = kpis["recovered_today"]
    wa_state = _wa_state(src)
    store_ok = _store_connected(src)

    decisions_count = 0
    decisions_title = ""
    decisions_evidence = "none"
    schedules = 0
    meif = src.get("merchant_experience_integration_v1")
    if isinstance(meif, Mapping):
        pages = meif.get("pages") if isinstance(meif.get("pages"), Mapping) else {}
        home = pages.get("home") if isinstance(pages, Mapping) else {}
        sections = (
            home.get("sections")
            if isinstance(home, Mapping) and isinstance(home.get("sections"), Mapping)
            else {}
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
            if decisions_count and decisions_title:
                decisions_evidence = "decision_titles"
        carts_page = pages.get("carts") if isinstance(pages, Mapping) else {}
        if isinstance(carts_page, Mapping):
            waiting = max(waiting, _as_int(carts_page.get("durable_cart_count")))
            cops = (
                carts_page.get("operational_truth")
                if isinstance(carts_page.get("operational_truth"), Mapping)
                else {}
            )
            no_phone = max(no_phone, _as_int((cops or {}).get("no_phone_total")))
        comm = pages.get("communication") if isinstance(pages, Mapping) else {}
        if isinstance(comm, Mapping):
            cops = (
                comm.get("operational_truth")
                if isinstance(comm.get("operational_truth"), Mapping)
                else {}
            )
            wa_sent = max(wa_sent, _as_int((cops or {}).get("mock_whatsapp_sent")))
            schedules = _as_int((cops or {}).get("recovery_schedules"))

    # Gate 2D — Home teaser from canonical Decision Portfolio + domain summaries.
    portfolio_landscape: list[dict[str, Any]] = []
    domain_teasers: dict[str, Any] = {}
    if decisions_evidence == "none":
        slug = str(
            src.get("store_slug")
            or (src.get("merchant_home_experience_v1") or {}).get("store_slug")
            or ""
        ).strip()
        if slug:
            try:
                from services.cart_workspace.business_findings_enrichment_v1 import (  # noqa: PLC0415
                    count_fde_decisions_for_teaser_v1,
                )

                teaser_dec = count_fde_decisions_for_teaser_v1(slug, summary=src)
                decisions_count = int(teaser_dec.get("count") or 0)
                decisions_title = str(teaser_dec.get("top_title_ar") or "").strip()
                decisions_evidence = str(teaser_dec.get("evidence") or "none")
                raw_land = teaser_dec.get("category_landscape")
                if isinstance(raw_land, list):
                    portfolio_landscape = [x for x in raw_land if isinstance(x, dict)]
                raw_dom = teaser_dec.get("home_domain_teasers")
                if isinstance(raw_dom, Mapping):
                    domain_teasers = dict(raw_dom)
            except Exception:  # noqa: BLE001
                pass

    obs_count = 0
    obs_top: dict[str, str] | None = None
    # Prefer Business Facts (truth atoms). Themes are out of target architecture.
    try:
        from services.business_facts_v1.attach_v1 import (  # noqa: PLC0415
            home_observation_teaser_from_facts_v1,
        )

        bf_teaser = home_observation_teaser_from_facts_v1(src)
        if isinstance(bf_teaser, dict) and bf_teaser.get("top"):
            obs_count = int(bf_teaser.get("count") or 0)
            top_bf = (
                bf_teaser.get("top")
                if isinstance(bf_teaser.get("top"), Mapping)
                else {}
            )
            obs_top = {
                "product_name_ar": str(top_bf.get("product_name_ar") or "").strip(),
                "statement_ar": str(top_bf.get("statement_ar") or "").strip(),
                "fact_id": str(top_bf.get("fact_id") or "").strip(),
                "source": "business_facts_v1",
            }
    except Exception:  # noqa: BLE001
        pass
    if obs_top is None:
        orv = src.get("observation_reality_validation_v1")
        if isinstance(orv, Mapping):
            findings = [
                f for f in list(orv.get("findings") or []) if isinstance(f, Mapping)
            ]
            named = [
                f
                for f in findings
                if str(f.get("product_name_ar") or "").strip()
                and (
                    str(f.get("home_teaser_ar") or "").strip()
                    or str(f.get("statement_ar") or "").strip()
                )
            ]
            obs_count = len(named)
            if named:
                top_f = named[0]
                statement = str(
                    top_f.get("statement_ar") or top_f.get("home_teaser_ar") or ""
                ).strip()
                obs_top = {
                    "product_name_ar": str(top_f.get("product_name_ar") or "").strip(),
                    "statement_ar": statement,
                }

    needs_attention = waiting > 0 or no_phone > 0 or store_ok is False
    if domain_teasers.get("store_health_attention") is True:
        needs_attention = True
    return {
        "schema": "home_teaser_inputs_v1",
        "version": "gate_2d_business_domain_composition",
        "health": {
            "watching": waiting > 0 or active > 0,
            "abandoned_carts": waiting,
            "active_carts": active,
            "recovered_today": recovered,
            "no_phone": no_phone,
            "store_connected": store_ok,
            "wa_state_key": wa_state,
            "needs_attention": needs_attention,
            "domain_summary_ar": str(domain_teasers.get("store_health_ar") or "").strip(),
        },
        "decisions": {
            "count": decisions_count,
            "top_title_ar": decisions_title,
            "evidence": decisions_evidence,
            "category_landscape": portfolio_landscape,
            "portfolio": True,
            "gate_2d": True,
        },
        "observations": {
            "count": obs_count,
            "top": obs_top,
            "evidence": "product_findings" if obs_count and obs_top else "none",
        },
        "carts": {
            "count": waiting,
            "waiting": waiting,
            "active": active,
            "no_phone": no_phone,
            "domain_summary_ar": str(domain_teasers.get("carts_ar") or "").strip(),
        },
        "communication": {
            "sent": wa_sent,
            "schedules": schedules,
            "no_phone": no_phone,
            "waiting": waiting,
            "wa_state_key": wa_state,
            "activity": (wa_sent + schedules + waiting + no_phone) > 0,
            "domain_summary_ar": str(
                domain_teasers.get("communication_ar") or ""
            ).strip(),
        },
    }


def strip_heavy_home_summary_payload_v1(summary: dict[str, Any]) -> dict[str, Any]:
    """Remove page-owned heavy packages from the Home summary transport."""
    if not isinstance(summary, dict):
        return summary
    for key in HEAVY_SUMMARY_KEYS_V1:
        summary.pop(key, None)
    # Keep slim Facts + Themes stamps (teaser already extracted).
    bf = summary.get("business_facts_v1")
    if isinstance(bf, dict) and bf.get("ok"):
        routing = bf.get("routing") if isinstance(bf.get("routing"), dict) else {}
        summary["business_facts_v1"] = {
            "ok": True,
            "enabled": True,
            "schema": bf.get("schema") or "business_facts_v1",
            "store_slug": bf.get("store_slug"),
            "counts": bf.get("counts") or {"total": 0},
            "routing": {
                "home_teaser": (routing or {}).get("home_teaser"),
            },
            "slim_transport": True,
            "product_intelligence": False,
        }
    bt = summary.get("business_themes_v1")
    if isinstance(bt, dict) and bt.get("ok"):
        tr = bt.get("routing") if isinstance(bt.get("routing"), dict) else {}
        summary["business_themes_v1"] = {
            "ok": True,
            "enabled": True,
            "schema": bt.get("schema") or "business_themes_v1",
            "store_slug": bt.get("store_slug"),
            "counts": bt.get("counts") or {},
            "routing": {"home_teaser": (tr or {}).get("home_teaser")},
            "slim_transport": True,
            "constitution": bt.get("constitution"),
            "product_intelligence": False,
        }
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
