# -*- coding: utf-8 -*-
"""
INV-002 Phase 5 — Reality Attach contract tests (ICT-20 / ICT-21 class).

Attach binds SimulationClock → Time Authority and run canonical → MQIC ATTACH.
Attach is not an authority. Consumers remain unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.identity_authority import (
    AUTHORITY_SOURCE_ID,
    AttachState,
    CanonicalStoreIdentity,
    DualResolveViolation,
    IdentityError,
    LifecycleState,
    ResolutionPath,
    SessionMembershipSnapshot,
    attach_diagnostics,
    clear_mqic,
    clear_reality_attach,
    get_active_attach,
    get_mqic,
    peek_attach_resolve_inputs,
    reality_attach_declaration_scope,
    reality_attach_scope,
    reset_counters,
    resolve_and_bind,
    build_session_resolve_input,
)
from services.identity_authority.reality_attach_v1 import build_attach_declaration
from services.store_reality_simulator.clock_v1 import SimulationClock
from services.time_authority import (
    authority_now,
    authority_source_id,
    clear_query_time_context,
    get_query_time_context,
)


DEMO = CanonicalStoreIdentity(
    canonical_store_id="store_demo",
    store_slug="demo",
    store_display_name="Demo Store",
)
SIGNUP = CanonicalStoreIdentity(
    canonical_store_id="store_signup",
    store_slug="signup-store",
    store_display_name="Signup Store",
)
STORES = {
    DEMO.canonical_store_id: DEMO,
    SIGNUP.canonical_store_id: SIGNUP,
}
MEMBERSHIP = frozenset({DEMO.canonical_store_id, SIGNUP.canonical_store_id})
MAY_END = datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)
RUN_ID = "srs_phase5_attach_1"


def setup_function() -> None:
    clear_mqic()
    clear_reality_attach()
    clear_query_time_context()
    reset_counters()


def teardown_function() -> None:
    clear_mqic()
    clear_reality_attach()
    clear_query_time_context()
    reset_counters()


def _membership(*, primary: CanonicalStoreIdentity = SIGNUP) -> SessionMembershipSnapshot:
    return SessionMembershipSnapshot(
        merchant_id="m_attach_1",
        primary_store_id=primary.canonical_store_id,
        membership_store_ids=MEMBERSHIP,
        stores_by_id=STORES,
    )


# --- ICT-20: Attach sets MQIC to run’s canonical store ---


def test_ict20_attach_sets_mqic_to_run_canonical() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ) as handle:
        mqic = get_mqic()
        assert mqic is not None
        assert mqic.resolution_path == ResolutionPath.ATTACH
        assert mqic.canonical_store_id == DEMO.canonical_store_id
        assert mqic.store_slug == DEMO.store_slug
        assert mqic.simulation_run_id == RUN_ID
        assert handle.attach_state == AttachState.ATTACHED
        assert handle.lifecycle_state == LifecycleState.ACTIVE


def test_attach_binds_time_authority_simulation_clock() -> None:
    snap = _membership()
    clock = SimulationClock(MAY_END)
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_clock=clock,
    ):
        qtc = get_query_time_context()
        assert qtc is not None
        assert qtc.mode.value == "simulation"
        assert qtc.simulation_run_id == RUN_ID
        assert authority_source_id() == "simulation"
        assert authority_now() == MAY_END


def test_attach_removed_cleanly() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        assert get_mqic() is not None
        assert get_query_time_context() is not None
        assert get_active_attach() is not None

    assert get_mqic() is None
    assert get_query_time_context() is None
    assert get_active_attach() is None
    assert peek_attach_resolve_inputs() is None
    diag = attach_diagnostics()
    assert diag["attach_state"] == AttachState.DETACHED.value


def test_mqic_authority_owner_unchanged() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        mqic = get_mqic()
        assert mqic is not None
        mqic.assert_authority_owned()
        assert mqic.identity_provenance.get("authority_source") == AUTHORITY_SOURCE_ID
        diag = attach_diagnostics()
        assert diag["is_authority"] is False
        assert diag["authority_health"]["identity_authority"] == AUTHORITY_SOURCE_ID
        assert diag["authority_health"]["time_authority"] == "platform_time_authority"


def test_time_authority_remains_sole_clock_source() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        # Attach must not invent a parallel clock API — only Authority now().
        assert authority_now() == MAY_END
        assert get_query_time_context() is not None


# --- ICT-21: Unauthorized attach rejected ---


def test_ict21_unauthorized_attach_rejected() -> None:
    snap = SessionMembershipSnapshot(
        merchant_id="m_attach_1",
        primary_store_id=SIGNUP.canonical_store_id,
        membership_store_ids=frozenset({SIGNUP.canonical_store_id}),
        stores_by_id={SIGNUP.canonical_store_id: SIGNUP},
    )
    with pytest.raises(IdentityError) as exc:
        with reality_attach_scope(
            simulation_run_id=RUN_ID,
            simulation_canonical_store_id=DEMO.canonical_store_id,
            store_slug=DEMO.store_slug,
            membership=snap,
            simulation_start=MAY_END,
        ):
            pass
    assert exc.value.code == "attach_membership_denied"
    assert get_mqic() is None
    assert get_active_attach() is None


def test_fail_closed_slug_mismatch() -> None:
    snap = _membership()
    with pytest.raises(IdentityError) as exc:
        with reality_attach_scope(
            simulation_run_id=RUN_ID,
            simulation_canonical_store_id=DEMO.canonical_store_id,
            store_slug="wrong-slug",
            membership=snap,
            simulation_start=MAY_END,
        ):
            pass
    assert exc.value.code == "attach_slug_mismatch"


def test_fail_closed_dual_attach() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        with pytest.raises(IdentityError) as exc:
            with reality_attach_scope(
                simulation_run_id="srs_other",
                simulation_canonical_store_id=DEMO.canonical_store_id,
                store_slug=DEMO.store_slug,
                membership=snap,
                simulation_start=MAY_END,
            ):
                pass
        assert exc.value.code == "attach_already_active"


def test_fail_closed_second_mqic_bind() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        with pytest.raises(DualResolveViolation):
            resolve_and_bind(
                build_session_resolve_input(snap)
            )


# --- Phase 3 merge + consumers unchanged ---


def test_phase3_declaration_merges_attach_inputs() -> None:
    snap = _membership()
    declaration = build_attach_declaration(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        simulation_start=MAY_END,
    )
    with reality_attach_declaration_scope(declaration):
        inp = build_session_resolve_input(snap)
        assert inp.simulation_run_id == RUN_ID
        assert inp.simulation_canonical_store_id == DEMO.canonical_store_id
        mqic = resolve_and_bind(inp)
        assert mqic.resolution_path == ResolutionPath.ATTACH
        assert mqic.store_slug == DEMO.store_slug


def test_consumers_unchanged_use_attached_mqic() -> None:
    """Home/Knowledge/Brief/Timeline consume MQIC only — no attach-specific APIs."""
    from services.identity_authority.knowledge_consumer_v1 import ensure_knowledge_mqic
    from services.identity_authority.daily_brief_consumer_v1 import ensure_daily_brief_mqic
    from services.identity_authority.dashboard_home_consumer_v1 import (
        ensure_dashboard_home_mqic,
    )
    from services.identity_authority.timeline_consumer_v1 import ensure_timeline_mqic

    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
    ):
        k = ensure_knowledge_mqic()
        b = ensure_daily_brief_mqic()
        h = ensure_dashboard_home_mqic()
        t = ensure_timeline_mqic()
        assert k.store_slug == b.store_slug == h.store_slug == t.store_slug == "demo"
        assert k.simulation_run_id == RUN_ID
        assert k is get_mqic()


def test_deterministic_replay_preserved() -> None:
    snap = _membership()
    results = []
    for _ in range(2):
        clear_mqic()
        clear_reality_attach()
        clear_query_time_context()
        with reality_attach_scope(
            simulation_run_id=RUN_ID,
            simulation_canonical_store_id=DEMO.canonical_store_id,
            store_slug=DEMO.store_slug,
            membership=snap,
            simulation_start=MAY_END,
            correlation_id="corr_replay_fixed",
        ):
            mqic = get_mqic()
            qtc = get_query_time_context()
            assert mqic is not None and qtc is not None
            results.append(
                (
                    mqic.store_slug,
                    mqic.canonical_store_id,
                    mqic.simulation_run_id,
                    mqic.resolution_path,
                    authority_now(),
                    qtc.simulation_run_id,
                )
            )
    assert results[0] == results[1]


def test_attach_provenance_exposed() -> None:
    snap = _membership()
    with reality_attach_scope(
        simulation_run_id=RUN_ID,
        simulation_canonical_store_id=DEMO.canonical_store_id,
        store_slug=DEMO.store_slug,
        membership=snap,
        simulation_start=MAY_END,
        replay_id="replay_p5",
    ):
        diag = attach_diagnostics()
        prov = diag["simulation_provenance"]
        assert prov["simulation_run_id"] == RUN_ID
        assert prov["simulation_time_source"] == "simulation"
        assert prov["authority_source_identity"] == AUTHORITY_SOURCE_ID
        assert prov["authority_source_time"] == "platform_time_authority"
        assert prov["replay_id"] == "replay_p5"
        assert diag["lifecycle_diagnostics"]["attach_state"] == AttachState.ATTACHED.value


def test_production_path_unaffected_without_attach() -> None:
    """Without attach, Phase 3 primary resolve remains production-shaped."""
    snap = _membership()
    inp = build_session_resolve_input(snap)
    assert inp.simulation_run_id == ""
    assert inp.simulation_canonical_store_id == ""
    mqic = resolve_and_bind(inp)
    assert mqic.resolution_path == ResolutionPath.PRIMARY
    assert mqic.store_slug == SIGNUP.store_slug
    assert mqic.simulation_run_id == ""
