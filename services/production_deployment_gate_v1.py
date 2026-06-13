# -*- coding: utf-8 -*-
"""
Production deployment gate v1 — evaluate operational readiness checks.

Used by ``scripts/production_deployment_gate_v1.py`` and tests.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable, Optional


def _fetch_json(url: str, *, timeout: float = 120.0, cookies: Optional[list] = None) -> dict[str, Any]:
    import http.cookiejar

    if cookies:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        for c in cookies:
            cj.set_cookie(
                http.cookiejar.Cookie(
                    version=0,
                    name=c["name"],
                    value=c["value"],
                    port=None,
                    port_specified=False,
                    domain=c.get("domain", "").lstrip("."),
                    domain_specified=True,
                    domain_initial_dot=False,
                    path=c.get("path", "/"),
                    path_specified=True,
                    secure=bool(c.get("secure")),
                    expires=None,
                    discard=True,
                    comment=None,
                    comment_url=None,
                    rest={},
                    rfc2109=False,
                )
            )
        opener_open: Callable[..., Any] = opener.open
    else:
        opener_open = urllib.request.urlopen

    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with opener_open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError as exc:
                return {
                    "status": getattr(resp, "status", None),
                    "parse_error": str(exc)[:200],
                    "body": None,
                }
            return {
                "status": getattr(resp, "status", None),
                "parse_error": None,
                "body": body if isinstance(body, dict) else {"raw": body},
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"error": raw[:300]}
        return {
            "status": exc.code,
            "parse_error": None,
            "body": body if isinstance(body, dict) else {},
            "http_error": str(exc)[:200],
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": None, "parse_error": str(exc)[:200], "body": None}


def evaluate_pool_health_gate(pool: dict[str, Any]) -> dict[str, Any]:
    """Fail closed when in-process pool counters show exhaustion."""
    errors: list[str] = []
    if pool.get("exhausted"):
        errors.append("db_pool_exhausted=true")
    timeout_count = int(pool.get("timeout_count") or 0)
    if timeout_count > 0:
        errors.append(f"db_pool_timeout_count={timeout_count}")
    checked_out = pool.get("checked_out")
    max_conn = pool.get("max_connections")
    if (
        checked_out is not None
        and max_conn is not None
        and int(checked_out) >= int(max_conn)
    ):
        errors.append(f"db_pool_checked_out={checked_out} max={max_conn}")
    return {
        "name": "db_pool_health",
        "passed": len(errors) == 0,
        "errors": errors,
        "pool": pool,
    }


def evaluate_scheduler_gate(health: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not health.get("ok"):
        errors.append(f"scheduler ok=false reasons={health.get('failure_reasons')}")
    role = str(health.get("scheduler_role") or health.get("role") or "")
    if role != "scheduler":
        errors.append(f"scheduler_role={role!r} expected scheduler")
    if not bool(health.get("due_scanner_enabled")):
        errors.append("due_scanner_enabled=false")
    overdue = int(health.get("overdue_scheduled_count") or 0)
    stuck = int(health.get("stuck_running_count") or health.get("running_stale_count") or 0)
    if overdue > 0:
        errors.append(f"overdue_scheduled_count={overdue}")
    if stuck > 0:
        errors.append(f"stuck_running_count={stuck}")
    pool = health.get("db_pool") or {}
    if pool.get("exhausted"):
        errors.append("scheduler_db_pool_exhausted=true")
    scanner_err = str(
        (health.get("scheduler_heartbeat") or {}).get("scanner_last_error")
        or health.get("scanner_last_error")
        or ""
    ).lower()
    if "queuepool" in scanner_err or "timed out" in scanner_err:
        errors.append(f"scanner_pool_error={scanner_err[:120]}")
    return {
        "name": "scheduler_health",
        "passed": len(errors) == 0,
        "errors": errors,
        "health": health,
    }


def evaluate_dashboard_endpoint(
    name: str,
    fetch_result: dict[str, Any],
    *,
    require_partial_false: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    status = fetch_result.get("status")
    body = fetch_result.get("body") or {}
    if status != 200:
        errors.append(f"status={status}")
    if fetch_result.get("parse_error"):
        errors.append(f"parse_error={fetch_result['parse_error']}")
    if body.get("ok") is False:
        errors.append(f"ok=false error={body.get('error')}")
    if name == "normal_carts":
        if body.get("error") and "ImportError" in str(body.get("error")):
            errors.append("import_error_in_body")
        perf = body.get("_perf") or {}
        if bool(perf.get("partial")):
            errors.append("partial=true")
        if bool(perf.get("degraded")):
            errors.append("degraded=true")
        if perf.get("timeout_stage"):
            errors.append(f"timeout_stage={perf.get('timeout_stage')}")
    if require_partial_false and name == "normal_carts":
        perf = body.get("_perf") or {}
        if perf and bool(perf.get("partial")):
            errors.append("partial=true")
    return {
        "name": name,
        "passed": len(errors) == 0,
        "errors": errors,
        "status": status,
        "body_ok": body.get("ok"),
        "perf": (body.get("_perf") if name == "normal_carts" else None),
    }


def run_production_deployment_gate(
    base_url: str,
    *,
    cookies: Optional[list[dict[str, Any]]] = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    base = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []

    scheduler_fetch = _fetch_json(f"{base}/health/scheduler", timeout=timeout)
    scheduler_body = scheduler_fetch.get("body") or {}
    checks.append(evaluate_scheduler_gate(scheduler_body))

    pool_body = scheduler_body.get("db_pool") or {}
    checks.append(evaluate_pool_health_gate(pool_body))

    dashboard_paths = {
        "normal_carts": f"{base}/api/dashboard/normal-carts?debug_perf=1",
        "vip_carts": f"{base}/api/dashboard/vip-carts?debug_perf=1",
        "refresh_state": f"{base}/api/dashboard/refresh-state",
        "summary": f"{base}/api/dashboard/summary",
    }
    for name, path in dashboard_paths.items():
        result = _fetch_json(path, timeout=timeout, cookies=cookies)
        checks.append(
            evaluate_dashboard_endpoint(
                name,
                result,
                require_partial_false=name == "normal_carts",
            )
        )

    passed = all(bool(c.get("passed")) for c in checks)
    return {
        "passed": passed,
        "base_url": base,
        "checks": checks,
    }


__all__ = [
    "evaluate_dashboard_endpoint",
    "evaluate_pool_health_gate",
    "evaluate_scheduler_gate",
    "run_production_deployment_gate",
]
