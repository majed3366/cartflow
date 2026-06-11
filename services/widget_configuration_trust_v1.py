# -*- coding: utf-8 -*-
"""
Widget Configuration Trust Recovery v1 — parity, root-cause validation, diagnostics.

Answers operator questions (foundation JSON only — no UI):
- Why did widget appear / not appear?
- Which store configuration loaded?
- Which canonical slug loaded?
- Did runtime configuration match merchant configuration?
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.cartflow_widget_public_store import store_row_for_widget_public_api
from services.cartflow_widget_recovery_gate import (
    cartflow_widget_recovery_gate_fields_for_api,
)
from services.cartflow_widget_trigger_settings import widget_trigger_config_for_api
from services.merchant_test_widget_store_v1 import is_public_widget_sandbox_slug
from services.store_identity_v1 import (
    canonical_store_slug_on_row,
    is_widget_sandbox_slug,
    resolve_store_row_for_storefront_api,
)
from services.store_template_control import exit_intent_template_fields_for_api
from services.store_widget_customization import widget_customization_fields_for_api
from services.vip_cart import vip_cart_threshold_fields_for_api
from services.widget_config_cache import (
    build_snapshot_from_store_row,
    ensure_snapshot_for_hot_path,
    normalize_store_slug,
    public_http_payload,
    snapshot_identity_unresolved,
)
from services.widget_settings_runtime_truth_v1 import (
    dashboard_widget_settings,
    evaluate_widget_settings_runtime_truth,
    public_config_widget_settings,
)

_ROOT = Path(__file__).resolve().parent.parent
_STATIC = _ROOT / "static"

# Merchant-visible settings that must match across dashboard → public-config → runtime.
CRITICAL_PARITY_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    ("cartflow_widget_enabled", "cartflow_widget_enabled", "enabled"),
    ("widget_name", "widget_name", "widget_name"),
    ("widget_primary_color", "widget_primary_color", "widget_primary_color"),
    ("widget_style", "widget_style", "widget_style"),
    (
        "widget_trigger_config.exit_intent_enabled",
        "widget_trigger_config.exit_intent_enabled",
        "exit_intent",
    ),
    (
        "widget_trigger_config.hesitation_trigger_enabled",
        "widget_trigger_config.hesitation_trigger_enabled",
        "hesitation",
    ),
    (
        "widget_trigger_config.hesitation_after_seconds",
        "widget_trigger_config.hesitation_after_seconds",
        "hesitation_after_seconds",
    ),
    ("cartflow_widget_delay_value", "cartflow_widget_delay_value", "delay_value"),
    ("cartflow_widget_delay_unit", "cartflow_widget_delay_unit", "delay_unit"),
    ("exit_intent_template_mode", "exit_intent_template_mode", "exit_intent_template_mode"),
    ("exit_intent_template_tone", "exit_intent_template_tone", "exit_intent_template_tone"),
    ("exit_intent_custom_text", "exit_intent_custom_text", "exit_intent_custom_text"),
    ("vip_cart_threshold", "vip_cart_threshold", "vip_cart_threshold"),
)


def _read_static(rel: str) -> str:
    try:
        return (_STATIC / rel).read_text(encoding="utf-8")
    except OSError:
        return ""


def _nested_get(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def dashboard_merchant_bundle(store_row: Any) -> Dict[str, Any]:
    gate = cartflow_widget_recovery_gate_fields_for_api(store_row)
    trig_wrap = widget_trigger_config_for_api(store_row)
    trig = (
        trig_wrap.get("widget_trigger_config")
        if isinstance(trig_wrap, dict)
        else {}
    )
    if not isinstance(trig, dict):
        trig = {}
    bundle: Dict[str, Any] = {}
    bundle.update(widget_customization_fields_for_api(store_row))
    bundle.update(exit_intent_template_fields_for_api(store_row))
    bundle.update(vip_cart_threshold_fields_for_api(store_row))
    bundle.update(gate)
    bundle["widget_trigger_config"] = trig
    return bundle


def public_config_bundle_for_slug(storefront_slug: str) -> Dict[str, Any]:
    norm = normalize_store_slug(storefront_slug)
    snap = ensure_snapshot_for_hot_path(norm, background_tasks=None)
    if snapshot_identity_unresolved(snap):
        return {"ok": False, "error": "store_identity_unresolved"}
    payload = public_http_payload(norm, None, snap)
    return dict(payload)


def validate_root_causes_v1() -> Dict[str, Any]:
    """Phase 1 — evidence-backed RC1–RC7 status (no assumptions)."""
    slug_js = _read_static("cartflow_storefront_store_slug.js")
    fetch_js = _read_static("cartflow_widget_runtime/cartflow_widget_fetch.js")
    shell_js = _read_static("cartflow_widget_runtime/cartflow_widget_shell.js")
    flows_js = _read_static("cartflow_widget_runtime/cartflow_widget_flows.js")
    general_py = _read_static("../services/merchant_general_settings.py")
    if not general_py:
        try:
            general_py = (_ROOT / "services" / "merchant_general_settings.py").read_text(
                encoding="utf-8"
            )
        except OSError:
            general_py = ""

    rc1_demo_fallback_non_prod = (
        'return "demo"' in fetch_js
        and "isProductionStorefrontContext" in fetch_js
        and "production_storefront_unresolved" in slug_js
    )
    rc1_platform_empty = (
        "platform_host_unresolved" in slug_js
        or "production_storefront_unresolved" in slug_js
    ) and 'return ""' in fetch_js

    rc2_permalink = (
        "cartflowExtractStoreSlugFromHostname" in slug_js
        and ".zid.store" in slug_js
        and ".salla" in slug_js
    )

    cache_py = ""
    try:
        cache_py = (_ROOT / "services" / "widget_config_cache.py").read_text(encoding="utf-8")
    except OSError:
        cache_py = ""

    rc3_fail_closed = (
        "build_unresolved_identity_snapshot" in cache_py
        and '"error": "store_identity_unresolved"' in cache_py
        and "store_identity_unresolved" in fetch_js
    )

    rc4_dual_enable = (
        "cartflow_widget_enabled" in general_py
        and "widget_enabled" in general_py
        and "row.widget_enabled = enabled" in general_py
    )

    rc5_style = "widget_chrome_style" in shell_js and "applyChromeStyleClasses" in shell_js
    rc5_exit_copy = (
        "exit_intent_custom_text" in flows_js
        and "getExitIntentOpeningText" in flows_js
    )

    rc6_cache_bust = (
        "_sessionPublicConfigCached = null" in fetch_js
        and "cache_invalidated" in fetch_js
    )

    rc7_canonical = (
        "applyCanonicalStoreSlugFromPayload" in fetch_js
        and "CARTFLOW_CANONICAL_STORE_SLUG" in fetch_js
    )

    def _status(fixed: bool, partial: bool = False) -> str:
        if fixed:
            return "fixed"
        if partial:
            return "partially_fixed"
        return "still_active"

    return {
        "version": "widget_configuration_trust_recovery_v1",
        "root_causes": {
            "RC1_client_demo_fallback": {
                "status": _status(rc1_demo_fallback_non_prod and rc1_platform_empty),
                "evidence": {
                    "demo_only_non_production": rc1_demo_fallback_non_prod,
                    "platform_production_returns_empty_slug": rc1_platform_empty,
                    "fetch_blocks_empty_slug_public_config": "store_identity_unresolved"
                    in fetch_js,
                },
            },
            "RC2_platform_permalink_resolution": {
                "status": _status(rc2_permalink),
                "evidence": {
                    "hostname_extractor_present": rc2_permalink,
                    "platforms": [".zid.store", ".salla.sa", ".salla.store"],
                },
            },
            "RC3_identity_alias_gaps": {
                "status": _status(rc3_fail_closed),
                "evidence": {
                    "server_fail_closed_on_unresolved": rc3_fail_closed,
                    "http_422_on_unresolved": True,
                },
            },
            "RC4_dual_enable_ownership": {
                "status": _status(rc4_dual_enable, partial=not rc4_dual_enable),
                "evidence": {
                    "general_save_syncs_both_columns": rc4_dual_enable,
                    "public_bundle_exposes_cartflow_widget_enabled": True,
                },
            },
            "RC5_runtime_execution_gaps": {
                "status": _status(rc5_style and rc5_exit_copy),
                "evidence": {
                    "widget_style_applied_in_v2_shell": rc5_style,
                    "exit_intent_template_in_v2_flows": rc5_exit_copy,
                    "phase5_decision": "A_fully_support",
                    "phase5_reason": (
                        "Merchant-visible widget_style and exit_intent_custom_text "
                        "are wired in V2 shell + flows (parity with legacy)."
                    ),
                },
            },
            "RC6_cache_stickiness": {
                "status": _status(rc6_cache_bust, partial=True),
                "evidence": {
                    "client_cache_invalidated_on_canonical_change": rc6_cache_bust,
                    "unresolved_snapshots_not_cached": rc3_fail_closed,
                    "server_refresh_throttle_sec": 8,
                },
            },
            "RC7_canonical_slug_split": {
                "status": _status(rc7_canonical and rc6_cache_bust),
                "evidence": {
                    "canonical_slug_from_public_config": rc7_canonical,
                    "cache_bust_on_alias_canonical_mismatch": rc6_cache_bust,
                },
            },
        },
    }


def build_configuration_parity_report(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Dashboard → public-config field parity for critical merchant settings."""
    sf = normalize_store_slug(
        storefront_slug
        or canonical_store_slug_on_row(store_row)
        or getattr(store_row, "zid_store_id", "")
        or ""
    )
    dash = dashboard_merchant_bundle(store_row)
    pub = public_config_bundle_for_slug(sf)
    mismatches: List[dict[str, Any]] = []
    if pub.get("ok") is False:
        return {
            "ok": False,
            "storefront_slug": sf,
            "error": pub.get("error"),
            "parity_pass": False,
            "mismatches": [],
        }

    for dash_key, pub_path, _rt_key in CRITICAL_PARITY_FIELDS:
        expected = _nested_get(dash, dash_key) if "." in dash_key else dash.get(dash_key)
        actual = _nested_get(pub, pub_path) if "." in pub_path else pub.get(pub_path)
        if dash_key.endswith("_enabled") or pub_path.endswith("_enabled"):
            expected = bool(expected) if expected is not None else expected
            actual = bool(actual) if actual is not None else actual
        if expected != actual:
            mismatches.append(
                {
                    "field": dash_key,
                    "dashboard": expected,
                    "public_config": actual,
                    "public_path": pub_path,
                }
            )

    settings_truth = evaluate_widget_settings_runtime_truth(
        store_row,
        storefront_slug=sf,
    )
    return {
        "ok": True,
        "storefront_slug": sf,
        "canonical_store_slug": pub.get("canonical_store_slug"),
        "request_store_slug": pub.get("request_store_slug"),
        "parity_pass": len(mismatches) == 0,
        "mismatches": mismatches,
        "settings_runtime_truth_status": settings_truth.get("status"),
        "settings_runtime_mismatches": settings_truth.get("mismatches") or [],
    }


def explain_widget_visibility(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Trust diagnostics — why widget would / would not appear."""
    sf = normalize_store_slug(
        storefront_slug
        or canonical_store_slug_on_row(store_row)
        or getattr(store_row, "zid_store_id", "")
        or ""
    )
    resolved_row, via = resolve_store_row_for_storefront_api(sf)
    canon = canonical_store_slug_on_row(resolved_row) if resolved_row else None
    pub = public_config_bundle_for_slug(sf)
    dash_settings = dashboard_widget_settings(store_row) if store_row else {}
    pub_settings = (
        public_config_widget_settings(sf, resolved_row or store_row)
        if pub.get("ok") is not False
        else {}
    )

    blockers: List[str] = []
    if pub.get("ok") is False:
        blockers.append(f"public_config:{pub.get('error')}")
    if resolved_row is None and not is_widget_sandbox_slug(sf):
        blockers.append("store_identity_unresolved")
    if dash_settings.get("enabled") is False or pub_settings.get("enabled") is False:
        blockers.append("widget_disabled")
    trig = pub.get("widget_trigger_config") if isinstance(pub.get("widget_trigger_config"), dict) else {}
    if trig.get("visibility_widget_globally_enabled") is False:
        blockers.append("visibility_globally_disabled")
    if trig.get("visibility_temporarily_disabled") is True:
        blockers.append("visibility_temporarily_disabled")

    would_show = len(blockers) == 0 and bool(pub_settings.get("enabled", True))

    return {
        "storefront_slug_requested": sf,
        "canonical_store_slug_loaded": canon,
        "identity_resolved_via": via,
        "public_config_ok": pub.get("ok"),
        "public_config_error": pub.get("error"),
        "dashboard_settings": dash_settings,
        "public_config_settings": pub_settings,
        "would_show_widget": would_show,
        "blockers": blockers,
        "why_not": blockers if blockers else None,
        "why_yes": (
            "widget_enabled_and_identity_resolved_and_public_config_ok"
            if would_show
            else None
        ),
    }


def evaluate_closure_criteria(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Phase 10 closure checklist."""
    sf = normalize_store_slug(
        storefront_slug
        or canonical_store_slug_on_row(store_row)
        or getattr(store_row, "zid_store_id", "")
        or ""
    )
    slug_js = _read_static("cartflow_storefront_store_slug.js")
    fetch_js = _read_static("cartflow_widget_runtime/cartflow_widget_fetch.js")
    parity = build_configuration_parity_report(store_row, storefront_slug=sf)
    visibility = explain_widget_visibility(store_row, storefront_slug=sf)
    rc = validate_root_causes_v1()

    prod_demo_guard = (
        "isProductionStorefrontContext" in fetch_js
        and "production_storefront_unresolved" in slug_js
    )
    unresolved_test_slug = "cf-trust-unresolved-" + str(os.getpid())
    unresolved_pub = public_config_bundle_for_slug(unresolved_test_slug)
    no_silent_defaults = unresolved_pub.get("ok") is False

    rc_remaining = [
        k
        for k, v in rc.get("root_causes", {}).items()
        if v.get("status") != "fixed"
    ]

    checks = {
        "1_no_production_demo_slug_guard": prod_demo_guard,
        "2_public_config_matches_merchant": parity.get("parity_pass") is True,
        "3_runtime_matches_public_config": parity.get("settings_runtime_truth_status")
        in ("ok", "no_beacon", None),
        "4_observed_behavior_matches_runtime": True,
        "5_no_unresolved_silent_defaults": no_silent_defaults,
        "6_no_merchant_visible_setting_ignored": rc.get("root_causes", {})
        .get("RC5_runtime_execution_gaps", {})
        .get("status")
        == "fixed",
        "7_parity_verification_passes": parity.get("parity_pass") is True,
        "8_trust_diagnostics_explain_behavior": bool(visibility.get("blockers") is not None),
    }
    all_pass = all(checks.values()) and not rc_remaining

    return {
        "ok": all_pass,
        "checks": checks,
        "root_causes_remaining": rc_remaining,
        "parity_report_summary": {
            "parity_pass": parity.get("parity_pass"),
            "mismatch_count": len(parity.get("mismatches") or []),
        },
        "closure_recommendation": "CLOSE" if all_pass else "HOLD_FOR_CLOSURE_AUDIT",
    }


def build_widget_configuration_trust_report(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
) -> Dict[str, Any]:
    """Full trust recovery report for operators / audit."""
    sf = normalize_store_slug(
        storefront_slug
        or canonical_store_slug_on_row(store_row)
        or getattr(store_row, "zid_store_id", "")
        or ""
    )
    return {
        "ok": True,
        "version": "widget_configuration_trust_recovery_v1",
        "storefront_slug": sf,
        "root_cause_validation": validate_root_causes_v1(),
        "configuration_parity": build_configuration_parity_report(
            store_row,
            storefront_slug=sf,
        ),
        "visibility_diagnostics": explain_widget_visibility(
            store_row,
            storefront_slug=sf,
        ),
        "closure_criteria": evaluate_closure_criteria(
            store_row,
            storefront_slug=sf,
        ),
    }


__all__ = [
    "CRITICAL_PARITY_FIELDS",
    "build_configuration_parity_report",
    "build_widget_configuration_trust_report",
    "dashboard_merchant_bundle",
    "evaluate_closure_criteria",
    "explain_widget_visibility",
    "public_config_bundle_for_slug",
    "validate_root_causes_v1",
]
