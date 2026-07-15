# -*- coding: utf-8 -*-
"""
Scenario registry — versioned metadata + Phase 3 eligibility.

Execution lives in the Reality Engine / planner — not here.
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
    scenario_version: str = "v1"
    scenario_revision: int = 1
    phase3_eligible: bool = True
    planner_key: str = ""  # internal planner family

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def versioned_id(self) -> str:
        return f"{self.scenario_id}@{self.scenario_version}.r{self.scenario_revision}"


def _s(
    scenario_id: str,
    name: str,
    purpose: str,
    readiness: str,
    *,
    phase3_eligible: bool = True,
    planner_key: str = "",
    revision: int = 1,
) -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id=scenario_id,
        name=name,
        business_purpose=purpose,
        readiness=readiness,
        scenario_version="v1",
        scenario_revision=revision,
        phase3_eligible=phase3_eligible,
        planner_key=planner_key or scenario_id,
    )


_SCENARIOS: dict[str, ScenarioSpec] = {
    "S01_normal_store_baseline": _s(
        "S01_normal_store_baseline",
        "Normal Store Baseline",
        "Believable everyday store activity",
        "partial",
        planner_key="baseline",
    ),
    "S02_high_traffic_low_conversion": _s(
        "S02_high_traffic_low_conversion",
        "High Traffic, Low Conversion",
        "Distinguish volume from conversion",
        "partial",
        planner_key="high_traffic_low_conv",
    ),
    "S03_shipping_cost_hesitation": _s(
        "S03_shipping_cost_hesitation",
        "Shipping Cost Hesitation",
        "Concentrated shipping hesitation evidence",
        "ready",
        planner_key="shipping_hesitation",
    ),
    "S04_product_high_atc_low_purchase": _s(
        "S04_product_high_atc_low_purchase",
        "Product Added Often, Purchased Rarely",
        "Product-level conversion friction",
        "partial",
        planner_key="product_low_conv",
    ),
    "S05_wa_return_without_purchase": _s(
        "S05_wa_return_without_purchase",
        "WhatsApp Return Without Purchase",
        "Engagement is not purchase",
        "ready",
        planner_key="wa_return_no_purchase",
    ),
    "S06_wa_success": _s(
        "S06_wa_success",
        "WhatsApp Success",
        "Governed recovery success path",
        "ready",
        planner_key="wa_success",
    ),
    "S07_discount_message_failure": _s(
        "S07_discount_message_failure",
        "Discount Message Failure",
        "Discount-oriented recovery underperforms",
        "partial",
        planner_key="discount_fail",
    ),
    "S08_repeated_product_interest": _s(
        "S08_repeated_product_interest",
        "Repeated Product Interest",
        "Sustained interest with friction",
        "partial",
        planner_key="repeat_interest",
    ),
    "S09_widget_opened_ignored": _s(
        "S09_widget_opened_ignored",
        "Widget Opened and Ignored",
        "Widget non-participation still leaves storefront truth",
        "partial",
        planner_key="widget_ignore",
    ),
    "S10_widget_reason_capture": _s(
        "S10_widget_reason_capture",
        "Widget Reason Capture",
        "Realistic reason distributions",
        "ready",
        planner_key="reason_mix",
    ),
    "S11_ignore_all_recovery": _s(
        "S11_ignore_all_recovery",
        "Customer Ignores All Recovery",
        "Terminal lifecycle without false engagement",
        "ready",
        planner_key="ignore_all",
    ),
    "S12_multi_return_customer": _s(
        "S12_multi_return_customer",
        "Customer Returns Multiple Times",
        "Identity and movement across days",
        "partial",
        planner_key="multi_return",
    ),
    "S13_organic_purchase": _s(
        "S13_organic_purchase",
        "Purchase Without CartFlow Influence",
        "Organic purchase integrity",
        "ready",
        planner_key="organic_purchase",
    ),
    "S14_ambiguous_influence": _s(
        "S14_ambiguous_influence",
        "Purchase After Possible Influence",
        "Conservative attribution under ambiguity",
        "ready",
        planner_key="ambiguous_influence",
    ),
    "S15_vip_customer": _s(
        "S15_vip_customer",
        "VIP Customer",
        "VIP lane and phone semantics",
        "ready",
        planner_key="vip",
    ),
    "S16_insufficient_data": _s(
        "S16_insufficient_data",
        "Insufficient Data",
        "Honest insufficiency messaging",
        "ready",
        planner_key="insufficient",
    ),
    "S17_conflicting_evidence": _s(
        "S17_conflicting_evidence",
        "Conflicting Evidence",
        "No dominant pattern",
        "ready",
        planner_key="conflict",
    ),
    "S18_purchase_closure_suppression": _s(
        "S18_purchase_closure_suppression",
        "Purchase Closure and Suppression",
        "Stop recovery at every purchase timing",
        "ready",
        planner_key="closure",
    ),
    "S19_channel_failure": _s(
        "S19_channel_failure",
        "Channel Failure",
        "Provider failure is not hesitation",
        "partial",
        planner_key="channel_fail",
    ),
    "S20_data_growth": _s(
        "S20_data_growth",
        "Data Growth",
        "Bounded historical scale",
        "blocked",
        phase3_eligible=False,
        planner_key="data_growth",
    ),
}

# Friendly aliases (brief naming)
_ALIASES: dict[str, str] = {
    "shipping_hesitation": "S03_shipping_cost_hesitation",
    "normal_baseline": "S01_normal_store_baseline",
}


def resolve_scenario_id(raw: str) -> str:
    s = str(raw or "").strip()
    if "@" in s:
        s = s.split("@", 1)[0]
    return _ALIASES.get(s, s)


def list_scenarios() -> list[ScenarioSpec]:
    return [_SCENARIOS[k] for k in sorted(_SCENARIOS.keys())]


def get_scenario(scenario_id: str) -> Optional[ScenarioSpec]:
    return _SCENARIOS.get(resolve_scenario_id(scenario_id))


def require_scenario(scenario_id: str) -> ScenarioSpec:
    spec = get_scenario(scenario_id)
    if spec is None:
        raise KeyError(f"unknown_scenario:{scenario_id}")
    return spec


def validate_scenario_ids(scenario_ids: list[str]) -> list[str]:
    out: list[str] = []
    for raw in scenario_ids:
        sid = resolve_scenario_id(raw)
        if not sid:
            continue
        require_scenario(sid)
        if sid not in out:
            out.append(sid)
    if not out:
        raise ValueError("scenario_ids_required")
    return out


def scenario_versions_payload(scenario_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sid in validate_scenario_ids(scenario_ids):
        spec = require_scenario(sid)
        rows.append(
            {
                "scenario_id": spec.scenario_id,
                "scenario_version": spec.scenario_version,
                "scenario_revision": spec.scenario_revision,
                "versioned_id": spec.versioned_id,
                "planner_key": spec.planner_key,
                "phase3_eligible": spec.phase3_eligible,
            }
        )
    return rows


def registry_snapshot() -> dict[str, Any]:
    return {
        "version": "v1",
        "count": len(_SCENARIOS),
        "scenarios": [s.to_dict() for s in list_scenarios()],
        "aliases": dict(_ALIASES),
        "execution_implemented": True,
        "note": "Phase 3 Reality Engine executes versioned scenarios via planner",
    }
