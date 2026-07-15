# -*- coding: utf-8 -*-
"""Validators for Time Authority / Query Time Context (WP-1)."""
from __future__ import annotations

from services.time_authority.contracts import ClockProvider, QueryTimeContextKind
from services.time_authority.exceptions import (
    InvalidClockProvider,
    MissingQueryTimeContext,
    QueryTimeContextError,
)
from services.time_authority.providers import validate_provider
from services.time_authority.query_context import get_query_time_context


def assert_provider_valid(provider: ClockProvider) -> None:
    validate_provider(provider)


def assert_query_time_context_active() -> None:
    """Fail if no explicit Query Time Context is active."""
    if get_query_time_context() is None:
        raise MissingQueryTimeContext("query_time_context_not_active")


def assert_context_kind(expected: QueryTimeContextKind) -> None:
    ctx = get_query_time_context()
    if ctx is None:
        raise MissingQueryTimeContext("query_time_context_not_active")
    if ctx.kind != expected:
        raise QueryTimeContextError(
            f"context_kind_mismatch:expected={expected.value}:actual={ctx.kind.value}"
        )


def assert_source_id(expected: str) -> None:
    from services.time_authority.authority import authority_source_id

    sid = authority_source_id()
    if sid != expected:
        raise InvalidClockProvider(f"source_id_mismatch:expected={expected}:actual={sid}")
