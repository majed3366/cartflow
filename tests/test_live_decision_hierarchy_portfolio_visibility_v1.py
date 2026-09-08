# -*- coding: utf-8 -*-
"""Live Decision Hierarchy & Portfolio Visibility V1 — lab presentation gate."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    FAMILY_PRICE,
    FAMILY_SHIPPING,
    MISSION_SHIPPING_AR,
)
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.live_decision_hierarchy_v1 import (
    attach_live_decision_hierarchy_to_summary_v1,
    compose_live_decision_hierarchy_v1,
)
from services.live_decision_hierarchy_v1.contract_v1 import (
    AMBIGUOUS_NEXT_LABEL_AR,
    COMMERCIAL_STATUS_OWNER,
    FORBIDDEN_INSUFFICIENCY_AR,
    LABEL_MONITORING_AR,
    LABEL_NEXT_AR,
    LABEL_NOW_AR,
    OPERATIONAL_GUIDANCE_OWNER,
)
from services.mission_catalog_v1.compose_v1 import compose_mission_catalog_v1
from services.mission_portfolio_v1.compose_v1 import compose_mission_portfolio_v1

ROOT = Path(__file__).resolve().parents[1]
LAB = "cf_live_reality_lab"
NORMAL = "cf_founder_evaluation"
COUNTS = {"shipping": 12, "price": 5, "thinking": 3}


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _r17_layers(slug: str = LAB) -> dict:
    summary = {
        "store_slug": slug,
        "merchant_reason_counts_week": dict(COUNTS),
        "merchant_store_cart_counts": {"no_phone_total": 0},
        "truth_class": "production_ready",
    }
    col = compose_commercial_opportunity_layer_v1(summary, store_slug=slug)
    cat = compose_mission_catalog_v1(col_package=col, store_slug=slug)
    port = compose_mission_portfolio_v1(catalog_package=cat, store_slug=slug)
    body = {
        "store_slug": slug,
        "merchant_reason_counts_week": dict(COUNTS),
        "commercial_opportunity_layer_v1": col,
        "mission_catalog_v1": cat,
        "mission_portfolio_v1": port,
    }
    project_commercial_action_language_v1(body)
    return body


def _hierarchy(slug: str = LAB, body: dict | None = None) -> dict | None:
    src = body if body is not None else _r17_layers(slug)
    attach_live_decision_hierarchy_to_summary_v1(src, store_slug=slug)
    return src.get("live_decision_hierarchy_v1")


class LiveDecisionHierarchyPortfolioVisibilityV1Tests(unittest.TestCase):
    def test_r17_current_commercial_mission_is_shipping(self) -> None:
        pkg = _hierarchy()
        self.assertIsNotNone(pkg)
        self.assertTrue(pkg["enabled"])
        self.assertEqual(pkg["truth"]["primary_family"], FAMILY_SHIPPING)
        self.assertEqual(pkg["home"]["now"]["family"], FAMILY_SHIPPING)
        self.assertEqual(pkg["truth"]["counts"]["shipping"], 12)
        self.assertEqual(pkg["truth"]["counts"]["price"], 5)
        self.assertEqual(pkg["truth"]["counts"]["thinking"], 3)
        self.assertEqual(pkg["truth"]["counts"]["total"], 20)
        self.assertIn("12 من 20 (60٪)", pkg["home"]["now"]["evidence_ar"])

    def test_commercial_state_has_one_owner(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["commercial_status_owner"], COMMERCIAL_STATUS_OWNER)
        self.assertEqual(pkg["operational_guidance_owner"], OPERATIONAL_GUIDANCE_OWNER)
        self.assertTrue(pkg["suppress_same_mission_ogl_insufficiency"])

    def test_ready_cannot_coexist_with_same_mission_insufficiency(self) -> None:
        pkg = _hierarchy()
        painted = " ".join(
            [
                str(pkg["home"]),
                str(pkg["workspace"]),
                str(pkg["sidebar"]),
                str(pkg["home"]["now"]["commercial_state_ar"]),
            ]
        )
        for phrase in FORBIDDEN_INSUFFICIENCY_AR:
            self.assertNotIn(phrase, painted)
        self.assertEqual(pkg["home"]["now"]["commercial_state_ar"], "جاهزة للتنفيذ")
        self.assertTrue(pkg["suppress_same_mission_ogl_insufficiency"])

    def test_home_primary_is_shipping_not_second_workspace(self) -> None:
        pkg = _hierarchy()
        now = pkg["home"]["now"]
        self.assertEqual(now["state_label_ar"], LABEL_NOW_AR)
        self.assertEqual(now["decision_ar"], MISSION_SHIPPING_AR)
        self.assertEqual(now["cta_ar"], "افتح القرار")
        self.assertIn("الشحن", now["title_ar"])

    def test_price_is_not_parallel_execution(self) -> None:
        pkg = _hierarchy()
        mon = pkg["home"]["monitoring"]
        self.assertTrue(mon)
        self.assertEqual(mon[0]["family"], FAMILY_PRICE)
        self.assertEqual(mon[0]["portfolio_state"], "SAFE_SECONDARY")
        self.assertFalse(mon[0]["executable"])
        self.assertFalse(mon[0]["consumes_active_capacity"])
        self.assertIsNone(mon[0]["cta_ar"])
        self.assertIn("5 من 20", mon[0]["body_ar"])
        self.assertIn("25٪", mon[0]["body_ar"])

    def test_secondary_status_comes_from_portfolio(self) -> None:
        body = _r17_layers()
        port = body["mission_portfolio_v1"]
        fams = {s["family"] for s in port.get("safe_secondaries") or []}
        pkg = _hierarchy(body=body)
        if FAMILY_PRICE in fams:
            self.assertEqual(pkg["home"]["monitoring"][0]["family"], FAMILY_PRICE)
        else:
            deferred = {d["family"] for d in port.get("deferred") or []}
            self.assertIn(FAMILY_PRICE, deferred)
            self.assertTrue(
                any(x["family"] == FAMILY_PRICE for x in pkg["home"]["later"])
            )

    def test_baadahu_absent_from_package_and_lab_renderers(self) -> None:
        pkg = _hierarchy()
        self.assertNotIn(AMBIGUOUS_NEXT_LABEL_AR, str(pkg))
        home_fn = _read("static/merchant_ui_v2_home.js").split(
            "function renderHierarchyHome"
        )[1].split("function phaseStatusAr")[0]
        ws_fn = _read("static/merchant_ui_v2_workspace.js").split(
            "function renderHierarchyWorkspace"
        )[1].split("function catalogCardToOpp")[0]
        self.assertNotIn(AMBIGUOUS_NEXT_LABEL_AR, home_fn)
        self.assertNotIn(AMBIGUOUS_NEXT_LABEL_AR, ws_fn)
        for phrase in ("الأدلة ما زالت محدودة", "يحتاج مزيدًا من الأدلة"):
            self.assertNotIn(phrase, home_fn)
            self.assertNotIn(phrase, ws_fn)

    def test_next_mission_label_only_when_distinct(self) -> None:
        pkg = _hierarchy()
        self.assertIsNone(pkg["home"]["next_mission"])
        self.assertNotIn(LABEL_NEXT_AR, str(pkg["home"]["now"]))

    def test_deferred_item_is_not_executable(self) -> None:
        body = _r17_layers()
        cat = body["mission_catalog_v1"]
        primary = cat.get("primary") or {}
        primary["cdc_phase"] = "ACTION_CHOSEN"
        primary["commitment"] = {"phase": "ACTION_CHOSEN"}
        cat["primary"] = primary
        body["mission_portfolio_v1"] = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=LAB
        )
        pkg = compose_live_decision_hierarchy_v1(body, store_slug=LAB)
        self.assertIsNotNone(pkg)
        for row in pkg["home"]["later"]:
            self.assertFalse(row["executable"])
        self.assertNotEqual(
            pkg["truth"]["cdc_phase"], "UNDER_MEASUREMENT"
        )

    def test_action_chosen_not_under_measurement(self) -> None:
        body = _r17_layers()
        cat = body["mission_catalog_v1"]
        cat["primary"]["cdc_phase"] = "ACTION_CHOSEN"
        cat["primary"]["commitment"] = {"phase": "ACTION_CHOSEN"}
        body["mission_catalog_v1"] = cat
        body["mission_portfolio_v1"] = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=LAB
        )
        chosen = compose_live_decision_hierarchy_v1(body, store_slug=LAB)
        self.assertEqual(chosen["truth"]["cdc_phase"], "ACTION_CHOSEN")
        self.assertEqual(
            chosen["home"]["now"]["commercial_state_ar"], ACCEPTED_STATE_AR
        )
        ids = [i["id"] for i in chosen["sidebar"]["items"]]
        self.assertIn("in_progress", ids)
        self.assertEqual(
            [i for i in chosen["sidebar"]["items"] if i["id"] == "in_progress"][0][
                "label"
            ],
            "قيد التنفيذ",
        )
        cat["primary"]["cdc_phase"] = "UNDER_MEASUREMENT"
        cat["primary"]["commitment"] = {"phase": "UNDER_MEASUREMENT"}
        body["mission_portfolio_v1"] = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=LAB
        )
        measured = compose_live_decision_hierarchy_v1(body, store_slug=LAB)
        self.assertEqual(measured["truth"]["cdc_phase"], "UNDER_MEASUREMENT")
        self.assertNotEqual(chosen["truth"]["cdc_phase"], measured["truth"]["cdc_phase"])
        self.assertEqual(
            [i for i in measured["sidebar"]["items"] if i["id"] == "measuring"][0][
                "label"
            ],
            "قيد القياس",
        )

    def test_recheck_due_paints_as_review(self) -> None:
        body = _r17_layers()
        cat = body["mission_catalog_v1"]
        cat["primary"]["cdc_phase"] = "RECHECK_DUE"
        cat["primary"]["commitment"] = {"phase": "RECHECK_DUE"}
        body["mission_portfolio_v1"] = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=LAB
        )
        pkg = compose_live_decision_hierarchy_v1(body, store_slug=LAB)
        ids = [i["id"] for i in pkg["sidebar"]["items"]]
        self.assertIn("review", ids)
        self.assertEqual(pkg["home"]["now"]["commercial_state_ar"], "حان وقت المراجعة")

    def test_no_frontend_ranking(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["frontend_ranking"], 0)
        home_js = _read("static/merchant_ui_v2_home.js")
        ws_js = _read("static/merchant_ui_v2_workspace.js")
        app_js = _read("static/merchant_ui_v2_app.js")
        self.assertIn("data-cf2-frontend-ranking=\"0\"", home_js)
        self.assertIn("data-cf2-frontend-ranking=\"0\"", ws_js)
        self.assertNotIn("rankMissions", home_js + ws_js + app_js)
        self.assertNotIn("sortCatalog", home_js + ws_js + app_js)

    def test_tenant_isolation_and_no_query_bypass(self) -> None:
        lab = _hierarchy(LAB)
        self.assertTrue(lab["enabled"])
        normal_body = _r17_layers(NORMAL)
        normal_body["query_store_slug"] = LAB
        attach_live_decision_hierarchy_to_summary_v1(
            normal_body, store_slug=NORMAL
        )
        self.assertNotIn("live_decision_hierarchy_v1", normal_body)
        spoof = compose_live_decision_hierarchy_v1(
            {"store_slug": NORMAL, "query_store_slug": LAB},
            store_slug=NORMAL,
        )
        self.assertIsNone(spoof)

    def test_normal_merchant_payload_omits_package(self) -> None:
        body = _r17_layers("acme_store")
        attach_live_decision_hierarchy_to_summary_v1(body, store_slug="acme_store")
        self.assertNotIn("live_decision_hierarchy_v1", body)

    def test_no_cross_tenant_mutation(self) -> None:
        lab = _r17_layers(LAB)
        other = _r17_layers(NORMAL)
        attach_live_decision_hierarchy_to_summary_v1(lab, store_slug=LAB)
        attach_live_decision_hierarchy_to_summary_v1(other, store_slug=NORMAL)
        self.assertIn("live_decision_hierarchy_v1", lab)
        self.assertNotIn("live_decision_hierarchy_v1", other)
        self.assertEqual(lab["live_decision_hierarchy_v1"]["store_slug"], LAB)

    def test_workspace_flow_and_no_duplicate_diagnosis_contract(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(
            pkg["workspace"]["flow"],
            ["EVIDENCE", "DECISION", "EXECUTION", "MEASUREMENT", "RECHECK"],
        )
        self.assertEqual(pkg["workspace"]["execution_label_ar"], "تنفيذ المهمة")
        ev = pkg["workspace"]["evidence_ar"]
        self.assertEqual(ev, "12 من 20 (60٪)")
        self.assertNotEqual(pkg["workspace"]["execution_ar"], ev)
        self.assertNotIn("12 / 20", pkg["workspace"]["execution_ar"])

    def test_section_labels_are_stacked_not_inline(self) -> None:
        css = _read("static/merchant_ui_v2_home.css") + _read(
            "static/merchant_ui_v2_workspace.css"
        )
        self.assertIn("body[data-cf-ui=\"v2\"] .cf2-ldh__label", css)
        self.assertIn("display: block", css)
        ws_js = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("cf2-ldh__label", ws_js)
        self.assertIn("لماذا هذه المهمة الآن؟", ws_js)
        self.assertIn("لا تفعل هذا الآن", ws_js)
        self.assertIn("تحت المراقبة", ws_js)

    def test_sidebar_state_groups_and_closed_unsupported(self) -> None:
        pkg = _hierarchy()
        ids = [i["id"] for i in pkg["sidebar"]["items"]]
        self.assertIn("now", ids)
        self.assertFalse(pkg["closed_history_supported"])
        self.assertFalse(pkg["sidebar"]["completed_supported"])
        self.assertNotIn("completed", ids)
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("readLdhSidebar", app)
        self.assertNotIn("الزيارات", app.split("function contextualFor")[1].split("function anyOverlayOpen")[0])

    def test_query_delta_and_economics(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["query_delta"], 0)
        self.assertEqual(pkg["n_plus_one"], 0)

    def test_owner_logic_files_unchanged_markers(self) -> None:
        # Presentation package must not import rank/conflict mutators as writers.
        compose = _read("services/live_decision_hierarchy_v1/compose_v1.py")
        self.assertNotIn("rank_mission_catalog_v1", compose)
        self.assertNotIn("evaluate_conflict_v1", compose)
        self.assertIn("compose_mission_portfolio_v1", _read("services/mission_portfolio_v1/compose_v1.py"))

    def test_mobile_clipping_guards(self) -> None:
        css = _read("static/merchant_ui_v2_home.css")
        self.assertIn("overflow-wrap: break-word", css)
        self.assertNotIn(".cf2-ldh__title {\n  text-overflow: ellipsis", css)

    def test_founder_v12_markers_preserved(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("أكد إتمام الضبط", ws)
        self.assertIn("اضبط أسباب التردد", ws)
        self.assertIn("#settings?area=recovery&focus=shipping-hesitation", ws)
        self.assertIn(ACCEPTED_STATE_AR, ws)
        tpl = _read("static/merchant_trigger_templates.js")
        self.assertIn("cf2-rec-reasons", tpl)


if __name__ == "__main__":
    unittest.main()
