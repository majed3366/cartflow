# -*- coding: utf-8 -*-
"""Schema inventory + production-vs-fresh classification. Read-only."""
from __future__ import annotations

from typing import Any

from sqlalchemy import inspect

# Tables Alembic create_table revisions own (surviving C-class + reconstructed A/B).
ALEMBIC_CREATED_TABLES: frozenset[str] = frozenset(
    {
        "abandoned_carts",
        "abandonment_reason_logs",
        "business_findings",
        "cart_line_snapshots",
        "cart_recovery_logs",
        "cart_recovery_reasons",
        "commerce_intelligence_syntheses",
        "commercial_guidance_records",
        "dashboard_snapshots",
        "dashboard_snapshots_archive",
        "db_ready_operational_snapshots",
        "diagnostic_snapshots",
        "evidence_confidence_evaluations",
        "evidence_gaps",
        "evidence_truth_materialization_runs",
        "evidence_truth_shadow_artifacts",
        "guidance_eligibility_evaluations",
        "guidance_routes",
        "knowledge_statements",
        "landing_page_events_v1",
        "lifecycle_closure_records",
        "merchant_cart_lifecycle_archives",
        "merchant_followup_actions",
        "merchant_password_reset_tokens",
        "merchant_presentations",
        "merchant_subscription_audit_logs",
        "merchant_users",
        "message_logs",
        "movement_snapshots",
        "objection_tracks",
        "operational_control_snapshots",
        "order_economic_facts",
        "product_catalog_entries",
        "product_evidence_bundles",
        "product_evidence_items",
        "product_exposure_daily_facts",
        "product_exposure_events",
        "product_hesitation_mappings",
        "product_metric_values",
        "product_purchase_mappings",
        "product_signal_events",
        "product_trend_values",
        "provider_retry_ledger",
        "purchase_truth_records",
        "recovery_events",
        "recovery_schedules",
        "recovery_truth_timeline_events",
        "simulation_event_ledger",
        "simulation_row_index",
        "simulation_run_archives",
        "simulation_runs",
        "store_identity_aliases",
        "stores",
        "surface_compositions",
        "whatsapp_delivery_truth",
    }
)

# No remaining ALTER-only tables: birth CREATEs now exist for former stubs.
ALEMBIC_ALTER_ONLY_TABLES: frozenset[str] = frozenset()

# Production leftover only. Not a required fresh-runtime object. Do not delete.
DEPRECATED_PRODUCTION_ONLY_TABLES: frozenset[str] = frozenset(
    {
        "commercial_decision_commitments",
    }
)

# Legacy name kept for V1.1 tests; now equals deprecated leftovers only.
CREATE_ALL_OWNED_TABLES: frozenset[str] = DEPRECATED_PRODUCTION_ONLY_TABLES

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
        elif in_prod and not in_fresh and name in DEPRECATED_PRODUCTION_ONLY_TABLES:
            cls = "EXPECTED_DEPRECATED_DRIFT"
            owner = "deprecate"
        elif in_prod and not in_fresh:
            cls = "UNRESOLVED_DRIFT"
            owner = "production_only_unknown"
        elif in_fresh and not in_prod and name in ALEMBIC_CREATED_TABLES:
            cls = "UNRESOLVED_DRIFT"
            owner = "alembic_missing_in_production"
        elif in_fresh and not in_prod:
            cls = "UNRESOLVED_DRIFT"
            owner = "fresh_only_unknown"
        else:
            cls = "UNRESOLVED_DRIFT"
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
        cls = "UNRESOLVED_DRIFT"
        reason = "alembic_columns_missing_in_production"
    elif extra_prod and table in DEPRECATED_PRODUCTION_ONLY_TABLES:
        cls = "EXPECTED_DEPRECATED_DRIFT"
        reason = "deprecated_production_only"
    elif extra_prod:
        cls = "UNRESOLVED_DRIFT"
        reason = "production_extra_columns"
    elif not ft and pt:
        cls = (
            "EXPECTED_DEPRECATED_DRIFT"
            if table in DEPRECATED_PRODUCTION_ONLY_TABLES
            else "UNRESOLVED_DRIFT"
        )
        reason = (
            "deprecated_production_only"
            if table in DEPRECATED_PRODUCTION_ONLY_TABLES
            else "missing_from_fresh"
        )
    elif ft and not pt:
        cls = "UNRESOLVED_DRIFT"
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


def _norm_type(raw: Any) -> str:
    s = str(raw or "").strip().upper().replace(" ", "")
    s = s.replace("CHARACTERVARYING", "VARCHAR")
    s = s.replace("DOUBLEPRECISION", "FLOAT")
    s = s.replace("TIMESTAMPWITHOUTTIMEZONE", "TIMESTAMP")
    s = s.replace("TIMESTAMPWITHTIMEZONE", "TIMESTAMPTZ")
    if s in {"BOOL", "BOOLEAN"}:
        return "BOOLEAN"
    if s in {"INT", "INTEGER", "SERIAL"}:
        return "INTEGER"
    if s in {"FLOAT", "REAL"}:
        return "FLOAT"
    if s.startswith("TIMESTAMP("):
        return "TIMESTAMP"
    return s


def _norm_default(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in {"none", "null"}:
        return None
    if "nextval(" in s.lower():
        return "SEQUENCE"
    if "::" in s:
        s = s.split("::", 1)[0]
    return s.strip().strip("'").strip('"')


def _col_sig(col: dict[str, Any]) -> tuple[str, str, bool, str | None]:
    return (
        col.get("name") or "",
        _norm_type(col.get("type")),
        bool(col.get("nullable", True)),
        _norm_default(col.get("default")),
    )


def _index_key(ix: dict[str, Any]) -> tuple[tuple[str, ...], bool]:
    cols = tuple(ix.get("columns") or [])
    return (cols, bool(ix.get("unique")))


def _fk_key(fk: dict[str, Any]) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    return (
        tuple(fk.get("columns") or []),
        str(fk.get("referred_table") or ""),
        tuple(fk.get("referred_columns") or []),
    )


def _uq_key(uq: dict[str, Any]) -> tuple[str, ...]:
    return tuple(uq.get("columns") or [])


def classify_full_schema(
    *,
    fresh: dict[str, Any],
    production: dict[str, Any],
) -> dict[str, Any]:
    """Classify live objects. CDC-only leftovers are EXPECTED_DEPRECATED_DRIFT."""
    ftables = (fresh.get("tables") or {}) if isinstance(fresh.get("tables"), dict) else {}
    ptables = (
        (production.get("tables") or {})
        if isinstance(production.get("tables"), dict)
        else {}
    )
    if not ftables and fresh.get("table_names"):
        ftables = {n: {} for n in fresh.get("table_names") or []}
    if not ptables and production.get("table_names"):
        ptables = {n: {} for n in production.get("table_names") or []}

    fresh_names = set(ftables) | set(fresh.get("table_names") or [])
    prod_names = set(ptables) | set(production.get("table_names") or [])
    presence = classify_table_presence(fresh_names=fresh_names, production_names=prod_names)

    axes = {
        "tables": "MATCH",
        "columns": "MATCH",
        "types": "MATCH",
        "nullability": "MATCH",
        "defaults": "MATCH",
        "pk": "MATCH",
        "fk": "MATCH",
        "unique": "MATCH",
        "indexes": "MATCH",
    }
    unresolved: list[dict[str, Any]] = []
    deprecated: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []

    for row in presence:
        name = row["table"]
        if name == "alembic_version":
            table_rows.append({**row, "detail": "version_table"})
            continue
        if row["class"] == "EXPECTED_DEPRECATED_DRIFT":
            deprecated.append(row)
            table_rows.append(row)
            continue
        if row["class"] == "UNRESOLVED_DRIFT":
            axes["tables"] = "UNRESOLVED_DRIFT"
            unresolved.append(row)
            table_rows.append(row)
            continue

        fs = ftables.get(name) or {}
        ps = ptables.get(name) or {}
        if not fs or not ps or not fs.get("columns") or not ps.get("columns"):
            table_rows.append({**row, "detail": "presence_only"})
            continue

        fcols = {c["name"]: c for c in fs.get("columns") or []}
        pcols = {c["name"]: c for c in ps.get("columns") or []}
        extra_p = sorted(set(pcols) - set(fcols))
        extra_f = sorted(set(fcols) - set(pcols))
        type_drift = []
        null_drift = []
        default_drift = []
        for col in sorted(set(fcols) & set(pcols)):
            fa, pa = _col_sig(fcols[col]), _col_sig(pcols[col])
            if fa[1] != pa[1]:
                type_drift.append({"column": col, "fresh": fa[1], "production": pa[1]})
            if fa[2] != pa[2]:
                null_drift.append(
                    {"column": col, "fresh_nullable": fa[2], "production_nullable": pa[2]}
                )
            if fa[3] != pa[3]:
                default_drift.append(
                    {"column": col, "fresh": fa[3], "production": pa[3]}
                )

        fpk = list(fs.get("pk") or [])
        ppk = list(ps.get("pk") or [])
        ffk = {_fk_key(x) for x in fs.get("foreign_keys") or []}
        pfk = {_fk_key(x) for x in ps.get("foreign_keys") or []}
        fuq = {_uq_key(x) for x in fs.get("uniques") or []}
        puq = {_uq_key(x) for x in ps.get("uniques") or []}
        # Unique indexes count as unique constraints for parity.
        for ix in fs.get("indexes") or []:
            if ix.get("unique"):
                fuq.add(tuple(ix.get("columns") or []))
        for ix in ps.get("indexes") or []:
            if ix.get("unique"):
                puq.add(tuple(ix.get("columns") or []))
        fix = {_index_key(x) for x in fs.get("indexes") or []}
        pix = {_index_key(x) for x in ps.get("indexes") or []}

        issues: list[str] = []
        if extra_p or extra_f:
            axes["columns"] = "UNRESOLVED_DRIFT"
            issues.append("columns")
        if type_drift:
            axes["types"] = "UNRESOLVED_DRIFT"
            issues.append("types")
        if null_drift:
            axes["nullability"] = "UNRESOLVED_DRIFT"
            issues.append("nullability")
        if default_drift:
            axes["defaults"] = "UNRESOLVED_DRIFT"
            issues.append("defaults")
        if fpk != ppk:
            axes["pk"] = "UNRESOLVED_DRIFT"
            issues.append("pk")
        if ffk != pfk:
            axes["fk"] = "UNRESOLVED_DRIFT"
            issues.append("fk")
        if fuq != puq:
            axes["unique"] = "UNRESOLVED_DRIFT"
            issues.append("unique")
        if fix != pix:
            axes["indexes"] = "UNRESOLVED_DRIFT"
            issues.append("indexes")

        detail = {
            **row,
            "issues": issues,
            "production_only_columns": extra_p,
            "fresh_only_columns": extra_f,
            "type_drift": type_drift,
            "nullability_drift": null_drift,
            "default_drift": default_drift,
            "fresh_pk": fpk,
            "production_pk": ppk,
            "fk_only_fresh": [list(x) for x in sorted(ffk - pfk)],
            "fk_only_production": [list(x) for x in sorted(pfk - ffk)],
            "unique_only_fresh": [list(x) for x in sorted(fuq - puq)],
            "unique_only_production": [list(x) for x in sorted(puq - fuq)],
            "index_only_fresh": [list(x) for x in sorted(fix - pix)],
            "index_only_production": [list(x) for x in sorted(pix - fix)],
        }
        if issues:
            detail["class"] = "UNRESOLVED_DRIFT"
            unresolved.append(detail)
        table_rows.append(detail)

    all_match = all(v == "MATCH" for v in axes.values()) and not unresolved
    return {
        "ok": all_match,
        "axes": axes,
        "unresolved_active_drift_count": len(unresolved),
        "unresolved": unresolved,
        "expected_deprecated_drift": deprecated,
        "tables": table_rows,
        "fresh_table_count": len(fresh_names),
        "production_table_count": len(prod_names),
    }
