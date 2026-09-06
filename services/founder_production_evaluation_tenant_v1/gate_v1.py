# -*- coding: utf-8 -*-
"""
Founder Production Evaluation Tenant V1 — server-side gate.

Single production owner:

    is_founder_production_evaluation_tenant(...)

Production evaluation allowlist (count = 1):
    cf_founder_evaluation

NOT production-eligible:
    cf_fe_v1_* fixtures, demo, labs, query params, frontend flags,
    environment-global merchandising enablement.

Test/local merchandising logic may use an explicit test-only flag
(CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE) — never a production request path.
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from services.founder_production_evaluation_tenant_v1.contract_v1 import (
    EVALUATION_FEATURES,
    FEATURE_MERCHANDISING_MISSION_SLICE_V1,
    FIXTURE_EVAL_INTEGRATION_SOURCE,
    FIXTURE_EVAL_PREFIX,
    FOUNDER_EVAL_INTEGRATION_SOURCE,
    FOUNDER_EVAL_STORE_SLUG,
    MERCHANDISING_EVAL_FAMILIES,
    PRODUCTION_EVALUATION_ALLOWLIST,
)

# Explicit test/lab infrastructure only — must never be set on production hosts.
ENV_TEST_ALLOW_MERCHANDISING_SLICE = "CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"


def _truthy(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def normalize_store_slug(store_slug: Any) -> str:
    return str(store_slug or "").strip()[:191]


def is_fixture_evaluation_slug(store_slug: Any) -> bool:
    """Local/test cf_fe_v1_* tenants — logic fixtures, not production evaluation."""
    slug = normalize_store_slug(store_slug)
    return bool(slug.startswith(FIXTURE_EVAL_PREFIX))


def is_founder_production_evaluation_tenant(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
) -> bool:
    """
    True only for the dedicated production founder evaluation tenant.

    Authoritative input: authenticated store context (session-owned Store /
    zid_store_id). Callers must never pass client-supplied store_slug over
    authenticated store identity when both are available — pass ``store=``.

    Production allowlist size: 1 (cf_founder_evaluation).
    No wildcard / prefix matching.
    """
    slug = normalize_store_slug(store_slug)
    src_override = integration_source

    if store is not None:
        # Authenticated Store row wins over any caller-supplied slug.
        slug = normalize_store_slug(
            getattr(store, "zid_store_id", None)
            if not isinstance(store, Mapping)
            else store.get("zid_store_id")
        )
        src = (
            store.get("integration_source")
            if isinstance(store, Mapping)
            else getattr(store, "integration_source", None)
        )
        if src is not None:
            src_override = src

    if slug not in PRODUCTION_EVALUATION_ALLOWLIST:
        return False
    if slug != FOUNDER_EVAL_STORE_SLUG:
        return False

    src_s = str(src_override or "").strip().lower()
    if not src_s:
        # Auth-resolved exact slug alone is acceptable when source unknown.
        return True
    if src_s == FOUNDER_EVAL_INTEGRATION_SOURCE.lower():
        return True
    # Wrong source on reserved slug → deny (incl. fixture source collision).
    if src_s == FIXTURE_EVAL_INTEGRATION_SOURCE.lower():
        return False
    return False


# Repository-equivalent alias (historical name).
is_founder_evaluation_tenant = is_founder_production_evaluation_tenant


def test_merchandising_slice_infrastructure_enabled(
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    """
    Test/local controlled evaluation only.

    Requires explicit CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE — slug prefix
    alone never unlocks production merchandising projection.
    """
    env = environ if environ is not None else os.environ
    return _truthy(env.get(ENV_TEST_ALLOW_MERCHANDISING_SLICE))


def founder_evaluation_feature_enabled(
    feature: str,
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    """
    Candidate feature availability for authenticated store (production path).

    Merchandising slice: founder production tenant ONLY.
    No env-global release unlock. No cf_fe_v1_* production eligibility.
    Unknown features → False (fail closed).
    """
    feat = str(feature or "").strip()
    if feat not in EVALUATION_FEATURES:
        return False

    if feat == FEATURE_MERCHANDISING_MISSION_SLICE_V1:
        return is_founder_production_evaluation_tenant(
            store_slug=store_slug,
            integration_source=integration_source,
            store=store,
        )
    return False


def merchandising_families_allowed_for_store(
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
    environ: Optional[Mapping[str, str]] = None,
) -> bool:
    """
    Whether merchandising COL families may appear in projection.

    Production: cf_founder_evaluation only.
    Test infrastructure: explicit CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE=1
    (fixtures may then exercise merchandising without production eligibility).
    Empty / missing store context: deny (fail closed).
    """
    if founder_evaluation_feature_enabled(
        FEATURE_MERCHANDISING_MISSION_SLICE_V1,
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
        environ=environ,
    ):
        return True
    if test_merchandising_slice_infrastructure_enabled(environ=environ):
        return True
    return False


def filter_merchandising_opportunities(
    opportunities: list,
    *,
    store_slug: Any = None,
    integration_source: Any = None,
    store: Any = None,
    environ: Optional[Mapping[str, str]] = None,
) -> list:
    """Strip merchandising families unless production founder or test infra allows."""
    if merchandising_families_allowed_for_store(
        store_slug=store_slug,
        integration_source=integration_source,
        store=store,
        environ=environ,
    ):
        return list(opportunities or [])
    out = []
    for opp in opportunities or []:
        if not isinstance(opp, Mapping):
            continue
        fam = str(opp.get("family") or "")
        if fam in MERCHANDISING_EVAL_FAMILIES:
            continue
        out.append(opp)
    return out


__all__ = [
    "ENV_TEST_ALLOW_MERCHANDISING_SLICE",
    "filter_merchandising_opportunities",
    "founder_evaluation_feature_enabled",
    "is_fixture_evaluation_slug",
    "is_founder_evaluation_tenant",
    "is_founder_production_evaluation_tenant",
    "merchandising_families_allowed_for_store",
    "normalize_store_slug",
    "test_merchandising_slice_infrastructure_enabled",
]
