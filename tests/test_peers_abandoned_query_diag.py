# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from services.peers_abandoned_query_diag import peers_abandoned_explain_diag_enabled


def test_peers_diag_env_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", raising=False)
    assert peers_abandoned_explain_diag_enabled() is False


@pytest.mark.parametrize("val", ["1", "TRUE", "on", "YeS"])
def test_peers_diag_env_on(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", val)
    assert peers_abandoned_explain_diag_enabled() is True


def test_peers_diag_env_explicit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", "0")
    assert peers_abandoned_explain_diag_enabled() is False
