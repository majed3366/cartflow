# -*- coding: utf-8 -*-
"""
Diagnostics-only: peers query (‎vip_mode‎ + OR على ‎recovery_session_id / zid_cart_id‎).

يشغَّل عند ‎CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG=1‎ فقط.

- يطبع شكل SQL (بفرضات وم literal).
- يذكر ما يمكن من فهارس الجدول (فحص DDL).
- ينفّذ خطة الشرح وفق المحكي:
    ‎PostgreSQL‎: ‎EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)‎ فوق SQL literal.
    ‎SQLite‎: ‎EXPLAIN QUERY PLAN‎ (بناء هذا الـ‎Python‎ غالباً لا يدعم ‎EXPLAIN ANALYZE‎ ل‎SELECT‎).

لا يفعِّل وحده ⇒ لا تأثير في المسار الافتراضي.

تحذير: عند الشرح ب‎literal binds‎ قد يظهر في السجلات محتوى قيم الـ‎IN‎.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Iterable

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text as sa_text

log = logging.getLogger("cartflow")


def peers_abandoned_explain_diag_enabled() -> bool:
    try:
        from services.cartflow_observability_mode import (
            observability_peers_sql_explain_enabled,
        )

        return observability_peers_sql_explain_enabled()
    except Exception:  # noqa: BLE001
        return False


EmitFn = Callable[[str], None]


def _emit_default(line: str) -> None:
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _compile_shape_parameterized(stmt: Any, dialect: Any) -> str:
    c = stmt.compile(
        dialect=dialect,
        compile_kwargs={"literal_binds": False, "render_postcompile": True},
    )
    return str(c).strip()


def _compile_for_literal_explain(stmt: Any, dialect: Any) -> str:
    c = stmt.compile(
        dialect=dialect,
        compile_kwargs={"literal_binds": True, "render_postcompile": True},
    )
    return str(c).strip()


def _sql_shape_literals_soft_fail(stmt: Any, dialect: Any) -> str:
    try:
        return _compile_for_literal_explain(stmt, dialect)
    except Exception as exc:  # noqa: BLE001
        return f"<literal_compile_failed {exc!r}>"


def _inspector_index_lines(bind: Any) -> list[str]:
    lines: list[str] = []
    try:
        insp = sa_inspect(bind)
        if not hasattr(insp, "get_indexes"):
            return lines
        for idx in insp.get_indexes("abandoned_carts") or []:
            nm = idx.get("name") or "(unnamed)"
            cols = idx.get("column_names") or []
            uniq = idx.get("unique")
            cols_s = ",".join(str(c) for c in cols)
            lines.append(f"  index={nm} cols=[{cols_s}] unique={uniq}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"  <index_introspection_failed {exc!r}>")
    return lines


def _dialect_lc(bind: Any) -> str:
    try:
        return str(getattr(bind.dialect, "name", "") or "").lower()
    except Exception:
        return ""


def _explain_output_lines(exec_conn: Any, sql_literal_inner: str) -> tuple[str, list[str]]:
    try:
        dialect = getattr(getattr(exec_conn, "engine", None), "dialect", None)
        dn = str(getattr(dialect, "name", "") or "").lower()
    except Exception:
        dn = ""

    row_out: list[str] = []

    tag = ""
    prefix = ""
    if dn.startswith("postgresql") or dn in ("postgres",):
        tag = "pg_explain_analyze_buffers_format_text"
        prefix = "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
    elif dn.startswith("sqlite"):
        tag = "sqlite_explain_query_plan"
        prefix = "EXPLAIN QUERY PLAN "
    elif dn.startswith("mysql") or dn in ("mariadb",):
        tag = "mysql_mariadb_explain_analyze"
        prefix = "EXPLAIN ANALYZE "
    else:
        msg = "(no explain strategy wired for dialect)"
        return "none", [msg]

    try:
        res = exec_conn.execute(sa_text(prefix + sql_literal_inner.strip()))
    except Exception as exc:  # noqa: BLE001
        return tag, [f"(explain_execute_failed:{exc!r})"]
    if res.returns_rows:
        for tup in res:
            row_out.append("\t".join(str(x) for x in tup) if tup else "")
    return tag, row_out or ["(explain returned zero rows - unexpected for dialect)"]


def _parse_pg_timings(plan_lines: Iterable[str]) -> tuple[str | None, str | None]:
    plan_s = "\n".join(plan_lines)
    pm = re.search(r"Planning Time:\s*([\d.]+)\s*ms", plan_s)
    em = re.search(r"Execution Time:\s*([\d.]+)\s*ms", plan_s)
    return (
        pm.group(1) if pm else None,
        em.group(1) if em else None,
    )


def _interpret_plan(plan_text: str, *, dialect_lc: str) -> list[str]:
    bullets: list[str] = []
    low = plan_text.lower()

    nodes_scanned_hint = ""
    for m in re.finditer(r"rows=(\d+)", low):
        nodes_scanned_hint = m.group(1)
    if nodes_scanned_hint:
        bullets.append(
            "Plan mentions node row estimates or actual rows=... Compare these to LIMIT 4000 "
            "and returned ORM rows; large values often mean heap/index churn before cutoff."
        )
    else:
        bullets.append(
            "Read per-node rows and loops estimates in full plan above (Postgres ANALYZE) "
            "or SEARCH lines (SQLite QUERY PLAN)."
        )

    if "seq scan" in low and "abandoned_cart" in low:
        bullets.append(
            "Sequential scan on abandoned_carts: each page read adds latency unrelated to LIMIT row count."
        )
    elif "bitmap" in low:
        bullets.append(
            "Bitmap-ish plans often visit many tuples (OR predicates, merging indexes) "
            "then filter (e.g. vip_mode) until LIMIT."
        )

    bullets.append(
        "OR(recovery_session_id IN (...), zid_cart_id IN (...)) may prevent one selective "
        "index probe; planner may BitmapOr/index union or choose seq scan depending on table "
        "size and statistics."
    )
    bullets.append(
        "vip_mode IS false applies after qualifying rows unless a composite index starts with vip_mode "
        "(model only has standalone indexes). Many rows matching session/cart IDs can be non-VIP-heavy "
        "or require extra filtering visits."
    )
    bullets.append(
        "~110ms at ~38 final rows commonly reflects: tuples actually read/scanned are often "
        "much larger than 38 (selectivity mismatch), cold caches / SSD I/O round-trips on "
        "large tables, contention, or remote DB latency - not payload size alone."
    )
    if dialect_lc.startswith("sqlite"):
        bullets.append(
            "SQLite in this toolchain: EXPLAIN ANALYZE for SELECT typically unavailable; QUERY PLAN "
            "shows SEARCH/SCAN hints only (no real execution timings)."
        )
    return bullets


def peers_non_vip_abandoned_scope_diag_maybe(
    session: Any,
    peers_sa_query: Any,
    *,
    sess_in_len: int,
    cid_in_len: int,
    emit_line: EmitFn | None = None,
) -> None:
    if not peers_abandoned_explain_diag_enabled():
        return
    ell = emit_line or _emit_default
    ell(
        "[PEERS_NON_VIP_SQL_DIAG] require=CARTFLOW_OBSERVABILITY_MODE=debug "
        "and_CARTFLOW_PEERS_ABANDONED_EXPLAIN_DIAG=1 warning=literals_may_include_IN_values"
        "_(single_log_via_logger_no_stdout_dup)"
    )
    ell(
        f"[PEERS_NON_VIP_SQL_DIAG] in_dims recovery_session_id_values={sess_in_len} "
        f"zid_cart_id_values={cid_in_len} limit=4000 filter=vip_mode IS false "
        "(OR across both IN clauses when pools non-empty)"
    )

    try:
        bind = session.get_bind()
    except Exception as exc:  # noqa: BLE001
        ell(f"[PEERS_NON_VIP_SQL_DIAG] skip: bind_unavailable ({exc!r})")
        return

    dn = _dialect_lc(bind)

    stmt = peers_sa_query.statement
    try:
        parameterized = _compile_shape_parameterized(stmt, bind.dialect)
    except Exception as exc:  # noqa: BLE001
        ell(f"[PEERS_NON_VIP_SQL_DIAG] shape_parameterized_compile_failed={exc!r}")
        parameterized = ""

    ell("[PEERS_NON_VIP_SQL_DIAG] sql_shape_parameterized(render_postcompile)=BEGIN<<")
    ell(parameterized if parameterized else "(empty)")
    ell("[PEERS_NON_VIP_SQL_DIAG] sql_shape_parameterized=END")

    literal_sql = _sql_shape_literals_soft_fail(stmt, bind.dialect)
    ell("[PEERS_NON_VIP_SQL_DIAG] sql_literal_for_explain=BEGIN<<")
    ell(literal_sql)
    ell("[PEERS_NON_VIP_SQL_DIAG] sql_literal_for_explain=END")

    ell("[PEERS_NON_VIP_SQL_DIAG] ddl_indexes_known_abandoned_carts (SQLAlchemy inspect)=BEGIN<<")
    for ln in _inspector_index_lines(bind):
        ell(f"[PEERS_NON_VIP_SQL_DIAG]{ln}")
    ell("[PEERS_NON_VIP_SQL_DIAG] ddl_indexes_known_abandoned_carts=END")

    ell("[PEERS_NON_VIP_SQL_DIAG] explain=BEGIN<<")
    strat = "none"
    outs: list[str]
    try:
        conn = session.connection()
        strat, outs = _explain_output_lines(conn, literal_sql.strip())
    except Exception as exc:  # noqa: BLE001
        outs = [f"(explain_skipped_session_connection:{exc!r})"]

    ell(f"[PEERS_NON_VIP_SQL_DIAG] explain_strategy_selected={strat}")
    for line in outs:
        ell(f"[PEERS_NON_VIP_SQL_DIAG]| {line}")
    if dn.startswith("postgresql") or dn in ("postgres",):
        pt, et = _parse_pg_timings(outs)
        if pt is not None or et is not None:
            ell(
                "[PEERS_NON_VIP_SQL_DIAG] parsed postgres summary "
                f"planning_ms={pt if pt else 'n/a'} execution_ms={et if et else 'n/a'}"
            )

    ell("[PEERS_NON_VIP_SQL_DIAG] explain=END")

    plan_blob = "\n".join(outs)
    ell("[PEERS_NON_VIP_SQL_DIAG] heuristic_why_slow_for_small_limit=BEGIN<<")
    for b in _interpret_plan(plan_blob, dialect_lc=dn):
        ell(f"[PEERS_NON_VIP_SQL_DIAG] - {b}")
    ell("[PEERS_NON_VIP_SQL_DIAG] heuristic_why_slow_for_small_limit=END")
