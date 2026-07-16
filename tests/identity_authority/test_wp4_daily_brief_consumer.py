# -*- coding: utf-8 -*-
"""INV-002 WP-4 — Daily Brief consumes Identity Authority (no independent resolve)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.identity_authority import (
    DualResolveViolation,
    IdentityError,
    IdentityImmutabilityViolation,
    ResolveIdentityInput,
    clear_mqic,
    daily_brief_identity_scope,
    ensure_daily_brief_mqic,
    get_mqic,
    mqic_from_caller_store_slug,
    reject_field_mutation,
    reset_counters,
    resolve_and_bind,
)
from services.identity_authority.contracts import CanonicalStoreIdentity
from services.merchant_daily_brief_v1 import build_merchant_daily_brief_api_payload


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def test_daily_brief_consumes_mqic_store_slug() -> None:
    mqic = mqic_from_caller_store_slug("demo-brief-wp4", merchant_id="9")
    with daily_brief_identity_scope(mqic=mqic):
        with patch(
            "services.knowledge_layer_v1.build_knowledge_report",
            side_effect=ImportError("skip"),
        ), patch(
            "services.normal_carts_dashboard_batch_v1.build_normal_carts_dashboard_api_payload",
            side_effect=ImportError("skip"),
        ):
            payload = build_merchant_daily_brief_api_payload(
                MagicMock(),
                mqic.store_slug,
                MagicMock(),
                mqic=mqic,
            )
    assert payload["store_slug"] == "demo-brief-wp4"
    assert get_mqic() is None


def test_daily_brief_caller_slug_sealed_via_authority() -> None:
    with patch(
        "services.knowledge_layer_v1.build_knowledge_report",
        side_effect=ImportError("skip"),
    ), patch(
        "services.normal_carts_dashboard_batch_v1.build_normal_carts_dashboard_api_payload",
        side_effect=ImportError("skip"),
    ):
        payload = build_merchant_daily_brief_api_payload(
            MagicMock(),
            "caller-slug-wp4",
            MagicMock(),
        )
    assert payload["store_slug"] == "caller-slug-wp4"
    assert get_mqic() is None


def test_daily_brief_slug_mismatch_fail_closed() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with daily_brief_identity_scope(mqic=mqic):
        with pytest.raises(IdentityError) as ei:
            build_merchant_daily_brief_api_payload(
                MagicMock(),
                "store-b",
                MagicMock(),
                mqic=mqic,
            )
        assert ei.value.code == "store_slug_mismatch"


def test_identity_resolved_once_in_daily_brief_scope() -> None:
    mqic = mqic_from_caller_store_slug("once-brief", merchant_id="1")
    with daily_brief_identity_scope(mqic=mqic):
        ensure_daily_brief_mqic(mqic=mqic)
        other = mqic_from_caller_store_slug("once-brief", merchant_id="1")
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


def test_immutability_preserved_under_daily_brief() -> None:
    mqic = mqic_from_caller_store_slug("imm-brief", merchant_id="1")
    with daily_brief_identity_scope(mqic=mqic):
        ensure_daily_brief_mqic(mqic=mqic)
        with pytest.raises(IdentityImmutabilityViolation):
            reject_field_mutation(mqic, "store_slug")


def test_provider_independence_brief_tenant_is_canonical() -> None:
    mqic = mqic_from_caller_store_slug("canonical-brief", merchant_id="1")
    assert mqic.store_slug == "canonical-brief"
    assert mqic.canonical_store_id.startswith("canonical:")


def test_daily_brief_route_has_no_legacy_auth_slug_resolve() -> None:
    src = Path("routes/daily_brief.py").read_text(encoding="utf-8")
    assert "from services.merchant_test_widget_store_v1 import" not in src
    assert "merchant_authenticated_store_slug(" not in src
    assert "bind_mqic_for_daily_brief" in src


def test_main_py_unchanged_by_wp4_identity() -> None:
    src = Path("main.py").read_text(encoding="utf-8")
    assert "daily_brief_consumer_v1" not in src
    assert "bind_mqic_for_daily_brief" not in src
