# -*- coding: utf-8 -*-
"""Schema inventory + production-vs-fresh classification. Read-only."""
from __future__ import annotations

from typing import Any

from sqlalchemy import inspect

# Tables Alembic create_table revisions own (plus foundation stubs).
ALEMBIC_CREATED_TABLES: frozenset[str] = frozenset(
    {
        "business_findings",
        "cart_line_snapshots",
        "cart_recovery_logs",
        "commerce_intelligence_syntheses",
        "commercial_guidance_records",
        "dashboard_snapshots",
        "dashboard_snapshots_archive",
        "evidence_confidence_evaluations",
        "evidence_truth_materialization_runs",
        "evidence_truth_shadow_artifacts",
        "guidance_eligibility_evaluations",
        "guidance_routes",
        "knowledge_statements",
        "merchant_presentations",
        "order_economic_facts",
        "product_catalog_entries",
        "product_evidence_bundles",
        "product_evidence_items",
        "product_hesitation_mappings",
        "product_metric_values",
        "product_purchase_mappings",
        "product_signal_events",
        "product_trend_values",
        "simulation_event_ledger",
        "simulation_row_index",
        "simulation_run_archives",
        "simulation_runs",
        "surface_compositions",
    }
)

# ALTER/index targets that Alembic never CREATE TABLEd. Owned by create_all.
ALEMBIC_ALTER_ONLY_TABLES: frozenset[str] = frozenset(
    {
        "stores",
        "abandoned_carts",
        "recovery_schedules",
    }
)

# Model tables with no Alembic create_table. Production has them via create_all.
CREATE_ALL_OWNED_TABLES: frozenset[str] = frozenset(
    {
        "store_identity_aliases",
        "merchant_users",
        "merchant_subscription_audit_logs",
        "merchant_password_reset_tokens",
        "message_logs",
        "objection_tracks",
        "abandonment_reason_logs",
        "cart_recovery_reasons",
        "recovery_schedules",
        "merchant_cart_lifecycle_archives",
        "whatsapp_delivery_truth",
        "provider_retry_ledger",
        "recovery_truth_timeline_events",
        "recovery_events",
        "merchant_followup_actions",
        "lifecycle_closure_records",
        "purchase_truth_records",
        "operational_control_snapshots",
        "db_ready_operational_snapshots",
        "product_exposure_events",
        "product_exposure_daily_facts",
        "movement_snapshots",
        "diagnostic_snapshots",
        "evidence_gaps",
        "landing_page_events_v1",
        "stores",
        "abandoned_carts",
        "recovery_schedules",
        "commercial_decision_commitments",
    }
)

FOCUS_TABLES: tuple[str, ...] = (
    "stores",
    "store_identity_aliases",
    "purchase_truth_records",
    "order_economic_facts",
    "product_catalog_entries",
    "product_purchase_mappings",
    "product_hesitation_mappings",
    "cart_line_snapshots",
    "product_signal_events",
    "product_metric_values",
    "product_trend_values",
    "commerce_intelligence_syntheses",
    "commercial_guidance_records",
    "business_findings",
)


def snapshot_schema(engine: Any) -> dict[str, Any]:
    insp = inspect(engine)
    tables: dict[str, Any] = {}
    for name in insp.get_table_names():
        cols = []
        for col in insp.get_columns(name):
            cols.append(
                {
                    "name": col["name"],
                    "type": str(col.get("type") or ""),
                    "nullable": bool(col.get("nullable", True)),
                    "default": str(col.get("default")) if col.get("default") is not None else None,
                }
            )
        pk = list((insp.get_pk_constraint(name) or {}).get("constrained_columns") or [])
        uniques = []
        for uq in insp.get_unique_constraints(name) or []:
            uniques.append(
                {
                    "name": uq.get("name"),
                    "columns": list(uq.get("column_names") or []),
                }
            )
        fks = []
        for fk in insp.get_foreign_keys(name) or []:
            fks.append(
                {
                    "name": fk.get("name"),
                    "columns": list(fk.get("constrained_columns") or []),
                    "referred_table": fk.get("referred_table"),
                    "referred_columns": list(fk.get("referred_columns") or []),
                }
            )
        indexes = []
        for ix in insp.get_indexes(name) or []:
            indexes.append(
                {
                    "name": ix.get("name"),
                    "columns": list(ix.get("column_names") or []),
                    "unique": bool(ix.get("unique")),
                }
            )
        tables[name] = {
            "columns": cols,
            "pk": pk,
            "uniques": uniques,
            "foreign_keys": fks,
            "indexes": indexes,
        }
    return {"tables": tables, "table_names": sorted(tables)}


def _col_map(table_snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["name"]: c for c in table_snap.get("columns") or []}


def classify_table_presence(
    *,
    fresh_names: set[str],
    production_names: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in sorted(fresh_names | production_names):
        in_fresh = name in fresh_names
        in_prod = name in production_names
        if name == "alembic_version":
            cls = "MATCH"
            owner = "alembic"
        elif in_fresh and in_prod:
            cls = "MATCH"
            owner = "alembic" if name in ALEMBIC_CREATED_TABLES else "shared"
        elif in_prod and not in_fresh and name in CREATE_ALL_OWNED_TABLES:
            cls = "EXPECTED_DRIFT"
            owner = "create_all"
        elif in_prod and not in_fresh:
            cls = "UNEXPLAINED_DRIFT"
            owner = "production_only_unknown"
        elif in_fresh and not in_prod and name in ALEMBIC_CREATED_TABLES:
            cls = "UNEXPLAINED_DRIFT"
            owner = "alembic_missing_in_production"
        elif in_fresh and not in_prod:
            cls = "UNEXPLAINED_DRIFT"
            owner = "fresh_only_unknown"
        else:
            cls = "UNEXPLAINED_DRIFT"
            owner = "unknown"
        rows.append(
            {
                "table": name,
                "class": cls,
                "owner": owner,
                "in_fresh": in_fresh,
                "in_production": in_prod,
            }
        )
    return rows


def classify_focus_columns(
    *,
    fresh: dict[str, Any],
    production: dict[str, Any],
    table: str,
) -> dict[str, Any]:
    ft = (fresh.get("tables") or {}).get(table) or {}
    pt = (production.get("tables") or {}).get(table) or {}
    fcols = _col_map(ft)
    pcols = _col_map(pt)
    extra_prod = sorted(set(pcols) - set(fcols))
    extra_fresh = sorted(set(fcols) - set(pcols))
    if extra_fresh:
        cls = "UNEXPLAINED_DRIFT"
        reason = "alembic_columns_missing_in_production"
    elif extra_prod and table in {"stores", "abandoned_carts"}:
        cls = "EXPECTED_DRIFT"
        reason = "create_all_columns_beyond_alembic_stub_chain"
    elif extra_prod and table in CREATE_ALL_OWNED_TABLES:
        cls = "EXPECTED_DRIFT"
        reason = "create_all_owned_table"
    elif extra_prod:
        cls = "UNEXPLAINED_DRIFT"
        reason = "production_extra_columns"
    elif not ft and pt:
        cls = "EXPECTED_DRIFT" if table in CREATE_ALL_OWNED_TABLES else "UNEXPLAINED_DRIFT"
        reason = "create_all_owned_absent_from_alembic" if table in CREATE_ALL_OWNED_TABLES else "missing_from_fresh"
    elif ft and not pt:
        cls = "UNEXPLAINED_DRIFT"
        reason = "missing_from_production"
    else:
        cls = "MATCH"
        reason = "column_names_match"
    return {
        "table": table,
        "class": cls,
        "reason": reason,
        "fresh_columns": sorted(fcols),
        "production_columns": sorted(pcols),
        "production_only_columns": extra_prod,
        "fresh_only_columns": extra_fresh,
        "fresh_pk": list(ft.get("pk") or []),
        "production_pk": list(pt.get("pk") or []),
    }
