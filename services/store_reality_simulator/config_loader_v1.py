# -*- coding: utf-8 -*-
"""Simulation configuration loader — Phase 2 (no execution)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG, assert_demo_store
from services.store_reality_simulator.scenario_registry_v1 import validate_scenario_ids
from services.store_reality_simulator.seed_v1 import normalize_seed


@dataclass
class SimulationConfig:
    store_slug: str
    scenario_ids: list[str]
    seed: int
    start_date: date
    duration_days: int
    scale: float = 1.0
    mode: str = "dry_run"  # dry_run | execute (execute reserved for later phases)
    batch_size: int = 50
    max_events_per_job: int = 500
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat()
        return d


def _parse_date(raw: Any) -> date:
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    s = str(raw or "").strip()
    if not s:
        raise ValueError("start_date_required")
    return date.fromisoformat(s[:10])


def load_simulation_config(raw: Optional[dict[str, Any]]) -> SimulationConfig:
    """Validate and normalize run configuration."""
    body = dict(raw or {})
    store_slug = assert_demo_store(body.get("store_slug", DEMO_STORE_SLUG))
    scenario_ids = validate_scenario_ids(
        list(body.get("scenario_ids") or body.get("scenarios") or [])
    )
    seed = normalize_seed(body.get("seed", 0))
    start_date = _parse_date(body.get("start_date"))
    try:
        duration_days = int(body.get("duration_days") or body.get("days") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration_days_invalid") from exc
    if duration_days < 1:
        raise ValueError("duration_days_must_be_positive")
    if duration_days > 366:
        raise ValueError("duration_days_exceeds_max_366")

    try:
        scale = float(body.get("scale", 1.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("scale_invalid") from exc
    if scale <= 0:
        raise ValueError("scale_must_be_positive")

    mode = str(body.get("mode") or "dry_run").strip().lower()
    if mode not in ("dry_run", "execute"):
        raise ValueError("mode_invalid")

    try:
        batch_size = max(1, min(500, int(body.get("batch_size", 50))))
    except (TypeError, ValueError) as exc:
        raise ValueError("batch_size_invalid") from exc
    try:
        max_events = max(1, min(5000, int(body.get("max_events_per_job", 500))))
    except (TypeError, ValueError) as exc:
        raise ValueError("max_events_per_job_invalid") from exc

    meta = body.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        raise ValueError("metadata_must_be_object")

    return SimulationConfig(
        store_slug=store_slug,
        scenario_ids=scenario_ids,
        seed=seed,
        start_date=start_date,
        duration_days=duration_days,
        scale=scale,
        mode=mode,
        batch_size=batch_size,
        max_events_per_job=max_events,
        metadata=dict(meta or {}),
    )
