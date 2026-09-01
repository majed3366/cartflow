# -*- coding: utf-8 -*-
"""
Merchant UI Production Config Parity — MERCHANT-UI-INV-CONFIG-01.

Governance only: compare EFFECTIVE material Merchant UI flag behavior
between review runtime and production-effective contract.

Raw env spelling is not sufficient. Secrets are never included.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional

MERCHANT_UI_CONFIG_VERSION = "merchant-ui-config-parity-v1"
INVARIANT_ID = "MERCHANT-UI-INV-CONFIG-01"
REGRESSION_GATE = "MERCHANT_UI_PRODUCTION_CONFIG_PARITY_REGRESSION_GATE"

FLAG_CART_WORKSPACE_V1 = "CARTFLOW_CART_WORKSPACE_V1"
FLAG_MERCHANT_UI_V2 = "CARTFLOW_MERCHANT_UI_V2"
FLAG_CARTS_V2_UI = "CARTFLOW_CARTS_V2_UI"

# Production-effective contract (parity proof 2026-09-01 on smartreplyai.net).
# Effective Workspace ON proven via projection 401≠feature_flag_off.
# Merchant UI V2 and Carts V2 UI default ON when env unset.
PRODUCTION_MERCHANT_UI_CONFIG: dict[str, bool] = {
    FLAG_CART_WORKSPACE_V1: True,
    FLAG_MERCHANT_UI_V2: True,
    FLAG_CARTS_V2_UI: True,
}


def _env_map(env: Optional[Mapping[str, str]] = None) -> Mapping[str, str]:
    if env is not None:
        return env
    return os.environ


def _raw(env: Mapping[str, str], name: str) -> Optional[str]:
    v = (env.get(name) or "").strip()
    return v or None


def _truthy_tri(raw: Optional[str]) -> Optional[bool]:
    if raw is None:
        return None
    v = raw.strip().lower()
    if not v:
        return None
    if v in {"1", "true", "yes", "on", "v2"}:
        return True
    if v in {"0", "false", "no", "off", "v1"}:
        return False
    return None


def _effective_workspace(env: Mapping[str, str]) -> Optional[bool]:
    """
    Mirror services.cart_workspace.feature_flag_v1.cart_workspace_v1_enabled.

    Explicit true/false win. Unset + Railway deploy SHA → ON. Unset elsewhere → OFF.
    """
    decided = _truthy_tri(_raw(env, FLAG_CART_WORKSPACE_V1))
    if decided is not None:
        return decided
    if (env.get("RAILWAY_GIT_COMMIT_SHA") or "").strip():
        return True
    return False


def _effective_merchant_ui_v2(env: Mapping[str, str]) -> Optional[bool]:
    """Env-level V2 gate (default ON). Query/cookie selectors are request-scoped."""
    decided = _truthy_tri(_raw(env, FLAG_MERCHANT_UI_V2))
    if decided is not None:
        return decided
    return True


def _effective_carts_v2_ui(env: Mapping[str, str]) -> Optional[bool]:
    """Default ON — empty/unset → True; explicit falsey → False."""
    raw = _raw(env, FLAG_CARTS_V2_UI)
    if raw is None:
        return True
    decided = _truthy_tri(raw)
    if decided is None:
        # Non-empty unrecognized token → cannot resolve safely.
        return None
    return decided


@dataclass(frozen=True)
class MaterialFlagSpec:
    name: str
    default: bool
    affects: tuple[str, ...]
    normalize: Callable[[Mapping[str, str]], Optional[bool]]
    source_of_truth: str


MATERIAL_FLAG_REGISTRY: tuple[MaterialFlagSpec, ...] = (
    MaterialFlagSpec(
        name=FLAG_CART_WORKSPACE_V1,
        default=False,
        affects=(
            "page_availability",
            "data_projection_path",
            "composition_path",
            "canonical_route_behavior",
        ),
        normalize=_effective_workspace,
        source_of_truth="services.cart_workspace.feature_flag_v1.cart_workspace_v1_enabled",
    ),
    MaterialFlagSpec(
        name=FLAG_MERCHANT_UI_V2,
        default=True,
        affects=(
            "renderer_family",
            "composition_path",
            "visual_state_path",
            "mobile_behavior",
            "canonical_route_behavior",
        ),
        normalize=_effective_merchant_ui_v2,
        source_of_truth="services.merchant_ui_v2.flag_v1.merchant_ui_v2_env_enabled",
    ),
    MaterialFlagSpec(
        name=FLAG_CARTS_V2_UI,
        default=True,
        affects=("composition_path", "visual_state_path", "page_availability"),
        normalize=_effective_carts_v2_ui,
        source_of_truth="services.cart_page_v2_ui_flag_v1.carts_v2_ui_enabled",
    ),
)


def material_flag_names() -> tuple[str, ...]:
    return tuple(spec.name for spec in MATERIAL_FLAG_REGISTRY)


def describe_material_flags() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in MATERIAL_FLAG_REGISTRY:
        out.append(
            {
                "flag": spec.name,
                "default": spec.default,
                "affects": list(spec.affects),
                "source_of_truth": spec.source_of_truth,
            }
        )
    return out


def resolve_material_flag(
    name: str,
    *,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    env_m = _env_map(env)
    spec = next((s for s in MATERIAL_FLAG_REGISTRY if s.name == name), None)
    if spec is None:
        return {
            "flag": name,
            "raw": _raw(env_m, name),
            "default": None,
            "effective": None,
            "resolved": False,
            "error": "unknown_material_flag",
            "source_of_truth": None,
        }
    effective = spec.normalize(env_m)
    return {
        "flag": spec.name,
        "raw": _raw(env_m, spec.name),
        "default": spec.default,
        "normalization_rule": spec.source_of_truth,
        "effective": effective,
        "resolved": effective is not None,
        "source_of_truth": spec.source_of_truth,
        "affects": list(spec.affects),
    }


def build_merchant_ui_config_identity(
    *,
    env: Optional[Mapping[str, str]] = None,
    role: str = "review",
) -> dict[str, Any]:
    """Deterministic identity: material flags → effective bools only."""
    env_m = _env_map(env)
    material: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for spec in MATERIAL_FLAG_REGISTRY:
        row = resolve_material_flag(spec.name, env=env_m)
        details.append(row)
        material[spec.name] = row["effective"]
        if not row["resolved"]:
            unresolved.append(spec.name)
    return {
        "merchant_ui_config_version": MERCHANT_UI_CONFIG_VERSION,
        "invariant": INVARIANT_ID,
        "role": role,
        "material_flags": material,
        "flag_details": details,
        "unresolved": unresolved,
        "resolved": len(unresolved) == 0,
    }


def production_merchant_ui_config_identity() -> dict[str, Any]:
    """Inspectable production-effective contract (no secrets)."""
    return {
        "merchant_ui_config_version": MERCHANT_UI_CONFIG_VERSION,
        "invariant": INVARIANT_ID,
        "role": "production",
        "material_flags": dict(PRODUCTION_MERCHANT_UI_CONFIG),
        "unresolved": [],
        "resolved": True,
        "source": "production_effective_contract_v1",
    }


def review_merchant_ui_config_identity(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    return build_merchant_ui_config_identity(env=env, role="review")


def compare_merchant_ui_config_parity(
    *,
    review: Optional[Mapping[str, Any]] = None,
    production: Optional[Mapping[str, Any]] = None,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """
    Fail-closed parity: REVIEW effective == PRODUCTION effective for every
    material flag. Unresolved effective values fail closed.
    """
    prod = dict(production) if production is not None else dict(PRODUCTION_MERCHANT_UI_CONFIG)
    if review is not None:
        rev_flags = dict(review)
        unresolved = [k for k, v in rev_flags.items() if v is None]
        review_identity = {
            "merchant_ui_config_version": MERCHANT_UI_CONFIG_VERSION,
            "role": "review",
            "material_flags": rev_flags,
            "unresolved": unresolved,
            "resolved": len(unresolved) == 0,
        }
    else:
        review_identity = review_merchant_ui_config_identity(env=env)
        rev_flags = dict(review_identity["material_flags"])
        unresolved = list(review_identity.get("unresolved") or [])

    prod_identity = (
        production_merchant_ui_config_identity()
        if production is None
        else {
            "merchant_ui_config_version": MERCHANT_UI_CONFIG_VERSION,
            "role": "production",
            "material_flags": prod,
            "unresolved": [],
            "resolved": True,
        }
    )

    mismatches: list[dict[str, Any]] = []
    for name in material_flag_names():
        p = prod.get(name)
        r = rev_flags.get(name)
        if r is None or name in unresolved:
            mismatches.append(
                {
                    "flag": name,
                    "reason": "unresolved_effective_value",
                    "production_effective": p,
                    "review_effective": r,
                }
            )
            continue
        if p != r:
            mismatches.append(
                {
                    "flag": name,
                    "reason": "effective_mismatch",
                    "production_effective": p,
                    "review_effective": r,
                }
            )

    # Extra review keys that are material but missing from production contract.
    for name, r in rev_flags.items():
        if name not in prod and name not in {m["flag"] for m in mismatches}:
            mismatches.append(
                {
                    "flag": name,
                    "reason": "missing_from_production_contract",
                    "production_effective": None,
                    "review_effective": r,
                }
            )

    status = "pass" if not mismatches else "fail"
    return {
        "ok": status == "pass",
        "status": status,
        "gate": REGRESSION_GATE,
        "invariant": INVARIANT_ID,
        "merchant_ui_config_version": MERCHANT_UI_CONFIG_VERSION,
        "production": prod_identity,
        "review": review_identity,
        "mismatches": mismatches,
        "review_equals_production": status == "pass",
    }


def evaluate_config_parity(
    *,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    return compare_merchant_ui_config_parity(env=env)


def attach_config_parity_to_identity(
    identity: MutableMapping[str, Any],
    *,
    env: Optional[Mapping[str, str]] = None,
) -> MutableMapping[str, Any]:
    """Attach non-secret config identity + live parity verdict to runtime identity."""
    parity = evaluate_config_parity(env=env)
    identity["merchant_ui_config_version"] = MERCHANT_UI_CONFIG_VERSION
    identity["merchant_ui_config_invariant"] = INVARIANT_ID
    identity["merchant_ui_config_parity_gate"] = REGRESSION_GATE
    identity["merchant_ui_material_flags"] = dict(
        parity["review"]["material_flags"]
    )
    identity["merchant_ui_production_material_flags"] = dict(
        parity["production"]["material_flags"]
    )
    identity["merchant_ui_config_parity"] = parity["status"]
    identity["merchant_ui_config_parity_ok"] = bool(parity["ok"])
    return identity


__all__ = [
    "FLAG_CARTS_V2_UI",
    "FLAG_CART_WORKSPACE_V1",
    "FLAG_MERCHANT_UI_V2",
    "INVARIANT_ID",
    "MATERIAL_FLAG_REGISTRY",
    "MERCHANT_UI_CONFIG_VERSION",
    "PRODUCTION_MERCHANT_UI_CONFIG",
    "REGRESSION_GATE",
    "attach_config_parity_to_identity",
    "build_merchant_ui_config_identity",
    "compare_merchant_ui_config_parity",
    "describe_material_flags",
    "evaluate_config_parity",
    "material_flag_names",
    "production_merchant_ui_config_identity",
    "resolve_material_flag",
    "review_merchant_ui_config_identity",
]
