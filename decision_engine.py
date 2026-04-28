# -*- coding: utf-8 -*-
"""Thin module so ``main.py`` can use ``from decision_engine import decide_recovery_action``."""

from services.decision_engine import decide_recovery_action

__all__ = ["decide_recovery_action"]
