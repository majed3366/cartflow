# -*- coding: utf-8 -*-
"""
Merchant Timeline v1 — Activity Timeline + evidence reads under Identity Authority.

INV-002 WP-6: Timeline consumes Platform Identity Authority MQIC only.
Never resolves merchant/store identity independently.
Presentation/projection only — does not mint decisions or truth events.
"""
from __future__ import annotations

from typing import Any, Mapping, MutableSet, Optional

from services.identity_authority import (
    MerchantQueryIdentityContext,
    attach_timeline_identity_observability,
    ensure_timeline_mqic,
    timeline_identity_scope,
)
from services.identity_authority.exceptions import IdentityError
from services.knowledge_routing_v1 import (
    SURFACE_TIMELINE,
    route_timeline_knowledge_v1,
)

TIMELINE_VERSION = "v1"
_SECTION_WHILE_AWAY = "while_away"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_key_from_topic(topic: Mapping[str, Any]) -> str:
    for key in (
        "aggregation_key",
        "topic_key",
        "brief_item_id",
        "decision_id",
        "insight_key",
    ):
        raw = _norm(topic.get(key))
        if raw:
            return raw
    return _norm(topic.get("title_ar")) or id(topic).__repr__()


def _project_while_away_item(topic: Mapping[str, Any]) -> dict[str, Any]:
    """Same projection shape as Home Activity Timeline (production equivalence)."""
    headline = _norm(topic.get("headline_ar"))
    if not headline:
        headline = _norm(topic.get("what_ar")) or "—"
    detail = _norm(topic.get("why_ar")) or _norm(topic.get("what_ar"))
    return {
        "headline_ar": headline,
        "detail_ar": detail,
        "action_ar": _norm(topic.get("action_ar")),
        "aggregation_key": _norm(topic.get("aggregation_key")),
        "source_knowledge_id": _norm(topic.get("routed_knowledge_id")),
        "routing_priority": int(topic.get("routing_priority") or 0),
        "section": _SECTION_WHILE_AWAY,
    }


def assert_timeline_evidence_matches_mqic(
    recovery_key: str,
    mqic: MerchantQueryIdentityContext,
) -> str:
    """
    Fail closed when recovery_key store prefix ≠ MQIC store_slug.

    No new DB query — parses recovery_key only.
    """
    from services.recovery_truth_timeline_v1 import parse_recovery_key  # noqa: PLC0415

    mqic.assert_authority_owned()
    rk = _norm(recovery_key)[:512]
    slug, _sid = parse_recovery_key(rk)
    if slug and slug != mqic.store_slug:
        raise IdentityError(
            "store_slug_mismatch",
            f"timeline_evidence_mismatch:{slug}!={mqic.store_slug}",
        )
    return mqic.store_slug


def get_recovery_truth_timeline_for_mqic(
    recovery_key: str,
    *,
    mqic: Optional[MerchantQueryIdentityContext] = None,
    store_slug: str = "",
) -> list[dict[str, Any]]:
    """
    Timeline evidence reader — merchant path must pass MQIC.

    Rejects recovery_keys whose store prefix is not the MQIC tenant.
    """
    from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
        get_recovery_truth_timeline,
    )

    with timeline_identity_scope(store_slug=store_slug, mqic=mqic) as bound:
        identity = ensure_timeline_mqic(store_slug=store_slug, mqic=bound)
        assert_timeline_evidence_matches_mqic(recovery_key, identity)
        return get_recovery_truth_timeline(recovery_key)


def bulk_timeline_status_sets_for_mqic(
    recovery_keys: Any,
    *,
    mqic: Optional[MerchantQueryIdentityContext] = None,
    store_slug: str = "",
) -> dict[str, frozenset[str]]:
    """
    Batch timeline status reader scoped to MQIC store.

    Keys whose store prefix ≠ MQIC are omitted (fail closed per key).
    No additional query beyond existing bulk reader for allowed keys.
    """
    from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
        bulk_timeline_status_sets,
        parse_recovery_key,
    )

    with timeline_identity_scope(store_slug=store_slug, mqic=mqic) as bound:
        identity = ensure_timeline_mqic(store_slug=store_slug, mqic=bound)
        allowed: list[str] = []
        for raw in recovery_keys or ():
            rk = _norm(str(raw))[:512]
            if not rk:
                continue
            slug, _ = parse_recovery_key(rk)
            if slug and slug != identity.store_slug:
                continue
            allowed.append(rk)
        return bulk_timeline_status_sets(allowed)


def build_merchant_activity_timeline_v1(
    *,
    daily_brief: Optional[Mapping[str, Any]] = None,
    store_slug: str = "",
    mqic: Optional[MerchantQueryIdentityContext] = None,
    seen_keys: Optional[MutableSet[str]] = None,
) -> dict[str, Any]:
    """
    Build merchant Activity Timeline section (Home ``while_away`` / MV-5).

    Tenant key from MQIC only. Projects Brief achievements — does not mint
    decisions. Routes via Timeline knowledge surface for observability.
    """
    with timeline_identity_scope(store_slug=store_slug, mqic=mqic) as bound:
        identity = ensure_timeline_mqic(store_slug=store_slug, mqic=bound)
        brief = daily_brief if isinstance(daily_brief, Mapping) else {}
        keys: MutableSet[str] = seen_keys if seen_keys is not None else set()
        items: list[dict[str, Any]] = []
        for raw in brief.get("achievements") or []:
            if not isinstance(raw, Mapping):
                continue
            key = _dedupe_key_from_topic(raw)
            if key in keys:
                continue
            keys.add(key)
            items.append(_project_while_away_item(raw))

        routed = route_timeline_knowledge_v1(
            store_slug=identity.store_slug,
            achievements=brief.get("achievements") or [],
        )
        section = {
            "version": TIMELINE_VERSION,
            "title_ar": "بينما كنت بعيداً",
            "lead_ar": "نتابع متجرك تلقائياً — هذا ما اكتمل:",
            "items": items,
            "empty_message_ar": (
                "نتابع متجرك — سنُظهر الإنجازات هنا عند توفرها."
            ),
            "store_slug": identity.store_slug,
            "canonical_store_id": identity.canonical_store_id,
            "knowledge_routing_v1": {
                "routing_version": routed.get("routing_version"),
                "surface": SURFACE_TIMELINE,
                "observability": dict(routed.get("observability") or {}),
            },
            "observability": {
                "while_away_items": len(items),
                "dedupe_keys": len(keys),
            },
        }
        attach_timeline_identity_observability(section)
        return section


__all__ = [
    "TIMELINE_VERSION",
    "assert_timeline_evidence_matches_mqic",
    "build_merchant_activity_timeline_v1",
    "bulk_timeline_status_sets_for_mqic",
    "get_recovery_truth_timeline_for_mqic",
]
