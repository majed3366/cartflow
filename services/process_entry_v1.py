# -*- coding: utf-8 -*-
"""
Explicit process entry (API vs Scheduler). Independent of uvicorn main:app.

CARTFLOW_PROCESS_ENTRY is set by cartflow_api / cartflow_scheduler only.
Wrong role for an entry fails closed.
"""
from __future__ import annotations

import os
from typing import Literal

ENV_PROCESS_ENTRY = "CARTFLOW_PROCESS_ENTRY"
ENV_PROCESS_ROLE = "CARTFLOW_PROCESS_ROLE"

ProcessEntry = Literal["api", "scheduler", "unset"]

_VALID = frozenset({"api", "scheduler"})


class ProcessEntryError(RuntimeError):
    """Entry point and process role do not match."""


def resolve_process_entry() -> ProcessEntry:
    raw = (os.getenv(ENV_PROCESS_ENTRY) or "").strip().lower()
    if not raw:
        return "unset"
    if raw in _VALID:
        return raw  # type: ignore[return-value]
    return "unset"


def configure_api_entry() -> None:
    os.environ[ENV_PROCESS_ENTRY] = "api"
    if not (os.getenv(ENV_PROCESS_ROLE) or "").strip():
        os.environ[ENV_PROCESS_ROLE] = "api"


def configure_scheduler_entry() -> None:
    os.environ[ENV_PROCESS_ENTRY] = "scheduler"
    os.environ[ENV_PROCESS_ROLE] = "scheduler"


def assert_entry_matches_role() -> None:
    entry = resolve_process_entry()
    role = (os.getenv(ENV_PROCESS_ROLE) or "").strip().lower()
    if entry == "api" and role and role != "api":
        raise ProcessEntryError(
            f"API entry requires CARTFLOW_PROCESS_ROLE=api (got {role!r})"
        )
    if entry == "scheduler" and role != "scheduler":
        raise ProcessEntryError(
            f"Scheduler entry requires CARTFLOW_PROCESS_ROLE=scheduler (got {role!r})"
        )


def is_api_process_entry() -> bool:
    return resolve_process_entry() == "api"


def is_scheduler_process_entry() -> bool:
    return resolve_process_entry() == "scheduler"


def reject_scheduler_via_web_entry() -> None:
    """uvicorn / FastAPI must never host the Scheduler process."""
    role = (os.getenv(ENV_PROCESS_ROLE) or "").strip().lower()
    entry = resolve_process_entry()
    if entry == "scheduler":
        raise ProcessEntryError(
            "Scheduler must run via `python -m cartflow_scheduler`, "
            "not uvicorn / cartflow_api / main:app"
        )
    env = (os.getenv("ENV") or "").strip().lower()
    production_like = env in ("production", "prod", "staging", "preview")
    if role == "scheduler" and (entry == "api" or production_like):
        raise ProcessEntryError(
            "Scheduler must run via `python -m cartflow_scheduler`, "
            "not uvicorn / cartflow_api / main:app"
        )
