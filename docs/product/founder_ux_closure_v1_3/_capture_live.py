# -*- coding: utf-8 -*-
"""LIVE founder evidence: R17 + real CDC sidebar states. 6 mobile shots."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

OUT = Path(__file__).resolve().parent / "live"
DESKTOP = Path(
    r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Founder_UX_Closure_V1_3"
)
PROOF = Path(__file__).resolve().parent / "live_proof.json"
LAB_EMAIL = "reality.lab@cartflow.local"
LAB_PASSWORD = "LiveRealityLab-Prod-Tenant-V1!"
FE_EMAIL = "founder.evaluation@cartflow.local"
FE_PASSWORD = "FounderEval-Prod-Tenant-V1!"
BASE = "https://smartreplyai.net"

SHOTS = [
    "01_home_evidence_ratio_mobile.png",
    "02_workspace_why_distinct_mobile.png",
    "03_workspace_accept_execute_sequence_mobile.png",
    "04_sidebar_ready_action_chosen_mobile.png",
    "05_sidebar_measuring_recheck_mobile.png",
    "06_home_workspace_final_consistency_mobile.png",
]


def _apply(page, scenario_id: str) -> dict:
    resp = page.request.post(
        f"{BASE}/api/live-reality-lab/v1/apply",
        data=json.dumps({"scenario_id": scenario_id}),
        headers={"Content-Type": "application/json"},
    )
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text()[:400]}
    return {"status": resp.status, "ok": bool((body or {}).get("ok")), "body": body}


def _summary(page) -> dict:
    resp = page.request.get(f"{BASE}/api/dashboard/summary")
    try:
        return resp.json()
    except Exception:
        return {}


def _ldh_slice(summary: dict) -> dict:
    pkg = summary.get("live_decision_hierarchy_v1") or {}
    ws = pkg.get("workspace") or {}
    home = pkg.get("home") or {}
    side = pkg.get("sidebar") or {}
    return {
        "enabled": pkg.get("enabled"),
        "store_slug": pkg.get("store_slug"),
        "cdc_phase": (pkg.get("truth") or {}).get("cdc_phase"),
        "title_ar": ws.get("title_ar"),
        "why_now_ar": ws.get("why_now_ar"),
        "evidence_ar": ws.get("evidence_ar") or (home.get("now") or {}).get("evidence_ar"),
        "monitoring": (home.get("monitoring") or [{}])[0].get("body_ar")
        if home.get("monitoring")
        else None,
        "journey_current": (ws.get("journey") or {}).get("current_step"),
        "sidebar": [
            {"id": i.get("id"), "label": i.get("label")} for i in (side.get("items") or [])
        ],
        "completed_supported": side.get("completed_supported"),
        "later": bool(home.get("later")),
    }


def _stitch(top_path: Path, bottom_path: Path, dest: Path) -> None:
    if Image is None:
        shutil.copy2(top_path, dest)
        return
    a = Image.open(top_path).convert("RGB")
    b = Image.open(bottom_path).convert("RGB")
    w = max(a.width, b.width)
    out = Image.new("RGB", (w, a.height + b.height), (255, 255, 255))
    out.paste(a, (0, 0))
    out.paste(b, (0, a.height))
    out.save(dest)


def _copy(dest: Path) -> None:
    DESKTOP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest, DESKTOP / dest.name)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DESKTOP.mkdir(parents=True, exist_ok=True)
    proof: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="ar-SA",
        )
        page = context.new_page()
        page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
        page.fill('input[name="email"]', LAB_EMAIL)
        page.fill('input[name="password"]', LAB_PASSWORD)
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_url("**/dashboard**", timeout=60000)
        page.wait_for_timeout(800)

        r17 = _apply(page, "R17_shipping_hesitation")
        proof["r17_apply"] = {"status": r17["status"], "ok": r17["ok"]}
        page.wait_for_timeout(1200)
        summary = _summary(page)
        proof["r17"] = _ldh_slice(summary)

        def snap_tmp(name: str) -> Path:
            dest = OUT / name
            page.screenshot(path=str(dest), full_page=False)
            print("wrote", dest)
            return dest

        page.goto(BASE + "/dashboard#home", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("[data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        snap_tmp(SHOTS[0])
        _copy(OUT / SHOTS[0])

        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.evaluate("try{sessionStorage.removeItem('cf2_ldh_v1')}catch(e){}")
        page.reload(wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(1000)
        snap_tmp(SHOTS[1])
        _copy(OUT / SHOTS[1])
        page.locator("[data-cf2-ldh-journey='1']").first.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        snap_tmp(SHOTS[2])
        _copy(OUT / SHOTS[2])

        handle = page.locator("#cf2-ctx-handle")
        if handle.count():
            handle.first.click()
            page.wait_for_timeout(700)
        ready_side = snap_tmp("_tmp_sidebar_ready.png")
        if page.locator("#cf2-ctx-close").count():
            page.locator("#cf2-ctx-close").first.click()
            page.wait_for_timeout(300)

        r8 = _apply(page, "R8_action_chosen")
        proof["r8_apply"] = {"status": r8["status"], "ok": r8["ok"]}
        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        proof["r8"] = _ldh_slice(_summary(page))
        if handle.count():
            handle = page.locator("#cf2-ctx-handle")
            handle.first.click()
            page.wait_for_timeout(700)
        chosen_side = snap_tmp("_tmp_sidebar_action_chosen.png")
        _stitch(ready_side, chosen_side, OUT / SHOTS[3])
        _copy(OUT / SHOTS[3])
        if page.locator("#cf2-ctx-close").count():
            page.locator("#cf2-ctx-close").first.click()

        r9 = _apply(page, "R9_under_measurement")
        proof["r9_apply"] = {"status": r9["status"], "ok": r9["ok"]}
        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        proof["r9"] = _ldh_slice(_summary(page))
        handle = page.locator("#cf2-ctx-handle")
        if handle.count():
            handle.first.click()
            page.wait_for_timeout(700)
        meas_side = snap_tmp("_tmp_sidebar_measuring.png")
        if page.locator("#cf2-ctx-close").count():
            page.locator("#cf2-ctx-close").first.click()

        r10 = _apply(page, "R10_recheck_due")
        proof["r10_apply"] = {"status": r10["status"], "ok": r10["ok"]}
        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        proof["r10"] = _ldh_slice(_summary(page))
        handle = page.locator("#cf2-ctx-handle")
        if handle.count():
            handle.first.click()
            page.wait_for_timeout(700)
        recheck_side = snap_tmp("_tmp_sidebar_recheck.png")
        _stitch(meas_side, recheck_side, OUT / SHOTS[4])
        _copy(OUT / SHOTS[4])

        r17b = _apply(page, "R17_shipping_hesitation")
        proof["r17_restore"] = {"status": r17b["status"], "ok": r17b["ok"]}
        page.goto(BASE + "/dashboard#home", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("[data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        home_final = snap_tmp("_tmp_home_final.png")
        page.goto(BASE + "/dashboard#workspace", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("#cf2-workspace-root [data-cf2-ldh='1']", timeout=25000)
        page.wait_for_timeout(800)
        ws_final = snap_tmp("_tmp_workspace_final.png")
        _stitch(home_final, ws_final, OUT / SHOTS[5])
        _copy(OUT / SHOTS[5])
        proof["r17_final"] = _ldh_slice(_summary(page))

        fe = context.browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="ar-SA",
        )
        fe_page = fe.new_page()
        fe_page.goto(BASE + "/login", wait_until="networkidle", timeout=90000)
        fe_page.fill('input[name="email"]', FE_EMAIL)
        fe_page.fill('input[name="password"]', FE_PASSWORD)
        fe_page.click('button[type="submit"], input[type="submit"]')
        fe_page.wait_for_url("**/dashboard**", timeout=60000)
        fe_apply = fe_page.request.post(
            f"{BASE}/api/live-reality-lab/v1/apply",
            data=json.dumps({"scenario_id": "R17_shipping_hesitation"}),
            headers={"Content-Type": "application/json"},
        )
        fe_sum = fe_page.request.get(f"{BASE}/api/dashboard/summary")
        try:
            fe_body = fe_sum.json()
        except Exception:
            fe_body = {}
        proof["founder_eval"] = {
            "apply_status": fe_apply.status,
            "summary_has_ldh": "live_decision_hierarchy_v1" in fe_body,
        }
        fe.close()
        browser.close()

    PROOF.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PROOF", PROOF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
