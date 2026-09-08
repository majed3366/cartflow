# -*- coding: utf-8 -*-
"""Founder UX Closure V1.3 — evidence arithmetic + why + journey + sidebar truth."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_SHIPPING,
)
from services.commercial_action_language_v1.execution_path_v1 import EXECUTION_CTA_AR
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
    JOURNEY_ACCEPT_AR,
    JOURNEY_CONFIRM_AR,
    JOURNEY_EXECUTE_AR,
    JOURNEY_MEASURE_AR,
    JOURNEY_RECHECK_AR,
    LABEL_NOW_AR,
    SIDEBAR_ACTION_CHOSEN_AR,
    SIDEBAR_LATER_AR,
    SIDEBAR_MEASURING_AR,
    SIDEBAR_NOW_AR,
    SIDEBAR_REVIEW_AR,
)
from services.mission_catalog_v1.compose_v1 import compose_mission_catalog_v1
from services.mission_portfolio_v1.compose_v1 import compose_mission_portfolio_v1

ROOT = Path(__file__).resolve().parents[1]
LAB = "cf_live_reality_lab"
NORMAL = "cf_founder_evaluation"
COUNTS = {"shipping": 12, "price": 5, "thinking": 3}
SHIP_RATIO = "12 من 20 (60٪)"
PRICE_RATIO = "5 من 20 (25٪)"
REVERSED = ("20 / 12", "20/12", "60% = 20", "60٪ = 20", "12 / 20 = 60%", "12 / 20 = 60٪")
CAUSATION = ("يسبب", "بسبب أن", "لذلك فإن", "يثبت أن", "السبب الجذري")
CONFIRM_AR = "أكد إتمام الضبط"


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


def _with_phase(phase: str) -> dict:
    body = _r17_layers()
    cat = body["mission_catalog_v1"]
    cat["primary"]["cdc_phase"] = phase
    cat["primary"]["commitment"] = {"phase": phase}
    body["mission_catalog_v1"] = cat
    body["mission_portfolio_v1"] = compose_mission_portfolio_v1(
        catalog_package=cat, store_slug=LAB
    )
    pkg = compose_live_decision_hierarchy_v1(body, store_slug=LAB)
    assert pkg is not None
    return pkg


def _painted(pkg: dict) -> str:
    return " ".join(
        [
            str(pkg.get("home") or {}),
            str(pkg.get("workspace") or {}),
            str(pkg.get("sidebar") or {}),
            str(pkg.get("truth") or {}),
        ]
    )


class FounderUxClosureV13Tests(unittest.TestCase):
    def test_shipping_ratio_is_numerator_over_denominator(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["home"]["now"]["evidence_ar"], SHIP_RATIO)
        self.assertEqual(pkg["workspace"]["evidence_ar"], SHIP_RATIO)
        self.assertEqual(pkg["truth"]["counts"]["shipping"], 12)
        self.assertEqual(pkg["truth"]["counts"]["total"], 20)

    def test_price_ratio_is_numerator_over_denominator(self) -> None:
        pkg = _hierarchy()
        mon = pkg["home"]["monitoring"]
        self.assertTrue(mon)
        self.assertEqual(mon[0]["family"], FAMILY_PRICE)
        self.assertIn("5 من 20", mon[0]["body_ar"])
        self.assertIn("25٪", mon[0]["body_ar"])
        self.assertNotIn("20 / 5", mon[0]["body_ar"])
        self.assertNotIn("5 / 20", mon[0]["body_ar"])

    def test_no_reversed_ratio_on_mission_surfaces(self) -> None:
        pkg = _hierarchy()
        blob = _painted(pkg)
        for bad in REVERSED:
            self.assertNotIn(bad, blob)
        self.assertNotIn("20 / 12", blob)
        self.assertNotIn("12 / 20", blob)
        compose = _read("services/live_decision_hierarchy_v1/compose_v1.py")
        self.assertIn('{n} من {total} ({pct}٪)', compose)
        self.assertNotIn('f"{n} / {total}', compose)
        self.assertNotIn('f"{total} / {n}', compose)
        home_fn = _read("static/merchant_ui_v2_home.js").split(
            "function renderHierarchyHome"
        )[1].split("function phaseStatusAr")[0]
        ws_fn = _read("static/merchant_ui_v2_workspace.js").split(
            "function renderHierarchyWorkspace"
        )[1].split("function catalogCardToOpp")[0]
        for src in (home_fn, ws_fn):
            self.assertNotIn("20 / 12", src)
            self.assertNotIn("${total} / ${n}", src)

    def test_why_now_explains_and_does_not_repeat_title(self) -> None:
        pkg = _hierarchy()
        title = pkg["workspace"]["title_ar"]
        why = pkg["workspace"]["why_now_ar"]
        self.assertTrue(title)
        self.assertTrue(why)
        self.assertNotEqual(why, title)
        self.assertIn("لأن الشحن يمثل 12 من 20 سبب تردد مسجّل", why)
        self.assertIn("خلال نافذة المراقبة الحالية", why)
        self.assertNotIn(title, why)
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("ws.why_now_ar !== ws.title_ar", ws)

    def test_why_is_evidence_backed_association_not_causation(self) -> None:
        pkg = _hierarchy()
        why = pkg["workspace"]["why_now_ar"]
        self.assertIn("12", why)
        self.assertIn("20", why)
        self.assertIn("الشحن", why)
        for word in CAUSATION:
            self.assertNotIn(word, why)
        self.assertNotIn("منتج", why)
        compose = _read("services/live_decision_hierarchy_v1/compose_v1.py")
        self.assertIn("Association only", compose)
        self.assertNotIn("يسبب", compose)

    def test_accept_execute_confirm_sequence_is_server_owned(self) -> None:
        ready = _hierarchy()
        journey = ready["workspace"]["journey"]
        ids = [s["id"] for s in journey["steps"]]
        self.assertEqual(ids, ["accept", "execute", "confirm", "measure", "recheck"])
        self.assertEqual(
            [s["label_ar"] for s in journey["steps"]],
            [
                JOURNEY_ACCEPT_AR,
                JOURNEY_EXECUTE_AR,
                JOURNEY_CONFIRM_AR,
                JOURNEY_MEASURE_AR,
                JOURNEY_RECHECK_AR,
            ],
        )
        self.assertEqual(journey["current_step"], "accept")
        self.assertEqual(journey["frontend_lifecycle_derivation"], 0)
        self.assertEqual(ready["frontend_lifecycle_derivation"], 0)
        chosen = _with_phase("ACTION_CHOSEN")
        self.assertEqual(chosen["workspace"]["journey"]["current_step"], "execute")
        measured = _with_phase("UNDER_MEASUREMENT")
        self.assertEqual(measured["workspace"]["journey"]["current_step"], "measure")
        recheck = _with_phase("RECHECK_DUE")
        self.assertEqual(recheck["workspace"]["journey"]["current_step"], "recheck")
        ws = _read("static/merchant_ui_v2_workspace.js")
        paint = ws.split("function renderHierarchyWorkspace")[1].split(
            "function catalogCardToOpp"
        )[0]
        self.assertIn("journey.current_step", paint)
        self.assertNotIn("if (phase ===", paint)
        self.assertIn(CTA_ACCEPT_MISSION_AR, ws)
        self.assertIn(EXECUTION_CTA_AR, ws)
        self.assertIn(CONFIRM_AR, ws)

    def test_accept_does_not_start_measurement(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("القبول يسجّل القرار فقط", ws)
        self.assertLess(ws.index('act === "accept"'), ws.index("confirm-execution"))
        chosen = _with_phase("ACTION_CHOSEN")
        self.assertEqual(chosen["truth"]["cdc_phase"], "ACTION_CHOSEN")
        self.assertNotEqual(chosen["truth"]["cdc_phase"], "UNDER_MEASUREMENT")
        self.assertEqual(
            chosen["home"]["now"]["commercial_state_ar"], ACCEPTED_STATE_AR
        )

    def test_open_settings_does_not_start_measurement(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn("فتح الإعدادات لا يبدأ القياس", ws)
        settings = _read("static/merchant_ui_v2_settings.js")
        self.assertNotIn("confirm-execution", settings)
        self.assertNotIn("/api/commercial-mission", settings)

    def test_confirm_is_measurement_authority(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn('missionPost("confirm-execution"', ws)
        self.assertIn("بعد التأكيد يبدأ CartFlow قياس أثر المهمة.", ws)
        measured = _with_phase("UNDER_MEASUREMENT")
        self.assertEqual(measured["truth"]["cdc_phase"], "UNDER_MEASUREMENT")
        self.assertEqual(measured["workspace"]["journey"]["current_step"], "measure")

    def test_ready_sidebar_is_truthful(self) -> None:
        pkg = _hierarchy()
        items = {i["id"]: i for i in pkg["sidebar"]["items"]}
        self.assertIn("now", items)
        self.assertEqual(items["now"]["label"], SIDEBAR_NOW_AR)
        self.assertEqual(pkg["home"]["now"]["state_label_ar"], LABEL_NOW_AR)
        self.assertNotIn("measuring", items)
        self.assertNotIn("review", items)

    def test_action_chosen_sidebar_is_truthful(self) -> None:
        pkg = _with_phase("ACTION_CHOSEN")
        items = {i["id"]: i for i in pkg["sidebar"]["items"]}
        self.assertIn("in_progress", items)
        self.assertEqual(items["in_progress"]["label"], SIDEBAR_ACTION_CHOSEN_AR)
        self.assertEqual(items["in_progress"]["parent_label"], "قيد التنفيذ / القياس")
        self.assertNotIn("now", items)
        self.assertNotIn("measuring", items)

    def test_under_measurement_sidebar_is_truthful(self) -> None:
        pkg = _with_phase("UNDER_MEASUREMENT")
        items = {i["id"]: i for i in pkg["sidebar"]["items"]}
        self.assertIn("measuring", items)
        self.assertEqual(items["measuring"]["label"], SIDEBAR_MEASURING_AR)
        self.assertIsNone(items["measuring"]["substate"])
        self.assertNotIn("in_progress", items)
        self.assertNotIn("now", items)

    def test_recheck_due_sidebar_is_truthful(self) -> None:
        pkg = _with_phase("RECHECK_DUE")
        items = {i["id"]: i for i in pkg["sidebar"]["items"]}
        self.assertIn("review", items)
        self.assertEqual(items["review"]["label"], SIDEBAR_REVIEW_AR)
        self.assertEqual(pkg["home"]["now"]["commercial_state_ar"], "حان وقت المراجعة")

    def test_deferred_only_from_portfolio_truth(self) -> None:
        ready = _hierarchy()
        later_ids = [i["id"] for i in ready["sidebar"]["items"] if i["id"] == "later"]
        port = _r17_layers()["mission_portfolio_v1"]
        deferred = list(port.get("deferred") or [])
        if deferred:
            self.assertTrue(later_ids)
            self.assertEqual(
                ready["sidebar"]["items"][-1]["label"], SIDEBAR_LATER_AR
            )
        else:
            self.assertFalse(later_ids)
        chosen = _with_phase("ACTION_CHOSEN")
        port_chosen_later = chosen["home"]["later"]
        side_later = [i for i in chosen["sidebar"]["items"] if i["id"] == "later"]
        if port_chosen_later:
            self.assertTrue(side_later)
            self.assertEqual(side_later[0]["count"], len(port_chosen_later))
        else:
            self.assertFalse(side_later)

    def test_completed_unsupported_correctly_hidden(self) -> None:
        pkg = _hierarchy()
        self.assertFalse(pkg["closed_history_supported"])
        self.assertFalse(pkg["sidebar"]["completed_supported"])
        ids = [i["id"] for i in pkg["sidebar"]["items"]]
        self.assertNotIn("completed", ids)
        self.assertNotIn("مكتملة", _painted(pkg))
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn("completed_supported", app)
        self.assertIn('it.id === "completed"', app)

    def test_frontend_ranking_and_lifecycle_derivation_are_zero(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["frontend_ranking"], 0)
        self.assertEqual(pkg["frontend_lifecycle_derivation"], 0)
        home = _read("static/merchant_ui_v2_home.js")
        ws = _read("static/merchant_ui_v2_workspace.js")
        app = _read("static/merchant_ui_v2_app.js")
        self.assertIn('data-cf2-frontend-ranking="0"', home)
        self.assertIn('data-cf2-frontend-ranking="0"', ws)
        self.assertIn('data-cf2-frontend-lifecycle-derivation="0"', home)
        self.assertIn('data-cf2-frontend-lifecycle-derivation="0"', ws)
        blob = home + ws + app
        self.assertNotIn("rankMissions", blob)
        self.assertNotIn("sortCatalog", blob)
        self.assertNotIn("deriveLifecycle", blob)
        self.assertGreaterEqual(blob.count("frontend-lifecycle-derivation"), 2)

    def test_home_primary_secondary_and_price_monitoring_unregressed(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["home"]["now"]["family"], FAMILY_SHIPPING)
        self.assertEqual(pkg["home"]["now"]["group_label_ar"], LABEL_NOW_AR)
        self.assertEqual(pkg["home"]["monitoring"][0]["family"], FAMILY_PRICE)
        self.assertFalse(pkg["home"]["monitoring"][0]["executable"])
        self.assertIsNone(pkg["home"]["monitoring"][0]["cta_ar"])
        self.assertIsNone(pkg["home"]["next_mission"])

    def test_price_parallel_execution_is_zero(self) -> None:
        pkg = _hierarchy()
        exec_ctas = [
            row
            for row in pkg["home"]["monitoring"]
            if row.get("cta_ar") or row.get("executable")
        ]
        self.assertEqual(len(exec_ctas), 0)
        self.assertNotIn("اعتمد", str(pkg["home"]["monitoring"]))

    def test_mobile_clipping_guards(self) -> None:
        css = _read("static/merchant_ui_v2_home.css") + _read(
            "static/merchant_ui_v2_workspace.css"
        )
        self.assertIn("overflow-wrap: break-word", css)
        self.assertIn("unicode-bidi: isolate", css)
        self.assertIn(".cf2-ldh__ratio", css)
        self.assertNotIn(".cf2-ldh__title {\n  text-overflow: ellipsis", css)

    def test_tenant_isolation_and_normal_merchant_negative(self) -> None:
        lab = _hierarchy(LAB)
        self.assertTrue(lab["enabled"])
        self.assertEqual(lab["store_slug"], LAB)
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
        other = _r17_layers("acme_store")
        attach_live_decision_hierarchy_to_summary_v1(other, store_slug="acme_store")
        self.assertNotIn("live_decision_hierarchy_v1", other)

    def test_economics_and_owner_invariants(self) -> None:
        pkg = _hierarchy()
        self.assertEqual(pkg["query_delta"], 0)
        self.assertEqual(pkg["n_plus_one"], 0)
        compose = _read("services/live_decision_hierarchy_v1/compose_v1.py")
        self.assertNotIn("rank_mission_catalog_v1", compose)
        self.assertNotIn("evaluate_conflict_v1", compose)
        self.assertNotIn("openai", compose.lower())
        self.assertNotIn("CREATE TABLE", compose)
        tpl = _read("templates/merchant_app_v2.html")
        self.assertIn("fux13", tpl)
        self.assertEqual(len(re.findall(r"fux13", tpl)), 5)

    def test_founder_v12_markers_preserved(self) -> None:
        ws = _read("static/merchant_ui_v2_workspace.js")
        self.assertIn(CONFIRM_AR, ws)
        self.assertIn(EXECUTION_CTA_AR, ws)
        self.assertIn("#settings?area=recovery&focus=shipping-hesitation", ws)
        self.assertIn(ACCEPTED_STATE_AR, ws)


if __name__ == "__main__":
    unittest.main()
