# -*- coding: utf-8 -*-
"""
Merchant visual deploy authorization — fail-closed compound gate.

Requires ALL of:
  VISUAL CONTRACTS = PASS
  SEMANTIC REGRESSION = PASS
  REAL-DEVICE REVIEW = PASS
  PRODUCTION CONFIG PARITY = PASS

If production config parity is not PASS → SAFE FOR EXACT-SHA DEPLOY = NO.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.merchant_ui_config_parity_v1 import (
    INVARIANT_ID,
    REGRESSION_GATE as CONFIG_PARITY_GATE,
    evaluate_config_parity,
)

DEPLOY_AUTH_GATE = "MERCHANT_VISUAL_DEPLOY_AUTHORIZATION_V1"

_PASS = "pass"
_FAIL = "fail"


def _norm_status(value: Any) -> str:
    s = str(value or "").strip().lower()
    if s in {_PASS, "ok", "true", "yes"}:
        return _PASS
    return _FAIL


def evaluate_merchant_visual_deploy_authorization(
    *,
    visual_contracts: Any,
    semantic_regression: Any,
    real_device_review: Any,
    production_config_parity: Any = None,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    """
    Compound authorization. production_config_parity may be supplied or
    derived live from evaluate_config_parity (current process env).
    """
    if production_config_parity is None:
        parity_eval = evaluate_config_parity(env=env)
        parity_status = parity_eval["status"]
        parity_detail = parity_eval
    else:
        parity_status = _norm_status(production_config_parity)
        parity_detail = {
            "status": parity_status,
            "gate": CONFIG_PARITY_GATE,
            "source": "caller_supplied",
        }

    axes = {
        "visual_contracts": _norm_status(visual_contracts),
        "semantic_regression": _norm_status(semantic_regression),
        "real_device_review": _norm_status(real_device_review),
        "production_config_parity": parity_status,
    }
    failed = [k for k, v in axes.items() if v != _PASS]
    safe = len(failed) == 0
    return {
        "ok": safe,
        "gate": DEPLOY_AUTH_GATE,
        "config_parity_gate": CONFIG_PARITY_GATE,
        "config_parity_invariant": INVARIANT_ID,
        "axes": axes,
        "failed_axes": failed,
        "safe_for_exact_sha_deploy": safe,
        "safe_for_exact_sha_deploy_label": "YES" if safe else "NO",
        "production_config_parity_detail": parity_detail,
        "rule": (
            "SAFE FOR EXACT-SHA DEPLOY requires visual_contracts, "
            "semantic_regression, real_device_review, and "
            "production_config_parity all PASS"
        ),
    }


__all__ = [
    "DEPLOY_AUTH_GATE",
    "evaluate_merchant_visual_deploy_authorization",
]
