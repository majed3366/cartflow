# -*- coding: utf-8 -*-
"""Deterministic simulation identity generator — Phase 2 (no event execution)."""
from __future__ import annotations

import hashlib
from typing import Any

from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG
from services.store_reality_simulator.seed_v1 import derive_subseed, normalize_seed


def _short_hash(*parts: Any, n: int = 12) -> str:
    material = "|".join(str(p) for p in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:n]


def simulation_customer_id(
    *,
    simulation_run_id: str,
    seed: int,
    scenario_id: str,
    customer_index: int,
) -> str:
    h = _short_hash(
        "customer",
        simulation_run_id,
        normalize_seed(seed),
        scenario_id,
        int(customer_index),
    )
    return f"srs_cust_{h}"


def simulation_session_id(
    *,
    simulation_run_id: str,
    seed: int,
    scenario_id: str,
    customer_index: int,
    session_index: int,
) -> str:
    h = _short_hash(
        "session",
        simulation_run_id,
        normalize_seed(seed),
        scenario_id,
        int(customer_index),
        int(session_index),
    )
    return f"srs_sess_{h}"


def simulation_cart_id(
    *,
    simulation_run_id: str,
    seed: int,
    scenario_id: str,
    customer_index: int,
    cart_index: int,
) -> str:
    h = _short_hash(
        "cart",
        simulation_run_id,
        normalize_seed(seed),
        scenario_id,
        int(customer_index),
        int(cart_index),
    )
    return f"srs_cart_{h}"


def simulation_product_id(
    *,
    simulation_run_id: str,
    seed: int,
    product_key: str,
) -> str:
    """Stable product id compatible with demo catalog style (demo_{key})."""
    key = str(product_key or "").strip() or "unknown"
    # Prefer canonical demo catalog id shape; hash only when needed for uniqueness.
    _ = derive_subseed(simulation_run_id, normalize_seed(seed), key)
    return f"demo_{key}"


def simulation_event_id(
    *,
    simulation_run_id: str,
    seed: int,
    scenario_id: str,
    event_index: int,
    event_type: str = "",
) -> str:
    h = _short_hash(
        "event",
        simulation_run_id,
        normalize_seed(seed),
        scenario_id,
        int(event_index),
        event_type,
    )
    return f"srs_evt_{h}"


def simulation_recovery_key(
    *,
    simulation_run_id: str,
    seed: int,
    scenario_id: str,
    customer_index: int,
    cart_index: int,
    store_slug: str = DEMO_STORE_SLUG,
) -> str:
    """demo:srs_{run_short}_{customer_short}_{cart_short}"""
    slug = str(store_slug or "").strip() or DEMO_STORE_SLUG
    run_short = _short_hash("run", simulation_run_id, n=8)
    cust = simulation_customer_id(
        simulation_run_id=simulation_run_id,
        seed=seed,
        scenario_id=scenario_id,
        customer_index=customer_index,
    )
    cart = simulation_cart_id(
        simulation_run_id=simulation_run_id,
        seed=seed,
        scenario_id=scenario_id,
        customer_index=customer_index,
        cart_index=cart_index,
    )
    cust_short = cust.replace("srs_cust_", "")[:8]
    cart_short = cart.replace("srs_cart_", "")[:8]
    return f"{slug}:srs_{run_short}_{cust_short}_{cart_short}"
