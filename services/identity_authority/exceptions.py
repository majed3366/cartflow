# -*- coding: utf-8 -*-
"""Identity Authority exceptions — INV-002 WP-1."""
from __future__ import annotations


class IdentityAuthorityError(Exception):
    """Base error for Platform Identity Authority."""


class IdentityError(IdentityAuthorityError):
    """Fail-closed identity resolution / verification error."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = (code or "identity_error").strip()
        super().__init__(message or self.code)


class MissingMerchantQueryIdentityContext(IdentityAuthorityError):
    """Raised when an operation requires an active MQIC and none is bound."""


class IdentityImmutabilityViolation(IdentityAuthorityError):
    """Raised when MQIC fields are mutated after bind (IA-3)."""


class IdentityOwnershipViolation(IdentityAuthorityError):
    """Raised when a non-Authority path attempts to author identity (IA-4)."""


class DualResolveViolation(IdentityAuthorityError):
    """Raised when identity is resolved more than once in the same request scope (IA-2)."""
