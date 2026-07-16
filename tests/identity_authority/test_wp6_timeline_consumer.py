# -*- coding: utf-8 -*-
"""INV-002 WP-6 — Timeline consumes Identity Authority (no independent resolve)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from services.identity_authority import (
    DualResolveViolation,
    IdentityError,
    IdentityImmutabilityViolation,
    ResolveIdentityInput,
    clear_mqic,
    ensure_timeline_mqic,
    get_mqic,
    mqic_from_caller_store_slug,
    reject_field_mutation,
    reset_counters,
    resolve_and_bind,
    timeline_identity_scope,
)
from services.identity_authority.contracts import CanonicalStoreIdentity
from services.merchant_timeline_v1 import (
    assert_timeline_evidence_matches_mqic,
    build_merchant_activity_timeline_v1,
    get_recovery_truth_timeline_for_mqic,
)


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def test_timeline_consumes_mqic_store_slug() -> None:
    mqic = mqic_from_caller_store_slug("demo-tl-wp6", merchant_id="9")
    brief = {
        "achievements": [
            {
                "headline_ar": "اكتمل شيء",
                "why_ar": "دليل",
                "aggregation_key": "a1",
                "eligible_surfaces": ["timeline", "daily_brief"],
            }
        ]
    }
    with timeline_identity_scope(mqic=mqic):
        section = build_merchant_activity_timeline_v1(
            daily_brief=brief, mqic=mqic
        )
    assert section["store_slug"] == "demo-tl-wp6"
    assert section["identity_authority_v1"]["authority_consumer"] == "timeline"
    assert len(section["items"]) == 1
    assert get_mqic() is None


def test_timeline_caller_slug_sealed_via_authority() -> None:
    section = build_merchant_activity_timeline_v1(
        daily_brief={"achievements": []},
        store_slug="caller-tl-wp6",
    )
    assert section["store_slug"] == "caller-tl-wp6"
    assert get_mqic() is None


def test_timeline_slug_mismatch_fail_closed() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with timeline_identity_scope(mqic=mqic):
        with pytest.raises(IdentityError) as ei:
            build_merchant_activity_timeline_v1(
                daily_brief={},
                store_slug="store-b",
                mqic=mqic,
            )
        assert ei.value.code == "store_slug_mismatch"


def test_identity_resolved_once_in_timeline_scope() -> None:
    mqic = mqic_from_caller_store_slug("once-tl", merchant_id="1")
    with timeline_identity_scope(mqic=mqic):
        ensure_timeline_mqic(mqic=mqic)
        other = mqic_from_caller_store_slug("once-tl", merchant_id="1")
        with pytest.raises(DualResolveViolation):
            resolve_and_bind(
                ResolveIdentityInput(
                    merchant_id="1",
                    stores_by_id={
                        other.canonical_store_id: CanonicalStoreIdentity(
                            canonical_store_id=other.canonical_store_id,
                            store_slug=other.store_slug,
                        )
                    },
                    membership_store_ids=frozenset({other.canonical_store_id}),
                    primary_store_id=other.canonical_store_id,
                )
            )


def test_immutability_preserved_under_timeline() -> None:
    mqic = mqic_from_caller_store_slug("imm-tl", merchant_id="1")
    with timeline_identity_scope(mqic=mqic):
        ensure_timeline_mqic(mqic=mqic)
        with pytest.raises(IdentityImmutabilityViolation):
            reject_field_mutation(mqic, "store_slug")


def test_provider_independence_timeline_tenant_is_canonical() -> None:
    mqic = mqic_from_caller_store_slug("canonical-tl", merchant_id="1")
    assert mqic.store_slug == "canonical-tl"
    assert mqic.canonical_store_id.startswith("canonical:")


def test_timeline_cannot_resolve_identity_directly() -> None:
    src = Path("services/merchant_timeline_v1.py").read_text(encoding="utf-8")
    assert "merchant_authenticated_store_slug" not in src
    assert "resolve_merchant_onboarding_store" not in src
    cons = Path("services/identity_authority/timeline_consumer_v1.py").read_text(
        encoding="utf-8"
    )
    assert "resolve_mqic_from_session" in cons


def test_timeline_evidence_mismatch_fail_closed() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with pytest.raises(IdentityError) as ei:
        assert_timeline_evidence_matches_mqic("store-b:session1", mqic)
    assert ei.value.code == "store_slug_mismatch"


def test_timeline_evidence_reader_uses_mqic() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with patch(
        "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
        return_value=[{"status": "scheduled", "store_slug": "store-a"}],
    ) as mocked:
        rows = get_recovery_truth_timeline_for_mqic(
            "store-a:sess", mqic=mqic
        )
    assert rows[0]["status"] == "scheduled"
    mocked.assert_called_once_with("store-a:sess")


def test_home_timeline_shares_mqic() -> None:
    """ICT-14 class: Home Activity Timeline store_slug ≡ MQIC."""
    from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

    mqic = mqic_from_caller_store_slug("shared-tl-home", merchant_id="1")
    composed = compose_merchant_home_experience_v1(
        daily_brief={
            "achievements": [
                {
                    "headline_ar": "x",
                    "aggregation_key": "k1",
                    "eligible_surfaces": ["timeline"],
                }
            ]
        },
        store_slug=mqic.store_slug,
        mqic=mqic,
    )
    assert composed["while_away"]["store_slug"] == "shared-tl-home"
    assert composed["while_away"]["identity_authority_v1"]["authority_consumer"] == (
        "timeline"
    )


def test_main_py_untouched_by_wp6_identity() -> None:
    src = Path("main.py").read_text(encoding="utf-8")
    assert "timeline_consumer_v1" not in src
    assert "bind_mqic_for_timeline" not in src
    assert "merchant_timeline_v1" not in src
