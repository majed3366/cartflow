# -*- coding: utf-8 -*-
"""
Production truth verification — Carts Archive/Reopen + Filter chips.

Probes smartreplyai.net for:
1) Archive API success + DB persistence (via normal-carts overlay fields)
2) Archived cart excluded from active after poll
3) Reopen action on completed/archived rows
4) Filter chips change visible MI queue set

Usage:
  set CARTFLOW_PROD_EMAIL / CARTFLOW_PROD_PASSWORD (optional; else signup seed)
  python scripts/_carts_archive_reopen_prod_truth_verify_v1.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = (os.environ.get("CARTFLOW_REVIEW_BASE") or "https://smartreplyai.net").rstrip("/")
OUT = Path(__file__).resolve().parent / "_carts_archive_reopen_prod_truth_v1_out"
COMMIT_HINT = "local-archive-truth-overlay"

_PVG = Path(__file__).resolve().parent / "_production_visual_gate.py"


def _load_pvg():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pvg_archive_truth", _PVG)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["pvg_archive_truth"] = mod
    spec.loader.exec_module(mod)
    return mod


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _auth(page, report: dict) -> None:
    email = (os.environ.get("CARTFLOW_PROD_EMAIL") or "").strip()
    password = (os.environ.get("CARTFLOW_PROD_PASSWORD") or "").strip()
    if email and password:
        page.goto(f"{BASE}/login", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.locator('input[name="email"]').fill(email, timeout=60000)
        page.locator('input[name="password"]').first.fill(password)
        page.get_by_role("button", name="دخول").click()
        page.wait_for_timeout(5000)
        report["auth"] = {"mode": "prod_merchant_login", "email": email}
        return
    uid = uuid.uuid4().hex[:8]
    email = f"archive.truth.{uid}@smartreplyai.net"
    password = f"ArchiveTruth!{uid}"
    page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.locator('input[name="store_name"]').fill(f"Archive Truth {uid}", timeout=60000)
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').first.fill(password)
    page.locator('input[name="confirm_password"]').fill(password)
    page.locator("button[type='submit']").click()
    page.wait_for_timeout(6000)
    report["auth"] = {"mode": "signup_seeded", "email": email}


def _fetch_normal_carts(page) -> dict:
    return page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/normal-carts?_ts=' + Date.now(), {
            credentials: 'same-origin',
            cache: 'no-store',
          });
          const body = await r.json();
          return {
            ok: !!body.ok,
            status: r.status,
            active: (body.merchant_carts_page_rows || []).length,
            archived: (body.merchant_archived_carts_page_rows || []).length,
            overlay: !!body.merchant_archive_truth_overlay,
            freshness: body.data_freshness || null,
            hot_rows: body.hot_slice_rows,
            active_keys: (body.merchant_carts_page_rows || []).map(
              (x) => x.recovery_key || ''
            ).filter(Boolean).slice(0, 40),
            archived_keys: (body.merchant_archived_carts_page_rows || []).map(
              (x) => x.recovery_key || ''
            ).filter(Boolean).slice(0, 40),
            archived_actions: (body.merchant_archived_carts_page_rows || []).map(
              (x) => ({
                rk: x.recovery_key || '',
                action: x.customer_lifecycle_dashboard_action || '',
                visual: !!x.customer_lifecycle_is_archived_visual,
              })
            ).slice(0, 20),
          };
        }"""
    )


def _post_archive(page, payload: dict) -> dict:
    return page.evaluate(
        """async (payload) => {
          const r = await fetch('/api/dashboard/cart-lifecycle/archive', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const body = await r.json().catch(() => ({}));
          return { status: r.status, body };
        }""",
        payload,
    )


def _post_reopen(page, payload: dict) -> dict:
    return page.evaluate(
        """async (payload) => {
          const r = await fetch('/api/dashboard/cart-lifecycle/reopen', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const body = await r.json().catch(() => ({}));
          return { status: r.status, body };
        }""",
        payload,
    )


def _pick_active_row(page) -> dict | None:
    return page.evaluate(
        """async () => {
          const r = await fetch('/api/dashboard/normal-carts?_ts=' + Date.now(), {
            credentials: 'same-origin',
            cache: 'no-store',
          });
          const body = await r.json();
          const rows = body.merchant_carts_page_rows || [];
          for (const mc of rows) {
            const rk = (mc.recovery_key || '').trim();
            if (!rk) continue;
            if (mc.customer_lifecycle_is_archived_visual) continue;
            return {
              recovery_key: rk,
              store_slug: mc.store_slug || mc.merchant_store_slug || '',
              abandoned_cart_id: mc.merchant_case_row_id || mc.id || null,
              session_id: mc.session_id || mc.recovery_session_id || '',
              cart_id: mc.cart_id || mc.zid_cart_id || '',
            };
          }
          return null;
        }"""
    )


def _filter_chip_probe(page) -> dict:
    page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="networkidle")
    page.wait_for_timeout(4000)
    return page.evaluate(
        """() => {
          const bar = document.getElementById('ma-cart-filters');
          const chips = {};
          const modes = ['all', 'recovered', 'sent', 'attention', 'nophone'];
          function visibleCount() {
            const root = document.getElementById('ma-carts-groups-v2');
            if (!root) return 0;
            let n = 0;
            root.querySelectorAll('.v2-queue-item').forEach((el) => {
              if (el.style.display === 'none' || el.hidden) return;
              n += 1;
            });
            return n;
          }
          const before = visibleCount();
          const results = {};
          modes.forEach((mode) => {
            const btn = bar && bar.querySelector('[data-filter=\"' + mode + '\"]');
            if (!btn) {
              results[mode] = { present: false };
              return;
            }
            btn.click();
            results[mode] = {
              present: true,
              hidden_attr: !!bar.hidden,
              display: getComputedStyle(bar).display,
              visible_items: visibleCount(),
              active: btn.classList.contains('active'),
            };
          });
          const allBtn = bar && bar.querySelector('[data-filter=\"all\"]');
          if (allBtn) allBtn.click();
          return {
            bar_present: !!bar,
            bar_hidden: !!(bar && bar.hidden),
            bar_display: bar ? getComputedStyle(bar).display : null,
            before_all_visible: before,
            chips: results,
            mi_items_have_filter_attr: !!(
              document.querySelector('#ma-carts-groups-v2 .v2-queue-item[data-ma-filter]')
            ),
          };
        }"""
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "generated_at_utc": _utc(),
        "base": BASE,
        "commit_hint": COMMIT_HINT,
        "checks": {},
        "verdict": "FAIL",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        try:
            _auth(page, report)
            page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="networkidle")
            page.wait_for_timeout(5000)

            before = _fetch_normal_carts(page)
            report["checks"]["baseline_normal_carts"] = before

            target = _pick_active_row(page)
            if not target:
                # Seed storefront carts so archive/reopen can be exercised.
                try:
                    pvg = _load_pvg()
                    seed_dir = OUT / "seed"
                    seed_dir.mkdir(parents=True, exist_ok=True)
                    for i in range(2):
                        sub = seed_dir / f"seed_{i + 1}"
                        sub.mkdir(parents=True, exist_ok=True)
                        page.evaluate(
                            """() => {
                              try {
                                sessionStorage.removeItem(
                                  'cartflow_cf_suppress_after_dismiss'
                                );
                              } catch (e) {}
                            }"""
                        )
                        pvg._widget_journey(
                            page,
                            product_selector="#p-perfume .add-btn",
                            flow_label=f"archive_seed_{i + 1}",
                            out_sub=sub,
                        )
                        page.wait_for_timeout(1200)
                    page.goto(
                        f"{BASE}/dashboard#carts",
                        timeout=120000,
                        wait_until="networkidle",
                    )
                    page.wait_for_timeout(8000)
                    report["checks"]["seeded_carts"] = True
                    before = _fetch_normal_carts(page)
                    report["checks"]["baseline_after_seed"] = before
                    target = _pick_active_row(page)
                except Exception as seed_exc:  # noqa: BLE001
                    report["checks"]["seed_error"] = str(seed_exc)[:400]

            report["checks"]["target_row"] = target
            if not target:
                report["checks"]["archive"] = {
                    "skipped": True,
                    "reason": "no_active_cart_to_archive",
                }
            else:
                rk = target["recovery_key"]
                arch = _post_archive(page, target)
                report["checks"]["archive_api"] = arch
                time.sleep(1.5)
                after_arch = _fetch_normal_carts(page)
                report["checks"]["after_archive_poll"] = after_arch
                in_active = rk in (after_arch.get("active_keys") or [])
                in_archived = rk in (after_arch.get("archived_keys") or [])
                report["checks"]["archive_persistence"] = {
                    "recovery_key": rk,
                    "still_in_active": in_active,
                    "in_archived_pool": in_archived,
                    "overlay_flag": after_arch.get("overlay"),
                    "pass": (not in_active) and in_archived and bool(arch.get("body", {}).get("ok")),
                }

                # Wait for a second poll window (snapshot/hot merge race)
                time.sleep(8)
                after_wait = _fetch_normal_carts(page)
                report["checks"]["after_archive_wait_poll"] = after_wait
                bounced = rk in (after_wait.get("active_keys") or [])
                report["checks"]["archive_survives_poll"] = {
                    "recovery_key": rk,
                    "bounced_to_active": bounced,
                    "pass": not bounced,
                }

                # Reopen action exposure on archived payload
                reopen_exposed = any(
                    (x.get("rk") == rk and x.get("action") == "reopen")
                    for x in (after_wait.get("archived_actions") or [])
                )
                report["checks"]["reopen_action_exposed"] = {
                    "pass": reopen_exposed,
                    "recovery_key": rk,
                }

                reo = _post_reopen(page, target)
                report["checks"]["reopen_api"] = reo
                time.sleep(1.5)
                after_reo = _fetch_normal_carts(page)
                report["checks"]["after_reopen_poll"] = after_reo
                report["checks"]["reopen_persistence"] = {
                    "recovery_key": rk,
                    "in_active": rk in (after_reo.get("active_keys") or []),
                    "in_archived": rk in (after_reo.get("archived_keys") or []),
                    "pass": rk in (after_reo.get("active_keys") or [])
                    and rk not in (after_reo.get("archived_keys") or []),
                }

            # Desktop filter chips
            desktop_filters = _filter_chip_probe(page)
            report["checks"]["filters_desktop"] = desktop_filters
            chip_vals = [
                (desktop_filters.get("chips") or {}).get(m, {}).get("visible_items")
                for m in ("all", "sent", "attention", "recovered", "nophone")
                if (desktop_filters.get("chips") or {}).get(m, {}).get("present")
            ]
            meaningful = len(set([v for v in chip_vals if v is not None])) > 1 or (
                desktop_filters.get("before_all_visible") or 0
            ) == 0
            report["checks"]["filters_desktop_meaningful"] = {
                "pass": bool(desktop_filters.get("mi_items_have_filter_attr"))
                and not desktop_filters.get("bar_hidden")
                and (desktop_filters.get("bar_display") != "none")
                and meaningful,
                "distinct_visible_counts": sorted(
                    set([v for v in chip_vals if v is not None])
                ),
            }

            # Mobile viewport
            page.set_viewport_size({"width": 390, "height": 844})
            mobile_filters = _filter_chip_probe(page)
            report["checks"]["filters_mobile"] = mobile_filters
            report["checks"]["filters_mobile_meaningful"] = {
                "pass": bool(mobile_filters.get("mi_items_have_filter_attr"))
                and (mobile_filters.get("bar_display") != "none"),
            }

            page.screenshot(path=str(OUT / "desktop_carts.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(OUT / "mobile_carts.png"), full_page=True)

        except Exception as exc:  # noqa: BLE001
            report["error"] = str(exc)[:500]
        finally:
            browser.close()

    passes = []
    for key in (
        "archive_persistence",
        "archive_survives_poll",
        "reopen_action_exposed",
        "reopen_persistence",
        "filters_desktop_meaningful",
        "filters_mobile_meaningful",
    ):
        node = report["checks"].get(key) or {}
        if "pass" in node:
            passes.append(bool(node["pass"]))
    if passes and all(passes):
        report["verdict"] = "PASS"
    elif report["checks"].get("archive", {}).get("skipped"):
        report["verdict"] = "INCONCLUSIVE_NO_CARTS"
    else:
        report["verdict"] = "FAIL"

    out_path = OUT / "prod_truth_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "report": str(out_path)}, indent=2))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
