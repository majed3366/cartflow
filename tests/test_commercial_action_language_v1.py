# -*- coding: utf-8 -*-
"""Commercial Action Language Contract V1."""
from __future__ import annotations

import unittest

from services.commercial_action_language_v1.contract_v1 import (
    CTA_ACCEPT_MISSION_AR,
    FAMILY_PRICE,
    FAMILY_PRODUCT,
    FAMILY_SHIPPING,
    FAMILY_WAIT,
    FORBIDDEN_WIDGET_ALT_AR,
    FORBIDDEN_WIDGET_AR,
    contract_for_family_v1,
    starts_with_vague_opener,
)
from services.commercial_action_language_v1.project_v1 import (
    project_commercial_action_language_v1,
    project_guidance_action_language_v1,
)
from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.operational_guidance_v1.compose_v1 import (
    compose_from_hesitation_distribution_v1,
    compose_wait_insufficient_v1,
)


def _r17_summary() -> dict:
    return {
        "store_slug": "cf_live_reality_lab",
        "merchant_reason_counts_week": {"shipping": 12, "price": 5, "thinking": 3},
        "merchant_store_cart_counts": {"no_phone_total": 0},
    }


class CommercialActionLanguageContractTests(unittest.TestCase):
    def test_cta_frozen(self) -> None:
        self.assertEqual(CTA_ACCEPT_MISSION_AR, "اعتمد هذه المهمة")
        for fam in (FAMILY_SHIPPING, FAMILY_PRODUCT, FAMILY_PRICE, FAMILY_WAIT):
            pack = contract_for_family_v1(fam)
            assert pack is not None
            self.assertEqual(pack["cta_ar"], CTA_ACCEPT_MISSION_AR)

    def test_actions_are_concrete_and_merchant_first(self) -> None:
        ev = {
            "counts": {
                "hesitation_total": 20,
                "top_reason": "shipping",
                "top_count": 12,
                "top_share": 0.6,
            }
        }
        packs = {
            FAMILY_SHIPPING: contract_for_family_v1(FAMILY_SHIPPING, evidence=ev),
            FAMILY_PRODUCT: contract_for_family_v1(
                FAMILY_PRODUCT,
                evidence={
                    "counts": {
                        "hesitation_total": 20,
                        "top_reason": "quality",
                        "top_count": 9,
                        "top_share": 0.45,
                    }
                },
                reason_label_ar="الجودة",
            ),
            FAMILY_PRICE: contract_for_family_v1(
                FAMILY_PRICE,
                evidence={
                    "counts": {
                        "hesitation_total": 20,
                        "top_reason": "price",
                        "top_count": 8,
                        "top_share": 0.4,
                    }
                },
            ),
            FAMILY_WAIT: contract_for_family_v1(FAMILY_WAIT),
        }
        required = (
            "situation_ar",
            "evidence_ar",
            "diagnosis_ar",
            "action_ar",
            "dont_ar",
            "measure_ar",
            "recheck_ar",
            "cta_ar",
        )
        for fam, pack in packs.items():
            assert pack is not None
            for key in required:
                self.assertTrue(pack.get(key), msg=f"{fam}.{key}")
            self.assertFalse(
                starts_with_vague_opener(pack["action_ar"]), msg=fam
            )
            blob = " ".join(pack.values())
            self.assertNotIn(FORBIDDEN_WIDGET_AR, blob)
            self.assertNotIn(FORBIDDEN_WIDGET_ALT_AR, blob)
            self.assertIn(pack["dont_ar"], blob)

        ship = packs[FAMILY_SHIPPING]
        assert ship is not None
        self.assertIn("12", ship["evidence_ar"])
        self.assertIn("20", ship["evidence_ar"])
        self.assertIn("60", ship["evidence_ar"])
        self.assertIn("تكلفة", ship["action_ar"])
        self.assertIn("مدة", ship["action_ar"])
        self.assertIn("مجاني", ship["dont_ar"])
        self.assertNotIn("احتكاك", blob)
        self.assertNotIn("يوقف الشراء", ship["action_ar"])
        self.assertNotIn("يقطع الشراء", blob)

        price = packs[FAMILY_PRICE]
        assert price is not None
        self.assertIn("خصم", price["dont_ar"])
        self.assertIn("صفحة المنتج", price["action_ar"])

        prod = packs[FAMILY_PRODUCT]
        assert prod is not None
        self.assertIn("صفحة المنتج", prod["action_ar"])
        self.assertNotIn("حسّن ثقة المنتج", prod["action_ar"])

        wait = packs[FAMILY_WAIT]
        assert wait is not None
        self.assertIn("أبقِ", wait["action_ar"])
        self.assertIn("حد الكفاية", wait["recheck_ar"])

    def test_col_overlay_rewrites_shipping_action_without_changing_family(self) -> None:
        col = compose_commercial_opportunity_layer_v1(
            _r17_summary(), store_slug="cf_live_reality_lab"
        )
        self.assertEqual((col.get("primary") or {}).get("family"), FAMILY_SHIPPING)
        raw_action = str((col.get("primary") or {}).get("action_ar") or "")
        self.assertIn("ودج", raw_action)
        body = {"commercial_opportunity_layer_v1": col}
        project_commercial_action_language_v1(body)
        primary = (body["commercial_opportunity_layer_v1"].get("primary") or {})
        self.assertEqual(primary.get("family"), FAMILY_SHIPPING)
        self.assertFalse(bool((body.get("commercial_opportunity_layer_v1") or {}).get("empty")))
        action = str(primary.get("action_ar") or "")
        self.assertNotIn("ودج", action)
        self.assertFalse(starts_with_vague_opener(action))
        dc = primary.get("decision_contract_ar") or {}
        self.assertEqual(dc.get("cta_ar"), CTA_ACCEPT_MISSION_AR)
        self.assertIn("12", str(primary.get("why_ar") or ""))
        self.assertNotIn("احتكاك", str(primary.get("title_ar") or ""))
        self.assertEqual(primary.get("title_ar"), dc.get("decision_ar"))
        ev = (primary.get("evidence") or {}).get("counts") or {}
        self.assertEqual(ev.get("top_count"), 12)
        self.assertEqual(ev.get("hesitation_total"), 20)

    def test_price_and_product_overlays(self) -> None:
        price_body = {
            "commercial_opportunity_layer_v1": compose_commercial_opportunity_layer_v1(
                {
                    "store_slug": "cf_live_reality_lab",
                    "merchant_reason_counts_week": {
                        "price": 12,
                        "shipping": 5,
                        "thinking": 3,
                    },
                },
                store_slug="cf_live_reality_lab",
            )
        }
        project_commercial_action_language_v1(price_body)
        p = (price_body["commercial_opportunity_layer_v1"].get("primary") or {})
        self.assertEqual(p.get("family"), FAMILY_PRICE)
        self.assertIn("خصم", str((p.get("decision_contract_ar") or {}).get("dont_ar") or ""))
        self.assertNotIn("راجع السعر", str(p.get("action_ar") or ""))

        prod_body = {
            "commercial_opportunity_layer_v1": compose_commercial_opportunity_layer_v1(
                {
                    "store_slug": "cf_live_reality_lab",
                    "merchant_reason_counts_week": {
                        "quality": 12,
                        "shipping": 5,
                        "thinking": 3,
                    },
                },
                store_slug="cf_live_reality_lab",
            )
        }
        project_commercial_action_language_v1(prod_body)
        q = (prod_body["commercial_opportunity_layer_v1"].get("primary") or {})
        self.assertEqual(q.get("family"), FAMILY_PRODUCT)
        self.assertNotIn("حسّن ثقة المنتج", str(q.get("action_ar") or ""))

    def test_ogl_wait_and_shipping_projection(self) -> None:
        wait = compose_wait_insufficient_v1(
            store_slug="cf_live_reality_lab",
            missing_ar="عدد أسباب التردد المسجّلة (3) أقل من الحد الآمن (8).",
            observe_ar="استمر في تشغيل الودجيت لجمع أسباب تردد مؤهّلة دون تغيير السعر أو الشحن.",
            unlock_ar="أعد القرار عندما يصل إجمالي أسباب التردد إلى 8.",
        )
        project_guidance_action_language_v1(wait)
        self.assertEqual(wait.get("family"), FAMILY_WAIT)
        self.assertNotIn("ودج", str(wait.get("merchant_action") or ""))
        self.assertFalse(starts_with_vague_opener(str(wait.get("merchant_action") or "")))
        self.assertIn("حد الكفاية", str(wait.get("recheck_condition") or ""))

        ship = compose_from_hesitation_distribution_v1(
            store_slug="cf_live_reality_lab",
            total=20,
            distribution={"shipping": 12, "price": 5, "thinking": 3},
        )
        assert ship is not None
        self.assertEqual(ship.get("family"), FAMILY_SHIPPING)
        project_guidance_action_language_v1(ship)
        self.assertNotIn("ودج", str(ship.get("merchant_action") or ""))
        self.assertIn("مجاني", str(ship.get("recommendation") or ""))

    def test_lab_manifests_answer_what_to_do_now(self) -> None:
        from services.live_reality_lab_v1.contract_v1 import (
            SCENARIO_R15,
            SCENARIO_R17,
            SCENARIO_R20,
            SCENARIO_R21,
        )
        from services.live_reality_lab_v1.dataset_v2 import scenario_manifests_v2
        from services.operational_guidance_v1.compose_v1 import (
            compose_operational_guidance_v1,
        )

        manifests = scenario_manifests_v2()
        cases = {
            SCENARIO_R17: FAMILY_SHIPPING,
            SCENARIO_R20: FAMILY_PRODUCT,
            SCENARIO_R21: FAMILY_PRICE,
            SCENARIO_R15: FAMILY_WAIT,
        }
        for sid, family in cases.items():
            truth = ((manifests.get(sid) or {}).get("truth") or {})
            counts = dict(truth.get("reason_counts") or {})
            summary = {
                "store_slug": "cf_live_reality_lab",
                "merchant_reason_counts_week": counts,
                "hesitation_evidence_v1": {
                    "hesitation_total": sum(int(v) for v in counts.values()),
                    "hesitation_distribution": counts,
                },
            }
            body = {
                "commercial_opportunity_layer_v1": compose_commercial_opportunity_layer_v1(
                    summary, store_slug="cf_live_reality_lab"
                ),
                "operational_guidance_v1": compose_operational_guidance_v1(
                    summary, store_slug="cf_live_reality_lab"
                ),
            }
            project_commercial_action_language_v1(body)
            col = body["commercial_opportunity_layer_v1"]
            ogl = body["operational_guidance_v1"]
            primary = col.get("primary") or {}
            if family == FAMILY_WAIT:
                self.assertTrue(col.get("empty") or primary.get("family") in (None, FAMILY_WAIT))
                action = str(ogl.get("merchant_action") or "")
            else:
                self.assertEqual(primary.get("family"), family, msg=sid)
                action = str(primary.get("action_ar") or "")
            self.assertTrue(action, msg=sid)
            self.assertFalse(starts_with_vague_opener(action), msg=sid)
            self.assertNotIn("ودج", action)
            self.assertNotIn("راجع", action[:4])
            dc = primary.get("decision_contract_ar") or {}
            if family != FAMILY_WAIT:
                self.assertTrue(dc.get("dont_ar"), msg=sid)
                self.assertTrue(dc.get("measure_ar"), msg=sid)
                self.assertTrue(dc.get("recheck_ar"), msg=sid)
                self.assertEqual(dc.get("cta_ar"), CTA_ACCEPT_MISSION_AR)
            if family == FAMILY_SHIPPING:
                self.assertIn("12", str(primary.get("why_ar") or ""))
                self.assertIn("60", str(primary.get("why_ar") or ""))
            if family == FAMILY_PRODUCT:
                self.assertIn("صفحة المنتج", str(ogl.get("merchant_action") or ""))
                self.assertNotIn("ودج", str(ogl.get("merchant_action") or ""))
                self.assertIn("لا تخفّض", str(ogl.get("recommendation") or ""))

    def test_cta_source_unchanged(self) -> None:
        from pathlib import Path

        js = Path("static/merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
        self.assertIn('اعتمد هذه المهمة', js)
        self.assertNotIn("ابدأ التنفيذ", js)


if __name__ == "__main__":
    unittest.main()
