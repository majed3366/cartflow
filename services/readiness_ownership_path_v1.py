# -*- coding: utf-8 -*-
"""
Readiness Ownership Path v1 — who owns each blocker (read-only).

Maps merchant production readiness missing items to owner categories.
Does not change recovery, send, widget, or dashboard behavior.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.merchant_production_readiness_path_v1 import (
    MerchantProductionReadinessPath,
    ReadinessPathItem,
    build_merchant_production_readiness_path,
)

log = logging.getLogger("cartflow")

OWNER_MERCHANT = "merchant"
OWNER_CARTFLOW_OPS = "cartflow_ops"
OWNER_PROVIDER = "provider"
OWNER_PLATFORM = "platform"
OWNER_SHARED = "shared"

_ALL_OWNERS = frozenset(
    {
        OWNER_MERCHANT,
        OWNER_CARTFLOW_OPS,
        OWNER_PROVIDER,
        OWNER_PLATFORM,
        OWNER_SHARED,
    }
)

_OWNER_LABEL_AR: dict[str, str] = {
    OWNER_MERCHANT: "التاجر",
    OWNER_CARTFLOW_OPS: "تشغيل CartFlow",
    OWNER_PROVIDER: "مزود واتساب",
    OWNER_PLATFORM: "المنصة",
    OWNER_SHARED: "مشترك (التاجر + التشغيل)",
}

# Every production-path item code → owner categories (v1 catalog).
OWNERSHIP_BY_CODE: dict[str, list[str]] = {
    "dashboard_init": [OWNER_MERCHANT],
    "store_connected": [OWNER_MERCHANT, OWNER_PLATFORM],
    "widget_enabled": [OWNER_MERCHANT],
    "recovery_enabled": [OWNER_MERCHANT],
    "recovery_delays": [OWNER_MERCHANT],
    "templates_local": [OWNER_MERCHANT],
    "store_whatsapp_number": [OWNER_MERCHANT],
    "production_provider": [OWNER_CARTFLOW_OPS, OWNER_PLATFORM],
    "delivery_truth": [OWNER_CARTFLOW_OPS],
    "templates_approved": [OWNER_MERCHANT, OWNER_PROVIDER],
    "template_routing": [OWNER_MERCHANT, OWNER_CARTFLOW_OPS],
    "24h_window_evidence": [OWNER_MERCHANT, OWNER_SHARED],
    "queue_foundation": [OWNER_CARTFLOW_OPS, OWNER_PLATFORM],
    "restart_survival_foundation": [OWNER_CARTFLOW_OPS, OWNER_PLATFORM],
    "provider_not_connected": [OWNER_CARTFLOW_OPS, OWNER_PLATFORM],
    "delivery_truth_callback": [OWNER_CARTFLOW_OPS],
    "templates_not_configured": [OWNER_MERCHANT],
    "templates_not_provider_approved": [OWNER_MERCHANT, OWNER_PROVIDER],
    "production_mode_off_or_twilio_missing": [OWNER_CARTFLOW_OPS, OWNER_PLATFORM],
}


@dataclass
class ReadinessOwnershipBlock:
    code: str
    problem_ar: str
    owners: list[str] = field(default_factory=list)
    owners_display_ar: str = ""
    action_ar: str = ""
    expected_result_ar: str = ""
    risk_level: str = ""
    estimated_effort: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessOwnershipPath:
    store_slug: str = ""
    onboarding_state: str = ""
    blockers: list[ReadinessOwnershipBlock] = field(default_factory=list)
    path: Optional[MerchantProductionReadinessPath] = None
    admin_knows_who_should_act: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["blockers"] = [b.to_dict() for b in self.blockers]
        if self.path is not None:
            d["path"] = self.path.to_dict()
        return d


def owners_for_code(code: str) -> list[str]:
    owners = list(OWNERSHIP_BY_CODE.get((code or "").strip(), [OWNER_SHARED]))
    return [o for o in owners if o in _ALL_OWNERS] or [OWNER_SHARED]


def format_owners_ar(owners: list[str]) -> str:
    key = tuple(sorted(owners))
    presets: dict[tuple[str, ...], str] = {
        (OWNER_MERCHANT, OWNER_PROVIDER): "التاجر + مزود واتساب",
        (OWNER_CARTFLOW_OPS, OWNER_PLATFORM): "تشغيل CartFlow + المنصة",
        (OWNER_MERCHANT, OWNER_PLATFORM): "التاجر + المنصة",
        (OWNER_MERCHANT, OWNER_SHARED): "التاجر + مشترك",
    }
    if key in presets:
        return presets[key]
    return " + ".join(_OWNER_LABEL_AR.get(o, o) for o in owners)


def _block_from_item(item: ReadinessPathItem) -> ReadinessOwnershipBlock:
    owners = owners_for_code(item.code)
    owners_ar = format_owners_ar(owners)
    return ReadinessOwnershipBlock(
        code=item.code,
        problem_ar=item.label_ar,
        owners=owners,
        owners_display_ar=owners_ar,
        action_ar=item.next_action_ar,
        expected_result_ar=item.expected_result_ar,
        risk_level=item.risk_level,
        estimated_effort=item.estimated_effort,
    )


def _log_readiness_owner(block: ReadinessOwnershipBlock, *, store_slug: str) -> None:
    owner_s = "+".join(block.owners)
    line = (
        f"[READINESS OWNER] store_slug={store_slug} problem={block.problem_ar} "
        f"owner={owner_s} action={block.action_ar}"
    )
    print(line, flush=True)
    log.info("%s", line)


def build_readiness_ownership_path(
    store: Optional[Any] = None,
    *,
    emit_logs: bool = True,
    emit_path_logs: bool = False,
) -> ReadinessOwnershipPath:
    path = build_merchant_production_readiness_path(
        store, emit_logs=emit_path_logs
    )
    blockers = [_block_from_item(it) for it in path.missing_items]
    if emit_logs:
        for b in blockers:
            _log_readiness_owner(b, store_slug=path.store_slug)
        if not blockers and path.onboarding_state:
            _log_readiness_owner(
                ReadinessOwnershipBlock(
                    code="none",
                    problem_ar="لا توجد عوائق",
                    owners=[OWNER_MERCHANT],
                    owners_display_ar=_OWNER_LABEL_AR[OWNER_MERCHANT],
                    action_ar=path.next_action_ar,
                    expected_result_ar=path.expected_result_ar,
                ),
                store_slug=path.store_slug,
            )
    admin_ok = all(bool(b.owners) for b in blockers) if blockers else True
    return ReadinessOwnershipPath(
        store_slug=path.store_slug,
        onboarding_state=path.onboarding_state,
        blockers=blockers,
        path=path,
        admin_knows_who_should_act=admin_ok,
    )


def enrich_merchant_readiness_card_with_ownership(
    card: dict[str, Any],
    *,
    store: Optional[Any] = None,
) -> dict[str, Any]:
    """Add ownership rows to admin جاهزية المتجر card (presentation only)."""
    ownership = build_readiness_ownership_path(store, emit_logs=False, emit_path_logs=False)
    path = ownership.path
    out = dict(card)
    blockers = ownership.blockers

    if blockers:
        top = blockers[0]
        owner_lines = [
            "——— الملكية (من يتصرف) ———",
            f"المشكلة: {top.problem_ar}",
            f"المسؤول: {top.owners_display_ar}",
            f"الإجراء: {top.action_ar}",
            f"الأثر المتوقع: {top.expected_result_ar}",
        ]
        for b in blockers[1:4]:
            owner_lines.extend(
                [
                    "—",
                    f"المشكلة: {b.problem_ar}",
                    f"المسؤول: {b.owners_display_ar}",
                    f"الإجراء: {b.action_ar}",
                    f"الأثر المتوقع: {b.expected_result_ar}",
                ]
            )
    else:
        owner_lines = [
            "——— الملكية ———",
            "المشكلة: لا توجد عوائق",
            "المسؤول: التاجر (متابعة)",
            f"الإجراء: {(path.next_action_ar if path else '—')}",
            f"الأثر المتوقع: {(path.expected_result_ar if path else '—')}",
        ]

    detail = list(out.get("detail_lines") or []) + owner_lines
    out["detail_lines"] = detail
    out["technical_detail_lines"] = list(out.get("technical_detail_lines") or []) + owner_lines
    out["ownership"] = ownership.to_dict()
    out["admin_knows_who_should_act"] = ownership.admin_knows_who_should_act

    if out.get("operational") and isinstance(out["operational"], dict) and blockers:
        op = dict(out["operational"])
        op["suggested_action_ar"] = (
            f"{blockers[0].action_ar} — المسؤول: {blockers[0].owners_display_ar}"
        )
        op["verification_lines"] = [
            f"الأثر المتوقع: {blockers[0].expected_result_ar}",
            f"المسؤول: {blockers[0].owners_display_ar}",
        ]
        out["operational"] = op

    return out


def build_merchant_readiness_card_with_ownership(
    store: Optional[Any] = None,
) -> dict[str, Any]:
    from services.merchant_production_readiness_path_v1 import (
        build_merchant_production_readiness_card,
    )

    card = build_merchant_production_readiness_card(store)
    return enrich_merchant_readiness_card_with_ownership(card, store=store)
