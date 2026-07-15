# -*- coding: utf-8 -*-
"""Time Authority exceptions — WP-1."""
from __future__ import annotations


class TimeAuthorityError(Exception):
    """Base error for Platform Time Authority."""


class MissingQueryTimeContext(TimeAuthorityError):
    """Raised when a merchant-relevant decision requires an active Query Time Context."""


class InvalidClockProvider(TimeAuthorityError):
    """Raised when a provider is missing, unbound, or fails validation."""


class QueryTimeContextError(TimeAuthorityError):
    """Raised for invalid Query Time Context activation or nesting rules."""
