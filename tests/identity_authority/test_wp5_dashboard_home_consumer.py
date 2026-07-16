# -*- coding: utf-8 -*-
"""INV-002 WP-5 — Dashboard/Home consumes Identity Authority (no independent resolve)."""
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
    dashboard_home_identity_scope,
    ensure_dashboard_home_mqic,
    get_mqic,
    mqic_from_caller_store_slug,
    reject_field_mutation,
    reset_counters,
    resolve_and_bind,
)
from services.identity_authority.contracts import CanonicalStoreIdentity
from services.merchant_home_composition_v1 import (
    build_merchant_home_experience_api_payload,
)
from services.merchant_home_experience_activation_v1 import (
    compose_home_api_payload_from_summary_context,
)


def setup_function() -> None:
    clear_mqic()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    reset_counters()


def test_home_consumes_mqic_store_slug() -> None:
    mqic = mqic_from_caller_store_slug("demo-home-wp5", merchant_id="9")
    with dashboard_home_identity_scope(mqic=mqic):
        with patch(
            "services.merchant_daily_brief_v1.build_merchant_daily_brief_api_payload",
            return_value={
                "ok": True,
                "brief_date": "2026-07-16",
                "store_slug": "demo-home-wp5",
                "items": [],
                "empty": True,
            },
        ), patch(
            "services.knowledge_layer_v1.build_knowledge_report",
            side_effect=ImportError("skip"),
        ):
            payload = build_merchant_home_experience_api_payload(
                MagicMock(),
                mqic.store_slug,
                MagicMock(store_name="متجر"),
                mqic=mqic,
            )
    assert payload["store_slug"] == "demo-home-wp5"
    assert payload.get("identity_authority_v1", {}).get("authority_consumer") == (
        "dashboard_home"
    )
    assert get_mqic() is None


def test_home_caller_slug_sealed_via_authority() -> None:
    with patch(
        "services.merchant_daily_brief_v1.build_merchant_daily_brief_api_payload",
        return_value={
            "ok": True,
            "brief_date": "2026-07-16",
            "store_slug": "caller-home-wp5",
            "items": [],
            "empty": True,
        },
    ), patch(
        "services.knowledge_layer_v1.build_knowledge_report",
        side_effect=ImportError("skip"),
    ):
        payload = build_merchant_home_experience_api_payload(
            MagicMock(),
            "caller-home-wp5",
            MagicMock(store_name="متجر"),
        )
    assert payload["store_slug"] == "caller-home-wp5"
    assert get_mqic() is None


def test_home_slug_mismatch_fail_closed() -> None:
    mqic = mqic_from_caller_store_slug("store-a", merchant_id="1")
    with dashboard_home_identity_scope(mqic=mqic):
        with pytest.raises(IdentityError) as ei:
            build_merchant_home_experience_api_payload(
                MagicMock(),
                "store-b",
                MagicMock(),
                mqic=mqic,
            )
        assert ei.value.code == "store_slug_mismatch"


def test_home_brief_knowledge_share_same_mqic() -> None:
    """ICT-14 class: nested Brief + Knowledge see one bound MQIC."""
    mqic = mqic_from_caller_store_slug("shared-surface", merchant_id="1")
    seen: dict[str, str] = {}

    def _brief(db_session, store_slug, dash_store, *, mqic=None, **kwargs):
        seen["brief"] = mqic.store_slug if mqic is not None else store_slug
        return {
            "ok": True,
            "brief_date": "2026-07-16",
            "store_slug": seen["brief"],
            "items": [],
            "empty": True,
        }

    def _kl(db_session, store_slug, *args, mqic=None, **kwargs):
        seen["kl"] = mqic.store_slug if mqic is not None else store_slug
        raise ImportError("stop after identity capture")

    with patch(
        "services.merchant_daily_brief_v1.build_merchant_daily_brief_api_payload",
        side_effect=_brief,
    ), patch(
        "services.knowledge_layer_v1.build_knowledge_report",
        side_effect=_kl,
    ):
        payload = build_merchant_home_experience_api_payload(
            MagicMock(),
            mqic.store_slug,
            MagicMock(store_name="x"),
            mqic=mqic,
        )
    assert payload["store_slug"] == "shared-surface"
    assert seen["brief"] == "shared-surface"
    assert seen["kl"] == "shared-surface"


def test_identity_resolved_once_in_home_scope() -> None:
    mqic = mqic_from_caller_store_slug("once-home", merchant_id="1")
    with dashboard_home_identity_scope(mqic=mqic):
        ensure_dashboard_home_mqic(mqic=mqic)
        other = mqic_from_caller_store_slug("once-home", merchant_id="1")
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


def test_immutability_preserved_under_home() -> None:
    mqic = mqic_from_caller_store_slug("imm-home", merchant_id="1")
    with dashboard_home_identity_scope(mqic=mqic):
        ensure_dashboard_home_mqic(mqic=mqic)
        with pytest.raises(IdentityImmutabilityViolation):
            reject_field_mutation(mqic, "store_slug")


def test_activation_attach_seals_slug_via_authority() -> None:
    home = compose_home_api_payload_from_summary_context(
        {"merchant_ar_date_header": "اليوم"},
        store_slug="snap-home-wp5",
    )
    assert home["store_slug"] == "snap-home-wp5"
    assert home["identity_authority_v1"]["authority_consumer"] == "dashboard_home"


def test_main_py_composition_only_for_wp5() -> None:
    src = Path("main.py").read_text(encoding="utf-8")
    assert "bind_mqic_for_dashboard_home" not in src
    assert "resolve_mqic_from_session" not in src
    assert "cookies=cookies" in src
    # Home builder owns bind; main only wires cookies.
    assert "build_merchant_home_experience_api_payload" in src
