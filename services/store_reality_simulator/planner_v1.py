# -*- coding: utf-8 -*-
"""
Deterministic Reality Engine planner — Phase 3.

Produces governed planned events. Does not persist platform truth.
Unsupported storefront chrome events are planned as unsupported markers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.store_reality_simulator.behavior_catalog_v1 import (
    REASON_WEIGHTS_BASELINE,
    REASON_WEIGHTS_SHIPPING,
    catalog_product,
    pick_product_key,
    weighted_choice,
)
from services.store_reality_simulator.identity_v1 import (
    simulation_cart_id,
    simulation_customer_id,
    simulation_event_id,
    simulation_recovery_key,
    simulation_session_id,
)
from services.store_reality_simulator.scale_profiles_v1 import ScaleProfile
from services.store_reality_simulator.scenario_registry_v1 import (
    ScenarioSpec,
    require_scenario,
    scenario_versions_payload,
)
from services.store_reality_simulator.seed_v1 import make_rng, normalize_seed

# Events with no durable ingest — accounted as unsupported when "executed"
UNSUPPORTED_MARKERS = frozenset(
    {
        "session_started",
        "page_viewed",
        "product_viewed",
        "scroll_depth_reached",
        "dwell_time_recorded",
        "widget_opened",
        "widget_ignored",
    }
)

SUPPORTED_PLATFORM = frozenset(
    {
        "cart_state_sync",
        "cart_abandoned",
        "hesitation_reason_selected",
        "phone_submitted",
        "passive_return",
        "returned_to_site",
        "whatsapp_scheduled",
        "whatsapp_sent_mock",
        "purchase_created",
    }
)


@dataclass
class PlannedEvent:
    simulated_event_id: str
    event_index: int
    simulated_at: datetime
    event_type: str
    scenario_id: str
    scenario_version: str
    scenario_revision: int
    customer_id: str
    session_id: str
    cart_id: str
    recovery_key: str
    product_key: str
    product_id: str
    product_price: float
    reason_tag: str = ""
    customer_phone: str = ""
    archetype: str = ""
    support: str = "supported"  # supported | unsupported | internal
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["simulated_at"] = self.simulated_at.isoformat()
        return d


@dataclass
class RealityPlan:
    simulation_run_id: str
    seed: int
    start_date: datetime
    duration_days: int
    scale_profile: str
    scenario_versions: list[dict[str, Any]]
    events: list[PlannedEvent]
    products: list[dict[str, Any]]
    customers: list[str]
    sessions: list[str]
    warnings: list[str] = field(default_factory=list)

    @property
    def expected_event_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for ev in self.events:
            out[ev.event_type] = out.get(ev.event_type, 0) + 1
        return out

    def to_summary(self) -> dict[str, Any]:
        return {
            "simulation_run_id": self.simulation_run_id,
            "seed": self.seed,
            "scale_profile": self.scale_profile,
            "duration_days": self.duration_days,
            "event_count": len(self.events),
            "supported_count": sum(1 for e in self.events if e.support == "supported"),
            "unsupported_count": sum(
                1 for e in self.events if e.support == "unsupported"
            ),
            "customer_count": len(self.customers),
            "session_count": len(self.sessions),
            "product_count": len(self.products),
            "expected_event_counts": self.expected_event_counts,
            "scenario_versions": self.scenario_versions,
            "warnings": list(self.warnings),
        }


def _day_start(start: datetime, day_offset: int) -> datetime:
    base = start.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return base + timedelta(days=int(day_offset))


def _phone_for(archetype: str, customer_index: int) -> str:
    if archetype == "anonymous_no_phone":
        return ""
    # Deterministic demo-safe test phones (not merchant-equal lab phone)
    return f"9665{10000000 + int(customer_index):08d}"[:12]


def build_reality_plan(
    *,
    simulation_run_id: str,
    seed: int,
    start_date: datetime,
    duration_days: int,
    scenario_ids: list[str],
    scale: ScaleProfile,
    scale_factor: float = 1.0,
) -> RealityPlan:
    rng = make_rng(normalize_seed(seed))
    versions = scenario_versions_payload(scenario_ids)
    specs = [require_scenario(v["scenario_id"]) for v in versions]
    warnings: list[str] = []
    for spec in specs:
        if not spec.phase3_eligible:
            warnings.append(f"scenario_not_phase3_eligible:{spec.scenario_id}")
        if spec.readiness == "blocked":
            warnings.append(f"scenario_blocked:{spec.scenario_id}")

    events: list[PlannedEvent] = []
    customers: list[str] = []
    sessions: list[str] = []
    products_used: dict[str, dict[str, Any]] = {}
    event_index = 0

    days = min(int(duration_days), int(scale.duration_days) if scale else duration_days)
    days = max(1, days)
    journeys_target = max(
        1, int(round(scale.journeys_per_day * days * float(scale_factor)))
    )
    # Cap by max events roughly (avg ~6 platform events + markers per journey)
    max_journeys = max(1, int(scale.max_events_per_run // 8))
    journeys_target = min(journeys_target, max_journeys)

    eligible = [s for s in specs if s.phase3_eligible and s.readiness != "blocked"]
    if not eligible:
        warnings.append("no_eligible_scenarios_using_baseline")
        eligible = [require_scenario("S01_normal_store_baseline")]

    for j in range(journeys_target):
        spec = eligible[j % len(eligible)]
        day_offset = j % days
        hour = 9 + (j % 10)
        minute = (j * 7) % 50
        when = _day_start(start_date, day_offset) + timedelta(hours=hour, minutes=minute)
        cust_i = j
        sess_i = 0
        cart_i = 0
        customer_id = simulation_customer_id(
            simulation_run_id=simulation_run_id,
            seed=seed,
            scenario_id=spec.scenario_id,
            customer_index=cust_i,
        )
        session_id = simulation_session_id(
            simulation_run_id=simulation_run_id,
            seed=seed,
            scenario_id=spec.scenario_id,
            customer_index=cust_i,
            session_index=sess_i,
        )
        cart_id = simulation_cart_id(
            simulation_run_id=simulation_run_id,
            seed=seed,
            scenario_id=spec.scenario_id,
            customer_index=cust_i,
            cart_index=cart_i,
        )
        recovery_key = simulation_recovery_key(
            simulation_run_id=simulation_run_id,
            seed=seed,
            scenario_id=spec.scenario_id,
            customer_index=cust_i,
            cart_index=cart_i,
        )
        customers.append(customer_id)
        sessions.append(session_id)

        archetype, product_role, reason_weights, outcomes = _scenario_behavior(
            spec, rng
        )
        product_key = pick_product_key(product_role, rng)
        product = catalog_product(product_key)
        products_used[product_key] = product
        phone = _phone_for(archetype, cust_i)
        price = float(product["price"])
        if spec.planner_key == "vip":
            price = max(price, 500.0)

        def _add(
            etype: str,
            at: datetime,
            *,
            reason: str = "",
            support: Optional[str] = None,
            extra: Optional[dict[str, Any]] = None,
        ) -> None:
            nonlocal event_index
            if etype in UNSUPPORTED_MARKERS:
                sup = "unsupported"
            elif support:
                sup = support
            elif etype in SUPPORTED_PLATFORM:
                sup = "supported"
            else:
                sup = "unsupported"
            eid = simulation_event_id(
                simulation_run_id=simulation_run_id,
                seed=seed,
                scenario_id=spec.scenario_id,
                event_index=event_index,
                event_type=etype,
            )
            events.append(
                PlannedEvent(
                    simulated_event_id=eid,
                    event_index=event_index,
                    simulated_at=at,
                    event_type=etype,
                    scenario_id=spec.scenario_id,
                    scenario_version=spec.scenario_version,
                    scenario_revision=spec.scenario_revision,
                    customer_id=customer_id,
                    session_id=session_id,
                    cart_id=cart_id,
                    recovery_key=recovery_key,
                    product_key=product_key,
                    product_id=str(product["id"]),
                    product_price=price,
                    reason_tag=reason,
                    customer_phone=phone,
                    archetype=archetype,
                    support=sup,
                    payload=dict(extra or {}),
                )
            )
            event_index += 1

        # Believable storefront markers (unsupported — accounted, not faked as truth)
        _add("session_started", when)
        _add("page_viewed", when + timedelta(seconds=5))
        _add("product_viewed", when + timedelta(seconds=20))
        if rng.random() < 0.55:
            _add("scroll_depth_reached", when + timedelta(seconds=45))
        if rng.random() < 0.4:
            _add("dwell_time_recorded", when + timedelta(seconds=70))

        # Platform path
        _add("cart_state_sync", when + timedelta(minutes=2))

        abandon_at = when + timedelta(minutes=8)
        if outcomes.get("abandon", True):
            _add("cart_abandoned", abandon_at)

        reason = ""
        if outcomes.get("reason"):
            reason = weighted_choice(reason_weights, rng)
            _add(
                "hesitation_reason_selected",
                abandon_at + timedelta(seconds=30),
                reason=reason,
            )
            if phone and outcomes.get("phone", True):
                _add(
                    "phone_submitted",
                    abandon_at + timedelta(seconds=45),
                    reason=reason,
                )

        if outcomes.get("widget_ignore"):
            _add("widget_opened", abandon_at + timedelta(seconds=10))
            _add("widget_ignored", abandon_at + timedelta(seconds=25))

        if outcomes.get("whatsapp"):
            _add(
                "whatsapp_scheduled",
                abandon_at + timedelta(minutes=1),
                reason=reason,
                support="internal",
            )
            _add(
                "whatsapp_sent_mock",
                abandon_at + timedelta(minutes=2),
                reason=reason,
                support="internal",
            )

        cursor = abandon_at + timedelta(hours=3)
        if outcomes.get("return"):
            # may cross midnight
            cursor = abandon_at + timedelta(hours=6 + (j % 5))
            _add("returned_to_site", cursor)
            if outcomes.get("passive"):
                _add("passive_return", cursor + timedelta(minutes=1))

        if outcomes.get("multi_return"):
            cursor = abandon_at + timedelta(days=1, hours=2)
            _add("returned_to_site", cursor)
            _add("passive_return", cursor + timedelta(minutes=2))

        if outcomes.get("purchase"):
            delay_h = int(outcomes.get("purchase_delay_hours", 4))
            _add(
                "purchase_created",
                abandon_at + timedelta(hours=delay_h),
                reason=reason,
                extra={"organic": bool(outcomes.get("organic"))},
            )

        # Hard cap
        if len(events) >= scale.max_events_per_run:
            warnings.append("plan_truncated_at_max_events_per_run")
            break

    events.sort(key=lambda e: (e.simulated_at, e.event_index))
    # re-index for chronological order stability in reports
    for i, ev in enumerate(events):
        ev.event_index = i

    return RealityPlan(
        simulation_run_id=simulation_run_id,
        seed=int(seed),
        start_date=start_date.astimezone(timezone.utc),
        duration_days=days,
        scale_profile=scale.profile_id,
        scenario_versions=versions,
        events=events,
        products=list(products_used.values()),
        customers=customers,
        sessions=sessions,
        warnings=warnings,
    )


def _scenario_behavior(
    spec: ScenarioSpec, rng: Any
) -> tuple[str, str, dict[str, float], dict[str, Any]]:
    key = spec.planner_key
    if key == "shipping_hesitation":
        return (
            "shipping_sensitive",
            "shipping_hesitation",
            REASON_WEIGHTS_SHIPPING,
            {
                "abandon": True,
                "reason": True,
                "phone": True,
                "whatsapp": True,
                "return": True,
                "passive": True,
                "purchase": rng.random() < 0.25,
                "purchase_delay_hours": 20,
            },
        )
    if key == "wa_return_no_purchase":
        return (
            "whatsapp_responder",
            "wa_recovery",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": True,
                "phone": True,
                "whatsapp": True,
                "return": True,
                "passive": True,
                "purchase": False,
            },
        )
    if key == "wa_success":
        return (
            "whatsapp_responder",
            "wa_recovery",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": True,
                "phone": True,
                "whatsapp": True,
                "return": True,
                "purchase": True,
                "purchase_delay_hours": 5,
            },
        )
    if key == "organic_purchase":
        return (
            "organic_buyer",
            "low_price_volume",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": False,
                "reason": False,
                "phone": False,
                "whatsapp": False,
                "return": False,
                "purchase": True,
                "organic": True,
                "purchase_delay_hours": 1,
            },
        )
    if key == "ignore_all":
        return (
            "recovery_resistant",
            "high_price_consideration",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": False,
                "widget_ignore": True,
                "whatsapp": True,
                "return": False,
                "purchase": False,
            },
        )
    if key == "insufficient":
        return (
            "fast_buyer",
            "low_price_volume",
            REASON_WEIGHTS_BASELINE,
            {"abandon": True, "reason": True, "phone": False, "purchase": False},
        )
    if key == "vip":
        return (
            "high_value_vip",
            "vip",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": True,
                "phone": rng.random() < 0.6,
                "whatsapp": False,
                "purchase": rng.random() < 0.35,
            },
        )
    if key == "ambiguous_influence":
        return (
            "repeated_visitor",
            "wa_recovery",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": True,
                "phone": True,
                "whatsapp": True,
                "return": True,
                "multi_return": True,
                "purchase": True,
                "purchase_delay_hours": 48,
            },
        )
    if key == "high_traffic_low_conv":
        return (
            "comparison_shopper",
            "high_atc_low_conv",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": True,
                "phone": True,
                "whatsapp": False,
                "return": rng.random() < 0.3,
                "purchase": rng.random() < 0.08,
            },
        )
    if key == "widget_ignore":
        return (
            "widget_engager",
            "low_price_volume",
            REASON_WEIGHTS_BASELINE,
            {
                "abandon": True,
                "reason": False,
                "widget_ignore": True,
                "purchase": rng.random() < 0.2,
                "organic": True,
                "purchase_delay_hours": 2,
            },
        )
    # baseline default
    return (
        rng.choice(
            [
                "fast_buyer",
                "price_sensitive",
                "shipping_sensitive",
                "organic_buyer",
                "repeated_visitor",
            ]
        ),
        "low_price_volume",
        REASON_WEIGHTS_BASELINE,
        {
            "abandon": rng.random() < 0.7,
            "reason": rng.random() < 0.55,
            "phone": rng.random() < 0.5,
            "whatsapp": rng.random() < 0.35,
            "return": rng.random() < 0.3,
            "purchase": rng.random() < 0.35,
            "purchase_delay_hours": 6,
        },
    )
