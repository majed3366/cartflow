# -*- coding: utf-8 -*-
"""End-to-end store identity + widget public-config truth report."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from extensions import db
from models import StoreIdentityAlias
from services.cartflow_widget_public_store import store_row_for_widget_public_api
from services.store_identity_v1 import (
    canonical_store_slug_on_row,
    ensure_zid_permalink_alias_for_dashboard_store,
    fetch_zid_identity_sources_for_store,
    list_public_cache_keys_for_store_row,
    normalize_identity_value,
    resolve_store_row_by_identifier,
    resolve_store_row_for_storefront_api,
    _permalink_values_from_zid_sources,
)
from services.cartflow_widget_recovery_gate import (
    cartflow_widget_recovery_gate_fields_for_api,
)
from services.store_widget_customization import widget_customization_fields_for_api
from services.cartflow_widget_trigger_settings import widget_trigger_config_for_api
from services.widget_config_cache import (
    build_snapshot_from_store_row,
    get_snapshot,
    normalize_store_slug,
)


def _alias_rows_for_store(store_id: int) -> List[dict[str, Any]]:
    out: List[dict[str, Any]] = []
    try:
        rows = (
            db.session.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.store_id == int(store_id))
            .all()
        )
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return out
    for row in rows:
        out.append(
            {
                "alias_kind": getattr(row, "alias_kind", None),
                "alias_value": getattr(row, "alias_value", None),
                "platform": getattr(row, "platform", None),
            }
        )
    return out


def _public_config_fields_for_slug(slug: str, row: Any) -> dict[str, Any]:
    norm = normalize_store_slug(slug)
    snap = get_snapshot(norm) if norm else None
    if snap is None and row is not None:
        snap = build_snapshot_from_store_row(row)
    elif snap is None:
        snap = build_snapshot_from_store_row(None)
    tpl = snap.get("template_bundle") if isinstance(snap, dict) else {}
    if not isinstance(tpl, dict):
        tpl = {}
    trig_cfg = tpl.get("widget_trigger_config")
    if not isinstance(trig_cfg, dict):
        trig_cfg = {}
    return {
        "public_config_widget_name": tpl.get("widget_name"),
        "public_config_color": tpl.get("widget_primary_color"),
        "public_config_widget_enabled": tpl.get("cartflow_widget_enabled"),
        "public_config_exit_intent_enabled": trig_cfg.get("exit_intent_enabled"),
        "public_config_hesitation_enabled": trig_cfg.get("hesitation_trigger_enabled"),
    }


def build_store_identity_runtime_truth_report(
    *,
    storefront_slug: str,
    dashboard_store_row: Any = None,
) -> Dict[str, Any]:
    """
    Compare dashboard Store row vs storefront slug resolution + public-config payload.
    """
    sf = normalize_identity_value(storefront_slug)
    dash_id = getattr(dashboard_store_row, "id", None) if dashboard_store_row is not None else None
    dash_slug = canonical_store_slug_on_row(dashboard_store_row)

    link_attempted = False
    if dashboard_store_row is not None and sf:
        existing, _ev = resolve_store_row_by_identifier(sf)
        if existing is None:
            link_attempted = True
            ensure_zid_permalink_alias_for_dashboard_store(dashboard_store_row, sf)

    resolved_row, resolved_via = resolve_store_row_for_storefront_api(sf)
    resolved_id = getattr(resolved_row, "id", None) if resolved_row is not None else None

    zid_diag: dict[str, Any] = {}
    if dashboard_store_row is not None:
        token = (getattr(dashboard_store_row, "access_token", None) or "").strip()
        profile, manager_store, store_url = fetch_zid_identity_sources_for_store(
            dashboard_store_row
        )
        zid_diag = {
            "access_token_present": bool(token),
            "profile_fetched": isinstance(profile, dict),
            "manager_store_fetched": isinstance(manager_store, dict),
            "manager_store_url": store_url,
            "permalink_values_from_zid_api": sorted(
                _permalink_values_from_zid_sources(
                    profile=profile,
                    manager_store=manager_store,
                    store_url=store_url,
                )
            ),
            "dashboard_link_attempted": link_attempted,
        }

    alias_match = (
        dash_id is not None
        and resolved_id is not None
        and int(dash_id) == int(resolved_id)
    )

    storefront_pub = _public_config_fields_for_slug(
        sf,
        store_row_for_widget_public_api(sf) if sf else None,
    )
    dash_custom = (
        widget_customization_fields_for_api(dashboard_store_row)
        if dashboard_store_row is not None
        else {}
    )
    dash_gate = (
        cartflow_widget_recovery_gate_fields_for_api(dashboard_store_row)
        if dashboard_store_row is not None
        else {}
    )
    dash_trig = (
        widget_trigger_config_for_api(dashboard_store_row)
        if dashboard_store_row is not None
        else {}
    )
    dash_trig_cfg = (
        dash_trig.get("widget_trigger_config")
        if isinstance(dash_trig, dict)
        else {}
    )

    name_match = (
        dashboard_store_row is not None
        and storefront_pub.get("public_config_widget_name")
        == dash_custom.get("widget_name")
    )
    color_match = (
        dashboard_store_row is not None
        and str(storefront_pub.get("public_config_color") or "").casefold()
        == str(dash_custom.get("widget_primary_color") or "").casefold()
    )
    enabled_match = (
        dashboard_store_row is not None
        and storefront_pub.get("public_config_widget_enabled")
        == dash_gate.get("cartflow_widget_enabled")
    )
    exit_match = (
        dashboard_store_row is not None
        and storefront_pub.get("public_config_exit_intent_enabled")
        == dash_trig_cfg.get("exit_intent_enabled")
    )
    hesitation_match = (
        dashboard_store_row is not None
        and storefront_pub.get("public_config_hesitation_enabled")
        == dash_trig_cfg.get("hesitation_trigger_enabled")
    )

    cache_keys = (
        list_public_cache_keys_for_store_row(dashboard_store_row)
        if dashboard_store_row is not None
        else []
    )
    cache_hits = {
        k: get_snapshot(normalize_store_slug(k)) is not None for k in cache_keys[:24]
    }

    checks = {
        "storefront_resolved": resolved_row is not None,
        "alias_match": alias_match,
        "widget_name_match": name_match,
        "widget_color_match": color_match,
        "widget_enabled_match": enabled_match,
        "exit_intent_match": exit_match,
        "hesitation_match": hesitation_match,
    }
    passed = all(checks.values()) if dashboard_store_row is not None else checks["storefront_resolved"]

    return {
        "ok": True,
        "passed": passed,
        "checks": checks,
        "dashboard_store_id": dash_id,
        "dashboard_slug": dash_slug,
        "storefront_slug": sf or None,
        "resolved_store_id": resolved_id,
        "resolved_via": resolved_via,
        "alias_match": alias_match,
        "aliases": _alias_rows_for_store(int(resolved_id)) if resolved_id else [],
        "dashboard_widget_name": dash_custom.get("widget_name"),
        "dashboard_widget_color": dash_custom.get("widget_primary_color"),
        "dashboard_widget_enabled": dash_gate.get("cartflow_widget_enabled"),
        "public_config_widget_name": storefront_pub.get("public_config_widget_name"),
        "public_config_color": storefront_pub.get("public_config_color"),
        "public_config_widget_enabled": storefront_pub.get("public_config_widget_enabled"),
        "public_config_exit_intent_enabled": storefront_pub.get(
            "public_config_exit_intent_enabled"
        ),
        "public_config_hesitation_enabled": storefront_pub.get(
            "public_config_hesitation_enabled"
        ),
        "cache_keys": cache_keys,
        "cache_hits": cache_hits,
        "zid_identity": zid_diag,
    }


__all__ = ["build_store_identity_runtime_truth_report"]
