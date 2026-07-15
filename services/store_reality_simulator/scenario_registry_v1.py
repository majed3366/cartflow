# -*- coding: utf-8 -*-
"""
Scenario registry — metadata only (Phase 2).

No scenario execution. No event generation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ScenarioSpec:
    scenario_id: str
    name: str
    business_purpose: str
    readiness: str  # ready | partial | blocked | observe_only
    phase3_eligible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SCENARIOS: dict[str, ScenarioSpec] = {
    "S01_normal_store_baseline": ScenarioSpec(
        scenario_id="S01_normal_store_baseline",
        name="Normal Store Baseline",
        business_purpose="Believable everyday store activity",
        readiness="partial",
    ),
    "S02_high_traffic_low_conversion": ScenarioSpec(
        scenario_id="S02_high_traffic_low_conversion",
        name="High Traffic, Low Conversion",
        business_purpose="Distinguish volume from conversion",
        readiness="partial",
    ),
    "S03_shipping_cost_hesitation": ScenarioSpec(
        scenario_id="S03_shipping_cost_hesitation",
        name="Shipping Cost Hesitation",
        business_purpose="Concentrated shipping hesitation evidence",
        readiness="ready",
    ),
    "S04_product_high_atc_low_purchase": ScenarioSpec(
        scenario_id="S04_product_high_atc_low_purchase",
        name="Product Added Often, Purchased Rarely",
        business_purpose="Product-level conversion friction",
        readiness="partial",
    ),
    "S05_wa_return_without_purchase": ScenarioSpec(
        scenario_id="S05_wa_return_without_purchase",
        name="WhatsApp Return Without Purchase",
        business_purpose="Engagement is not purchase",
        readiness="ready",
    ),
    "S06_wa_success": ScenarioSpec(
        scenario_id="S06_wa_success",
        name="WhatsApp Success",
        business_purpose="Governed recovery success path",
        readiness="ready",
    ),
    "S07_discount_message_failure": ScenarioSpec(
        scenario_id="S07_discount_message_failure",
        name="Discount Message Failure",
        business_purpose="Discount-oriented recovery underperforms",
        readiness="partial",
    ),
    "S08_repeated_product_interest": ScenarioSpec(
        scenario_id="S08_repeated_product_interest",
        name="Repeated Product Interest",
        business_purpose="Sustained interest with friction",
        readiness="partial",
    ),
    "S09_widget_opened_ignored": ScenarioSpec(
        scenario_id="S09_widget_opened_ignored",
        name="Widget Opened and Ignored",
        business_purpose="Widget non-participation still leaves storefront truth",
        readiness="partial",
    ),
    "S10_widget_reason_capture": ScenarioSpec(
        scenario_id="S10_widget_reason_capture",
        name="Widget Reason Capture",
        business_purpose="Realistic reason distributions",
        readiness="ready",
    ),
    "S11_ignore_all_recovery": ScenarioSpec(
        scenario_id="S11_ignore_all_recovery",
        name="Customer Ignores All Recovery",
        business_purpose="Terminal lifecycle without false engagement",
        readiness="ready",
    ),
    "S12_multi_return_customer": ScenarioSpec(
        scenario_id="S12_multi_return_customer",
        name="Customer Returns Multiple Times",
        business_purpose="Identity and movement across days",
        readiness="partial",
    ),
    "S13_organic_purchase": ScenarioSpec(
        scenario_id="S13_organic_purchase",
        name="Purchase Without CartFlow Influence",
        business_purpose="Organic purchase integrity",
        readiness="ready",
    ),
    "S14_ambiguous_influence": ScenarioSpec(
        scenario_id="S14_ambiguous_influence",
        name="Purchase After Possible Influence",
        business_purpose="Conservative attribution under ambiguity",
        readiness="ready",
    ),
    "S15_vip_customer": ScenarioSpec(
        scenario_id="S15_vip_customer",
        name="VIP Customer",
        business_purpose="VIP lane and phone semantics",
        readiness="ready",
    ),
    "S16_insufficient_data": ScenarioSpec(
        scenario_id="S16_insufficient_data",
        name="Insufficient Data",
        business_purpose="Honest insufficiency messaging",
        readiness="ready",
    ),
    "S17_conflicting_evidence": ScenarioSpec(
        scenario_id="S17_conflicting_evidence",
        name="Conflicting Evidence",
        business_purpose="No dominant pattern",
        readiness="ready",
    ),
    "S18_purchase_closure_suppression": ScenarioSpec(
        scenario_id="S18_purchase_closure_suppression",
        name="Purchase Closure and Suppression",
        business_purpose="Stop recovery at every purchase timing",
        readiness="ready",
    ),
    "S19_channel_failure": ScenarioSpec(
        scenario_id="S19_channel_failure",
        name="Channel Failure",
        business_purpose="Provider failure is not hesitation",
        readiness="partial",
    ),
    "S20_data_growth": ScenarioSpec(
        scenario_id="S20_data_growth",
        name="Data Growth",
        business_purpose="Bounded historical scale",
        readiness="blocked",
        phase3_eligible=False,
    ),
}


def list_scenarios() -> list[ScenarioSpec]:
    return [_SCENARIOS[k] for k in sorted(_SCENARIOS.keys())]


def get_scenario(scenario_id: str) -> Optional[ScenarioSpec]:
    return _SCENARIOS.get(str(scenario_id or "").strip())


def require_scenario(scenario_id: str) -> ScenarioSpec:
    spec = get_scenario(scenario_id)
    if spec is None:
        raise KeyError(f"unknown_scenario:{scenario_id}")
    return spec


def validate_scenario_ids(scenario_ids: list[str]) -> list[str]:
    out: list[str] = []
    for raw in scenario_ids:
        sid = str(raw or "").strip()
        if not sid:
            continue
        require_scenario(sid)
        if sid not in out:
            out.append(sid)
    if not out:
        raise ValueError("scenario_ids_required")
    return out


def registry_snapshot() -> dict[str, Any]:
    return {
        "version": "v1",
        "count": len(_SCENARIOS),
        "scenarios": [s.to_dict() for s in list_scenarios()],
        "execution_implemented": False,
        "note": "Phase 2 registry only — no scenario execution",
    }
