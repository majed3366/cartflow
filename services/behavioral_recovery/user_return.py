# -*- coding: utf-8 -*-
"""Persist return-to-site on the cart row (in addition to in-memory anti-spam flag)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.cartflow_identity import (
    IDENTITY_TRUST_FAILED_KEY,
    IDENTITY_TRUST_MESSAGE_KEY,
    MERCHANT_IDENTITY_TRUST_AR,
    inferred_expected_store_pk_from_candidates,
    log_cartflow_identity_warning,
    resolve_store_pk_for_event_slug,
    should_merge_behavioral_for_store,
)
from services.recovery_conversation_state_machine import (
    build_return_to_site_behavioral_patch,
)
from services.behavioral_recovery.state_store import (
    abandoned_carts_for_session_or_cart,
    behavioral_dict_for_abandoned_cart,
    merge_behavioral_state,
    utc_now_iso,
)
from services.cartflow_observability_runtime import RecoveryLifecycleEvent, trace_recovery_lifecycle

log = logging.getLogger("cartflow")

RETURN_VISIT_KIND_PASSIVE = "passive_return_visit"
RETURN_VISIT_KIND_ACTIVE = "active_commercial_reengagement"


def payload_indicates_user_returned_to_site(payload: dict[str, Any]) -> bool:
    """
    Deprecated semantic: historically any return tracker ping.
    Kept for callers that mean «payload mentions return tracking» only.
    Prefer payload_indicates_active_commercial_reengagement /
    payload_indicates_passive_return_visit.
    """
    return bool(
        payload_indicates_active_commercial_reengagement(payload)
        or payload_indicates_passive_return_visit(payload)
    )


def payload_indicates_active_commercial_reengagement(payload: dict[str, Any]) -> bool:
    """
    عودة ذات معنى تجاري — تفعّل إيقاف الاسترجاع و‎customer_returned‎ فقط عند هذه الإشارات.
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("active_commercial_reengagement") is True:
        return True
    if (
        str(payload.get("return_visit_kind") or "").strip().lower()
        == RETURN_VISIT_KIND_ACTIVE
    ):
        return True
    if payload.get("returned_checkout_page") is True:
        return True
    _, rc = _return_page_flags_from_payload(payload)
    if rc:
        return True
    et = str(payload.get("event_type") or "").strip().lower()
    ev = str(payload.get("event") or "").strip().lower()
    if et in (
        "checkout_started",
        "checkout_clicked",
        "purchase_completed",
        "cart_quantity_changed",
    ):
        return True
    if ev in (
        "checkout_started",
        "checkout_clicked",
        "user_converted",
        "purchase_completed",
        "add_to_cart",
        "cart_quantity_changed",
    ):
        return True
    if payload.get("purchase_completed") is True or payload.get("user_converted") is True:
        return True
    ctx = str(
        payload.get("recovery_return_context")
        or payload.get("return_context")
        or ""
    ).strip().lower()
    ur = payload.get("user_returned_to_site")
    ur_true = ur is True or (
        isinstance(ur, str) and ur.strip().lower() in ("1", "true", "yes", "on")
    )
    legacy_tracker = ur_true or et == "user_returned_to_site" or ev == "user_returned_to_site"
    if legacy_tracker and ctx in ("checkout", "checkout_page", "payment", "pay"):
        return True
    return False


def payload_indicates_passive_return_visit(payload: dict[str, Any]) -> bool:
    """تصفّح / تنقّل فقط — تشخيصات فقط دون إيقاف الاسترجاع."""
    if not isinstance(payload, dict):
        return False
    if payload_indicates_active_commercial_reengagement(payload):
        return False
    if payload.get("passive_return_visit") is True:
        return True
    if (
        str(payload.get("return_visit_kind") or "").strip().lower()
        == RETURN_VISIT_KIND_PASSIVE
    ):
        return True
    ur = payload.get("user_returned_to_site")
    ur_true = ur is True or (
        isinstance(ur, str) and ur.strip().lower() in ("1", "true", "yes", "on")
    )
    et = str(payload.get("event_type") or "").strip().lower()
    ev = str(payload.get("event") or "").strip().lower()
    legacy_signal = ur_true or et == "user_returned_to_site" or ev == "user_returned_to_site"
    return legacy_signal


def _return_page_flags_from_payload(payload: dict[str, Any]) -> tuple[bool, bool]:
    rp = payload.get("returned_product_page") is True
    rc = payload.get("returned_checkout_page") is True
    ctx = str(
        payload.get("recovery_return_context")
        or payload.get("return_page")
        or payload.get("return_context")
        or ""
    ).strip().lower()
    if ctx in ("product", "product_page", "pdp", "item"):
        rp = True
    if ctx in ("checkout", "checkout_page", "payment", "pay"):
        rc = True
    return rp, rc


def _mark_identity_trust_failure(ac: Any, *, internal_reason: str) -> None:
    _ = internal_reason  # logged at call sites; not persisted to avoid leaking internals
    merge_behavioral_state(
        ac,
        **{
            IDENTITY_TRUST_FAILED_KEY: True,
            IDENTITY_TRUST_MESSAGE_KEY: MERCHANT_IDENTITY_TRUST_AR,
        },
    )
    db.session.add(ac)


def record_passive_return_visit_from_payload(payload: dict[str, Any]) -> None:
    """
    تسجيل عودة تصفّحية فقط — لا ‎user_returned_to_site‎ ولا سجل ‎returned_to_site‎ ولا إيقاف إرسال.
    """
    if not isinstance(payload, dict) or not payload_indicates_passive_return_visit(payload):
        return
    sid = ""
    raw_sid = payload.get("session_id")
    if isinstance(raw_sid, str) and raw_sid.strip():
        sid = raw_sid.strip()[:512]
    cid_raw = payload.get("cart_id")
    cid = str(cid_raw).strip()[:255] if cid_raw is not None else ""
    if not sid and not cid:
        log.info("[PASSIVE RETURN] behavioral_persist_skipped missing session_id and cart_id")
        return
    store_slug_disp = str(
        payload.get("store") or payload.get("store_slug") or ""
    ).strip() or "default"
    ctx_raw = str(
        payload.get("recovery_return_context")
        or payload.get("return_context")
        or ""
    ).strip()[:64]

    from services.cartflow_duplicate_guard import try_consume_behavioral_return_merge

    minute_bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    passive_sig = (
        f"passive_v1|{store_slug_disp}|{sid}|{cid}|{minute_bucket}|"
        f"{(ctx_raw or '-')[:48]}"
    )
    if not try_consume_behavioral_return_merge(signature=passive_sig, ttl_seconds=25.0):
        log.info(
            "[PASSIVE RETURN] merge_skipped duplicate_guard session_id=%s cart_id=%s",
            (sid or "-")[:64],
            (cid or "-")[:48],
        )
        return
    try:
        from main import _ensure_cartflow_api_db_warmed

        _ensure_cartflow_api_db_warmed()
        cands = abandoned_carts_for_session_or_cart(sid, cid or None)
        non_vip_pre = [ac for ac in cands if not bool(getattr(ac, "vip_mode", False))]
        store_pk = resolve_store_pk_for_event_slug(store_slug_disp)
        inferred_src = "payload_slug"
        inferred_only = False
        if store_pk is None and non_vip_pre:
            store_pk, inferred_src = inferred_expected_store_pk_from_candidates(
                non_vip_pre
            )
            inferred_only = inferred_src != "payload_slug"
        if (
            store_pk is None
            and inferred_src == "ambiguous_multi_store_cart_rows"
            and non_vip_pre
        ):
            log_cartflow_identity_warning(
                store_slug=store_slug_disp,
                resolved_store_id="-",
                expected_store_id="-",
                session_id=sid,
                cart_id=cid,
                reason="passive_return_merge_blocked_ambiguous_store_scope",
            )
            _mark_identity_trust_failure(
                non_vip_pre[0], internal_reason="ambiguous_multi_store"
            )
            db.session.commit()
            return
        touched = False
        for ac in cands:
            if bool(getattr(ac, "vip_mode", False)):
                continue
            ok, skip_reason = should_merge_behavioral_for_store(
                ac,
                expected_store_pk=store_pk,
                inferred_only=inferred_only,
            )
            if not ok:
                continue
            prior = behavioral_dict_for_abandoned_cart(ac)
            try:
                n = int(prior.get("passive_return_visit_count") or 0)
            except (TypeError, ValueError):
                n = 0
            passive_patch: dict[str, Any] = {
                "passive_return_visit_count": n + 1,
                "last_passive_return_visit_at": utc_now_iso(),
                "return_visit_kind_last": RETURN_VISIT_KIND_PASSIVE,
                IDENTITY_TRUST_FAILED_KEY: False,
                IDENTITY_TRUST_MESSAGE_KEY: None,
            }
            if ctx_raw:
                passive_patch["last_passive_return_context"] = ctx_raw
            merge_behavioral_state(ac, **passive_patch)
            db.session.add(ac)
            touched = True
        if touched:
            db.session.commit()
            trace_recovery_lifecycle(
                RecoveryLifecycleEvent.PASSIVE_RETURN_VISIT,
                session_id=sid,
                cart_id=cid,
                store_slug=store_slug_disp,
                extra_status="behavioral_passive_only",
            )
            log.info(
                "[PASSIVE RETURN] persisted store_slug=%s session_id=%s cart_id=%s context=%s",
                store_slug_disp,
                sid,
                cid or "-",
                ctx_raw or "-",
            )
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("passive return visit: %s", e, exc_info=True)


def record_behavioral_user_return_from_payload(
    payload: dict[str, Any],
    *,
    skip_db_schema_bootstrap: bool = False,
) -> None:
    """Persist commercial return-to-site on ‎AbandonedCart.cf_behavioral‎ (normal carts only)."""
    if not isinstance(payload, dict):
        return
    if not payload_indicates_active_commercial_reengagement(payload):
        return
    sid = ""
    raw_sid = payload.get("session_id")
    if isinstance(raw_sid, str) and raw_sid.strip():
        sid = raw_sid.strip()[:512]
    cid_raw = payload.get("cart_id")
    cid = str(cid_raw).strip()[:255] if cid_raw is not None else ""
    if not sid and not cid:
        log.info(
            "[RETURN TO SITE] behavioral_persist_skipped missing session_id and cart_id"
        )
        return
    store_slug_disp = str(
        payload.get("store") or payload.get("store_slug") or ""
    ).strip() or "default"
    returned_product_page, returned_checkout_page = _return_page_flags_from_payload(
        payload
    )
    rts = payload.get("return_timestamp")
    if isinstance(rts, str) and rts.strip():
        return_ts_iso = rts.strip()[:64]
    else:
        return_ts_iso = utc_now_iso()
    from services.cartflow_duplicate_guard import (
        behavioral_return_merge_signature,
        try_consume_behavioral_return_merge,
    )

    ctx_tail_preview = str(
        payload.get("recovery_return_context")
        or payload.get("return_context")
        or ""
    ).strip()[:64]
    _beh_sig = behavioral_return_merge_signature(
        store_slug=store_slug_disp,
        session_id=sid,
        cart_id=cid,
        return_ts_iso=return_ts_iso,
        returned_product_page=returned_product_page,
        returned_checkout_page=returned_checkout_page,
        context_tail=ctx_tail_preview,
    )
    if not try_consume_behavioral_return_merge(signature=_beh_sig):
        log.info(
            "[RETURN TO SITE] behavioral_merge_skipped duplicate_guard session_id=%s cart_id=%s",
            (sid or "-")[:64],
            (cid or "-")[:48],
        )
        return
    try:
        if not skip_db_schema_bootstrap:
            from main import _ensure_cartflow_api_db_warmed

            _ensure_cartflow_api_db_warmed()
        cands = abandoned_carts_for_session_or_cart(sid, cid or None)
        non_vip_pre = [
            ac for ac in cands if not bool(getattr(ac, "vip_mode", False))
        ]
        store_pk = resolve_store_pk_for_event_slug(store_slug_disp)
        inferred_src = "payload_slug"
        inferred_only = False
        if store_pk is None and non_vip_pre:
            store_pk, inferred_src = inferred_expected_store_pk_from_candidates(
                non_vip_pre
            )
            inferred_only = inferred_src != "payload_slug"
        if (
            store_pk is None
            and inferred_src == "ambiguous_multi_store_cart_rows"
            and non_vip_pre
        ):
            log_cartflow_identity_warning(
                store_slug=store_slug_disp,
                resolved_store_id="-",
                expected_store_id="-",
                session_id=sid,
                cart_id=cid,
                reason="behavioral_merge_blocked_ambiguous_store_scope",
            )
            _mark_identity_trust_failure(
                non_vip_pre[0], internal_reason="ambiguous_multi_store"
            )
            trace_recovery_lifecycle(
                RecoveryLifecycleEvent.MERGE_BLOCKED,
                session_id=sid,
                cart_id=cid,
                store_slug=store_slug_disp,
                extra_status="ambiguous_multi_store",
            )
            db.session.commit()
            return

        touched = False
        last_rc = 0
        last_ctx = ""
        last_ac: Any = None
        merge_attempted = False
        for ac in cands:
            if bool(getattr(ac, "vip_mode", False)):
                continue
            merge_attempted = True
            ok, skip_reason = should_merge_behavioral_for_store(
                ac,
                expected_store_pk=store_pk,
                inferred_only=inferred_only,
            )
            if not ok:
                log_cartflow_identity_warning(
                    store_slug=store_slug_disp,
                    resolved_store_id=str(getattr(ac, "store_id", "") or "")
                    or "-",
                    expected_store_id=str(store_pk if store_pk is not None else "")
                    or "-",
                    session_id=sid,
                    cart_id=cid,
                    reason=f"behavioral_merge_skipped:{skip_reason}",
                )
                trace_recovery_lifecycle(
                    RecoveryLifecycleEvent.MERGE_BLOCKED,
                    session_id=sid,
                    cart_id=cid,
                    store_slug=store_slug_disp,
                    extra_status=f"skip:{skip_reason}",
                )
                continue
            prior = behavioral_dict_for_abandoned_cart(ac)
            extra = build_return_to_site_behavioral_patch(
                prior,
                returned_product_page=returned_product_page,
                returned_checkout_page=returned_checkout_page,
                return_timestamp_iso=return_ts_iso,
                fuse_adaptive=True,
            )
            ctx_raw = str(
                payload.get("recovery_return_context")
                or payload.get("return_context")
                or ""
            ).strip()[:64]
            merge_fields: dict[str, Any] = {
                "user_returned_to_site": True,
                "customer_returned_to_site": True,
                "user_returned_at": utc_now_iso(),
                "lifecycle_hint": "returned",
                IDENTITY_TRUST_FAILED_KEY: False,
                IDENTITY_TRUST_MESSAGE_KEY: None,
                **extra,
            }
            if ctx_raw:
                merge_fields["recovery_return_context"] = ctx_raw
            merge_behavioral_state(ac, **merge_fields)
            db.session.add(ac)
            touched = True
            last_ac = ac
            try:
                last_rc = int(extra.get("recovery_site_return_count") or 0)
            except (TypeError, ValueError):
                last_rc = 0
            last_ctx = ctx_raw or str(prior.get("recovery_return_context") or "")[:64]
        if not touched and merge_attempted and non_vip_pre:
            log_cartflow_identity_warning(
                store_slug=store_slug_disp,
                resolved_store_id="-",
                expected_store_id=str(store_pk if store_pk is not None else "")
                or "-",
                session_id=sid,
                cart_id=cid,
                reason="behavioral_merge_skipped_all_rows_store_mismatch",
            )
            _mark_identity_trust_failure(
                non_vip_pre[0],
                internal_reason="all_rows_skipped",
            )
            trace_recovery_lifecycle(
                RecoveryLifecycleEvent.MERGE_BLOCKED,
                session_id=sid,
                cart_id=cid,
                store_slug=store_slug_disp,
                extra_status="all_rows_store_mismatch",
            )
            db.session.commit()
            return
        if touched:
            db.session.commit()
            trace_recovery_lifecycle(
                RecoveryLifecycleEvent.RETURNED_TO_SITE,
                session_id=sid,
                cart_id=cid,
                store_slug=store_slug_disp,
                extra_status="behavioral_persisted",
            )
            if last_ctx == "" and last_ac is not None:
                last_ctx = str(
                    behavioral_dict_for_abandoned_cart(last_ac).get(
                        "recovery_return_context"
                    )
                    or "-"
                )[:64]
            elif last_ctx == "":
                last_ctx = "-"
            line = (
                "[LIFECYCLE STATE] hint=returned_to_site session_id=%s cart_id=%s "
                "return_count=%s context=%s"
                % (
                    (sid or "-")[:64],
                    (cid or "-")[:48],
                    last_rc,
                    last_ctx,
                )
            )
            print(line, flush=True)
            log.info("%s", line)
            line = (
                "[RETURN TO SITE] persisted_behavioral store_slug=%s session_id=%s "
                "cart_id=%s context=%s return_count=%s"
                % (
                    store_slug_disp,
                    sid,
                    cid or "-",
                    last_ctx,
                    last_rc,
                )
            )
            print(line, flush=True)
            log.info("%s", line)
            line2 = (
                "[RETURN TO SITE] recovery_stopped_signal session_id=%s cart_id=%s"
                % (sid, cid)
            )
            print(line2, flush=True)
            log.info("%s", line2)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("behavioral user return: %s", e, exc_info=True)
