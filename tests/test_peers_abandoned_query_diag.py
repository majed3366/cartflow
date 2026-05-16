# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from services.peers_abandoned_query_diag import peers_abandoned_explain_diag_enabled


def test_peers_diag_off_without_dual_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", raising=False)
    monkeypatch.delenv("CARTFLOW_OBSERVABILITY_MODE", raising=False)
    assert peers_abandoned_explain_diag_enabled() is False


@pytest.mark.parametrize("val", ["1", "TRUE", "on", "YeS"])
def test_peers_diag_requires_observability_debug_and_flag(
    monkeypatch: pytest.MonkeyPatch,
    val: str,
) -> None:
    monkeypatch.setenv("CARTFLOW_OBSERVABILITY_MODE", "debug")
    monkeypatch.setenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", val)
    assert peers_abandoned_explain_diag_enabled() is True


def test_peers_diag_blocked_in_basic_even_if_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARTFLOW_OBSERVABILITY_MODE", "basic")
    monkeypatch.setenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", "1")
    assert peers_abandoned_explain_diag_enabled() is False


def test_peers_diag_debug_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARTFLOW_OBSERVABILITY_MODE", "debug")
    monkeypatch.setenv("CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG", "0")
    assert peers_abandoned_explain_diag_enabled() is False
