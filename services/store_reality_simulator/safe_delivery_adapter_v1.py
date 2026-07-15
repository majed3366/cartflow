# -*- coding: utf-8 -*-
"""
Simulation-safe delivery adapter — Phase 2.

Intercepts outbound WhatsApp / provider / merchant notifications while a
simulation context is active. Multiple safety layers:

1. Simulation context must be active for adapter enforcement
2. store_slug must be demo — otherwise reject
3. Never call real Twilio / Meta / external delivery APIs
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import (
    DEMO_STORE_SLUG,
    PROVIDER_SUPPRESSED_SIMULATION,
)
from services.store_reality_simulator.context_v1 import (
    get_simulation_context,
    is_simulation_active,
)

log = logging.getLogger("cartflow.store_reality_simulator")


def _norm_slug(store_slug: Optional[str]) -> str:
    return str(store_slug or "").strip()


def simulation_outbound_guard(
    *,
    store_slug: Optional[str] = None,
    channel: str = "whatsapp",
    reason_tag: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    If simulation is active, return a response that callers must use instead
    of calling the real provider. Returns None when production path may proceed.
    """
    if not is_simulation_active():
        return None

    ctx = get_simulation_context()
    run_id = getattr(ctx, "simulation_run_id", "") if ctx else ""
    slug = _norm_slug(store_slug) or _norm_slug(getattr(ctx, "store_slug", None))

    if slug != DEMO_STORE_SLUG:
        log.warning(
            "[SRS SAFE DELIVERY] non_demo_rejected run=%s store=%s channel=%s",
            run_id,
            slug,
            channel,
        )
        return {
            "ok": False,
            "error": "simulation_non_demo_rejected",
            "simulation": True,
            PROVIDER_SUPPRESSED_SIMULATION: True,
            "simulation_run_id": run_id,
            "store_slug": slug,
            "channel": channel,
            "reason_tag": reason_tag,
            "wa_send_allowed": False,
        }

    log.info(
        "[SRS SAFE DELIVERY] mock_suppressed run=%s store=%s channel=%s tag=%s",
        run_id,
        slug,
        channel,
        reason_tag,
    )
    return {
        "ok": True,
        "mock": True,
        "sid": f"SIM_{(run_id or 'run')[:12]}",
        "status": "mock_sent",
        "simulation": True,
        PROVIDER_SUPPRESSED_SIMULATION: True,
        "simulation_run_id": run_id,
        "store_slug": DEMO_STORE_SLUG,
        "channel": channel,
        "reason_tag": reason_tag,
        "wa_send_allowed": False,
        "provider_called": False,
        "external_api_called": False,
    }


def guard_send_whatsapp(
    *,
    store_slug: Optional[str],
    reason_tag: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    return simulation_outbound_guard(
        store_slug=store_slug,
        channel="whatsapp_twilio",
        reason_tag=reason_tag,
    )


def guard_meta_whatsapp_message() -> Optional[tuple[bool, Optional[str], Any]]:
    """
    Gate for main.send_whatsapp_message (Meta CTA).
    Returns tuple compatible with that function, or None to proceed.
    """
    if not is_simulation_active():
        return None
    ctx = get_simulation_context()
    run_id = getattr(ctx, "simulation_run_id", "") if ctx else ""
    store_slug = _norm_slug(getattr(ctx, "store_slug", None)) or DEMO_STORE_SLUG
    if store_slug != DEMO_STORE_SLUG:
        return False, "simulation_non_demo_rejected", None
    # Mock success without external call
    return True, None, f"SIM_META_{(run_id or 'run')[:12]}"


def assert_no_outbound_in_simulation() -> None:
    """Test helper — raise if simulation inactive (adapter not engaged)."""
    if not is_simulation_active():
        raise AssertionError("expected_active_simulation_for_outbound_guard")
