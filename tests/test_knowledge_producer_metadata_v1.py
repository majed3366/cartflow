# -*- coding: utf-8 -*-
"""Knowledge Producer Metadata v1 — standardized publisher contract tests."""
from __future__ import annotations

import unittest

from services.customer_lifecycle_states_v1 import (
    STATE_RETURN_TO_SITE,
    STATE_WAITING_PURCHASE_WINDOW,
)
from services.knowledge_producer_metadata_v1 import (
    KNOWLEDGE_METADATA_VERSION,
    build_knowledge_id,
    enrich_decision_knowledge_metadata_v1,
    enrich_explanation_knowledge_metadata_v1,
    enrich_kl_insight_knowledge_metadata_v1,
    enrich_knowledge_report_producer_metadata_v1,
    validate_knowledge_metadata_v1,
)
from services.merchant_decision_layer_v1 import (
    attach_merchant_decisions_v1,
    build_cart_row_merchant_decisions_v1,
    build_kl_observation_decision_v1,
    enrich_knowledge_report_merchant_decisions_v1,
)
from services.merchant_explanation_v1 import attach_merchant_explanation_v1
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1


def _sample_proof(**overrides: object) -> dict:
    base = {
        "version": "v1",
        "confidence": "medium",
        "evidence_id": "customer_journey",
        "proof_source": "demo-store:rk_abc123",
        "what_happened_ar": "عاد العميل",
        "why_we_know_ar": "حالة المسار",
        "recovery_steps": [],
    }
    base.update(overrides)
    return base


class KnowledgeIdStabilityTests(unittest.TestCase):
    def test_build_knowledge_id_is_deterministic(self) -> None:
        kid_a = build_knowledge_id(
            prefix="expl",
            type_key="return_without_purchase",
            scope="my-store",
            subject_key="rk_abc123",
        )
        kid_b = build_knowledge_id(
            prefix="expl",
            type_key="return_without_purchase",
            scope="my-store",
            subject_key="rk_abc123",
        )
        self.assertEqual(kid_a, kid_b)
        self.assertEqual(
            kid_a,
            "expl:return_without_purchase:my-store:rk_abc123",
        )

    def test_build_knowledge_id_never_random(self) -> None:
        kid = build_knowledge_id(
            prefix="kl",
            type_key="hesitation_top_reason",
            scope="store-1",
            subject_key="7d",
        )
        self.assertRegex(kid, r"^kl:hesitation_top_reason:store-1:7d$")


class ExplanationMetadataTests(unittest.TestCase):
    def test_attach_explanation_includes_full_metadata(self) -> None:
        row: dict = {
            "store_slug": "demo-store",
            "recovery_key": "rk_abc123",
            "customer_lifecycle_state": STATE_WAITING_PURCHASE_WINDOW,
            "customer_lifecycle_label_ar": "عاد العميل",
            "customer_lifecycle_what_happened_ar": "عاد العميل إلى المتجر.",
            "customer_lifecycle_system_did_ar": "CartFlow أوقف المتابعة.",
            "customer_lifecycle_what_next_ar": "سيواصل لاحقاً.",
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_proof_surface_v1": _sample_proof(),
        }
        attach_merchant_explanation_v1(row)
        expl = row["merchant_explanation_v1"]
        missing = validate_knowledge_metadata_v1(expl)
        self.assertEqual(missing, [], msg=f"missing: {missing}")
        self.assertEqual(expl["knowledge_version"], KNOWLEDGE_METADATA_VERSION)
        self.assertEqual(
            expl["knowledge_id"],
            "expl:return_without_purchase:demo-store:rk_abc123",
        )
        self.assertEqual(expl["knowledge_type"], "return_without_purchase")
        self.assertEqual(expl["explanation_id"], "return_without_purchase")
        self.assertEqual(expl["source_domain"], "recovery")

    def test_explanation_metadata_stable_on_regeneration(self) -> None:
        kwargs = dict(
            store_slug="demo-store",
            recovery_key="rk_stable",
            abandoned_cart_id=99,
            proof=_sample_proof(),
            lifecycle_state=STATE_RETURN_TO_SITE,
        )
        expl_a = enrich_explanation_knowledge_metadata_v1(
            {
                "version": "v1",
                "explanation_id": "customer_returned",
                "knowledge_event_type": "customer_returned_to_site",
                "merchant_visibility": "merchant_dashboard",
                "eligible_surfaces": ["cart_detail"],
                "action_required": False,
                "attention_level": "informational",
            },
            **kwargs,
        )
        expl_b = enrich_explanation_knowledge_metadata_v1(
            dict(expl_a),
            **kwargs,
        )
        self.assertEqual(expl_a["knowledge_id"], expl_b["knowledge_id"])

    def test_explanation_merchant_copy_unchanged(self) -> None:
        row: dict = {
            "store_slug": "demo-store",
            "recovery_key": "rk_1",
            "customer_lifecycle_state": STATE_WAITING_PURCHASE_WINDOW,
            "customer_lifecycle_what_happened_ar": "عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
            "customer_lifecycle_system_did_ar": "CartFlow أوقف المتابعة مؤقتًا.",
            "customer_lifecycle_what_next_ar": "سيواصل لاحقاً.",
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_proof_surface_v1": _sample_proof(),
        }
        attach_merchant_explanation_v1(row)
        expl = row["merchant_explanation_v1"]
        self.assertIn("CartFlow", expl["system_did_ar"])
        self.assertEqual(expl["explanation_id"], "return_without_purchase")


class DecisionMetadataTests(unittest.TestCase):
    def test_cart_row_decisions_include_metadata(self) -> None:
        bundle = build_cart_row_merchant_decisions_v1(
            proof=_sample_proof(),
            recovery_key="rk_abc123",
            store_slug="demo-store",
            customer_lifecycle_state="return_to_site",
            customer_lifecycle_what_happened_ar="عاد العميل",
            merchant_decision_key="monitor",
            purchase_truth=False,
        )
        self.assertTrue(bundle["decisions"])
        dec = bundle["decisions"][0]
        missing = validate_knowledge_metadata_v1(dec)
        self.assertEqual(missing, [], msg=f"missing: {missing}")
        self.assertTrue(dec["knowledge_id"].startswith("dec:decision_monitor_return:"))
        self.assertEqual(dec["explanation_id"], "return_without_purchase")

    def test_attach_decisions_backward_compatible(self) -> None:
        row: dict = {
            "store_slug": "demo-store",
            "recovery_key": "rk_abc123",
            "customer_lifecycle_state": "needs_intervention",
            "customer_lifecycle_merchant_needed_ar": "نعم",
            "customer_lifecycle_what_happened_ar": "تحتاج تدخل",
            "merchant_decision_key": "contact_customer",
            "merchant_intervention_executable": True,
            "merchant_proof_surface_v1": _sample_proof(),
        }
        attach_merchant_decisions_v1(row)
        bundle = row["merchant_decisions_v1"]
        self.assertIn("decisions", bundle)
        self.assertIn("suppressed", bundle)
        self.assertIn("version", bundle)
        dec = bundle["decisions"][0]
        self.assertIn("decision_id", dec)
        self.assertIn("priority", dec)
        self.assertIn("knowledge_id", dec)


class KnowledgeLayerMetadataTests(unittest.TestCase):
    def test_kl_insight_metadata(self) -> None:
        insight = {
            "insight_key": "hesitation_top_reason",
            "category": "hesitation",
            "severity": "notice",
            "title_ar": "سبب التردد",
            "message_ar": "الشحن",
            "confidence": "medium",
            "evidence_id": "hesitation_reason",
            "source_tables": ["cart_recovery_reason"],
        }
        enrich_kl_insight_knowledge_metadata_v1(
            insight,
            store_slug="demo-store",
            window_days=7,
        )
        missing = validate_knowledge_metadata_v1(insight)
        self.assertEqual(missing, [], msg=f"missing: {missing}")
        self.assertEqual(
            insight["knowledge_id"],
            "kl:hesitation_top_reason:demo-store:7d",
        )
        self.assertEqual(insight["knowledge_type"], "hesitation_pattern")
        self.assertIn("knowledge_layer", insight["eligible_surfaces"])
        self.assertIn("merchant_home", insight["eligible_surfaces"])

    def test_kl_report_enrichment_and_decision_link(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo-store",
            "window_days": 7,
            "insights": [
                {
                    "insight_key": "hesitation_top_reason",
                    "category": "hesitation",
                    "severity": "notice",
                    "title_ar": "سبب",
                    "message_ar": "msg",
                    "confidence": "medium",
                    "evidence_id": "hesitation_reason",
                }
            ],
        }
        enrich_knowledge_report_producer_metadata_v1(payload)
        enrich_knowledge_report_merchant_decisions_v1(payload)
        insight = payload["insights"][0]
        self.assertTrue(insight.get("knowledge_id"))
        dec = payload["merchant_decisions_v1"]["decisions"][0]
        trace = dec.get("traceability") or {}
        self.assertEqual(trace.get("linked_insight_knowledge_id"), insight["knowledge_id"])

    def test_kl_observation_decision_metadata(self) -> None:
        insight = {
            "insight_key": "hesitation_top_reason",
            "title_ar": "سبب",
            "confidence": "medium",
            "evidence_id": "hesitation_reason",
            "knowledge_id": "kl:hesitation_top_reason:demo-store:7d",
        }
        dec = build_kl_observation_decision_v1(insight, store_slug="demo-store")
        assert dec is not None
        missing = validate_knowledge_metadata_v1(dec)
        self.assertEqual(missing, [], msg=f"missing: {missing}")


class TraceabilityTests(unittest.TestCase):
    def test_traceability_minimum_fields(self) -> None:
        expl = enrich_explanation_knowledge_metadata_v1(
            {
                "version": "v1",
                "explanation_id": "cart_active",
                "knowledge_event_type": "cart_active",
                "merchant_visibility": "merchant_dashboard",
                "eligible_surfaces": ["cart_detail"],
                "action_required": False,
                "attention_level": "informational",
            },
            store_slug="s1",
            recovery_key="rk1",
        )
        trace = expl["traceability"]
        self.assertEqual(trace["origin_layer"], "merchant_explanation")
        self.assertTrue(trace["origin_identifier"])
        self.assertIsInstance(trace["source_records"], list)
        self.assertTrue(trace["producer_version"])
        self.assertIsInstance(trace["created_from"], list)


if __name__ == "__main__":
    unittest.main()
