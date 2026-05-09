# -*- coding: utf-8 -*-
"""Persist return-to-site on the cart row (in addition to in-memory anti-spam flag)."""
from __future__ import annotations

import logging
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

log = logging.getLogger("cartflow")


def payload_indicates_user_returned_to_site(payload: dict[str, Any]) -> bool:
    """‎POST /api/cart-event‎: عودة للموقع — علَم صريح أو ‎event_type‎."""
    if not isinstance(payload, dict):
        return False
    ur = payload.get("user_returned_to_site")
    if ur is True:
        return True
    if isinstance(ur, str) and ur.strip().lower() in ("1", "true", "yes", "on"):
        return True
    if isinstance(ur, int) and ur == 1:
        return True
    et = str(payload.get("event_type") or "").strip().lower()
    if et == "user_returned_to_site":
        return True
    ev = str(payload.get("event") or "").strip().lower()
    if ev == "user_returned_to_site":
        return True
    return False


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


def record_behavioral_user_return_from_payload(payload: dict[str, Any]) -> None:
    """Persist return-to-site on ‎AbandonedCart.cf_behavioral‎ (normal carts only)."""
    if not isinstance(payload, dict):
        return
    if not payload_indicates_user_returned_to_site(payload):
        return
    sid = ""
    raw_sid = payload.get("session_id")
    if isinstance(raw_sid, str) and raw_sid.strip():
        sid = raw_sid.strip()[:512]
    cid_raw = payload.get("cart_id")
    cid = str(cid_raw).strip()[:255] if cid_raw is not None else ""
    if not sid and not cid:
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
    try:
        db.create_all()
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
            db.session.commit()
            return
        if touched:
            db.session.commit()
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
                "[RETURN TO SITE BACKEND PERSISTED] "
                f"store_slug={store_slug_disp} session_id={sid} "
                f"cart_id={cid or '-'} context={last_ctx} return_count={last_rc}"
            )
            print(line, flush=True)
            log.info("%s", line)
            line2 = f"[RECOVERY STOPPED USER RETURNED] session_id={sid} cart_id={cid}"
            print(line2, flush=True)
            log.info("%s", line2)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("behavioral user return: %s", e, exc_info=True)
