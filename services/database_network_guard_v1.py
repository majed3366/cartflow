# -*- coding: utf-8 -*-
"""
Classify DATABASE_URL host class without logging credentials.

Production allows Railway private hosts only. Public proxy is rejected unless
CARTFLOW_ALLOW_PUBLIC_DATABASE is explicitly enabled (default OFF).
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlparse, unquote

ENV_ALLOW_PUBLIC = "CARTFLOW_ALLOW_PUBLIC_DATABASE"

CLASS_PRIVATE = "railway_private"
CLASS_PUBLIC_PROXY = "railway_public_proxy"
CLASS_EXTERNAL = "external_public"
CLASS_LOCAL = "localhost"
CLASS_SQLITE = "sqlite"
CLASS_MISSING = "missing"
CLASS_MALFORMED = "malformed"

_SECRET_KEYS = (
    "password",
    "passwd",
    "username",
    "user",
    "hostname",
    "host",
    "port",
    "database",
    "dbname",
    "url",
    "dsn",
)


class DatabaseNetworkGuardError(RuntimeError):
    """Database host class is not allowed for this runtime."""


def _env_truthy(name: str) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def public_database_override_enabled() -> bool:
    return _env_truthy(ENV_ALLOW_PUBLIC)


def _raw_database_url() -> str:
    return (os.getenv("DATABASE_URL") or "").strip()


def classify_database_url(raw: Optional[str] = None) -> dict[str, Any]:
    value = (raw if raw is not None else _raw_database_url()).strip()
    if not value:
        return {"class": CLASS_MISSING, "allowed": False, "reason": "missing_database_url"}
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://") :]
    if value.startswith("sqlite:"):
        return {"class": CLASS_SQLITE, "allowed": True, "reason": "sqlite"}
    try:
        parsed = urlparse(value)
    except Exception:  # noqa: BLE001
        return {"class": CLASS_MALFORMED, "allowed": False, "reason": "malformed_url"}
    if not parsed.scheme or parsed.scheme not in (
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
        "mysql",
        "mysql+pymysql",
    ):
        if "://" not in value:
            return {"class": CLASS_MALFORMED, "allowed": False, "reason": "malformed_url"}
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host and parsed.scheme.startswith("postgres"):
        return {"class": CLASS_MALFORMED, "allowed": False, "reason": "malformed_url"}
    if host in ("localhost", "127.0.0.1", "::1"):
        return {"class": CLASS_LOCAL, "allowed": True, "reason": "localhost"}
    if host.endswith(".railway.internal"):
        return {"class": CLASS_PRIVATE, "allowed": True, "reason": "railway_private"}
    if (
        host.endswith(".proxy.rlwy.net")
        or host.endswith(".rlwy.net")
        or host.endswith(".up.railway.app")
        or host.endswith(".railway.app")
    ):
        return {
            "class": CLASS_PUBLIC_PROXY,
            "allowed": False,
            "reason": "railway_public_proxy",
        }
    if host:
        return {"class": CLASS_EXTERNAL, "allowed": False, "reason": "external_public"}
    return {"class": CLASS_MALFORMED, "allowed": False, "reason": "malformed_url"}


def _is_production_like() -> bool:
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "development":
        return False
    if env in ("production", "prod", "staging", "preview"):
        return True
    return False


def assert_database_url_allowed(raw: Optional[str] = None) -> dict[str, Any]:
    """
    Fail closed in production-like runtimes for public/missing/malformed hosts.

    SQLite and localhost are allowed (tests / local). Never include secrets
    in the raised message.
    """
    decision = classify_database_url(raw)
    klass = str(decision.get("class") or CLASS_MALFORMED)
    if klass in (CLASS_SQLITE, CLASS_LOCAL):
        return decision
    production_like = _is_production_like()
    if not production_like and klass != CLASS_MISSING:
        if klass == CLASS_MALFORMED:
            raise DatabaseNetworkGuardError("database url rejected: malformed")
        return decision
    if klass == CLASS_MISSING:
        raise DatabaseNetworkGuardError("database url rejected: missing")
    if klass == CLASS_MALFORMED:
        raise DatabaseNetworkGuardError("database url rejected: malformed")
    if klass == CLASS_PRIVATE:
        return decision
    if public_database_override_enabled():
        decision = dict(decision)
        decision["allowed"] = True
        decision["reason"] = "emergency_override"
        return decision
    if klass == CLASS_PUBLIC_PROXY:
        raise DatabaseNetworkGuardError("database url rejected: public_proxy")
    raise DatabaseNetworkGuardError("database url rejected: external")


def sanitize_guard_text(text: str) -> str:
    """Strip credential-like fragments from error strings for tests."""
    s = str(text or "")
    for key in _SECRET_KEYS:
        if key in s.lower() and "rejected" not in s.lower():
            return "database url rejected"
    # Never echo a URL
    if "://" in s or "@" in s:
        return "database url rejected"
    return s


def redact_url_for_logs(_raw: str) -> str:
    return "[redacted]"


__all__ = [
    "CLASS_EXTERNAL",
    "CLASS_LOCAL",
    "CLASS_MALFORMED",
    "CLASS_MISSING",
    "CLASS_PRIVATE",
    "CLASS_PUBLIC_PROXY",
    "CLASS_SQLITE",
    "DatabaseNetworkGuardError",
    "ENV_ALLOW_PUBLIC",
    "assert_database_url_allowed",
    "classify_database_url",
    "public_database_override_enabled",
    "redact_url_for_logs",
    "sanitize_guard_text",
    "unquote",
]
