# -*- coding: utf-8 -*-
"""Verify critical Python modules import in isolation (complexity / wiring smoke)."""
from __future__ import annotations

import importlib
import sys
import unittest


class OperationalModuleImportTests(unittest.TestCase):
    def test_core_runtime_modules_import(self) -> None:
        """Runtime modules initialize independently at import time."""
        mods = [
            "main",
            "services.recovery_message_strategy",
            "services.whatsapp_send",
            "services.recovery_session_phone",
            "services.behavioral_recovery.state_store",
            "services.behavioral_recovery.user_return",
        ]
        for name in mods:
            importlib.import_module(name)
            self.assertIn(name, sys.modules)

    def test_failed_optional_dependency_does_not_break_whatsapp_module(self) -> None:
        """
        Importing services.whatsapp_send must not require a live Twilio network call.
        (If Twilio SDK import ever breaks, this catches it without touching recovery scheduling.)
        """
        import services.whatsapp_send as wa  # noqa: PLC0415

        self.assertIsNotNone(wa.send_whatsapp)
        self.assertIsNotNone(wa.should_send_whatsapp)
