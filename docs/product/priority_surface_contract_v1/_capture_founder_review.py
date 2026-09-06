# -*- coding: utf-8 -*-
"""
Priority Surface Contract V1 — founder screenshots (local production-shaped UI).

6 shots. Real /dashboard?cf_ui=v2. Injects summary paint for lane proof.
No deploy. No ranking change.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "founder_review_v1"
DESKTOP = Path(
    r"C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Priority_Surface_Contract_V1"
)

SHOTS = [
    ("01_home_two_lane_mobile.png", 390, "home"),
    ("02_home_commercial_only_mobile.png", 390, "home"),
    ("03_home_operational_only_mobile.png", 390, "home"),
    ("04_workspace_two_lane_mobile.png", 390, "workspace"),
    ("05_home_two_lane_desktop.png", 1280, "home"),
    ("06_workspace_two_lane_desktop.png", 1280, "workspace"),
]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = int(s.getsockname()[1])
    s.close()
    return p


def _hes_ops_pkg(*, title: str, diagnosis: str, recommendation: str) -> dict:
    return {
        "ok": True,
        "sections": [
            {
                "id": "decisions",
                "title_ar": "أهم قرار اليوم",
                "summary_ar": title,
                "diagnosis_ar": diagnosis,
                "recommendation_ar": recommendation,
                "dominant": True,
                "executive_rank": 1,
                "empty": False,
                "view_details_href": "#workspace",
            }
        ],
        "operational_guidance_v1": {
            "ok": True,
            "family": "communication_followup",
            "home_surface": {
                "what_we_see_ar": diagnosis,
                "what_it_means_ar": "مسار الاسترجاع متوقف بلا تواصل صالح.",
                "what_to_do_now_ar": recommendation,
                "when_to_recheck_ar": "أعد الفحص عندما ينخفض عدد السلال بلا رقم.",
            },
        },
    }


def _catalog_focus() -> dict:
    return {
        "ok": True,
        "empty": False,
        "primary": {
            "opportunity_id": "col:product_opportunity_focus:product_trust:cf_founder_evaluation",
            "family": "product_opportunity_focus",
            "truth_class": "PRODUCTION_TRUTH_READY",
            "title_ar": "تركيز الانتباه على ثقة المنتج",
            "why_ar": "أسباب الجودة/الضمان مجتمعة — تركّز يستحق توضيح ثقة المنتج.",
            "action_ar": "ركّز على توضيح ثقة المنتج من الأدلة المسجّلة فقط.",
            "measure_ar": "حصة أسباب ثقة المنتج خلال 7 أيام.",
            "recheck_ar": "أعد النظر بعد نافذة القياس.",
            "mission_ready": True,
            "cdc_phase": None,
            "workspace_href": "#workspace",
        },
        "secondaries": [],
        "suppressed_count": 0,
        "explain": {
            "why_this_one_now_ar": "أدلة ثقة المنتج جاهزة كمهمة تجارية."
        },
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    db_path = os.path.join(tempfile.gettempdir(), "cartflow_priority_surface_contract_v1.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
    env["ENV"] = "development"
    env["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
    env["CARTFLOW_MERCHANT_UI_V2"] = "1"
    env["CARTFLOW_CART_WORKSPACE_V1"] = "true"
    env["CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"] = "1"
    env["SECRET_KEY"] = "priority-surface-contract-v1-local"

    sys.path.insert(0, str(ROOT))
    for k, v in env.items():
        os.environ[k] = v

    from extensions import db, init_database  # noqa: E402
    import models  # noqa: F401, E402
    from schema_commercial_decision_commitment_v1 import (  # noqa: E402
        ensure_commercial_decision_commitment_schema,
        reset_commercial_decision_commitment_schema_guard_for_tests,
    )
    from services.founder_evaluation_reality_v1.constants_v1 import (  # noqa: E402
        EMAIL_FOCUS,
        EMAIL_INSUFFICIENT,
        EMAIL_QUALITY,
    )
    from services.founder_evaluation_reality_v1.seed_v1 import (  # noqa: E402
        seed_founder_evaluation_tenants_v1,
    )
    from services.merchant_auth_http import (  # noqa: E402
        issue_merchant_session_cookie_value,
        merchant_cookie_name,
    )
    from services.merchant_auth_v1 import get_merchant_user_by_email  # noqa: E402

    init_database()
    db.create_all()
    reset_commercial_decision_commitment_schema_guard_for_tests()
    ensure_commercial_decision_commitment_schema(db)
    seed_info = seed_founder_evaluation_tenants_v1(reset=True)

    def cookie_for_email(email: str) -> str:
        user = get_merchant_user_by_email(email)
        assert user is not None
        return issue_merchant_session_cookie_value(int(user.id))

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(base + "/ping", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("server_start_timeout")

        two_lane = {
            "store_slug": "cf_founder_evaluation",
            "ok": True,
            "home_executive_summary_v1": _hes_ops_pkg(
                title="تأمين وسيلة تواصل للسلال المعلّقة",
                diagnosis="يوجد 39 سلة تحتاج متابعة لكن رقم التواصل غير متاح.",
                recommendation="اجمع وسيلة اتصال للسلال ذات الأولوية بلا رقم.",
            ),
            "mission_catalog_v1": _catalog_focus(),
            "mission_portfolio_v1": {
                "ok": True,
                "capacity": {
                    "max_active": 1,
                    "active_count": 0,
                    "available_slots": 1,
                },
                "active_mission": None,
                "ready_consumes_capacity": False,
            },
            "commercial_opportunity_layer_v1": {"ok": True, "enabled": True},
        }
        commercial_only = {
            "store_slug": "cf_fe_v1_quality",
            "ok": True,
            "home_executive_summary_v1": {
                "ok": True,
                "sections": [
                    {
                        "id": "health",
                        "title_ar": "حالة المتجر",
                        "summary_ar": "المتجر مستقر.",
                        "dominant": True,
                        "executive_rank": 1,
                        "empty": False,
                    }
                ],
            },
            "mission_catalog_v1": {
                "ok": True,
                "empty": False,
                "primary": {
                    "opportunity_id": "col:product_confidence:quality:cf_fe_v1_quality",
                    "family": "product_confidence",
                    "title_ar": "تعزيز ثقة المنتج",
                    "why_ar": "ضعف ثقة المنتج يظهر كتردّد متكرر.",
                    "action_ar": "وضّح إثباتات المنتج — بلا خصم.",
                    "measure_ar": "حصة سبب الجودة.",
                    "recheck_ar": "أعد النظر بعد 7 أيام.",
                    "mission_ready": True,
                    "truth_class": "PRODUCTION_TRUTH_READY",
                },
                "secondaries": [],
                "suppressed_count": 0,
                "explain": {"why_this_one_now_ar": "أدلة الجودة جاهزة."},
            },
            "mission_portfolio_v1": {
                "ok": True,
                "capacity": {"active_count": 0, "available_slots": 1},
                "ready_consumes_capacity": False,
            },
        }
        ops_only = {
            "store_slug": "cf_fe_v1_insufficient",
            "ok": True,
            "home_executive_summary_v1": _hes_ops_pkg(
                title="تأمين وسيلة تواصل للسلال المعلّقة",
                diagnosis="يوجد 5 سلال بلا رقم.",
                recommendation="اجمع وسيلة اتصال صالحة.",
            ),
            "mission_catalog_v1": {
                "ok": True,
                "empty": True,
                "primary": None,
                "secondaries": [],
                "suppressed_count": 0,
                "explain": {
                    "why_this_one_now_ar": "لا توجد مهمة تجارية جاهزة من أدلة متجرك الآن."
                },
            },
            "mission_portfolio_v1": {
                "ok": True,
                "capacity": {"active_count": 0, "available_slots": 1},
                "ready_consumes_capacity": False,
            },
        }

        summaries = {
            "01": (EMAIL_FOCUS, two_lane),
            "02": (EMAIL_QUALITY, commercial_only),
            "03": (EMAIL_INSUFFICIENT, ops_only),
            "04": (EMAIL_FOCUS, two_lane),
            "05": (EMAIL_FOCUS, two_lane),
            "06": (EMAIL_FOCUS, two_lane),
        }

        from playwright.sync_api import sync_playwright

        captures = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for fname, width, surface in SHOTS:
                key = fname[:2]
                email, summary = summaries[key]
                height = 900 if width >= 1280 else 844
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=2,
                )
                context.add_cookies(
                    [
                        {
                            "name": merchant_cookie_name(),
                            "value": cookie_for_email(email),
                            "domain": "127.0.0.1",
                            "path": "/",
                            "httpOnly": False,
                            "secure": False,
                            "sameSite": "Lax",
                        }
                    ]
                )
                page = context.new_page()
                hash_path = "#workspace" if surface == "workspace" else "#home"
                page.goto(
                    base + "/dashboard?cf_ui=v2" + hash_path,
                    wait_until="domcontentloaded",
                )
                page.wait_for_timeout(900)
                meta = page.evaluate(
                    """(args) => {
  const summary = args.summary;
  const surface = args.surface;
  document.querySelectorAll('[data-cf2-page]').forEach(el => {
    el.hidden = el.getAttribute('data-cf2-page') !== (surface === 'workspace' ? 'workspace' : 'home');
  });
  if (surface === 'home') {
    const host = document.getElementById('cf2-home-root')
      || document.querySelector('[data-cf2-page=\"home\"]');
    if (host && window.CartFlowUiV2Home && window.CartFlowUiV2Home.paint) {
      window.CartFlowUiV2Home.paint(host, summary);
    }
  } else {
    try {
      sessionStorage.setItem('cf2_col_focus_v1', JSON.stringify(
        (summary.mission_catalog_v1 && summary.mission_catalog_v1.primary) || {}
      ));
    } catch (e) {}
    const host = document.querySelector('[data-cf2-page=\"workspace\"]')
      || document.getElementById('cf2-workspace-root');
    if (host && window.CartFlowUiV2Workspace && window.CartFlowUiV2Workspace.render) {
      const projection = {
        zone_b: [{
          is_primary_decision: true,
          decision_sentence_ar: 'راجع أولوية إصلاح التقاط وسيلة التواصل.',
          diagnosis_ar: 'متابعة مقيدة بلا رقم.',
          operational_guidance_v1: {
            workspace_surface: {
              diagnosis_ar: 'متابعة مقيدة بلا رقم.',
              recommendation_ar: 'أمّن وسيلة تواصل قبل حملات جديدة.',
              why_ar: 'بلا تواصل لا تُنفَّذ متابعة.',
              action_ar: 'اجمع وسيلة اتصال للسلال ذات الأولوية.',
              recheck_condition_ar: 'عندما ينخفض العدد بلا رقم.'
            }
          },
          evidence_lines_ar: ['سلال بلا رقم ظاهرة في صحة المتجر.'],
          view_details_href: '#communication'
        }]
      };
      host.innerHTML = window.CartFlowUiV2Workspace.render(projection);
    }
  }
  const ops = document.querySelector('[data-cf2-priority-lane=\"operational\"]');
  const com = document.querySelector('[data-cf2-priority-lane=\"commercial\"]');
  return {
    ops: !!(ops && (ops.innerText || '').indexOf('إجراء تشغيلي') >= 0),
    commercial: !!(com && (com.innerText || '').indexOf('المهمة التجارية') >= 0),
    banned: !!(document.body.innerText || '').match(/مركز الجاذبية|ما أهم مهمة|ما الذي أحتاج فعله الآن/),
  };
}""",
                    {"summary": summary, "surface": surface},
                )
                if meta.get("banned"):
                    raise RuntimeError(f"{fname} banned competing heading: {meta}")
                if key in ("01", "04", "05", "06"):
                    if not meta.get("ops") or not meta.get("commercial"):
                        raise RuntimeError(f"{fname} two-lane fail: {meta}")
                if key == "02" and not meta.get("commercial"):
                    raise RuntimeError(f"{fname} commercial-only fail: {meta}")
                if key == "03" and not meta.get("ops"):
                    raise RuntimeError(f"{fname} ops-only fail: {meta}")

                page.screenshot(path=str(OUT / fname), full_page=False)
                captures.append({"file": fname, "meta": meta, "email": email})
                context.close()

            browser.close()

        if DESKTOP.exists():
            shutil.rmtree(DESKTOP)
        DESKTOP.mkdir(parents=True, exist_ok=True)
        for fname, _, _ in SHOTS:
            shutil.copy2(OUT / fname, DESKTOP / fname)

        (OUT / "MANIFEST.md").write_text(
            "\n".join(
                [
                    "# Priority Surface Contract V1 — Founder Review",
                    "",
                    "Two lanes: إجراء تشغيلي مطلوب · المهمة التجارية الحالية",
                    "No ranking / CDC / Portfolio / OGL logic change.",
                    "",
                    *[f"- {f[0]}" for f in SHOTS],
                    "",
                    f"FOUNDER DESKTOP PATH: {DESKTOP}",
                    f"SCREENSHOT COUNT: {len(SHOTS)}",
                    "DESKTOP COPY READY: YES",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (OUT / "PATH_PROOF.json").write_text(
            json.dumps(
                {
                    "shots": [s[0] for s in SHOTS],
                    "captures": captures,
                    "seed": seed_info,
                    "desktop": str(DESKTOP),
                    "canonical": str(OUT),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print("CAPTURE_OK", OUT)
        print("DESKTOP", DESKTOP)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
