# -*- coding: utf-8 -*-
"""Versioned decision / baseline snapshot JSON contracts (CDC V1)."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, MutableMapping, Optional

from services.commercial_decision_commitment_v1.contract_v1 import (
    BASELINE_SNAPSHOT_SCHEMA,
    DECISION_SNAPSHOT_SCHEMA,
    SIGNAL_COUNTS_MAX_KEYS,
    SNAPSHOT_MAX_BYTES,
)

_METRIC_KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{0,127}$")

_DECISION_ALLOWED = frozenset(
    {
        "schema_version",
        "opportunity_key",
        "opportunity_family",
        "opportunity_reason",
        "truth_class",
        "action_code",
        "proposed_metric_key",
        "signal_counts",
        "accepted_at",
    }
)

_BASELINE_ALLOWED = frozenset(
    {
        "schema_version",
        "metric_key",
        "metric_value",
        "metric_unit",
        "signal_counts",
        "opportunity_key",
        "truth_class_at_start",
        "window_days",
        "started_at",
    }
)


class SnapshotContractError(ValueError):
    """Invalid snapshot schema or payload."""


def validate_metric_key(metric_key: str) -> str:
    key = str(metric_key or "").strip()
    if not key or not _METRIC_KEY_RE.match(key):
        raise SnapshotContractError("invalid_metric_key")
    return key


def _bound_signal_counts(raw: Any) -> dict[str, float]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise SnapshotContractError("signal_counts_not_object")
    out: dict[str, float] = {}
    for i, (k, v) in enumerate(raw.items()):
        if i >= SIGNAL_COUNTS_MAX_KEYS * 2:
            # scan a bit more to skip non-numeric labels like top_reason
            break
        if len(out) >= SIGNAL_COUNTS_MAX_KEYS:
            break
        sk = str(k).strip()[:64]
        if not sk:
            continue
        try:
            out[sk] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _assert_size(payload: Mapping[str, Any]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(blob.encode("utf-8")) > SNAPSHOT_MAX_BYTES:
        raise SnapshotContractError("snapshot_too_large")
    return blob


def build_decision_snapshot(
    *,
    opportunity_key: str,
    opportunity_family: str,
    opportunity_reason: str,
    truth_class: str,
    accepted_at: str,
    action_code: str = "",
    proposed_metric_key: Optional[str] = None,
    signal_counts: Optional[Mapping[str, Any]] = None,
) -> str:
    body: dict[str, Any] = {
        "schema_version": DECISION_SNAPSHOT_SCHEMA,
        "opportunity_key": str(opportunity_key)[:255],
        "opportunity_family": str(opportunity_family)[:64],
        "opportunity_reason": str(opportunity_reason)[:128],
        "truth_class": str(truth_class)[:64],
        "accepted_at": str(accepted_at)[:64],
    }
    if action_code:
        body["action_code"] = str(action_code)[:64]
    if proposed_metric_key:
        body["proposed_metric_key"] = validate_metric_key(proposed_metric_key)
    counts = _bound_signal_counts(signal_counts)
    if counts:
        body["signal_counts"] = counts
    return _assert_size(body)


def build_baseline_snapshot(
    *,
    opportunity_key: str,
    metric_key: str,
    started_at: str,
    window_days: int,
    truth_class_at_start: str = "",
    metric_value: Optional[float] = None,
    metric_unit: str = "",
    signal_counts: Optional[Mapping[str, Any]] = None,
) -> str:
    mk = validate_metric_key(metric_key)
    body: dict[str, Any] = {
        "schema_version": BASELINE_SNAPSHOT_SCHEMA,
        "opportunity_key": str(opportunity_key)[:255],
        "metric_key": mk,
        "started_at": str(started_at)[:64],
        "window_days": int(window_days),
    }
    if truth_class_at_start:
        body["truth_class_at_start"] = str(truth_class_at_start)[:64]
    if metric_value is not None:
        body["metric_value"] = float(metric_value)
    if metric_unit:
        body["metric_unit"] = str(metric_unit)[:32]
    counts = _bound_signal_counts(signal_counts)
    if counts:
        body["signal_counts"] = counts
    return _assert_size(body)


def parse_and_validate_decision_snapshot(raw: str | Mapping[str, Any]) -> dict[str, Any]:
    data = _load(raw)
    if data.get("schema_version") != DECISION_SNAPSHOT_SCHEMA:
        raise SnapshotContractError("invalid_decision_schema_version")
    unknown = set(data) - _DECISION_ALLOWED
    if unknown:
        raise SnapshotContractError("decision_snapshot_unknown_keys")
    _assert_size(data)
    return data


def parse_and_validate_baseline_snapshot(raw: str | Mapping[str, Any]) -> dict[str, Any]:
    data = _load(raw)
    if data.get("schema_version") != BASELINE_SNAPSHOT_SCHEMA:
        raise SnapshotContractError("invalid_baseline_schema_version")
    unknown = set(data) - _BASELINE_ALLOWED
    if unknown:
        raise SnapshotContractError("baseline_snapshot_unknown_keys")
    validate_metric_key(str(data.get("metric_key") or ""))
    _assert_size(data)
    return data


def _load(raw: str | Mapping[str, Any]) -> MutableMapping[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        data = json.loads(str(raw or "{}"))
    except json.JSONDecodeError as exc:
        raise SnapshotContractError("snapshot_json_invalid") from exc
    if not isinstance(data, dict):
        raise SnapshotContractError("snapshot_not_object")
    return data


__all__ = [
    "SnapshotContractError",
    "build_baseline_snapshot",
    "build_decision_snapshot",
    "parse_and_validate_baseline_snapshot",
    "parse_and_validate_decision_snapshot",
    "validate_metric_key",
]
