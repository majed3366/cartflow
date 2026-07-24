# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Mapping

ENV_HOME_EXECUTIVE_SUMMARY_V1 = "CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1"


def home_executive_summary_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    import os

    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_HOME_EXECUTIVE_SUMMARY_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_HOME_EXECUTIVE_SUMMARY_V1", "home_executive_summary_v1_enabled"]
