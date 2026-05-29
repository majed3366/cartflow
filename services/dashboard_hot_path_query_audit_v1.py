# -*- coding: utf-8 -*-
"""
SQL-level audit for dashboard hot-path functions (metrics only).

Produces "Where the N queries come from" — per-function counts, repeated SQL
fingerprints, N+1 patterns, duplicate lookups, and bulk-load opportunities.
Does not alter SQL or dashboard behavior.
"""
from __future__ import annotations

import contextvars
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Optional

HOT_PATH_ROOTS: tuple[str, ...] = (
    "_normal_recovery_merchant_lightweight_alert_list_for_api",
    "_merchant_normal_dashboard_batch_reads",
    "_merchant_normal_recovery_light_payload_merchant_batch",
)

_PER_CALL_CALLEES: frozenset[str] = frozenset(
    {
        "_merchant_normal_batch_resolve_customer_phone_raw",
        "_merchant_normal_batch_extended_phone_resolve",
        "_resolve_cartflow_recovery_phone",
    }
)

_LOOP_SPAN_PREFIX = "loop:"
_N_PLUS_ONE_MIN = 3
_TOP_FINGERPRINTS = 25

_active: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "hot_path_query_audit_active", default=False
)

_fp_total: DefaultDict[str, int] = defaultdict(int)
_fp_by_span: DefaultDict[tuple[str, str], int] = defaultdict(int)
_fp_by_hot_root: DefaultDict[tuple[str, str], int] = defaultdict(int)
_span_query_total: DefaultDict[str, int] = defaultdict(int)
_hot_root_query_total: DefaultDict[str, int] = defaultdict(int)
_fp_example: dict[str, str] = {}


@dataclass
class _HotPathAuditMerge:
    """Aggregates audit samples across multiple dashboard checks."""

    total_queries: int = 0
    dashboard_calls: int = 0
    fp_total: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    fp_by_span: DefaultDict[tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    fp_by_hot_root: DefaultDict[tuple[str, str], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    span_query_total: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    hot_root_query_total: DefaultDict[str, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    fp_example: dict[str, str] = field(default_factory=dict)
    fn_query_inclusive: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    fn_calls: DefaultDict[str, int] = field(default_factory=lambda: defaultdict(int))
    fn_child_spans: DefaultDict[str, DefaultDict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )

    def merge_sample(
        self,
        *,
        total_queries: int,
        span_snap: list[dict[str, Any]],
        audit_report: dict[str, Any],
    ) -> None:
        self.dashboard_calls += 1
        self.total_queries += max(0, int(total_queries))

        for row in span_snap or ():
            fn = str(row.get("fn") or "")
            if not fn:
                continue
            self.fn_query_inclusive[fn] += int(row.get("queries_inclusive") or 0)
            self.fn_calls[fn] += int(row.get("calls") or 0)

        for root, block in (audit_report.get("hot_path_functions") or {}).items():
            for child in block.get("child_spans") or ():
                cname = str(child.get("span") or "")
                cq = int(child.get("query_count") or 0)
                if cname:
                    self.fn_child_spans[str(root)][cname] += cq

        for fp, cnt in (audit_report.get("_fp_total") or {}).items():
            self.fp_total[str(fp)] += int(cnt)
        for key, cnt in (audit_report.get("_fp_by_span") or {}).items():
            parts = str(key).split("|", 1)
            if len(parts) == 2:
                self.fp_by_span[(parts[0], parts[1])] += int(cnt)
        for key, cnt in (audit_report.get("_fp_by_hot_root") or {}).items():
            parts = str(key).split("|", 1)
            if len(parts) == 2:
                self.fp_by_hot_root[(parts[0], parts[1])] += int(cnt)
        for span, cnt in (audit_report.get("_span_query_total") or {}).items():
            self.span_query_total[str(span)] += int(cnt)
        for root, cnt in (audit_report.get("_hot_root_query_total") or {}).items():
            self.hot_root_query_total[str(root)] += int(cnt)
        for fp, ex in (audit_report.get("_fp_example") or {}).items():
            if fp not in self.fp_example:
                self.fp_example[str(fp)] = str(ex)[:400]

    def build_report(self) -> dict[str, Any]:
        calls = max(1, int(self.dashboard_calls))
        avg_total = (
            round(float(self.total_queries) / float(calls))
            if self.dashboard_calls
            else int(self.total_queries)
        )
        span_snap_proxy: list[dict[str, Any]] = []
        for fn in HOT_PATH_ROOTS:
            q = int(self.fn_query_inclusive.get(fn) or 0)
            c = int(self.fn_calls.get(fn) or 0)
            span_snap_proxy.append(
                {
                    "fn": fn,
                    "queries_inclusive": round(q / calls) if self.dashboard_calls > 1 else q,
                    "calls": round(c / calls) if self.dashboard_calls > 1 else c,
                }
            )
        for fn, q in self.fn_query_inclusive.items():
            if fn in HOT_PATH_ROOTS:
                continue
            c = int(self.fn_calls.get(fn) or 0)
            span_snap_proxy.append(
                {
                    "fn": fn,
                    "queries_inclusive": round(q / calls) if self.dashboard_calls > 1 else q,
                    "calls": round(c / calls) if self.dashboard_calls > 1 else c,
                }
            )

        def _avg_map(raw: dict[Any, int]) -> dict[Any, int]:
            if self.dashboard_calls <= 1:
                return dict(raw)
            out: dict[Any, int] = {}
            for k, v in raw.items():
                out[k] = max(0, round(float(v) / float(calls)))
            return out

        report = build_hot_path_query_report(
            total_queries=avg_total,
            span_snap=span_snap_proxy,
            fp_total=_avg_map(dict(self.fp_total)),
            fp_by_span=_avg_map(dict(self.fp_by_span)),
            fp_by_hot_root=_avg_map(dict(self.fp_by_hot_root)),
            span_query_total=_avg_map(dict(self.span_query_total)),
            hot_root_query_total=_avg_map(dict(self.hot_root_query_total)),
            fp_example=dict(self.fp_example),
            dashboard_calls=int(self.dashboard_calls),
        )
        if self.dashboard_calls > 1:
            report["title"] = (
                f"Where the ~{avg_total} queries come from "
                f"(avg per dashboard check, {self.dashboard_calls} samples)"
            )
            report["total_queries_avg_per_check"] = avg_total
            report["total_queries_all_samples"] = int(self.total_queries)
        return report


_merge_acc = _HotPathAuditMerge()


def hot_path_query_audit_active() -> bool:
    return bool(_active.get())


def hot_path_query_audit_begin() -> None:
    _active.set(True)
    _fp_total.clear()
    _fp_by_span.clear()
    _fp_by_hot_root.clear()
    _span_query_total.clear()
    _hot_root_query_total.clear()
    _fp_example.clear()


def hot_path_query_audit_end() -> None:
    _active.set(False)


def hot_path_query_audit_merge_reset() -> None:
    global _merge_acc
    _merge_acc = _HotPathAuditMerge()


def hot_path_query_audit_merge_sample(
    *,
    total_queries: int,
    span_snap: list[dict[str, Any]],
    audit_report: dict[str, Any],
) -> None:
    _merge_acc.merge_sample(
        total_queries=total_queries,
        span_snap=span_snap,
        audit_report=audit_report,
    )


def hot_path_query_audit_merged_report() -> dict[str, Any]:
    return _merge_acc.build_report()


def sql_fingerprint(statement: str) -> str:
    s = re.sub(r"\s+", " ", (statement or "").strip().lower())
    s = re.sub(r"'(?:''|[^'])*'", "?", s)
    s = re.sub(r'"(?:[^"\\]|\\.)*"', "?", s)
    s = re.sub(r"\b\d+\b", "?", s)
    s = re.sub(r"\(\?(?:,\s*\?)+\)", "(?)", s)
    s = re.sub(r"in \(\?\)", "in (?)", s)
    return s[:512]


def extract_sql_tables(statement: str) -> list[str]:
    s = (statement or "").lower()
    tables: list[str] = []
    for m in re.finditer(r"\b(?:from|join)\s+([`\"a-z0-9_.]+)", s):
        raw = m.group(1).strip("`\"")
        if raw and raw not in ("select", "where", "on"):
            tables.append(raw)
    seen: set[str] = set()
    out: list[str] = []
    for t in tables:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _resolve_hot_root(stack: list[str]) -> str:
    found = [name for name in stack if name in HOT_PATH_ROOTS]
    if found:
        return found[-1]
    return ""


def hot_path_query_audit_record_sql(statement: str) -> None:
    if not hot_path_query_audit_active():
        return
    try:
        from services.normal_carts_query_profiler import (
            normal_carts_query_profiling_active,
            normal_carts_current_span_stack,
        )

        if not normal_carts_query_profiling_active():
            return
        stack = normal_carts_current_span_stack()
    except Exception:  # noqa: BLE001
        return

    fp = sql_fingerprint(statement)
    leaf = stack[-1] if stack else "(no_span)"
    hot_root = _resolve_hot_root(stack) or "_normal_recovery_merchant_lightweight_alert_list_for_api"

    _fp_total[fp] += 1
    _fp_by_span[(leaf, fp)] += 1
    _fp_by_hot_root[(hot_root, fp)] += 1
    _span_query_total[leaf] += 1
    _hot_root_query_total[hot_root] += 1
    if fp not in _fp_example:
        _fp_example[fp] = (statement or "").strip()[:400]


def _span_snap_index(span_snap: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in span_snap or ():
        fn = str(row.get("fn") or "")
        if fn:
            out[fn] = row
    return out


def _child_spans_for_root(
    root: str,
    span_index: dict[str, dict[str, Any]],
    span_query_total: dict[str, int],
) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = []
    for fn, row in span_index.items():
        if fn == root:
            continue
        if fn.startswith("_") and fn not in _PER_CALL_CALLEES:
            continue
        q_sql = int(span_query_total.get(fn) or 0)
        q_prof = int(row.get("queries_inclusive") or 0)
        q = max(q_sql, q_prof)
        if q <= 0 and int(row.get("calls") or 0) <= 0:
            continue
        children.append(
            {
                "span": fn,
                "query_count": q,
                "calls": int(row.get("calls") or 0),
                "queries_inclusive_profiler": q_prof,
                "queries_from_sql_audit": q_sql,
            }
        )
    children.sort(key=lambda r: (-int(r.get("query_count") or 0), r.get("span") or ""))
    return children


def _top_repeated_queries(
    fp_total: dict[str, int],
    fp_example: dict[str, str],
    *,
    limit: int = _TOP_FINGERPRINTS,
) -> list[dict[str, Any]]:
    ranked = sorted(fp_total.items(), key=lambda kv: (-kv[1], kv[0]))
    out: list[dict[str, Any]] = []
    for fp, cnt in ranked[: max(1, int(limit))]:
        out.append(
            {
                "fingerprint": fp,
                "count": int(cnt),
                "example_sql_truncated": fp_example.get(fp, fp[:200]),
                "tables": extract_sql_tables(fp_example.get(fp, fp)),
            }
        )
    return out


def _detect_n_plus_one(
    fp_by_span: dict[tuple[str, str], int],
    span_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for (span, fp), cnt in sorted(fp_by_span.items(), key=lambda kv: -kv[1]):
        if cnt < _N_PLUS_ONE_MIN:
            continue
        is_loop = span.startswith(_LOOP_SPAN_PREFIX)
        is_per_call = span in _PER_CALL_CALLEES
        if not is_loop and not is_per_call:
            continue
        key = (span, fp)
        if key in seen:
            continue
        seen.add(key)
        calls = int((span_index.get(span) or {}).get("calls") or 0)
        patterns.append(
            {
                "span": span,
                "fingerprint": fp,
                "query_count": int(cnt),
                "span_calls": calls,
                "avg_queries_per_call": round(float(cnt) / float(calls), 2) if calls else None,
                "pattern": (
                    "per-iteration SQL inside loop span"
                    if is_loop
                    else "per-call SQL inside wrapped callee"
                ),
            }
        )

    for fn in _PER_CALL_CALLEES:
        row = span_index.get(fn) or {}
        calls = int(row.get("calls") or 0)
        q = int(row.get("queries_inclusive") or 0)
        if calls >= _N_PLUS_ONE_MIN and q >= _N_PLUS_ONE_MIN:
            patterns.append(
                {
                    "span": fn,
                    "fingerprint": "(profiler aggregate)",
                    "query_count": q,
                    "span_calls": calls,
                    "avg_queries_per_call": round(float(q) / float(calls), 2),
                    "pattern": "wrapped per-row callee invoked from parent loop",
                }
            )

    patterns.sort(key=lambda r: (-int(r.get("query_count") or 0), r.get("span") or ""))
    return patterns[:30]


def _detect_duplicate_lookups(
    fp_by_span: dict[tuple[str, str], int],
    fp_total: dict[str, int],
) -> list[dict[str, Any]]:
    dupes: list[dict[str, Any]] = []

    fp_spans: DefaultDict[str, list[str]] = defaultdict(list)
    for (span, fp), cnt in fp_by_span.items():
        if cnt > 0:
            fp_spans[fp].append(span)

    for fp, spans in fp_spans.items():
        uniq = sorted(set(spans))
        if len(uniq) < 2:
            continue
        dupes.append(
            {
                "fingerprint": fp,
                "total_count": int(fp_total.get(fp) or 0),
                "spans": uniq,
                "kind": "same_sql_in_multiple_spans",
            }
        )

    bulk_spans = {s for s, _ in fp_by_span if s.startswith("sql:batch")}
    loop_spans = {s for s, _ in fp_by_span if s.startswith(_LOOP_SPAN_PREFIX)}
    table_bulk: DefaultDict[str, set[str]] = defaultdict(set)
    table_loop: DefaultDict[str, set[str]] = defaultdict(set)
    for (span, fp), cnt in fp_by_span.items():
        if cnt <= 0:
            continue
        for tbl in extract_sql_tables(fp):
            if span in bulk_spans:
                table_bulk[tbl].add(span)
            if span in loop_spans:
                table_loop[tbl].add(span)

    for tbl in sorted(set(table_bulk) | set(table_loop)):
        if table_bulk.get(tbl) and table_loop.get(tbl):
            dupes.append(
                {
                    "fingerprint": f"table:{tbl}",
                    "total_count": None,
                    "spans": sorted(table_bulk[tbl] | table_loop[tbl]),
                    "kind": "bulk_and_loop_both_touch_table",
                    "bulk_spans": sorted(table_bulk[tbl]),
                    "loop_spans": sorted(table_loop[tbl]),
                }
            )

    reason_store = int(
        sum(
            c
            for (span, fp), c in fp_by_span.items()
            if "cart_recovery_reason" in fp and "store_slug" in fp
        )
    )
    reason_any = int(
        sum(
            c
            for (span, fp), c in fp_by_span.items()
            if "cart_recovery_reason" in fp
            and "store_slug" not in fp
            and "session_id" in fp
        )
    )
    if reason_store and reason_any:
        dupes.append(
            {
                "fingerprint": "cart_recovery_reason:store_scoped + session_any_store",
                "total_count": reason_store + reason_any,
                "spans": ["sql:batch_cart_recovery_reason_by_session"],
                "kind": "paired_reason_queries_same_session_keys",
                "store_scoped_count": reason_store,
                "any_store_count": reason_any,
            }
        )

    dupes.sort(
        key=lambda r: (
            -(int(r.get("total_count") or 0) if r.get("total_count") is not None else 0),
            r.get("fingerprint") or "",
        )
    )
    return dupes[:25]


def _bulk_load_opportunities(
    n_plus_one: list[dict[str, Any]],
    span_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    opps: list[dict[str, Any]] = []

    known: list[tuple[str, str, str]] = [
        (
            "loop:batch_resolve_customer_phone_per_abandoned",
            "_merchant_normal_batch_resolve_customer_phone_raw",
            "Phone resolution runs once per abandoned row; batch path already bulk-loads message_logs and reasons — extend map coverage or skip redundant lookups.",
        ),
        (
            "merchant_group_stale_meta",
            "CartRecoveryLog queued probe",
            "RESOLVED: bulk prefetch in batch_reads (sql:batch_queued_followup_logs_bulk).",
        ),
        (
            "loop:for_grp_sorted_in_picked",
            "merchant_group_stale_meta",
            "Outer payload loop wraps stale meta per group; combine with bulk queued-log prefetch.",
        ),
    ]

    n1_by_span = {str(r.get("span") or ""): r for r in n_plus_one}
    for loc, callee, suggestion in known:
        n1 = n1_by_span.get(loc) or n1_by_span.get(callee)
        row = span_index.get(loc) or span_index.get(callee) or {}
        q = int(row.get("queries_inclusive") or 0)
        calls = int(row.get("calls") or 0)
        if n1 or q > 0 or calls > 0:
            opps.append(
                {
                    "location": loc,
                    "callee_or_table": callee,
                    "observed_query_count": int((n1 or {}).get("query_count") or q),
                    "observed_calls": int((n1 or {}).get("span_calls") or calls),
                    "suggestion": suggestion,
                }
            )

    opps.sort(key=lambda r: (-int(r.get("observed_query_count") or 0), r.get("location") or ""))
    return opps


def build_hot_path_query_report(
    *,
    total_queries: int,
    span_snap: list[dict[str, Any]],
    fp_total: Optional[dict[str, int]] = None,
    fp_by_span: Optional[dict[tuple[str, str], int]] = None,
    fp_by_hot_root: Optional[dict[tuple[str, str], int]] = None,
    span_query_total: Optional[dict[str, int]] = None,
    hot_root_query_total: Optional[dict[str, int]] = None,
    fp_example: Optional[dict[str, str]] = None,
    dashboard_calls: int = 1,
) -> dict[str, Any]:
    span_index = _span_snap_index(span_snap)

    fp_total = fp_total if fp_total is not None else dict(_fp_total)
    fp_by_span = fp_by_span if fp_by_span is not None else dict(_fp_by_span)
    fp_by_hot_root = fp_by_hot_root if fp_by_hot_root is not None else dict(_fp_by_hot_root)
    span_query_total = (
        span_query_total if span_query_total is not None else dict(_span_query_total)
    )
    hot_root_query_total = (
        hot_root_query_total
        if hot_root_query_total is not None
        else dict(_hot_root_query_total)
    )
    fp_example = fp_example if fp_example is not None else dict(_fp_example)

    hot_path_functions: dict[str, Any] = {}
    for root in HOT_PATH_ROOTS:
        row = span_index.get(root) or {}
        prof_q = int(row.get("queries_inclusive") or 0)
        sql_q = int(hot_root_query_total.get(root) or 0)
        hot_path_functions[root] = {
            "query_count_inclusive": max(prof_q, sql_q),
            "query_count_profiler": prof_q,
            "query_count_sql_audit": sql_q,
            "calls": int(row.get("calls") or 0),
            "child_spans": _child_spans_for_root(root, span_index, span_query_total),
            "top_fingerprints": _top_repeated_queries(
                {fp: c for (r, fp), c in fp_by_hot_root.items() if r == root},
                fp_example,
                limit=10,
            ),
        }

    n_plus_one = _detect_n_plus_one(fp_by_span, span_index)
    duplicate_lookups = _detect_duplicate_lookups(fp_by_span, fp_total)
    bulk_opportunities = _bulk_load_opportunities(n_plus_one, span_index)

    queries_by_span = [
        {
            "span": span,
            "query_count": int(cnt),
            "calls": int((span_index.get(span) or {}).get("calls") or 0),
        }
        for span, cnt in sorted(span_query_total.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    report: dict[str, Any] = {
        "title": f"Where the {int(total_queries)} queries come from",
        "total_queries": int(total_queries),
        "dashboard_calls_sampled": int(dashboard_calls),
        "hot_path_functions": hot_path_functions,
        "queries_by_span": queries_by_span,
        "top_repeated_queries": _top_repeated_queries(fp_total, fp_example),
        "n_plus_one_patterns": n_plus_one,
        "duplicate_lookups": duplicate_lookups,
        "bulk_load_opportunities": bulk_opportunities,
        "notes": [
            "Counts combine normal-carts subprofiler inclusive queries with SQL fingerprint audit.",
            "hot_path_functions covers the three dashboard batch/list/payload roots only.",
            "N+1 detection flags loop:* spans and per-call wrapped callees with >=3 repeated queries.",
            "Metrics only — no SQL or dashboard behavior is changed by this audit.",
        ],
        "_fp_total": fp_total,
        "_fp_by_span": {f"{a}|{b}": c for (a, b), c in fp_by_span.items()},
        "_fp_by_hot_root": {f"{a}|{b}": c for (a, b), c in fp_by_hot_root.items()},
        "_span_query_total": span_query_total,
        "_hot_root_query_total": hot_root_query_total,
        "_fp_example": fp_example,
    }
    return report


def public_hot_path_query_report(report: dict[str, Any]) -> dict[str, Any]:
    """Strip internal merge keys before exposing in API/simulation JSON."""
    return {k: v for k, v in (report or {}).items() if not str(k).startswith("_")}


_PHONE_BOTTLENECK_SPANS: frozenset[str] = frozenset(
    {
        "loop:batch_resolve_customer_phone_per_abandoned",
        "_merchant_normal_batch_resolve_customer_phone_raw",
        "_merchant_normal_batch_extended_phone_resolve",
        "_resolve_cartflow_recovery_phone",
    }
)
_QUEUED_FOLLOWUP_SPANS: frozenset[str] = frozenset({"merchant_group_stale_meta"})


def _is_schema_noise_fingerprint(fp: str) -> bool:
    f = (fp or "").strip().lower()
    return f.startswith("pragma ") or "table_info" in f or "table_xinfo" in f


def _aggregate_profiler_child_spans(hot: dict[str, Any]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for _root, block in (hot.get("hot_path_functions") or {}).items():
        if not isinstance(block, dict):
            continue
        for row in block.get("child_spans") or ():
            if not isinstance(row, dict):
                continue
            span = str(row.get("span") or "")
            if not span:
                continue
            cur = agg.setdefault(
                span,
                {"span": span, "query_count": 0, "calls": 0},
            )
            cur["query_count"] = max(
                int(cur.get("query_count") or 0), int(row.get("query_count") or 0)
            )
            cur["calls"] = max(int(cur.get("calls") or 0), int(row.get("calls") or 0))
    return sorted(
        agg.values(),
        key=lambda r: (-int(r.get("query_count") or 0), str(r.get("span") or "")),
    )


def build_next_bottleneck_report(
    *,
    dashboard_check_ms: dict[str, Any],
    hot_path_query_audit: Optional[dict[str, Any]],
    top_slowest_functions: list[dict[str, Any]],
    queued_followup_optimization: Optional[dict[str, Any]] = None,
    span_profiler: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Post-queued-followup-opt audit: identify the next dashboard hot-path bottleneck.
    Metrics only — no behavior changes.
    """
    hot = hot_path_query_audit if isinstance(hot_path_query_audit, dict) else {}
    qf = (
        queued_followup_optimization
        if isinstance(queued_followup_optimization, dict)
        else {}
    )

    total_dashboard_queries = round(
        float(dashboard_check_ms.get("avg_queries_per_call") or 0), 2
    )
    dashboard_check_avg_ms = round(
        float(dashboard_check_ms.get("avg_wall_ms_per_call") or 0), 2
    )

    top_repeated_raw = hot.get("top_repeated_queries") or []
    top_repeated = [
        x
        for x in top_repeated_raw
        if not _is_schema_noise_fingerprint(str(x.get("fingerprint") or ""))
    ][:10]
    n_plus_one = hot.get("n_plus_one_patterns") or []
    duplicate_lookups = hot.get("duplicate_lookups") or []
    top5_slow = (top_slowest_functions or [])[:5]
    profiler_child_spans = _aggregate_profiler_child_spans(hot)
    bulk_opportunities = hot.get("bulk_load_opportunities") or []

    phone_n1 = [
        p
        for p in n_plus_one
        if str(p.get("span") or "") in _PHONE_BOTTLENECK_SPANS
        or "phone" in str(p.get("span") or "").lower()
    ]
    queued_n1 = [
        p for p in n_plus_one if str(p.get("span") or "") in _QUEUED_FOLLOWUP_SPANS
    ]
    other_n1 = [p for p in n_plus_one if p not in phone_n1 and p not in queued_n1]

    phone_query_est = sum(int(p.get("query_count") or 0) for p in phone_n1)
    phone_calls_est = 0
    for fn in _PHONE_BOTTLENECK_SPANS:
        for row in hot.get("queries_by_span") or ():
            if str(row.get("span") or "") == fn:
                phone_query_est = max(
                    phone_query_est, int(row.get("query_count") or 0)
                )
        for row in profiler_child_spans:
            if str(row.get("span") or "") == fn:
                phone_query_est = max(
                    phone_query_est, int(row.get("query_count") or 0)
                )
                phone_calls_est = max(
                    phone_calls_est, int(row.get("calls") or 0)
                )
    if isinstance(span_profiler, list):
        for row in span_profiler:
            fn = str(row.get("function") or "")
            if fn in _PHONE_BOTTLENECK_SPANS or fn.startswith("loop:batch_resolve"):
                phone_query_est = max(
                    phone_query_est, int(row.get("total_queries") or 0)
                )
                phone_calls_est = max(
                    phone_calls_est, int(row.get("calls") or 0)
                )

    qf_removed = bool(qf.get("n_plus_one_removed"))
    qf_after = (qf.get("after_avg_per_dashboard_check") or {}) if qf else {}
    qf_per_group = float(qf_after.get("queued_followup_per_group_db_queries") or 0)

    ranked_n1 = sorted(
        n_plus_one,
        key=lambda r: (-int(r.get("query_count") or 0), str(r.get("span") or "")),
    )
    top_n1 = ranked_n1[0] if ranked_n1 else None
    top_n1_span = str((top_n1 or {}).get("span") or "")
    top_n1_queries = int((top_n1 or {}).get("query_count") or 0)

    phone_opp = next(
        (
            o
            for o in bulk_opportunities
            if "phone" in str(o.get("location") or "").lower()
            or "phone" in str(o.get("callee_or_table") or "").lower()
        ),
        None,
    )

    non_bulk_child = [
        r
        for r in profiler_child_spans
        if not str(r.get("span") or "").startswith("sql:batch")
        and int(r.get("query_count") or 0) > 0
    ]
    top_child = non_bulk_child[0] if non_bulk_child else (
        profiler_child_spans[0] if profiler_child_spans else None
    )

    phone_is_next = False
    next_bottleneck = ""
    rationale = ""
    simulation_caveat = (
        "Under 100-store simulation load many dashboard checks hit the cooperative "
        "wall budget before batch_reads completes, which suppresses SQL fingerprints "
        "for per-row loops in the audit sample. Structural code-path analysis still applies."
    )

    if qf_removed and qf_per_group <= 0 and not queued_n1:
        if phone_n1 or phone_query_est >= 3:
            phone_is_next = True
            next_bottleneck = "loop:batch_resolve_customer_phone_per_abandoned"
            rationale = (
                "Queued-followup per-group DB probes are eliminated (0 per-group queries). "
                f"Phone resolution loop remains: ~{phone_query_est} profiler/SQL-attributed "
                "queries on loop:batch_resolve_customer_phone_per_abandoned / "
                "_merchant_normal_batch_resolve_customer_phone_raw (once per abandoned row)."
            )
        elif phone_opp and int(phone_opp.get("observed_calls") or 0) >= 1:
            phone_is_next = True
            next_bottleneck = "loop:batch_resolve_customer_phone_per_abandoned"
            rationale = (
                "Queued-followup N+1 removed (0 per-group DB). Phone resolution loop is "
                "the next structural N+1 in batch_reads — per-row "
                "_merchant_normal_batch_resolve_customer_phone_raw over ~row_cap candidates. "
                + simulation_caveat
            )
        elif top_n1:
            next_bottleneck = top_n1_span
            rationale = (
                f"Queued-followup N+1 removed. Next highest SQL N+1 span: "
                f"{top_n1_span} (~{top_n1_queries} queries/check)."
            )
        elif top_child:
            next_bottleneck = str(top_child.get("span") or "")
            rationale = (
                f"Queued-followup N+1 removed. Top profiler child span by query count: "
                f"{next_bottleneck} (~{int(top_child.get('query_count') or 0)} queries/check). "
                + simulation_caveat
            )
        elif top_repeated:
            fp0 = top_repeated[0]
            next_bottleneck = str(fp0.get("fingerprint") or "unknown_sql")[:120]
            rationale = (
                "Queued-followup N+1 removed. Dominant repeated SQL (schema noise filtered): "
                f"count={fp0.get('count')}. "
                + simulation_caveat
            )
        else:
            phone_is_next = True
            next_bottleneck = "loop:batch_resolve_customer_phone_per_abandoned"
            rationale = (
                "Queued-followup N+1 removed. No SQL N+1 captured in this sample; "
                "pre-audit structural analysis identifies phone resolution loop as next "
                "per-row cost in _merchant_normal_dashboard_batch_reads. "
                + simulation_caveat
            )
    elif queued_n1:
        next_bottleneck = "merchant_group_stale_meta"
        rationale = (
            "Queued-followup per-group queries still present — optimization may not "
            "be active on this path."
        )
    elif top_n1:
        next_bottleneck = top_n1_span
        rationale = f"Top N+1 span: {top_n1_span} (~{top_n1_queries} queries/check)."

    return {
        "title": "Next dashboard hot-path bottleneck (post queued-followup optimization)",
        "queued_followup_n1_removed": qf_removed and qf_per_group <= 0,
        "total_dashboard_queries_avg_per_check": total_dashboard_queries,
        "dashboard_check_ms_avg_per_call": dashboard_check_avg_ms,
        "top_repeated_queries": top_repeated,
        "profiler_child_spans": profiler_child_spans[:15],
        "n_plus_one_patterns": ranked_n1[:15],
        "n_plus_one_phone_resolution": phone_n1,
        "n_plus_one_other": other_n1,
        "duplicate_lookups": duplicate_lookups[:10],
        "top_slowest_functions": top5_slow,
        "phone_resolution_is_next_bottleneck": phone_is_next,
        "phone_resolution_query_estimate": phone_query_est,
        "phone_resolution_calls_estimate": phone_calls_est,
        "next_bottleneck": next_bottleneck,
        "rationale": rationale,
        "simulation_caveat": simulation_caveat,
        "prior_bottleneck_resolved": {
            "name": "merchant_group_stale_meta -> _has_recent_queued_followup",
            "removed": qf_removed and qf_per_group <= 0,
            "after_per_group_db_queries_avg": qf_per_group,
        },
    }


__all__ = [
    "HOT_PATH_ROOTS",
    "build_hot_path_query_report",
    "build_next_bottleneck_report",
    "extract_sql_tables",
    "hot_path_query_audit_active",
    "hot_path_query_audit_begin",
    "hot_path_query_audit_end",
    "hot_path_query_audit_merge_reset",
    "hot_path_query_audit_merge_sample",
    "hot_path_query_audit_merged_report",
    "hot_path_query_audit_record_sql",
    "public_hot_path_query_report",
    "sql_fingerprint",
]
