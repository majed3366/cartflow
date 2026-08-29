# -*- coding: utf-8 -*-
from pathlib import Path
import json

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8767/docs/product/communication_product_composition_v1/verify_paint.html?mode=calm"

DESKTOP_JS = """() => {
  const r = document.querySelector('.cf2-comms');
  return {
    marker: r && r.getAttribute('data-cf2'),
    needs: r && r.getAttribute('data-cf-needs-merchant-response'),
    orient: document.querySelector('.cf2-comms__orient-h') && document.querySelector('.cf2-comms__orient-h').textContent,
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    wa: document.body.innerText.indexOf('فتح واتساب') >= 0,
    rowCount: document.querySelectorAll('.cf2-comms__row').length
  };
}"""

MOBILE_JS = """() => {
  const d = document.querySelector('.cf2-comms__detail');
  const h = document.querySelector('.cf2-comms__orient-h');
  return {
    detailDisplay: d ? getComputedStyle(d).display : null,
    overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    wrap: h ? getComputedStyle(h).overflowWrap : null
  };
}"""


def main() -> None:
    probe = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".cf2-comms")
        page.screenshot(path=str(OUT / "01_desktop_list.png"), full_page=True)
        page.screenshot(path=str(OUT / "02_desktop_selected.png"), full_page=True)
        page.screenshot(path=str(OUT / "05_desktop_detail_history.png"), full_page=True)
        page.click('[data-comms-filter="needs"]')
        page.screenshot(path=str(OUT / "04_desktop_needs_empty.png"), full_page=True)
        probe["desktop"] = page.evaluate(DESKTOP_JS)

        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector(".cf2-comms")
        page.screenshot(path=str(OUT / "06_mobile_list.png"), full_page=True)
        page.screenshot(path=str(OUT / "11_mobile_calm_state.png"), full_page=True)
        probe["mobile"] = page.evaluate(MOBILE_JS)
        browser.close()

    (ROOT / "production_probe.json").write_text(
        json.dumps(
            {
                "source": "local_verify_paint_127.0.0.1:8767",
                "label": "SAFE_LOCAL_RUNTIME — empty demo; no fabricated rows",
                "marker": "communication-product-composition-v1",
                "question": True,
                "rowCount": probe["desktop"]["rowCount"],
                "needsMerchantResponse": probe["desktop"]["needs"],
                "orientation": probe["desktop"]["orient"],
                "waCta": probe["desktop"]["wa"],
                "overflowX": probe["desktop"]["overflowX"],
                "merchantResponseAvailable": False,
                "automatedWaitingAvailable": False,
                "notes": [
                    "Local TestClient / demo store has 0 message rows and 0 follow-up rows.",
                    "Screenshots 03/07/08/09/10 omitted — those states were not present.",
                    "Do not declare PASS.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (ROOT / "mobile_overflow_probe.json").write_text(
        json.dumps(
            {
                "source": "local_verify_paint_127.0.0.1:8767",
                "viewport": "390x844",
                "overflowX": probe["mobile"]["overflowX"],
                "scrollWidth": probe["mobile"]["scrollWidth"],
                "clientWidth": probe["mobile"]["clientWidth"],
                "detailHiddenUntilSelect": probe["mobile"]["detailDisplay"] == "none",
                "overflowWrap": probe["mobile"]["wrap"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(probe)
    print("files", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
