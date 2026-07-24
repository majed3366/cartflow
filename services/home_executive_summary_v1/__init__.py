# -*- coding: utf-8 -*-
"""Home Executive Summary V1 — Home is executive summary only."""
from __future__ import annotations

from services.home_executive_summary_v1.compose_v1 import (
    attach_home_executive_summary_to_summary_v1,
    build_home_executive_summary_v1,
)
from services.home_executive_summary_v1.flag_v1 import (
    ENV_HOME_EXECUTIVE_SUMMARY_V1,
    home_executive_summary_v1_enabled,
)
from services.home_executive_summary_v1.slim_transport_v1 import (
    ENV_HOME_SLIM_TRANSPORT_V1,
    home_slim_transport_v1_enabled,
)

__all__ = [
    "ENV_HOME_EXECUTIVE_SUMMARY_V1",
    "ENV_HOME_SLIM_TRANSPORT_V1",
    "attach_home_executive_summary_to_summary_v1",
    "build_home_executive_summary_v1",
    "home_executive_summary_v1_enabled",
    "home_slim_transport_v1_enabled",
]
