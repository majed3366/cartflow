# -*- coding: utf-8 -*-
"""Merchant SaaS auth v1 — signup, login, session, password reset."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import MerchantPasswordResetToken, MerchantUser, Store
from services.merchant_auth_http import (
    issue_merchant_session_cookie_value,
    parse_merchant_session_cookie_value,
)
from services.recovery_store_lookup import is_widget_recovery_zid

log = logging.getLogger("cartflow")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8
_RESET_TTL_HOURS = 2


def is_development_env() -> bool:
    return (os.getenv("ENV") or "").strip().lower() == "development"


def development_dashboard_bypass_active() -> bool:
    return is_development_env()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt.encode("utf-8"),
        260_000,
    )
    return f"pbkdf2_sha256$260000${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    sh = (stored_hash or "").strip()
    parts = sh.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return secrets.compare_digest(dk.hex(), expected_hex)


def normalize_email(raw: str) -> Optional[str]:
    e = (raw or "").strip().lower()[:255]
    if not e or not _EMAIL_RE.match(e):
        return None
    return e


def resolve_merchant_display_name(merchant_name: str, store_name: str) -> str:
    """Public signup collects store name only; keep DB ``merchant_name`` populated."""
    mn = (merchant_name or "").strip()
    if len(mn) >= 2:
        return mn[:255]
    sn = (store_name or "").strip()
    if len(sn) >= 2:
        return sn[:255]
    return ""


def ensure_merchant_auth_db_ready() -> None:
    """Idempotent DDL for auth tables/columns (production has no startup create_all)."""
    from schema_production_store_bootstrap import ensure_production_store_schema

    ensure_production_store_schema(db, context="merchant_auth")


def _slugify_store_name(store_name: str) -> str:
    s = (store_name or "").strip().lower()
    s = re.sub(r"[^\w\s\u0600-\u06FF-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    s = s[:48] or "store"
    if is_widget_recovery_zid(s):
        s = "merchant-store"
    return s


def generate_unique_store_zid(store_name: str) -> str:
    base = _slugify_store_name(store_name)
    for _ in range(24):
        candidate = f"{base}-{secrets.token_hex(3)}"
        try:
            exists = (
                db.session.query(Store.id)
                .filter(Store.zid_store_id == candidate)
                .first()
            )
        except SQLAlchemyError:
            db.session.rollback()
            exists = None
        if exists is None:
            return candidate
    return f"{base}-{secrets.token_hex(6)}"


def get_merchant_user_by_id(merchant_user_id: int) -> Optional[MerchantUser]:
    try:
        return (
            db.session.query(MerchantUser)
            .filter(MerchantUser.id == int(merchant_user_id))
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def get_merchant_user_by_email(email: str) -> Optional[MerchantUser]:
    norm = normalize_email(email)
    if not norm:
        return None
    try:
        return (
            db.session.query(MerchantUser)
            .filter(MerchantUser.email == norm)
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def get_primary_store_for_merchant(user: MerchantUser) -> Optional[Store]:
    sid = getattr(user, "primary_store_id", None)
    if sid:
        try:
            row = db.session.query(Store).filter(Store.id == int(sid)).first()
            if row is not None:
                return row
        except SQLAlchemyError:
            db.session.rollback()
    try:
        return (
            db.session.query(Store)
            .filter(Store.merchant_user_id == user.id)
            .order_by(Store.id.asc())
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def merchant_id_from_request_cookies(cookies: dict[str, str]) -> Optional[int]:
    from services.merchant_auth_http import merchant_cookie_name

    raw = cookies.get(merchant_cookie_name())
    return parse_merchant_session_cookie_value(raw)


def resolve_authenticated_store_slug(cookies: dict[str, str]) -> Optional[str]:
    mid = merchant_id_from_request_cookies(cookies)
    if not mid:
        return None
    user = get_merchant_user_by_id(mid)
    if not user:
        return None
    store = get_primary_store_for_merchant(user)
    if not store:
        return None
    zid = (getattr(store, "zid_store_id", None) or "").strip()
    return zid or None


def merchant_user_has_linked_store(user: MerchantUser) -> bool:
    return get_primary_store_for_merchant(user) is not None


def signup_audit_context(
    *,
    email: str = "",
    password: str = "",
    merchant_name: str = "",
) -> dict[str, Any]:
    em = normalize_email(email)
    existing = get_merchant_user_by_email(em) if em else None
    orphan = (
        existing is not None and not merchant_user_has_linked_store(existing)
    )
    return {
        "email_present": bool((email or "").strip()),
        "password_present": bool((password or "").strip()),
        "merchant_name_present": bool((merchant_name or "").strip()),
        "existing_user": existing is not None,
        "orphan_user_no_store": orphan,
        "existing_user_id": int(existing.id) if existing is not None else None,
    }


def log_signup_400(
    *,
    reason: str,
    validation_error: str = "",
    email: str = "",
    password: str = "",
    merchant_name: str = "",
    reg_msg: str = "",
) -> None:
    ctx = signup_audit_context(
        email=email, password=password, merchant_name=merchant_name
    )
    line = (
        "[SIGNUP 400] "
        f"reason={reason} "
        f"email_present={str(ctx['email_present']).lower()} "
        f"password_present={str(ctx['password_present']).lower()} "
        f"merchant_name_present={str(ctx['merchant_name_present']).lower()} "
        f"existing_user={str(ctx['existing_user']).lower()} "
        f"orphan_user_no_store={str(ctx['orphan_user_no_store']).lower()} "
        f"validation_error={validation_error or '-'} "
        f"reg_msg={(reg_msg or '-')[:120]}"
    )
    if ctx.get("existing_user_id") is not None:
        line += f" existing_user_id={ctx['existing_user_id']}"
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def validate_signup_form(
    *,
    merchant_name: str = "",
    store_name: str,
    email: str,
    password: str,
    confirm_password: str,
) -> Tuple[bool, str, dict[str, str]]:
    errors: dict[str, str] = {}
    sn = (store_name or "").strip()
    mn = resolve_merchant_display_name(merchant_name, store_name)
    em = normalize_email(email)
    if len(sn) < 2:
        errors["store_name"] = "أدخل اسم المتجر (حرفان على الأقل)."
    if not em:
        errors["email"] = "أدخل بريداً إلكترونياً صالحاً."
    else:
        existing = get_merchant_user_by_email(em)
        if existing is not None and merchant_user_has_linked_store(existing):
            errors["email"] = "هذا البريد مسجّل مسبقاً."
    if len(password or "") < _MIN_PASSWORD_LEN:
        errors["password"] = f"كلمة المرور {_MIN_PASSWORD_LEN} أحرف على الأقل."
    if password != confirm_password:
        errors["confirm_password"] = "كلمتا المرور غير متطابقتين."
    if errors:
        return False, "تحقق من الحقول أدناه.", errors
    return True, "", {
        "merchant_name": mn,
        "store_name": sn,
        "email": em or "",
        "password": password,
    }


def format_signup_field_errors(errors: dict[str, str]) -> str:
    if not errors:
        return "-"
    return ",".join(f"{k}={v[:80]}" for k, v in sorted(errors.items()))


def _verify_merchant_store_linkage(user: MerchantUser) -> tuple[bool, str]:
    """Post-commit check: MerchantUser ↔ Store bidirectional link."""
    try:
        db.session.refresh(user)
    except SQLAlchemyError:
        db.session.rollback()
    store = get_primary_store_for_merchant(user)
    if store is None:
        return False, "no_store_resolved"
    owner = getattr(store, "merchant_user_id", None)
    if owner is None or int(owner) != int(user.id):
        return False, "store_merchant_user_id_mismatch"
    pid = getattr(user, "primary_store_id", None)
    if pid is None or int(pid) != int(store.id):
        return False, "primary_store_id_mismatch"
    return True, "ok"


def _link_store_to_merchant_user(
    user: MerchantUser,
    *,
    store_name: str,
) -> tuple[bool, str, Optional[Store]]:
    zid = generate_unique_store_zid(store_name)
    store = Store(
        zid_store_id=zid,
        merchant_user_id=int(user.id),
        widget_display_name=store_name[:255],
        recovery_delay=2,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    db.session.add(store)
    db.session.flush()
    user.primary_store_id = int(store.id)
    db.session.flush()
    return True, "", store


def register_merchant_account(
    *,
    merchant_name: str = "",
    store_name: str,
    email: str,
    password: str,
) -> Tuple[bool, str, Optional[MerchantUser]]:
    ensure_merchant_auth_db_ready()
    ok, msg, validated = validate_signup_form(
        merchant_name=merchant_name,
        store_name=store_name,
        email=email,
        password=password,
        confirm_password=password,
    )
    if not ok:
        field_keys = sorted(validated.keys()) if isinstance(validated, dict) else []
        log.info(
            "[MERCHANT SIGNUP] stage=validate outcome=fail reason=%s field_errors=%s",
            msg,
            field_keys,
        )
        return False, msg, None
    em = validated["email"]
    log.info("[MERCHANT SIGNUP] stage=validate outcome=ok")
    existing = get_merchant_user_by_email(em)
    orphan_complete = (
        existing is not None and not merchant_user_has_linked_store(existing)
    )
    try:
        if orphan_complete:
            assert existing is not None
            if not verify_password(validated["password"], existing.password_hash):
                log.info(
                    "[MERCHANT SIGNUP] stage=orphan_complete outcome=fail "
                    "user_id=%s reason=wrong_password",
                    existing.id,
                )
                return False, "هذا البريد مسجّل مسبقاً.", None
            user = existing
            if validated["merchant_name"]:
                user.merchant_name = validated["merchant_name"]
            link_ok, link_err, store = _link_store_to_merchant_user(
                user, store_name=validated["store_name"]
            )
            if not link_ok or store is None:
                db.session.rollback()
                return False, link_err or "تعذر ربط المتجر بالحساب.", None
            db.session.commit()
            db.session.refresh(user)
            db.session.refresh(store)
            mode = "orphan_link"
        else:
            user = MerchantUser(
                email=em,
                password_hash=hash_password(validated["password"]),
                merchant_name=validated["merchant_name"],
            )
            db.session.add(user)
            db.session.flush()
            link_ok, link_err, store = _link_store_to_merchant_user(
                user, store_name=validated["store_name"]
            )
            if not link_ok or store is None:
                db.session.rollback()
                return False, link_err or "تعذر إنشاء المتجر.", None
            db.session.commit()
            db.session.refresh(user)
            db.session.refresh(store)
            mode = "new_user"
        linked, link_reason = _verify_merchant_store_linkage(user)
        log.info(
            "[MERCHANT SIGNUP] stage=create outcome=ok mode=%s user_id=%s store_id=%s "
            "primary_store_id=%s store_merchant_user_id=%s verify_ok=%s verify_reason=%s",
            mode,
            user.id,
            store.id,
            getattr(user, "primary_store_id", None),
            getattr(store, "merchant_user_id", None),
            linked,
            link_reason,
        )
        if not linked:
            log.error(
                "[MERCHANT SIGNUP] stage=verify outcome=fail user_id=%s reason=%s",
                user.id,
                link_reason,
            )
            return False, "تعذر إنشاء الحساب. حاول مرة أخرى.", None
        return True, "", user
    except IntegrityError as exc:
        db.session.rollback()
        log.warning(
            "[MERCHANT SIGNUP] stage=create outcome=integrity_error exc_type=%s exc=%s",
            type(exc).__name__,
            exc,
        )
        return False, "هذا البريد مسجّل مسبقاً.", None
    except SQLAlchemyError as exc:
        db.session.rollback()
        log.warning(
            "[MERCHANT SIGNUP] stage=create outcome=db_error exc_type=%s exc=%s",
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return False, "تعذر إنشاء الحساب. حاول مرة أخرى.", None


def validate_login_form(email: str, password: str) -> Tuple[bool, str]:
    em = normalize_email(email)
    if not em:
        return False, "أدخل بريداً إلكترونياً صالحاً."
    if not (password or "").strip():
        return False, "أدخل كلمة المرور."
    user = get_merchant_user_by_email(em)
    if not user or not verify_password(password, user.password_hash):
        return False, "البريد أو كلمة المرور غير صحيحة."
    return True, ""


def authenticate_merchant(email: str, password: str) -> Optional[MerchantUser]:
    em = normalize_email(email)
    if not em:
        return None
    user = get_merchant_user_by_email(em)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def session_cookie_value_for_user(user: MerchantUser) -> str:
    return issue_merchant_session_cookie_value(int(user.id))


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def request_password_reset(
    email: str,
    *,
    reset_base_url: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Returns (user_message, dev_reset_url_or_none).
    Same message whether or not email exists (no enumeration).
    """
    from services.merchant_password_reset_email import (
        build_password_reset_link,
        deliver_password_reset_email,
    )

    safe_msg = "إذا كان البريد مسجلاً، ستصلك تعليمات الاستعادة."
    em = normalize_email(email)
    if not em:
        return safe_msg, None
    user = get_merchant_user_by_email(em)
    if not user:
        return safe_msg, None
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw)
    expires = _utcnow() + timedelta(hours=_RESET_TTL_HOURS)
    row = MerchantPasswordResetToken(
        merchant_user_id=user.id,
        token_hash=token_hash,
        expires_at=expires,
    )
    try:
        db.session.add(row)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log.warning("password reset token persist failed: %s", exc)
        return safe_msg, None
    reset_link = build_password_reset_link(raw, base_url=reset_base_url)
    _sent, dev_url = deliver_password_reset_email(to_email=em, reset_link=reset_link)
    return safe_msg, dev_url


def _valid_reset_token(raw_token: str) -> Optional[MerchantPasswordResetToken]:
    th = _hash_reset_token(raw_token)
    now = _utcnow()
    try:
        row = (
            db.session.query(MerchantPasswordResetToken)
            .filter(MerchantPasswordResetToken.token_hash == th)
            .filter(MerchantPasswordResetToken.used_at.is_(None))
            .filter(MerchantPasswordResetToken.expires_at >= now)
            .order_by(MerchantPasswordResetToken.id.desc())
            .first()
        )
        return row
    except SQLAlchemyError:
        db.session.rollback()
        return None


def validate_reset_password_form(
    *,
    token: str,
    password: str,
    confirm_password: str,
) -> Tuple[bool, str, Optional[MerchantPasswordResetToken]]:
    if not (token or "").strip():
        return False, "رابط الاستعادة غير صالح.", None
    if len(password or "") < _MIN_PASSWORD_LEN:
        return False, f"كلمة المرور {_MIN_PASSWORD_LEN} أحرف على الأقل.", None
    if password != confirm_password:
        return False, "كلمتا المرور غير متطابقتين.", None
    row = _valid_reset_token(token.strip())
    if not row:
        return False, "رابط الاستعادة غير صالح أو منتهٍ.", None
    return True, "", row


def apply_password_reset(
    *,
    token: str,
    password: str,
) -> Tuple[bool, str]:
    ok, msg, row = validate_reset_password_form(
        token=token,
        password=password,
        confirm_password=password,
    )
    if not ok or not row:
        return False, msg
    user = get_merchant_user_by_id(int(row.merchant_user_id))
    if not user:
        return False, "رابط الاستعادة غير صالح."
    try:
        user.password_hash = hash_password(password)
        row.used_at = _utcnow()
        db.session.commit()
        return True, ""
    except SQLAlchemyError as exc:
        db.session.rollback()
        log.warning("password reset apply failed: %s", exc)
        return False, "تعذر تحديث كلمة المرور."


def reset_token_is_valid(raw_token: str) -> bool:
    return _valid_reset_token((raw_token or "").strip()) is not None


def path_requires_merchant_auth(path: str) -> bool:
    p = (path or "").strip()
    if p == "/dashboard" or p.startswith("/dashboard/"):
        return True
    if p == "/api/dashboard" or p.startswith("/api/dashboard/"):
        return True
    if p == "/api/merchant" or p.startswith("/api/merchant/"):
        return True
    return False


def safe_redirect_path(next_path: Optional[str]) -> str:
    p = (next_path or "").strip()
    if p.startswith("/dashboard") and "://" not in p:
        return p
    return "/dashboard"


__all__ = [
    "apply_password_reset",
    "path_requires_merchant_auth",
    "reset_token_is_valid",
    "authenticate_merchant",
    "development_dashboard_bypass_active",
    "ensure_merchant_auth_db_ready",
    "generate_unique_store_zid",
    "resolve_merchant_display_name",
    "get_merchant_user_by_email",
    "get_merchant_user_by_id",
    "get_primary_store_for_merchant",
    "hash_password",
    "is_development_env",
    "merchant_id_from_request_cookies",
    "normalize_email",
    "format_signup_field_errors",
    "log_signup_400",
    "merchant_user_has_linked_store",
    "register_merchant_account",
    "request_password_reset",
    "signup_audit_context",
    "resolve_authenticated_store_slug",
    "safe_redirect_path",
    "session_cookie_value_for_user",
    "validate_login_form",
    "validate_reset_password_form",
    "validate_signup_form",
    "verify_password",
]
