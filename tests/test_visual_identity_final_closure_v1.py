# -*- coding: utf-8 -*-
"""PDS Final Closure V1 — superseded by Merchant Frontend Recomposition V1.

Legacy certification CSS files remain on disk for archaeology but are no longer
the live merchant shell. See tests/test_merchant_frontend_recomposition_v1.py.
"""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


class VisualIdentityFinalClosureV1Tests(unittest.TestCase):
    def test_recomposition_owns_shell(self) -> None:
        self.assertIn("merchant_frame_v1.css", _TEMPLATE)
        self.assertNotIn("merchant_shell_identity_v1.css", _TEMPLATE)

    def test_body_still_marks_merchant_app(self) -> None:
        self.assertIn('data-cf-merchant-app="1"', _TEMPLATE)
        self.assertIn("cf-pds-closure", _TEMPLATE)

    def test_legacy_closure_files_still_exist_offline(self) -> None:
        for name in (
            "merchant_shell_identity_v1.css",
            "merchant_card_system_v1.css",
            "merchant_icon_language_v1.css",
            "merchant_spacing_certification_v1.css",
        ):
            self.assertTrue((_ROOT / "static" / name).is_file(), msg=name)


if __name__ == "__main__":
    unittest.main()
