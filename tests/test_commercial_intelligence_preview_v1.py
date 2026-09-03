# -*- coding: utf-8 -*-
"""
Tests: Commercial Intelligence Preview V1 — controlled production preview gate.

Failure tests:
1. preview flag absent → 404 / normal production untouched
2. preview flag off → flag_off response
3. truth boundary — no production truth leak
4. preview API json shape when enabled
5. simulation provenance on every mission
"""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient


# ── helpers ──────────────────────────────────────────────────────────────────

def _app():
    from main import app  # noqa: PLC0415
    return app


def _client_flag_off() -> TestClient:
    """Client with preview flag explicitly OFF (default)."""
    os.environ.pop("CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW", None)
    return TestClient(_app(), raise_server_exceptions=True)


def _client_flag_on() -> TestClient:
    """Client with preview flag ON."""
    os.environ["CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW"] = "1"
    return TestClient(_app(), raise_server_exceptions=True)


def _teardown():
    os.environ.pop("CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW", None)


# ── 1. flag absent → 404, production routes unaffected ───────────────────────

def test_flag_absent_preview_returns_404():
    client = _client_flag_off()
    r = client.get("/preview/commercial-intelligence")
    _teardown()
    assert r.status_code == 404
    body = r.json()
    assert body["reason"] == "flag_off"
    assert body["flag_enabled"] is False


def test_flag_absent_api_returns_404():
    client = _client_flag_off()
    r = client.get("/preview/commercial-intelligence/api")
    _teardown()
    assert r.status_code == 404


def test_flag_absent_production_dashboard_unaffected():
    """Normal /dashboard must remain healthy regardless of preview state."""
    client = _client_flag_off()
    r = client.get("/dashboard", follow_redirects=True)
    _teardown()
    assert r.status_code == 200
    # Production identity headers intact
    text = r.text
    assert "cf2-root" in text or "CartFlow" in text


def test_flag_absent_health_unaffected():
    client = _client_flag_off()
    r = client.get("/health")
    _teardown()
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True


# ── 2. flag ON → preview available ────────────────────────────────────────────

def test_flag_on_preview_page_200():
    client = _client_flag_on()
    r = client.get("/preview/commercial-intelligence")
    _teardown()
    assert r.status_code == 200
    assert r.headers.get("X-CartFlow-Preview") == "commercial-intelligence-v1"
    assert r.headers.get("X-CartFlow-Truth-Source") == "SIMULATION_TRUTH"
    assert r.headers.get("X-CartFlow-Production-Home") == "false"


def test_flag_on_preview_page_contains_simulation_banner():
    client = _client_flag_on()
    r = client.get("/preview/commercial-intelligence")
    _teardown()
    assert "SIMULATION_TRUTH" in r.text


def test_flag_on_api_200():
    client = _client_flag_on()
    r = client.get("/preview/commercial-intelligence/api")
    _teardown()
    assert r.status_code == 200
    data = r.json()
    assert data.get("truth_source") == "SIMULATION_TRUTH"
    assert data.get("production_truth_present") is False
    assert data.get("preview_version") == "commercial_intelligence_preview_v1"


# ── 3. truth boundary — simulation provenance on all missions ─────────────────

def test_truth_boundary_all_missions_labeled_simulation():
    from services.commercial_intelligence_preview_v1 import (  # noqa: PLC0415
        build_preview_payload_v1,
        verify_no_production_truth_leak,
    )
    payload = build_preview_payload_v1()
    violations = verify_no_production_truth_leak(payload)
    assert violations == [], f"Truth boundary violations: {violations}"


def test_truth_source_top_level():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    assert payload["truth_source"] == "SIMULATION_TRUTH"
    assert payload["production_truth_present"] is False


def test_workspace_missions_simulation_labeled():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    ws_missions = payload.get("workspace", {}).get("cdi_missions") or []
    assert ws_missions, "workspace cdi_missions must be non-empty"
    for m in ws_missions:
        assert m.get("truth_source") == "SIMULATION_TRUTH", f"Mission missing SIMULATION_TRUTH: {m.get('scenario_id')}"
        assert m.get("simulation_only") is True


# ── 4. payload structure gates ────────────────────────────────────────────────

def test_payload_home_primary_secondary_present():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    home = payload.get("home") or {}
    primary = home.get("primary_mission")
    assert primary is not None, "primary_mission must exist"
    assert primary.get("scenario_id") == "D_discount_destroys_value"
    secondary = home.get("secondary_opportunities") or []
    assert len(secondary) <= 2
    sec_ids = {s["scenario_id"] for s in secondary}
    assert "B_high_interest_low_conversion" in sec_ids
    assert "A_discovery" in sec_ids


def test_payload_all_cdi_families_in_workspace():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    ws = payload["workspace"]["cdi_missions"]
    sids = {m["scenario_id"] for m in ws}
    # CDI families
    assert "D_discount_destroys_value" in sids
    assert "A_discovery" in sids
    assert "F_channel_quality" in sids
    # CDL families
    assert "E_bundle_cross_sell" in sids
    assert "B_high_interest_low_conversion" in sids


def test_payload_workspace_contracts_present():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    for m in payload["workspace"]["cdi_missions"]:
        if m.get("cdi_refined") or m.get("cdl_refined"):
            assert m.get("decision_contract_ar"), f"Missing decision_contract_ar for {m.get('scenario_id')}"
            assert m.get("falsifier_ar"), f"Missing falsifier_ar for {m.get('scenario_id')}"


# ── 5. laws still pass through preview ───────────────────────────────────────

def test_no_recommendation_without_evidence_law():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    assert payload.get("laws", {}).get("NO_RECOMMENDATION_WITHOUT_EVIDENCE") == "PASS"


def test_no_revenue_claim_without_measurement_law():
    from services.commercial_intelligence_preview_v1 import build_preview_payload_v1  # noqa: PLC0415
    payload = build_preview_payload_v1()
    assert payload.get("laws", {}).get("NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT") == "PASS"


# ── 6. unauthorized / flag values edge cases ──────────────────────────────────

@pytest.mark.parametrize("val", ["0", "false", "off", "no", "", "random"])
def test_flag_falsy_values_denied(val: str):
    os.environ["CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW"] = val
    from services.commercial_intelligence_preview_v1 import commercial_intelligence_preview_enabled  # noqa: PLC0415
    result = commercial_intelligence_preview_enabled()
    _teardown()
    assert result is False


# ── 7. flag on → production routes still healthy ──────────────────────────────

def test_flag_on_health_still_ok():
    client = _client_flag_on()
    r = client.get("/health")
    _teardown()
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_flag_on_runtime_identity_still_ok():
    client = _client_flag_on()
    r = client.get("/dev/merchant-runtime-identity")
    _teardown()
    assert r.status_code == 200
    data = r.json()
    assert data.get("canonical") is True
    assert data.get("renderer_id") == "merchant_ui_v2"
