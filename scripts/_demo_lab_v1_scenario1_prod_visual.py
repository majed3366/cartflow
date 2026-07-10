# -*- coding: utf-8 -*-
"""Demo Lab P2 — production visual capture (report only, no fixes).

Captures Home/Cart desktop+mobile on smartreplyai.net.
Does NOT run Lab Scenario 1 on production (Lab not deployed).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "https://smartreplyai.net"
OUT = Path(__file__).resolve().parent / "_demo_lab_v1_scenario1_out" / "prod_visual"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "task": "Demo Lab P2 production visual verification",
        "ts": _utc(),
        "base": BASE,
        "lab_deployed": False,
        "note": "Lab P1/P2 not on origin/main — screenshots are current production baseline only",
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ar-SA")
        page = context.new_page()

        uid = uuid.uuid4().hex[:8]
        email = f"cf.lab.vis.{uid}@smartreplyai.net"
        password = f"CfLabVis!{uid}"
        page.goto(f"{BASE}/signup", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.locator('input[name="store_name"]').fill(f"Lab Vis {uid}", timeout=60000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').first.fill(password)
        page.locator('input[name="confirm_password"]').fill(password)
        page.get_by_role("button", name="إنشاء الحساب").click()
        page.wait_for_timeout(5000)
        report["email"] = email
        report["after_signup_url"] = page.url

        # Home desktop
        page.goto(f"{BASE}/dashboard#home", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "01_home_desktop.png"), full_page=True)

        home_probe = page.evaluate(
            """async () => {
              const root = document.getElementById('ma-home-experience-root');
              const pulse = root && root.querySelector('.ma-pulse-v1');
              const slots = pulse
                ? Array.from(pulse.querySelectorAll('[data-pulse-slot]')).map(el => ({
                    key: el.getAttribute('data-pulse-slot'),
                    status: el.getAttribute('data-pulse-status'),
                    label: ((el.querySelector('.ma-pulse-slot__label') || {}).textContent || '').trim(),
                    message: ((el.querySelector('.ma-pulse-slot__message') || {}).textContent || '').trim(),
                  }))
                : [];
              let summary = null;
              try {
                const r = await fetch('/api/dashboard/summary?_=' + Date.now(), {
                  credentials: 'same-origin',
                  headers: { Accept: 'application/json' },
                });
                const j = await r.json();
                const pulseJ = j.merchant_pulse_v1 || null;
                const sig = j.commerce_signals_v1 || null;
                summary = {
                  ok: j.ok,
                  store_slug: j.store_slug || null,
                  has_pulse: !!pulseJ,
                  pulse_fork: pulseJ && pulseJ.fork,
                  pulse_brief: pulseJ && pulseJ.executive_brief && pulseJ.executive_brief.message,
                  pulse_progress: pulseJ && pulseJ.cartflow_progress && pulseJ.cartflow_progress.message,
                  commerce_signals_used: pulseJ && pulseJ.sources && pulseJ.sources.commerce_signals_used,
                  signal_count: sig && (sig.signal_count || (sig.signals || []).length),
                  signal_types: sig && (sig.signals || []).map(s => s.signal_type).slice(0, 12),
                };
              } catch (e) {
                summary = { error: String(e) };
              }
              return {
                pulse_dom_present: !!pulse,
                slots,
                body_text_sample: (document.body.innerText || '').slice(0, 1200),
                summary,
              };
            }"""
        )
        report["home_desktop"] = home_probe
        (OUT / "01_home_desktop_probe.json").write_text(
            json.dumps(home_probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Home mobile
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "02_home_mobile.png"), full_page=True)

        # Carts desktop
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{BASE}/dashboard#carts", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)
        page.screenshot(path=str(OUT / "03_carts_desktop.png"), full_page=True)
        carts_probe = page.evaluate(
            """() => {
              const text = (document.body.innerText || '');
              return {
                has_449: text.includes('449'),
                has_completed_ar: /مكتمل|مكتملة|مشترى|تم الشراء|مسترد|استرداد/.test(text),
                has_internal_recovery_path: text.includes('اكتمل مسار استرجاع'),
                sample: text.slice(0, 1500),
              };
            }"""
        )
        report["carts_desktop"] = carts_probe

        # Carts mobile
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "04_carts_mobile.png"), full_page=True)

        # Completed tab if present
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(500)
        completed_clicked = page.evaluate(
            """() => {
              const candidates = Array.from(document.querySelectorAll('button, a, [role=\"tab\"]'));
              const el = candidates.find(n => /مكتمل|مكتملة|منته|archived|completed/i.test((n.textContent || '').trim()));
              if (el) { el.click(); return (el.textContent || '').trim(); }
              return null;
            }"""
        )
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "05_carts_completed_desktop.png"), full_page=True)
        report["completed_tab_clicked"] = completed_clicked
        completed_probe = page.evaluate(
            """() => {
              const text = (document.body.innerText || '');
              return {
                has_449: text.includes('449'),
                has_internal_recovery_path: text.includes('اكتمل مسار استرجاع'),
                sample: text.slice(0, 1500),
              };
            }"""
        )
        report["carts_completed"] = completed_probe

        # Demo storefront (public) — not merchant Home
        page.goto(f"{BASE}/demo/store?store_slug=demo", timeout=120000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "06_demo_storefront.png"), full_page=False)
        report["demo_storefront_url"] = page.url

        browser.close()

    # Product language checks against desired outcome
    brief = ((home_probe.get("summary") or {}).get("pulse_brief") or "")
    progress = ((home_probe.get("summary") or {}).get("pulse_progress") or "")
    slots = home_probe.get("slots") or []
    slot_msgs = " | ".join(s.get("message") or "" for s in slots)
    combined = f"{brief} {progress} {slot_msgs}"
    report["product_language"] = {
        "desired_meaning": "خلال غيابك تم استرداد عملية شراء واحدة بقيمة 449 SR",
        "shows_desired_449_recovery": (
            ("449" in combined)
            and (("استرداد" in combined) or ("استرجع" in combined) or ("شراء" in combined))
        ),
        "shows_only_internal_path_copy": (
            "اكتمل مسار استرجاع بعد تأكيد الشراء" in combined
            and "449" not in combined
        ),
        "observed_brief": brief,
        "observed_progress": progress,
        "observed_slot_messages": [s.get("message") for s in slots],
    }

    (OUT / "prod_visual_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["product_language"], ensure_ascii=False, indent=2))
    print("screenshots=", sorted(p.name for p in OUT.glob("*.png")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
