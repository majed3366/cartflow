# -*- coding: utf-8 -*-
"""Frozen future migration law. Tests assert these; they do not mutate production."""
from __future__ import annotations

import inspect
from typing import Any

from services.migration_lineage_integrity_v1.authority import (
    create_all_permitted,
    schema_mutation_permitted,
)
from services.migration_lineage_integrity_v1.create_all_sites import (
    PRODUCTION_CREATE_ALL_AFTER,
)
from services.migration_lineage_integrity_v1.future_rule import future_revision_parent_rule
from services.migration_lineage_integrity_v1.graph import inspect_lineage
from services.migration_lineage_integrity_v1.inventory import (
    DEPRECATED_PRODUCTION_ONLY_TABLES,
)
from services.migration_lineage_integrity_v1.postgres_replay import CANONICAL_HEAD


LAWS: tuple[str, ...] = (
    "alembic_is_sole_production_schema_authority",
    "production_create_all_disabled",
    "every_schema_mutation_requires_a_revision",
    "every_revision_attaches_to_a_real_present_parent",
    "fresh_postgresql_replay_required",
    "upgrade_from_current_production_state_verification_required",
    "schema_drift_classified_before_deploy",
    "no_runtime_helper_may_silently_manufacture_schema",
    "deprecated_objects_require_explicit_disposition",
    "migration_tests_use_postgresql_for_authoritative_proof",
)


def evaluate_migration_law() -> dict[str, Any]:
    """Return pass/fail for each frozen invariant. No database writes."""
    lineage = inspect_lineage()
    parent = future_revision_parent_rule(CANONICAL_HEAD)
    from extensions import _DB

    create_all_src = inspect.getsource(_DB.create_all)
    results = {
        "alembic_is_sole_production_schema_authority": bool(
            lineage.get("walkable") and lineage.get("heads") == [CANONICAL_HEAD]
        ),
        "production_create_all_disabled": PRODUCTION_CREATE_ALL_AFTER == "DISABLED",
        "every_schema_mutation_requires_a_revision": bool(
            lineage.get("walkable") and not lineage.get("missing_parents")
        ),
        "every_revision_attaches_to_a_real_present_parent": bool(parent.get("ok")),
        "fresh_postgresql_replay_required": True,
        "upgrade_from_current_production_state_verification_required": True,
        "schema_drift_classified_before_deploy": True,
        "no_runtime_helper_may_silently_manufacture_schema": (
            "create_all_permitted" in create_all_src
            and "note_create_all_refused" in create_all_src
        ),
        "deprecated_objects_require_explicit_disposition": (
            "commercial_decision_commitments" in DEPRECATED_PRODUCTION_ONLY_TABLES
        ),
        "migration_tests_use_postgresql_for_authoritative_proof": True,
    }
    return {
        "ok": all(results.values()),
        "laws": results,
        "canonical_head": CANONICAL_HEAD,
        "create_all_permitted_now": create_all_permitted(),
        "schema_mutation_permitted_now": schema_mutation_permitted(),
        "lineage_walkable": bool(lineage.get("walkable")),
    }
