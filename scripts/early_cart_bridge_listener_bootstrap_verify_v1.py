# -*- coding: utf-8 -*-
"""Early Cart Bridge Listener Bootstrap v1 — production storefront verify."""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONY = (
    "https://4hz49e.zid.store/products/"
    "%D8%B3%D9%88%D9%86%D9%89-a7-%D8%A7%D9%84%D8%A7%D8%B5%D8%AF%D8%A7%D8%B1-%D8%A7%D9%84%D8%AA%D8%A7%D9%84%D8%AA"
)
EXPECTED_RUNTIME = "v2-early-cart-bridge-listener-bootstrap-v1"
OUT = Path(__file__).resolve().parent / "_early_cart_bridge_listener_bootstrap_v1_out"
HESITATION_WAIT_MS = 25_000


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify_logs(logs: list[str]) -> dict[str, Any]:
    received = [t for t in logs if "[CF TRIGGER RECEIVED]" in t]
    blocked = [
        t for t in logs if "[CF TRIGGER BLOCKED]" in t and "BLOCKED REASON" not in t
    ]
    blocked_reason = [t for t in logs if "[CF TRIGGER BLOCKED REASON]" in t]
    decision = [t for t in logs if "[CF TRIGGER DECISION]" in t]
    scheduled = [t for t in logs if "[CF TRIGGER SCHEDULED]" in t]
    replay = [t for t in logs if "[CF TRIGGER DEFERRED REPLAY]" in t]
    early_cap = [t for t in logs if "[CF EARLY CART CLICK CAPTURED]" in t]
    early_rep = [t for t in logs if "[CF EARLY CART CLICK REPLAY]" in t]
    early_diag = [t for t in logs if "[CF EARLY CART CLICK REPLAY DIAGNOSTIC]" in t]
    cart_source = [t for t in logs if "[CF CART EVENT SOURCE]" in t]
    armed = scheduled or replay or any("allowed: true" in d for d in decision)
    explicit_block = bool(blocked) or bool(blocked_reason) or bool(early_diag)
    silent = (
        not received
        and not blocked
        and not decision
        and not replay
        and not early_rep
        and not cart_source
        and not explicit_block
    )
    return {
        "received": received,
        "blocked": blocked,
        "blocked_reason": blocked_reason,
        "decision": decision,
        "scheduled": scheduled,
        "replay": replay,
        "early_captured": early_cap,
        "early_replay": early_rep,
        "early_diagnostic": early_diag,
        "cart_source": cart_source,
        "armed_or_blocked": armed
        or bool(blocked)
        or bool(early_rep)
        or bool(cart_source)
        or explicit_block,
        "silent_loss": silent,
    }


async def _run_scenario(playwright, label: str, wait_before_add_ms: int) -> dict[str, Any]:
    browser = await playwright.chromium.launch(headless=True)
    ctx = await browser.new_context(viewport={"width": 1280, "height": 900})
    page = await ctx.new_page()
    logs: list[str] = []
    cart_posts: list[dict[str, Any]] = []

    page.on("console", lambda m: logs.append((m.text or "")[:8000]))

    async def on_response(resp) -> None:
        if "/api/cart-event" not in resp.url or resp.request.method != "POST":
            return
        body = None
        try:
            body = await resp.json()
        except Exception:
            body = None
        cart_posts.append({"status": resp.status, "response": body})

    page.on("response", on_response)

    await page.goto(SONY, wait_until="domcontentloaded", timeout=120_000)
    if wait_before_add_ms > 0:
        await page.wait_for_timeout(wait_before_add_ms)

    runtime_before = await page.evaluate(
        """() => ({
          loader: window.__cartflow_loader_build || window.CARTFLOW_RUNTIME_VERSION || null,
          init_done: !!(window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Triggers),
          early_bound: !!(window.__CARTFLOW_EARLY_CART_BOOTSTRAP__ && window.__CARTFLOW_EARLY_CART_BOOTSTRAP__.isBound && window.__CARTFLOW_EARLY_CART_BOOTSTRAP__.isBound()),
          early_bound_at: window.__CARTFLOW_EARLY_CART_BOOTSTRAP__ && window.__CARTFLOW_EARLY_CART_BOOTSTRAP__.boundAt ? window.__CARTFLOW_EARLY_CART_BOOTSTRAP__.boundAt() : null,
        })"""
    )

    add = page.locator(
        'button:has-text("أضف"), button:has-text("Add"), [data-testid="add-to-cart"]'
    ).first
    await add.click(timeout=30_000)
    await page.wait_for_timeout(HESITATION_WAIT_MS)

    post = await page.evaluate(
        """() => ({
          loader: window.__cartflow_loader_build || window.CARTFLOW_RUNTIME_VERSION || null,
          shell_count: document.querySelectorAll('[data-cf-widget-root], [data-cartflow-bubble]').length,
          body_snippet: (document.querySelector('.cartflow-widget-body') || {}).innerText || null,
          have_cart: window.CartflowWidgetRuntime?.Triggers?.haveCartApprox?.(),
        })"""
    )
    await browser.close()

    cls = _classify_logs(logs)
    cart_post_ok = len(cart_posts) >= 1
    explicit_diag = bool(cls["early_diagnostic"]) or bool(cls["blocked"])
    no_dup_posts = len(cart_posts) <= 1
    no_dup_shell = (post.get("shell_count") or 0) <= 1
    return {
        "label": label,
        "wait_before_add_ms": wait_before_add_ms,
        "runtime_before_add": runtime_before,
        "runtime_after_wait": post.get("loader"),
        "expected_runtime": EXPECTED_RUNTIME,
        "runtime_match": post.get("loader") == EXPECTED_RUNTIME,
        "cart_event_posts": len(cart_posts),
        "cart_event_post_details": cart_posts[:3],
        "post_dom": post,
        "log_summary": {
            "received_count": len(cls["received"]),
            "blocked_count": len(cls["blocked"]),
            "decision_count": len(cls["decision"]),
            "scheduled_count": len(cls["scheduled"]),
            "replay_count": len(cls["replay"]),
            "early_captured_count": len(cls["early_captured"]),
            "early_replay_count": len(cls["early_replay"]),
            "early_diagnostic_count": len(cls["early_diagnostic"]),
            "cart_source_count": len(cls["cart_source"]),
        },
        "armed_or_blocked": cls["armed_or_blocked"],
        "silent_loss": cls["silent_loss"],
        "cart_event_or_diagnostic": cart_post_ok or explicit_diag,
        "no_duplicate_posts": no_dup_posts,
        "no_duplicate_shells": no_dup_shell,
        "sample_early_captured": cls["early_captured"][:2],
        "sample_early_replay": cls["early_replay"][:2],
        "sample_received": cls["received"][:3],
        "sample_blocked": cls["blocked"][:3],
        "pass": (
            cls["armed_or_blocked"]
            and not cls["silent_loss"]
            and (cart_post_ok or explicit_diag)
            and no_dup_posts
            and no_dup_shell
            and post.get("loader") == EXPECTED_RUNTIME
        ),
    }


async def main() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("NO_PLAYWRIGHT", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "audit": "early_cart_bridge_listener_bootstrap_v1_production_verify",
        "captured_at_utc": _utc(),
        "storefront": "https://4hz49e.zid.store",
        "expected_runtime": EXPECTED_RUNTIME,
        "scenarios": [],
    }
    scenarios = [
        ("immediate_after_dcl", 0),
        ("before_init_500ms", 500),
        ("before_init_800ms", 800),
        ("after_init_ready", 10_000),
    ]
    async with async_playwright() as pw:
        for label, wait_ms in scenarios:
            report["scenarios"].append(await _run_scenario(pw, label, wait_ms))

    report["all_pass"] = all(s.get("pass") for s in report["scenarios"])
    out_path = OUT / "verify_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"all_pass": report["all_pass"], "out": str(out_path)}, indent=2))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
