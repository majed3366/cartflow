# -*- coding: utf-8 -*-
"""Evidence Expansion Framework V1 — gap registry + no-random-collection gate."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.diagnostic_reasoning_v1.compose_v1 import compose_diagnostic_contract_v1
from services.diagnostic_reasoning_v1.contract_v1 import (
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPORTED,
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
)
from services.evidence_expansion_v1.contract_v1 import (
    GAP_STATUSES,
    GAP_STATUS_OPEN,
    GAP_STATUS_RESOLVED,
    GAP_STATUS_SUPERSEDED,
    GAP_STATUS_SUPPRESSED,
    resolve_gap_status_transition_v1,
    validate_evidence_gap_v1,
)
from services.evidence_expansion_v1.gap_compose_v1 import (
    compose_evidence_gap_from_diagnostic_v1,
    should_open_evidence_gap_v1,
)
from services.evidence_expansion_v1.observable_registry_v1 import (
    OBSERVABLE_CATALOG_V1,
    assert_observable_benefits_diagnosis_v1,
    observables_for_family_v1,
)
from services.evidence_expansion_v1.orchestrator_v1 import (
    register_evidence_gaps_from_diagnostics_v1,
)

_REPO = Path(__file__).resolve().parents[1]


class EvidenceExpansionV1Tests(unittest.TestCase):
    def test_insufficient_opens_gap_with_missing_observables(self) -> None:
        bag = {
            "signals": {"shipping": 5, "shipping_stage_observed": 1},
            "sample_n": 5,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_INSUFFICIENT)
        self.assertTrue(should_open_evidence_gap_v1(c))
        gap = compose_evidence_gap_from_diagnostic_v1(c)
        self.assertIsNotNone(gap)
        assert gap is not None
        ok, errs = validate_evidence_gap_v1(gap)
        self.assertTrue(ok, errs)
        self.assertTrue(gap["internal_only"])
        self.assertFalse(gap["merchant_safe"])
        missing_keys = {
            m["observable_key"] for m in gap["evidence_missing"] if isinstance(m, dict)
        }
        self.assertIn("shipping_option_selected", missing_keys)
        self.assertIn("delivery_estimate_shown", missing_keys)
        self.assertIn("payment_attempt_after_shipping", missing_keys)

    def test_supported_does_not_open_gap(self) -> None:
        bag = {
            "signals": {"shipping_cost": 8, "delivery_time": 0, "payment": 0},
            "sample_n": 8,
            "minimum_sample": 3,
            "product_identity_ok": True,
            "recurrence_days": 3,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        self.assertEqual(c["diagnosis_status"], DIAGNOSIS_STATUS_SUPPORTED)
        self.assertFalse(should_open_evidence_gap_v1(c))
        self.assertIsNone(compose_evidence_gap_from_diagnostic_v1(c))

    def test_every_catalog_observable_benefits_a_diagnosis(self) -> None:
        for key in OBSERVABLE_CATALOG_V1:
            self.assertTrue(
                assert_observable_benefits_diagnosis_v1(key),
                msg=f"orphan observable: {key}",
            )

    def test_shipping_family_observables_non_empty(self) -> None:
        rows = observables_for_family_v1(FAMILY_CHECKOUT_AFTER_SHIPPING)
        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            self.assertTrue(row["separates_causes"])
            self.assertIn(
                FAMILY_CHECKOUT_AFTER_SHIPPING, row["diagnosis_families_benefited"]
            )

    def test_register_dry_run_composes_without_persist(self) -> None:
        bag = {
            "signals": {"shipping": 4, "shipping_stage_observed": 1},
            "sample_n": 4,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        env = {
            "CARTFLOW_EVIDENCE_EXPANSION_V1": "1",
            "CARTFLOW_EVIDENCE_EXPANSION_EXECUTE": "0",
        }
        res = register_evidence_gaps_from_diagnostics_v1(
            [c], execute=True, environ=env
        )
        self.assertTrue(res["enabled"])
        self.assertFalse(res["execute"])
        self.assertGreaterEqual(res["composed"], 1)
        self.assertEqual(res["persisted"], 0)
        self.assertFalse(res["merchant_exposure"])

    def test_disabled_flag_skips(self) -> None:
        res = register_evidence_gaps_from_diagnostics_v1(
            [],
            execute=True,
            environ={"CARTFLOW_EVIDENCE_EXPANSION_V1": "0"},
        )
        self.assertFalse(res["enabled"])
        self.assertIn("evidence_expansion_disabled", res["errors"])

    def test_gaps_isolated_by_store_and_family(self) -> None:
        bag = {
            "signals": {"shipping": 4, "shipping_stage_observed": 1},
            "sample_n": 4,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        a = compose_diagnostic_contract_v1(
            store_slug="store_a",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        b = compose_diagnostic_contract_v1(
            store_slug="store_b",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        interest = compose_diagnostic_contract_v1(
            store_slug="store_a",
            family=FAMILY_INTEREST_WITHOUT_PURCHASE,
            evidence_bag={
                "signals": {"interest_without_purchase": 4},
                "sample_n": 4,
                "minimum_sample": 3,
                "product_identity_ok": True,
            },
        )
        ga = compose_evidence_gap_from_diagnostic_v1(a)
        gb = compose_evidence_gap_from_diagnostic_v1(b)
        gi = compose_evidence_gap_from_diagnostic_v1(interest)
        self.assertIsNotNone(ga)
        self.assertIsNotNone(gb)
        self.assertIsNotNone(gi)
        assert ga and gb and gi
        self.assertNotEqual(ga["gap_id"], gb["gap_id"])
        self.assertNotEqual(ga["gap_id"], gi["gap_id"])
        self.assertEqual(ga["store_slug"], "store_a")
        self.assertEqual(gb["store_slug"], "store_b")
        self.assertEqual(ga["diagnostic_family"], FAMILY_CHECKOUT_AFTER_SHIPPING)
        self.assertEqual(gi["diagnostic_family"], FAMILY_INTEREST_WITHOUT_PURCHASE)

    def test_repeated_compose_same_gap_id(self) -> None:
        bag = {
            "signals": {"shipping": 5, "shipping_stage_observed": 1},
            "sample_n": 5,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
            subject_id="nano",
        )
        g1 = compose_evidence_gap_from_diagnostic_v1(c)
        g2 = compose_evidence_gap_from_diagnostic_v1(c)
        self.assertIsNotNone(g1)
        self.assertIsNotNone(g2)
        assert g1 and g2
        self.assertEqual(g1["gap_id"], g2["gap_id"])

    def test_lifecycle_statuses_governed(self) -> None:
        self.assertIn(GAP_STATUS_OPEN, GAP_STATUSES)
        self.assertIn(GAP_STATUS_RESOLVED, GAP_STATUSES)
        self.assertIn(GAP_STATUS_SUPERSEDED, GAP_STATUSES)
        bag = {
            "signals": {"shipping": 3, "shipping_stage_observed": 1},
            "sample_n": 3,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        gap = compose_evidence_gap_from_diagnostic_v1(c)
        assert gap is not None
        self.assertEqual(gap["gap_status"], GAP_STATUS_OPEN)
        for bad in ("done", "closed", "merchant_visible"):
            gap["gap_status"] = bad
            ok, errs = validate_evidence_gap_v1(gap)
            self.assertFalse(ok)
            self.assertIn("gap_status", errs)

    def test_home_modules_do_not_import_evidence_expansion(self) -> None:
        home_paths = [
            _REPO / "services" / "merchant_home_experience_activation_v1.py",
            _REPO / "services" / "home_executive_summary_v1",
        ]
        banned = ("evidence_expansion_v1", "EvidenceGap", "register_evidence_gaps")
        for path in home_paths:
            if path.is_dir():
                files = list(path.glob("*.py"))
            else:
                files = [path]
            for f in files:
                src = f.read_text(encoding="utf-8")
                for token in banned:
                    self.assertNotIn(
                        token,
                        src,
                        msg=f"{f.name} must not reference {token}",
                    )

    def test_no_collector_module_in_package(self) -> None:
        pkg = _REPO / "services" / "evidence_expansion_v1"
        names = {p.name for p in pkg.glob("*.py")}
        for forbidden in (
            "collector_v1.py",
            "widget_collector_v1.py",
            "storefront_events_v1.py",
        ):
            self.assertNotIn(forbidden, names)

    def test_terminal_gaps_do_not_silently_reopen(self) -> None:
        for terminal in (
            GAP_STATUS_RESOLVED,
            GAP_STATUS_SUPERSEDED,
            GAP_STATUS_SUPPRESSED,
        ):
            status, note = resolve_gap_status_transition_v1(
                existing_status=terminal,
                incoming_status=GAP_STATUS_OPEN,
                reopen_reason="",
            )
            self.assertEqual(status, terminal)
            self.assertEqual(note, "terminal_preserved_no_reopen_reason")

        status, note = resolve_gap_status_transition_v1(
            existing_status=GAP_STATUS_RESOLVED,
            incoming_status=GAP_STATUS_OPEN,
            reopen_reason="new_competing_cause_set_after_catalog_change",
        )
        self.assertEqual(status, GAP_STATUS_OPEN)
        self.assertEqual(note, "reopened_with_reason")

    def test_gap_payload_avoids_sensitive_customer_fields(self) -> None:
        bag = {
            "signals": {"shipping": 4, "shipping_stage_observed": 1},
            "sample_n": 4,
            "minimum_sample": 3,
            "product_identity_ok": True,
        }
        c = compose_diagnostic_contract_v1(
            store_slug="demo",
            family=FAMILY_CHECKOUT_AFTER_SHIPPING,
            evidence_bag=bag,
        )
        # Inject accidental PII-shaped keys on the contract — must not land on gap.
        c["customer_phone"] = "+966500000000"
        c["customer_email"] = "x@example.com"
        gap = compose_evidence_gap_from_diagnostic_v1(c)
        assert gap is not None
        blob = str(gap)
        self.assertNotIn("+966500000000", blob)
        self.assertNotIn("x@example.com", blob)
        self.assertNotIn("customer_phone", gap)
        self.assertNotIn("customer_email", gap)


if __name__ == "__main__":
    unittest.main()