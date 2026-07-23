# -*- coding: utf-8 -*-
"""WP-ET-10.5 — Executive Knowledge Preview validation surface."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from services.evidence_truth import (
    FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW,
    build_executive_knowledge_preview_v1,
    compose_evidence_bundle_v1,
    compose_knowledge_record_v1,
    executive_knowledge_preview_enabled,
    list_consumer_eligibility_v1,
    reset_canonical_observation_store_v1,
    reset_evidence_accounting_ledger_v1,
    reset_evidence_bundle_store_v1,
    reset_evidence_truth_store_v1,
    reset_knowledge_record_store_v1,
    shadow_dual_write_evidence_v1,
)
from services.evidence_truth.knowledge_model_v1 import KNOWLEDGE_TYPE_FAMILY_PRESENCE
from services.evidence_truth.observation_types_v1 import RAW_KIND_PURCHASE


def setup_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()


def teardown_function() -> None:
    reset_evidence_accounting_ledger_v1()
    reset_canonical_observation_store_v1()
    reset_evidence_truth_store_v1()
    reset_evidence_bundle_store_v1()
    reset_knowledge_record_store_v1()


def test_preview_flag_default_off():
    assert executive_knowledge_preview_enabled(environ={}) is False
    payload = build_executive_knowledge_preview_v1(environ={})
    assert payload["flag_enabled"] is False
    assert payload["ok"] is False
    assert payload["reason"] == "flag_off"
    assert payload["production_home"] is False
    assert payload["read_only"] is True


def test_preview_empty_knowledge_honest():
    payload = build_executive_knowledge_preview_v1(
        environ={FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW: "1"}
    )
    assert payload["flag_enabled"] is True
    assert payload["ok"] is True
    assert payload["empty"] is True
    assert payload["honesty"]["status"] == "empty_knowledge"
    assert "nothing to say" in payload["honesty"]["message"].lower()
    assert payload["records"] == []
    assert payload["findings_enabled"] is False
    assert payload["guidance_enabled"] is False


def test_preview_renders_real_knowledge_only():
    shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload={
            "store_slug": "prev",
            "recovery_key": "prev:1",
            "purchase_completed": True,
        },
        force=True,
    )
    compose_evidence_bundle_v1(
        store_slug="prev", persist=True, environ={}, provenance="synthetic"
    )
    compose_knowledge_record_v1(
        store_slug="prev",
        knowledge_type=KNOWLEDGE_TYPE_FAMILY_PRESENCE,
        persist=True,
        environ={},
        provenance="synthetic",
    )
    payload = build_executive_knowledge_preview_v1(
        store_slug="prev",
        environ={FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW: "1"},
    )
    assert payload["empty"] is False
    assert payload["record_count"] >= 1
    assert payload["input_authority"] == "shadow_knowledge_only"
    assert "evidence_bundle" in payload["forbidden_inputs"]
    assert "evidence_truth" in payload["forbidden_inputs"]
    rec = payload["records"][0]
    assert rec["store_slug"] == "prev"
    assert rec["what_cartflow_knows"]
    assert rec.get("composition_notes", {}).get("findings") is False
    assert rec.get("composition_notes", {}).get("guidance") is False
    assert "sections" in payload
    assert "what_cartflow_currently_knows" in payload["sections"]
    assert "stable_patterns" in payload["sections"]
    assert "insufficient_evidence" in payload["sections"]


def test_preview_module_does_not_import_upstream_truth():
    src = Path(
        "services/evidence_truth/executive_knowledge_preview_v1.py"
    ).read_text(encoding="utf-8")
    for banned in (
        "get_evidence_truth_store",
        "get_canonical_observation_store",
        "get_evidence_bundle_store",
        "shadow_dual_write",
        "maybe_publish_",
    ):
        assert banned not in src


def test_consumer_eligibility_allows_preview_not_home():
    rows = list_consumer_eligibility_v1()
    kn = [r for r in rows if "KnowledgeRecordV1" in r.artifact]
    assert kn
    assert "executive_knowledge_preview" in kn[0].permitted_consumers
    assert "home_daily_brief" in kn[0].prohibited_consumers
    assert "business_findings_engine" in kn[0].prohibited_consumers


def test_http_routes_flag_off_and_on():
    from main import app

    client = TestClient(app)
    off = client.get("/preview/executive-knowledge/api")
    assert off.status_code == 404
    assert off.json().get("flag_enabled") is False

    on = client.get(
        "/preview/executive-knowledge/api",
        headers={},
    )
    # Still OFF unless env set — TestClient uses process env
    # Enable via monkeypatch of os.environ for this call through builder path already tested.
    # Route uses process environ: set temporarily.
    import os

    prev = os.environ.get(FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW)
    try:
        os.environ[FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW] = "1"
        page = client.get("/preview/executive-knowledge")
        assert page.status_code == 200
        assert "Validation surface" in page.text
        api = client.get("/preview/executive-knowledge/api")
        assert api.status_code == 200
        body = api.json()
        assert body["flag_enabled"] is True
        assert body["production_home"] is False
        assert body["read_only"] is True
    finally:
        if prev is None:
            os.environ.pop(FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW, None)
        else:
            os.environ[FLAG_EXECUTIVE_KNOWLEDGE_PREVIEW] = prev
