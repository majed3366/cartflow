# -*- coding: utf-8 -*-
"""CartFlow API process entry. Never starts Scheduler loops."""
from __future__ import annotations

from services.process_entry_v1 import assert_entry_matches_role, configure_api_entry, reject_scheduler_via_web_entry

configure_api_entry()
assert_entry_matches_role()
reject_scheduler_via_web_entry()

from main import app  # noqa: E402

__all__ = ["app"]
