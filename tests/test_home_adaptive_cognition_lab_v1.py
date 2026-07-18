# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from services.home_cognitive_router_v1 import clear_cognitive_sessions_v1


def setup_function() -> None:
    clear_cognitive_sessions_v1()


def test_lab_page_ok() -> None:
    client = TestClient(app)
    r = client.get("/dev/adaptive-cognition-lab?fixture=vip")
    assert r.status_code == 200
    assert b"Adaptive Cognition Lab V2" in r.content
    assert b"not_home" in r.content


def test_lab_stability_and_reeval_api() -> None:
    client = TestClient(app)
    started = client.post(
        "/dev/adaptive-cognition-lab/start", json={"fixture": "vip"}
    ).json()
    session = started["session"]
    sid = session["session_id"]
    assert session["selected_path"] == "C"

    tick = client.post(
        "/dev/adaptive-cognition-lab/view-tick", json={"session_id": sid}
    ).json()
    assert tick["ok"] is True
    assert tick["path_unchanged"] is True
    assert tick["selected_path"] == "C"

    forbidden = client.post(
        "/dev/adaptive-cognition-lab/reeval",
        json={"session_id": sid, "trigger": "periodic_poll"},
    ).json()
    assert forbidden["ok"] is False

    reeval = client.post(
        "/dev/adaptive-cognition-lab/reeval",
        json={
            "session_id": sid,
            "trigger": "significant_business_state_transition",
            "fixture": "vip_resolved",
        },
    ).json()
    assert reeval["ok"] is True
    assert reeval["previous_path"] == "C"
    assert reeval["selected_path"] == "A"
